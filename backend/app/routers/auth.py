import threading
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import autenticar_usuario, criar_token, usuario_atual
from ..database import get_db
from ..models import Usuario
from ..schemas import LoginEntrada, Token, UsuarioSaida

router = APIRouter(prefix="/auth", tags=["Autenticação"])

# =============================================================================
# Rate limiting do login — proteção mínima contra força bruta
# =============================================================================
# O sistema tem URL pública e usuários de demonstração conhecidos, então o
# login precisa de alguma fricção contra tentativas automatizadas.
#
# Estado em memória é suficiente aqui POR DESIGN: o backend roda com
# --workers 1 (ver start.sh — o APScheduler exige processo único). Se um dia
# houver múltiplos workers/instâncias, migrar para um store compartilhado.

MAX_TENTATIVAS = 5
JANELA_SEGUNDOS = 15 * 60  # 15 minutos

_tentativas_falhas: dict[str, list[float]] = defaultdict(list)
# Endpoints sync rodam no threadpool do FastAPI — o lock evita corrida
# entre requisições concorrentes no mesmo dicionário.
_lock = threading.Lock()


def _esta_bloqueado(email: str) -> bool:
    """Remove tentativas fora da janela e verifica se o e-mail está bloqueado."""
    agora = time.monotonic()
    with _lock:
        recentes = [t for t in _tentativas_falhas[email] if agora - t < JANELA_SEGUNDOS]
        _tentativas_falhas[email] = recentes
        return len(recentes) >= MAX_TENTATIVAS


def _registrar_falha(email: str) -> None:
    with _lock:
        _tentativas_falhas[email].append(time.monotonic())


def _limpar_falhas(email: str) -> None:
    """Login correto zera o contador — só tentativas consecutivas bloqueiam."""
    with _lock:
        _tentativas_falhas.pop(email, None)


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/login", response_model=Token)
def login(dados: LoginEntrada, db: Session = Depends(get_db)):
    email = dados.email.lower()

    if _esta_bloqueado(email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Muitas tentativas de login para este e-mail. "
                "Aguarde alguns minutos e tente novamente."
            ),
        )

    usuario = autenticar_usuario(db, dados.email, dados.senha)
    if not usuario:
        _registrar_falha(email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos.",
        )

    _limpar_falhas(email)
    return Token(
        access_token=criar_token(usuario),
        perfil=usuario.perfil,
        nome=usuario.nome,
    )


@router.get("/me", response_model=UsuarioSaida)
def usuario_logado(usuario: Usuario = Depends(usuario_atual)):
    """
    Retorna o usuário autenticado pelo token atual.

    Usado pelo frontend para validar a sessão salva no boot (token expirado
    → 401 → limpa a sessão antes de renderizar) e como endpoint de
    introspecção para integrações.
    """
    return usuario
