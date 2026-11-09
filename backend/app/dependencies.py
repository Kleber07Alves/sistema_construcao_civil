"""
Dependencies reutilizáveis do FastAPI.

Centraliza parâmetros compartilhados por vários routers — hoje, a paginação
padrão dos endpoints de listagem.
"""
from fastapi import Query


def paginacao(
    skip: int = Query(0, ge=0, description="Quantidade de registros a pular."),
    limit: int = Query(200, ge=1, le=500, description="Máximo de registros retornados."),
) -> dict[str, int]:
    """
    Paginação padrão para endpoints de listagem.

    O default limit=200 é retrocompatível: o frontend atual não envia
    parâmetros de paginação e os dados de demonstração ficam bem abaixo
    desse teto — o comportamento observado não muda. O teto de 500 protege
    a API quando a base real da construtora crescer.
    """
    return {"skip": skip, "limit": limit}
