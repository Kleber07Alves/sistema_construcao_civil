from __future__ import annotations
from datetime import date
from enum import Enum

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .core import Obra, Prioridade


class StatusPedido(str, Enum):
    pendente = "pendente"
    entregue = "entregue"
    atrasado = "atrasado"


class NivelAlerta(str, Enum):
    vermelho = "vermelho"
    amarelo  = "amarelo"
    verde    = "verde"


class Fornecedor(Base):
    __tablename__ = "fornecedores"

    id:                 Mapped[int]        = mapped_column(Integer, primary_key=True, index=True)
    nome:               Mapped[str]        = mapped_column(String(160), nullable=False)
    contato:            Mapped[str]        = mapped_column(String(180), nullable=False)
    media_atraso_dias:  Mapped[float]      = mapped_column(Float, default=0.0)
    taxa_atraso:        Mapped[float]      = mapped_column(Float, default=0.0)
    total_pedidos:      Mapped[int]        = mapped_column(Integer, default=0)
    desvio_atraso_dias: Mapped[float]      = mapped_column(Float, default=0.0)
    observacao:         Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relacionamentos ────────────────────────────────────────────────────
    historicos: Mapped[list[HistoricoEntrega]] = relationship(
        "HistoricoEntrega", back_populates="fornecedor"
    )
    
    pedidos: Mapped[list[Pedido]] = relationship(
        "Pedido", back_populates="fornecedor"
    )


class HistoricoEntrega(Base):
    __tablename__ = "historico_entregas"

    id:             Mapped[int]  = mapped_column(Integer, primary_key=True, index=True)
    # index=True: Postgres NÃO indexa FKs automaticamente — este é o join/filtro
    # mais frequente do pipeline de estatísticas (agregação por fornecedor).
    fornecedor_id:  Mapped[int]  = mapped_column(ForeignKey("fornecedores.id"), nullable=False, index=True)
    dias_atraso:    Mapped[int]  = mapped_column(Integer, nullable=False)
    tipo_insumo:    Mapped[str]  = mapped_column(String(100), nullable=False)
    mes_referencia: Mapped[date] = mapped_column(Date, nullable=False)

    fornecedor: Mapped[Fornecedor] = relationship("Fornecedor", back_populates="historicos")


class Pedido(Base):
    __tablename__ = "pedidos"

    id:                Mapped[int]          = mapped_column(Integer, primary_key=True, index=True)
    data_pedido:       Mapped[date]         = mapped_column(Date, nullable=False)
    data_prevista:     Mapped[date]         = mapped_column(Date, nullable=False)
    data_real_entrega: Mapped[date | None]  = mapped_column(Date, nullable=True)
    tipo_insumo:       Mapped[str]          = mapped_column(String(100), nullable=False)
    # index=True nas FKs e nos campos de filtro: Postgres não indexa FKs
    # automaticamente, e status/nivel_alerta são os filtros mais usados
    # em GET /pedidos, alertas e dashboard.
    fornecedor_id:     Mapped[int]          = mapped_column(ForeignKey("fornecedores.id"), nullable=False, index=True)
    obra_id:           Mapped[int]          = mapped_column(ForeignKey("obras.id"), nullable=False, index=True)
    prioridade:        Mapped[Prioridade]   = mapped_column(SQLEnum(Prioridade), default=Prioridade.media)
    status:            Mapped[StatusPedido] = mapped_column(SQLEnum(StatusPedido), default=StatusPedido.pendente, index=True)
    observacao:        Mapped[str | None]   = mapped_column(Text, nullable=True)
    prob_atraso:       Mapped[float]        = mapped_column(Float, default=0.0)
    nivel_alerta:      Mapped[NivelAlerta]  = mapped_column(SQLEnum(NivelAlerta), default=NivelAlerta.verde, index=True)
    texto_alerta:      Mapped[str]          = mapped_column(String(255), default="")

    # ── Relacionamentos ────────────────────────────────────────────────────
    obra: Mapped[Obra] = relationship("Obra", back_populates="pedidos")

    
    fornecedor: Mapped[Fornecedor] = relationship("Fornecedor", back_populates="pedidos")