from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import criar_hash_senha, exigir_perfis, usuario_atual
from ..database import get_db
from ..models import Obra, PerfilUsuario, Usuario
from ..schemas import ObraCriar, ObraSaida, UsuarioCriar, UsuarioSaida

router = APIRouter(prefix="/core", tags=["Core — Gestão"])


@router.get("/usuarios", response_model=list[UsuarioSaida])
def listar_usuarios(
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor)),
):
    return db.query(Usuario).order_by(Usuario.id).all()


@router.post("/usuarios", response_model=UsuarioSaida)
def criar_usuario(
    dados: UsuarioCriar,
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor)),
):
    existente = db.query(Usuario).filter(Usuario.email == dados.email).first()
    if existente:
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


@router.get("/obras", response_model=list[ObraSaida])
def listar_obras(
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
):
    return db.query(Obra).order_by(Obra.id).all()


@router.post("/obras", response_model=ObraSaida)
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
