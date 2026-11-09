"""indices_consultas_frequentes

Adiciona índices para os filtros e joins mais frequentes da API:

  • pedidos.status / pedidos.nivel_alerta — filtros de GET /pedidos,
    /alertas e do dashboard
  • pedidos.obra_id / pedidos.fornecedor_id — FKs (Postgres não indexa
    FKs automaticamente)
  • historico_entregas.fornecedor_id — agregação diária de estatísticas
    por fornecedor (pipeline Pandas)

Espelha o index=True adicionado em app/models/logistico.py — manter os
dois sincronizados para o autogenerate não recriar estes índices.

Revision ID: c4d8e2f1a5b9
Revises: adc70d0a3759
Create Date: 2026-07-08

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d8e2f1a5b9"
down_revision: Union[str, None] = "adc70d0a3759"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(op.f("ix_pedidos_status"), "pedidos", ["status"])
    op.create_index(op.f("ix_pedidos_nivel_alerta"), "pedidos", ["nivel_alerta"])
    op.create_index(op.f("ix_pedidos_obra_id"), "pedidos", ["obra_id"])
    op.create_index(op.f("ix_pedidos_fornecedor_id"), "pedidos", ["fornecedor_id"])
    op.create_index(
        op.f("ix_historico_entregas_fornecedor_id"),
        "historico_entregas",
        ["fornecedor_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_historico_entregas_fornecedor_id"), table_name="historico_entregas"
    )
    op.drop_index(op.f("ix_pedidos_fornecedor_id"), table_name="pedidos")
    op.drop_index(op.f("ix_pedidos_obra_id"), table_name="pedidos")
    op.drop_index(op.f("ix_pedidos_nivel_alerta"), table_name="pedidos")
    op.drop_index(op.f("ix_pedidos_status"), table_name="pedidos")
