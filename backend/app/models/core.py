
from __future__ import annotations
from datetime import date
from enum import Enum

from sqlalchemy import Boolean, Date
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class PerfilUsuario(str, Enum):
    gestor   = "gestor"
    operador = "operador"
    rh       = "rh"


class Prioridade(str, Enum):
    """Usada em Obra e Pedido — definida aqui para evitar dependência circular."""
    alta  = "alta"
    media = "media"
    baixa = "baixa"


class StatusObra(str, Enum):
    planejada    = "planejada"
    em_andamento = "em_andamento"
    concluida    = "concluida"
    pausada      = "pausada"


class Usuario(Base):
    __tablename__ = "usuarios"

    id:         Mapped[int]           = mapped_column(Integer, primary_key=True, index=True)
    nome:       Mapped[str]           = mapped_column(String(120), nullable=False)
    email:      Mapped[str]           = mapped_column(String(180), unique=True, index=True, nullable=False)
    senha_hash: Mapped[str]           = mapped_column(String(255), nullable=False)
    perfil:     Mapped[PerfilUsuario] = mapped_column(SQLEnum(PerfilUsuario), nullable=False)
    ativo:      Mapped[bool]          = mapped_column(Boolean, default=True)


class Obra(Base):
    __tablename__ = "obras"

    id:          Mapped[int]         = mapped_column(Integer, primary_key=True, index=True)
    nome:        Mapped[str]         = mapped_column(String(160), nullable=False)
    endereco:    Mapped[str]         = mapped_column(String(220), nullable=False)
    status:      Mapped[StatusObra]  = mapped_column(SQLEnum(StatusObra), default=StatusObra.em_andamento)
    prioridade:  Mapped[Prioridade]  = mapped_column(SQLEnum(Prioridade), default=Prioridade.media)
    data_inicio: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Forward ref: "Pedido" resolvido em tempo de execução via __future__.annotations
    pedidos: Mapped[list[Pedido]] = relationship("Pedido", back_populates="obra")