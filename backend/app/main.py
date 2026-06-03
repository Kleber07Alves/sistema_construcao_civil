from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, SessionLocal, engine
from .jobs import iniciar_jobs, parar_jobs
from .routers import auth, core, logistico, notificacoes, rh
from .seed import criar_dados_iniciais


@asynccontextmanager
async def lifespan(app: FastAPI):
    
    # ── Startup ──────────────────────────────────────────────────────────
    Base.metadata.create_all(bind=engine)  # TODO: remover após configurar Alembic

    db = SessionLocal()
    try:
        criar_dados_iniciais(db)
    finally:
        db.close()

    iniciar_jobs()

    yield  # aplicação fica aqui enquanto está rodando

    # ── Shutdown ─────────────────────────────────────────────────────────
    parar_jobs()


app = FastAPI(
    title="Sistema de Gestão — Construção Civil",
    description="MVP com Core, Logística, RH, Notificações, ML e NLP.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],   # vem do .env, não hardcoded
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
    return {"status": "ok"}