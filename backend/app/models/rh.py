# backend/app/models/rh.py
from __future__ import annotations
from enum import Enum

from sqlalchemy import Float
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class StatusVaga(str, Enum):
    aberta    = "aberta"
    pausada   = "pausada"
    encerrada = "encerrada"


class Vaga(Base):
    __tablename__ = "vagas"

    id:          Mapped[int]        = mapped_column(Integer, primary_key=True, index=True)
    titulo:      Mapped[str]        = mapped_column(String(160), nullable=False)
    tipo_obra:   Mapped[str]        = mapped_column(String(120), nullable=False)
    requisitos:  Mapped[str]        = mapped_column(Text, nullable=False)
    habilidades: Mapped[str]        = mapped_column(Text, nullable=False)
    status:      Mapped[StatusVaga] = mapped_column(SQLEnum(StatusVaga), default=StatusVaga.aberta)


class Candidato(Base):
    __tablename__ = "candidatos"

    id:               Mapped[int]        = mapped_column(Integer, primary_key=True, index=True)
    nome:             Mapped[str]        = mapped_column(String(160), nullable=False)
    email:            Mapped[str]        = mapped_column(String(180), nullable=False)
    cargo:            Mapped[str | None] = mapped_column(String(120), nullable=True)
    experiencia_anos: Mapped[float]      = mapped_column(Float, default=0.0)
    habilidades:      Mapped[str]        = mapped_column(Text, default="")
    curriculo_texto:  Mapped[str | None] = mapped_column(Text, nullable=True)
    resumo:           Mapped[str | None] = mapped_column(Text, nullable=True)