
import logging
import logging.config
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import SessionLocal
from .jobs import iniciar_jobs, parar_jobs
from .routers import auth, core, logistico, notificacoes, rh
from .seed import criar_dados_iniciais

# ── Logging centralizado ──────────────────────────────────────────────────────
logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%dT%H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            }
        },
        "root": {"level": "INFO", "handlers": ["console"]},
        # Silenciar loggers ruidosos de terceiros em produção
        "loggers": {
            "uvicorn.access": {"level": "WARNING"},
            "sqlalchemy.engine": {"level": "WARNING"},
            "apscheduler": {"level": "WARNING"},
        },
    }
)

logger = logging.getLogger(__name__)


# ── Seed isolado com tratamento de falha ───────────────────────────────────────
def _executar_seed() -> None:
    """
    Executa o seed em sessão isolada.

    Falhas são LOGADAS mas não propagadas — o servidor sobe mesmo que o seed
    falhe (ex: tabelas inexistentes num deploy incompleto, spaCy ausente, etc.).
    O health endpoint continuará respondendo; o banco apenas ficará vazio
    até que o seed seja corrigido e o container reiniciado.
    """
    db = SessionLocal()
    try:
        criar_dados_iniciais(db)
    except Exception as exc:
        db.rollback()
        logger.error(
            "Seed falhou — banco pode estar vazio: %s. "
            "Reinicie o container após verificar as migrations e dependências.",
            exc,
            exc_info=True,
        )
    finally:
        db.close()


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────
    logger.info("Iniciando servidor — ambiente: %s", settings.environment)
    _executar_seed()
    iniciar_jobs()
    logger.info("Servidor pronto.")

    yield  # aplicação fica aqui enquanto está rodando

    # ── Shutdown ──────────────────────────────────────────────────────────
    logger.info("Encerrando servidor...")
    parar_jobs()


# ── Aplicação ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Sistema de Gestão — Construção Civil",
    description="MVP com Core, Logística, RH, Notificações, ML e NLP.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(core.router)
app.include_router(logistico.router)
app.include_router(rh.router)
app.include_router(notificacoes.router)


@app.get("/health", tags=["Saúde"])
def health() -> dict[str, str]:
    """Endpoint de healthcheck para Docker e balanceadores de carga."""
    return {"status": "ok"}