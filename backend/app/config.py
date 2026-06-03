from __future__ import annotations

import sys
from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Fonte única de configuração da aplicação.

    Ordem de resolução do pydantic-settings (maior prioridade primeiro):
      1. Variáveis de ambiente do sistema operacional / Docker
      2. Arquivo .env na raiz do backend
      3. Valores default declarados aqui

    Em produção: defina tudo via variáveis de ambiente.
    Em desenvolvimento: use o .env.example como ponto de partida.
    Em testes: use .env.test ou sobrescreva via os.environ antes de importar.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,   
        extra="ignore",         
    )

    # ── Banco de dados ──────────────────────────────────────────────────────
    database_url: str = (
        "postgresql+psycopg2://postgres:postgres@localhost:5432/construcao_civil"
    )

    # ── Autenticação JWT ────────────────────────────────────────────────────
    jwt_secret: str = "troque_essa_chave_em_producao"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    
    # Defina ENVIRONMENT=production no Docker de produção.
    environment: Literal["development", "production", "test"] = "development"

    # ── CORS ────────────────────────────────────────────────────────────────
    frontend_url: str = "http://localhost:3000"

    # ── SMTP — todos opcionais; sem SMTP, notificações ficam em modo simulado ──
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "alertas@empresa.com"
    smtp_destinatario_padrao: str = "gestor@empresa.com"

    
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    

    @property
    def smtp_configurado(self) -> bool:
        """True quando as três variáveis mínimas do SMTP estão preenchidas."""
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)

    @property
    def llm_configurado(self) -> bool:
        """True quando a chave da OpenAI está presente."""
        return bool(self.openai_api_key)

    

    @field_validator("access_token_expire_minutes")
    @classmethod
    def validar_expiracao(cls, v: int) -> int:
        if v < 5:
            raise ValueError("access_token_expire_minutes deve ser >= 5.")
        return v

    @model_validator(mode="after")
    def validar_producao(self) -> Settings:
        """
        Em produção, recusa inicializar com configurações inseguras.
        Falha alto (sys.exit) em vez de rodar silenciosamente inseguro.
        """
        if self.environment != "production":
            return self

        inseguro = "troque_essa_chave_em_producao"
        problemas: list[str] = []

        if not self.jwt_secret or self.jwt_secret == inseguro:
            problemas.append("JWT_SECRET não definido ou igual ao valor padrão inseguro.")

        if len(self.jwt_secret) < 32:
            problemas.append(
                f"JWT_SECRET muito curto ({len(self.jwt_secret)} chars). Mínimo: 32."
            )

        if "localhost" in self.database_url or "127.0.0.1" in self.database_url:
            problemas.append(
                "DATABASE_URL aponta para localhost em ambiente de produção."
            )

        if problemas:
            print("\nERRO FATAL — configuração inválida para produção:", file=sys.stderr)
            for p in problemas:
                print(f"  • {p}", file=sys.stderr)
            print(
                "\nDefina as variáveis de ambiente corretas e reinicie.",
                file=sys.stderr,
            )
            sys.exit(1)

        return self


@lru_cache
def get_settings() -> Settings:
    """
    Retorna a instância singleton de Settings (lida uma única vez).

    Em testes, use antes de importar qualquer módulo da app:
        import os
        os.environ["ENVIRONMENT"] = "test"
        os.environ["DATABASE_URL"] = "sqlite:///./test.db"
        get_settings.cache_clear()   # força releitura
    """
    return Settings()



settings: Settings = get_settings()