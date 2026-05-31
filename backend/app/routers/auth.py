from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import autenticar_usuario, criar_token
from ..database import get_db
from ..schemas import LoginEntrada, Token

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/login", response_model=Token)
def login(dados: LoginEntrada, db: Session = Depends(get_db)):
    usuario = autenticar_usuario(db, dados.email, dados.senha)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos.",
        )
    return Token(
        access_token=criar_token(usuario),
        perfil=usuario.perfil,
        nome=usuario.nome,
    )
