import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
from .models import PerfilUsuario, Usuario

ALGORITHM = "HS256"


security = HTTPBearer()


def criar_hash_senha(senha: str) -> str:
    """Cria hash de senha sem dependência externa de bcrypt.

    O formato salvo é: pbkdf2_sha256$iteracoes$salt$hash.
    Essa escolha evita o erro comum do passlib/bcrypt em ambientes Docker recentes.
    """
    salt = secrets.token_hex(16)
    iteracoes = 120_000
    hash_bytes = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt.encode("utf-8"), iteracoes)
    return f"pbkdf2_sha256${iteracoes}${salt}${hash_bytes.hex()}"


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        algoritmo, iteracoes_txt, salt, hash_salvo = senha_hash.split("$", 3)
        if algoritmo != "pbkdf2_sha256":
            return False
        iteracoes = int(iteracoes_txt)
        hash_bytes = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt.encode("utf-8"), iteracoes)
        return hmac.compare_digest(hash_bytes.hex(), hash_salvo)
    except Exception:
        return False


def criar_token(usuario: Usuario) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    ...
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def autenticar_usuario(db: Session, email: str, senha: str) -> Usuario | None:
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario or not usuario.ativo:
        return None
    if not verificar_senha(senha, usuario.senha_hash):
        return None
    return usuario


def usuario_atual(
    credenciais: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Usuario:
    erro = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado.",
    )
    try:
        payload = jwt.decode(credenciais.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        email = payload.get("sub")
        if not email:
            raise erro
    except JWTError as exc:
        raise erro from exc

    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario or not usuario.ativo:
        raise erro
    return usuario


def exigir_perfis(*perfis: PerfilUsuario):
    def regra(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
        if usuario.perfil not in perfis:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuário sem permissão para esta ação.",
            )
        return usuario

    return regra
