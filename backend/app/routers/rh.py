# backend/app/routers/rh.py
"""
Router do Módulo de RH — Vagas e Candidatos.

CRUD completo adicionado nesta versão:
  Vagas:      PUT /{id} (atualização parcial), DELETE /{id} (hard-delete)
  Candidatos: DELETE /{id} (hard-delete)
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from ..auth import exigir_perfis, usuario_atual
from ..database import get_db
from ..dependencies import paginacao
from ..models import Candidato, PerfilUsuario, Usuario, Vaga
from ..schemas import (
    CandidatoCriar,
    CandidatoSaida,
    RankingCandidato,
    VagaAtualizar,
    VagaCriar,
    VagaSaida,
)
from ..services.rh_nlp import calcular_score, extrair_texto_pdf, processar_curriculo

router = APIRouter(prefix="/rh", tags=["Módulo de RH"])

# Limite de upload de currículo — evita esgotar a memória do container
# (o arquivo inteiro é lido em memória para o PyMuPDF processar).
TAMANHO_MAX_CURRICULO = 5 * 1024 * 1024  # 5 MB


# =============================================================================
# Vagas
# =============================================================================

@router.get("/vagas", response_model=list[VagaSaida])
def listar_vagas(
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
    pag: dict[str, int] = Depends(paginacao),
):
    return (
        db.query(Vaga)
        .order_by(Vaga.id)
        .offset(pag["skip"])
        .limit(pag["limit"])
        .all()
    )


@router.post("/vagas", response_model=VagaSaida, status_code=201)
def criar_vaga(
    dados: VagaCriar,
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor, PerfilUsuario.rh)),
):
    vaga = Vaga(**dados.model_dump())
    db.add(vaga)
    db.commit()
    db.refresh(vaga)
    return vaga


@router.put("/vagas/{vaga_id}", response_model=VagaSaida)
def atualizar_vaga(
    vaga_id: int,
    dados: VagaAtualizar,
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor, PerfilUsuario.rh)),
):
    """
    Atualização parcial de vaga.

    Uso principal: mudar o status do ciclo de vida da vaga:
      {"status": "pausada"}    — suspende temporariamente
      {"status": "encerrada"}  — fecha definitivamente (mantém histórico)

    Para remover o registro fisicamente, use DELETE após encerrar.
    """
    vaga = db.get(Vaga, vaga_id)
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada.")

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(vaga, campo, valor)

    db.commit()
    db.refresh(vaga)
    return vaga


@router.delete("/vagas/{vaga_id}", status_code=204)
def excluir_vaga(
    vaga_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor, PerfilUsuario.rh)),
) -> Response:
    """
    Hard-delete de vaga.

    Seguro para exclusão física: Vaga não possui FK de entrada (nenhuma outra
    tabela referencia vagas.id), portanto não há risco de violação de constraint.

    Fluxo recomendado antes de excluir:
      1. PUT /vagas/{id} com {"status": "encerrada"}
      2. DELETE /vagas/{id}  ← este endpoint
    """
    vaga = db.get(Vaga, vaga_id)
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada.")

    db.delete(vaga)
    db.commit()
    return Response(status_code=204)


# =============================================================================
# Candidatos
# =============================================================================

@router.get("/candidatos", response_model=list[CandidatoSaida])
def listar_candidatos(
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
    pag: dict[str, int] = Depends(paginacao),
):
    return (
        db.query(Candidato)
        .order_by(Candidato.id)
        .offset(pag["skip"])
        .limit(pag["limit"])
        .all()
    )


@router.post("/candidatos", response_model=CandidatoSaida, status_code=201)
def criar_candidato(
    dados: CandidatoCriar,
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor, PerfilUsuario.rh)),
):
    processado = processar_curriculo(dados.nome, dados.curriculo_texto or dados.habilidades)
    candidato = Candidato(
        nome=dados.nome,
        email=dados.email,
        cargo=dados.cargo or processado.cargo,
        experiencia_anos=dados.experiencia_anos or processado.experiencia_anos,
        habilidades=dados.habilidades or ", ".join(processado.habilidades),
        curriculo_texto=dados.curriculo_texto,
        resumo=processado.resumo,
    )
    db.add(candidato)
    db.commit()
    db.refresh(candidato)
    return candidato


@router.post("/candidatos/upload", response_model=CandidatoSaida, status_code=201)
async def upload_curriculo(
    nome: str = Form(...),
    email: str = Form(...),
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor, PerfilUsuario.rh)),
):
    if not arquivo.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Envie um currículo em PDF.")

    conteudo = await arquivo.read()
    if len(conteudo) > TAMANHO_MAX_CURRICULO:
        raise HTTPException(
            status_code=413,
            detail="Arquivo muito grande. O limite para currículos é 5 MB.",
        )

    # PyMuPDF e spaCy são CPU-bound: rodar fora do event loop para não
    # congelar as demais requisições durante o processamento.
    texto = await asyncio.to_thread(extrair_texto_pdf, conteudo)
    if not texto:
        raise HTTPException(status_code=400, detail="Não foi possível extrair texto do PDF.")

    dados = await asyncio.to_thread(processar_curriculo, nome, texto)
    candidato = Candidato(
        nome=nome,
        email=email,
        cargo=dados.cargo,
        experiencia_anos=dados.experiencia_anos,
        habilidades=", ".join(dados.habilidades),
        curriculo_texto=texto,
        resumo=dados.resumo,
    )
    db.add(candidato)
    db.commit()
    db.refresh(candidato)
    return candidato


@router.delete("/candidatos/{candidato_id}", status_code=204)
def excluir_candidato(
    candidato_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor, PerfilUsuario.rh)),
) -> Response:
    """
    Hard-delete de candidato.

    Seguro para exclusão física: Candidato não possui FK de entrada
    (nenhuma tabela referencia candidatos.id).

    Obs: a exclusão remove permanentemente o currículo e resumo do
    candidato. Considere usar o módulo de arquivo se precisar manter
    histórico de processos seletivos anteriores.
    """
    candidato = db.get(Candidato, candidato_id)
    if not candidato:
        raise HTTPException(status_code=404, detail="Candidato não encontrado.")

    db.delete(candidato)
    db.commit()
    return Response(status_code=204)


# =============================================================================
# Ranking e busca avançada
# =============================================================================

@router.get("/vagas/{vaga_id}/ranking", response_model=list[RankingCandidato])
def ranking_vaga(
    vaga_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
):
    vaga = db.get(Vaga, vaga_id)
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada.")

    candidatos = db.query(Candidato).all()
    ranking = [
        RankingCandidato(
            candidato=candidato,
            score=score,
            motivos=motivos,
        )
        for candidato in candidatos
        for score, motivos in [
            calcular_score(
                vaga_habilidades=vaga.habilidades,
                vaga_requisitos=vaga.requisitos,
                candidato_habilidades=candidato.habilidades,
                experiencia_anos=candidato.experiencia_anos,
            )
        ]
    ]
    return sorted(ranking, key=lambda item: item.score, reverse=True)
