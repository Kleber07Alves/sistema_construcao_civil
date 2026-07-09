"""
Handlers globais de exceção.

Sem estes handlers, erros de banco (ex.: violação de FK/unique) e falhas
inesperadas viram HTTP 500 com stacktrace exposto na resposta — inaceitável
em produção. Aqui cada categoria vira uma resposta JSON limpa e o detalhe
técnico fica apenas no log do servidor.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


def registrar_handlers(app: FastAPI) -> None:
    """Registra os handlers na aplicação — chamado uma única vez no main.py."""

    @app.exception_handler(IntegrityError)
    async def tratar_integridade(request: Request, exc: IntegrityError) -> JSONResponse:
        # Violação de constraint (unique, FK, not-null) que escapou das
        # validações explícitas dos routers.
        logger.warning(
            "Violação de integridade em %s %s: %s",
            request.method,
            request.url.path,
            exc.orig,
        )
        return JSONResponse(
            status_code=409,
            content={
                "detail": (
                    "Operação viola restrições de integridade dos dados "
                    "(registro duplicado ou referência inexistente)."
                )
            },
        )

    @app.exception_handler(Exception)
    async def tratar_erro_generico(request: Request, exc: Exception) -> JSONResponse:
        # Último recurso: loga o stacktrace completo no servidor e devolve
        # uma mensagem genérica — nunca vazar detalhes internos na resposta.
        logger.exception("Erro não tratado em %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Erro interno. Tente novamente."},
        )
