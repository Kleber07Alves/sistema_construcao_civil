from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..auth import exigir_perfis, usuario_atual
from ..database import get_db
from ..models import Candidato, PerfilUsuario, Usuario, Vaga
from ..schemas import CandidatoCriar, CandidatoSaida, RankingCandidato, VagaCriar, VagaSaida
from ..services.rh_nlp import calcular_score, extrair_texto_pdf, processar_curriculo

router = APIRouter(prefix="/rh", tags=["Módulo de RH"])


@router.get("/vagas", response_model=list[VagaSaida])
def listar_vagas(db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return db.query(Vaga).order_by(Vaga.id).all()


@router.post("/vagas", response_model=VagaSaida)
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


@router.get("/candidatos", response_model=list[CandidatoSaida])
def listar_candidatos(db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return db.query(Candidato).order_by(Candidato.id).all()


@router.post("/candidatos", response_model=CandidatoSaida)
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


@router.post("/candidatos/upload", response_model=CandidatoSaida)
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
    texto = extrair_texto_pdf(conteudo)
    if not texto:
        raise HTTPException(status_code=400, detail="Não foi possível extrair texto do PDF.")

    dados = processar_curriculo(nome, texto)
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


@router.get("/vagas/{vaga_id}/ranking", response_model=list[RankingCandidato])
def ranking_vaga(vaga_id: int, db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    vaga = db.get(Vaga, vaga_id)
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada.")

    candidatos = db.query(Candidato).all()
    ranking = []
    for candidato in candidatos:
        score, motivos = calcular_score(
            vaga_habilidades=vaga.habilidades,
            vaga_requisitos=vaga.requisitos,
            candidato_habilidades=candidato.habilidades,
            experiencia_anos=candidato.experiencia_anos,
        )
        ranking.append(RankingCandidato(candidato=candidato, score=score, motivos=motivos))

    return sorted(ranking, key=lambda item: item.score, reverse=True)
