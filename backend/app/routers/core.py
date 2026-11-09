# backend/app/routers/core.py
"""
Router do módulo Core — Gestão de Usuários e Obras.

CRUD completo adicionado nesta versão:
  Usuários: GET /{id}, PUT /{id}, DELETE /{id} (soft-delete via ativo=False)
  Obras:    GET /{id}, PUT /{id}, DELETE /{id} (guard contra pedidos associados)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ..auth import criar_hash_senha, exigir_perfis, usuario_atual
from ..database import get_db
from ..dependencies import paginacao
from ..models import Obra, PerfilUsuario, Usuario
from ..schemas import (
    ObraAtualizar,
    ObraCriar,
    ObraSaida,
    UsuarioAtualizar,
    UsuarioCriar,
    UsuarioSaida,
)

router = APIRouter(prefix="/core", tags=["Core — Gestão"])


# =============================================================================
# Usuários
# =============================================================================

@router.get("/usuarios", response_model=list[UsuarioSaida])
def listar_usuarios(
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor)),
    pag: dict[str, int] = Depends(paginacao),
):
    return (
        db.query(Usuario)
        .order_by(Usuario.id)
        .offset(pag["skip"])
        .limit(pag["limit"])
        .all()
    )


@router.post("/usuarios", response_model=UsuarioSaida, status_code=201)
def criar_usuario(
    dados: UsuarioCriar,
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor)),
):
    if db.query(Usuario).filter(Usuario.email == dados.email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado.")

    usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        perfil=dados.perfil,
        ativo=dados.ativo,
        senha_hash=criar_hash_senha(dados.senha),
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.get("/usuarios/{usuario_id}", response_model=UsuarioSaida)
def obter_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor)),
):
    usuario = db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return usuario


@router.put("/usuarios/{usuario_id}", response_model=UsuarioSaida)
def atualizar_usuario(
    usuario_id: int,
    dados: UsuarioAtualizar,
    db: Session = Depends(get_db),
    usuario_logado: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor)),
):
    """
    Atualização parcial de usuário.

    Regras especiais:
      • senha  — se presente no body, é hasheada antes de persistir; nunca
                 exposta na resposta (ausente em UsuarioSaida)
      • email  — verificado contra duplicatas de outros usuários
      • ativo  — pode ser True (reativar) ou False (desativar preventivamente)
    """
    usuario = db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    update_data = dados.model_dump(exclude_unset=True)

    if not update_data:
        return usuario  # body vazio — nenhuma alteração, retorna estado atual

    # ── Verificação de unicidade do e-mail ────────────────────────────────
    if "email" in update_data:
        duplicado = (
            db.query(Usuario)
            .filter(Usuario.email == update_data["email"], Usuario.id != usuario_id)
            .first()
        )
        if duplicado:
            raise HTTPException(
                status_code=400,
                detail="E-mail já cadastrado por outro usuário.",
            )

    # ── Senha precisa de hashing — tratada antes do loop genérico ─────────
    if "senha" in update_data:
        usuario.senha_hash = criar_hash_senha(update_data.pop("senha"))

    # ── Aplicar os demais campos diretamente no modelo ────────────────────
    for campo, valor in update_data.items():
        setattr(usuario, campo, valor)

    db.commit()
    db.refresh(usuario)
    return usuario


@router.delete("/usuarios/{usuario_id}", status_code=204)
def desativar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    usuario_logado: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor)),
) -> Response:
    """
    Soft-delete: define ativo=False, preserva o registro no banco.

    Por que soft-delete e não hard-delete?
      Usuários podem ter sido criadores de pedidos, obras ou outras entidades
      auditáveis. Removê-los fisicamente quebraria trilhas de auditoria.
      Para reativar, use PUT /usuarios/{id} com {"ativo": true}.

    Restrição: o gestor não pode desativar a própria conta.
    """
    usuario = db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    if usuario.id == usuario_logado.id:
        raise HTTPException(
            status_code=400,
            detail="Você não pode desativar a sua própria conta.",
        )

    if not usuario.ativo:
        raise HTTPException(
            status_code=400,
            detail="Usuário já está inativo.",
        )

    usuario.ativo = False
    db.commit()
    return Response(status_code=204)


# =============================================================================
# Obras
# =============================================================================

@router.get("/obras", response_model=list[ObraSaida])
def listar_obras(
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
    pag: dict[str, int] = Depends(paginacao),
):
    return (
        db.query(Obra)
        .order_by(Obra.id)
        .offset(pag["skip"])
        .limit(pag["limit"])
        .all()
    )


@router.post("/obras", response_model=ObraSaida, status_code=201)
def criar_obra(
    dados: ObraCriar,
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor, PerfilUsuario.operador)),
):
    obra = Obra(**dados.model_dump())
    db.add(obra)
    db.commit()
    db.refresh(obra)
    return obra


@router.get("/obras/{obra_id}", response_model=ObraSaida)
def obter_obra(
    obra_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
):
    obra = db.get(Obra, obra_id)
    if not obra:
        raise HTTPException(status_code=404, detail="Obra não encontrada.")
    return obra


@router.put("/obras/{obra_id}", response_model=ObraSaida)
def atualizar_obra(
    obra_id: int,
    dados: ObraAtualizar,
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor, PerfilUsuario.operador)),
):
    obra = db.get(Obra, obra_id)
    if not obra:
        raise HTTPException(status_code=404, detail="Obra não encontrada.")

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(obra, campo, valor)

    db.commit()
    db.refresh(obra)
    return obra


@router.delete("/obras/{obra_id}", status_code=204)
def excluir_obra(
    obra_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor)),
) -> Response:
    """
    Hard-delete de obra.

    Guarda de integridade: impede exclusão se houver pedidos associados.
    A FK Pedido.obra_id → obras.id sem cascade=DELETE provocaria erro de
    constraint no banco — esta verificação explícita retorna uma mensagem
    clara em vez de um erro 500 genérico.

    Para remover uma obra com pedidos: será necessário encerrar ou migrar os pedidos primeiro.
    """
    obra = db.get(Obra, obra_id)
    if not obra:
        raise HTTPException(status_code=404, detail="Obra não encontrada.")

    pedidos_ativos = [p for p in obra.pedidos if True]  # carrega via relationship
    if pedidos_ativos:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Não é possível excluir '{obra.nome}': "
                f"ela possui {len(pedidos_ativos)} pedido(s) associado(s). "
                "Encerre ou mova os pedidos antes de excluir a obra."
            ),
        )

    db.delete(obra)
    db.commit()
    return Response(status_code=204)
