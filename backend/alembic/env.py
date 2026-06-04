# Este arquivo é executado toda vez que um comando alembic roda.
#   1. Conectar ao banco via settings.database_url (nunca hardcoded)
#   2. Expor Base.metadata para o --autogenerate detectar os modelos
#   3. Suportar modo offline (gera SQL) e online (aplica direto no banco)

from __future__ import annotations

import logging
from logging.config import fileConfig

from sqlalchemy import Connection

from alembic import context

# ── 1. Importar configurações centralizadas ───────────────────────────────
from app.config import settings
from app.database import Base, engine

# ── 2. Importar TODOS os modelos para popular Base.metadata ──────────────

import app.models  # noqa: F401 — importado pelo efeito colateral de registro

# ── 3. Configuração do Alembic ────────────────────────────────────────────
config = context.config

# Configura o logging definido no [loggers] do alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

# ── 4. Injetar a URL em runtime ───────────────────────────────────────────

config.set_main_option("sqlalchemy.url", settings.database_url)

logger.info("Alembic usando banco: %s", settings.database_url.split("@")[-1])

# ── 5. Metadata alvo para autogenerate ───────────────────────────────────

target_metadata = Base.metadata


# =============================================================================
# Modo OFFLINE — gera um script SQL sem conectar ao banco
# =============================================================================

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Detecta mudanças de tipo de coluna (ex: String(100) → String(200))
        compare_type=True,
        # Detecta mudanças em valores default definidos no banco
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# =============================================================================
# Modo ONLINE — conecta ao banco e aplica as migrations diretamente
# =============================================================================

def run_migrations_online() -> None:
    with engine.connect() as connection:
        _configure_and_run(connection)


def _configure_and_run(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Detecta mudanças de tipo de coluna
        compare_type=True,
        # Detecta mudanças em valores default do banco
        compare_server_default=True,
        # Nomeia constraints geradas automaticamente (ForeignKey, Index, etc.)
        # Essencial para que futuras migrations possam fazer DROP CONSTRAINT
        # pelo nome, sem ambiguidade.
        render_as_batch=False,  # False para PostgreSQL; True apenas para SQLite
    )

    with context.begin_transaction():
        context.run_migrations()


# =============================================================================
# Entry point — Alembic escolhe o modo automaticamente
# =============================================================================
if context.is_offline_mode():
    logger.info("Executando migrations em modo OFFLINE (SQL script)")
    run_migrations_offline()
else:
    logger.info("Executando migrations em modo ONLINE (conexão direta)")
    run_migrations_online()
