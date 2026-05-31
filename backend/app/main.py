from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, SessionLocal, engine
from .jobs import iniciar_jobs, parar_jobs
from .routers import auth, core, logistico, notificacoes, rh
from .seed import criar_dados_iniciais

app = FastAPI(
    title="Sistema de Gestão — Construção Civil",
    description="MVP com Core, Logística, RH, Notificações, ML e NLP.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(core.router)
app.include_router(logistico.router)
app.include_router(rh.router)
app.include_router(notificacoes.router)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        criar_dados_iniciais(db)
    finally:
        db.close()
    iniciar_jobs()


@app.on_event("shutdown")
def shutdown() -> None:
    parar_jobs()


@app.get("/health", tags=["Saúde"])
def health() -> dict[str, str]:
    return {"status": "ok"}
