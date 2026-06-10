"""
conftest.py — Fixtures de teste 

Estratégia:
  • DATABASE_URL é sobrescrito para SQLite (arquivo temporário) ANTES de
    qualquer importação de app.*. Isso força o engine em database.py a usar
    SQLite em vez de PostgreSQL, tornando os testes autônomos (sem Docker).
  • O TestClient é de escopo "session": o lifespan (criar_dados_iniciais +
    APScheduler) executa uma única vez, semeando o banco com dados demo.
  • `headers` (session-scoped) faz login uma vez com o gestor e reusa o
    token em todos os testes — evita N chamadas de autenticação.
"""
from __future__ import annotations

import os
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# Estas variáveis de ambiente devem ser definidas antes de qualquer
# importação de módulos do app, pois settings e engine são criados no momento
# da importação (module-level). pydantic-settings prioriza os.environ sobre
# o .env, portanto estes valores sobrescrevem o arquivo .env existente.
# ──────────────────────────────────────────────────────────────────────────────
_DB_FILE = Path(__file__).parent.parent / "test_construcao.db"

# Limpa banco de teste anterior (garante estado fresh entre execuções)
if _DB_FILE.exists():
    _DB_FILE.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{_DB_FILE}"
os.environ["ENVIRONMENT"]  = "test"
os.environ["JWT_SECRET"]   = "test_jwt_secret_key_for_pytest_only"

# ── Importações do app (após setar os env vars) ────────────────────────────
import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine  # engine já aponta para SQLite
from app.main import app


# =============================================================================
# Fixtures de escopo de sessão
# =============================================================================

@pytest.fixture(scope="session")
def client():
    """
    Cria o TestClient uma única vez por sessão de testes.

    Sequência:
      1. Base.metadata.create_all — cria as tabelas no SQLite
      2. TestClient(app).__enter__ — dispara o lifespan:
           • criar_dados_iniciais() semeia gestor, obras, fornecedores, pedidos…
           • iniciar_jobs() inicia o APScheduler (cron às 7h, não dispara em testes)
      3. yield — testes rodam
      4. TestClient.__exit__ — para o APScheduler via parar_jobs()
      5. Base.metadata.drop_all — remove as tabelas
      6. DB file é removido no finalizer
    """
    Base.metadata.create_all(bind=engine)

    with TestClient(app) as c:
        yield c

    Base.metadata.drop_all(bind=engine)
    if _DB_FILE.exists():
        _DB_FILE.unlink()


@pytest.fixture(scope="session")
def headers(client: TestClient) -> dict[str, str]:
    """
    Autentica como gestor (seeded pelo criar_dados_iniciais) e retorna
    o header Authorization Bearer para reuso em todos os testes.
    """
    r = client.post(
        "/auth/login",
        json={"email": "gestor@empresa.com", "senha": "123456"},
    )
    assert r.status_code == 200, (
        f"Login do gestor falhou ({r.status_code}): {r.text}\n"
        "Verifique se criar_dados_iniciais() semeou corretamente."
    )
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}