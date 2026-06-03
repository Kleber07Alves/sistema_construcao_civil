from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


def _engine_kwargs() -> dict:
    """
    Retorna os kwargs do SQLAlchemy engine adequados para cada cenário.

    A decisão é feita sobre o URL, não sobre a variável de ambiente,
    porque em testes podemos usar SQLite independente do ENVIRONMENT.
    """
    url = settings.database_url

    # SQLite (usado em testes com banco em memória ou arquivo temporário)
    if url.startswith("sqlite"):
        return {
            "connect_args": {"check_same_thread": False},
            # SQLite não suporta pool de conexões real
        }

    if settings.environment == "production":
        return {
            "pool_pre_ping": True,    # verifica conexões mortas antes de usar
            "pool_size": 10,           # conexões permanentes no pool
            "max_overflow": 20,        # conexões extras permitidas sob carga
            "pool_timeout": 30,        # segundos para aguardar conexão disponível
            "pool_recycle": 1800,      # recicla conexões a cada 30 min (evita timeout do Postgres)
        }

    
    return {"pool_pre_ping": True}


engine = create_engine(settings.database_url, **_engine_kwargs())

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """
    Dependency FastAPI — fornece uma sessão de banco por request.
    A sessão é fechada automaticamente ao fim do request, com ou sem erro.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()