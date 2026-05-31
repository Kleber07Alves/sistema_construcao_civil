from datetime import date
from enum import Enum

from sqlalchemy import Boolean, Date, Enum as SQLEnum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class PerfilUsuario(str, Enum):
    gestor = "gestor"
    operador = "operador"
    rh = "rh"


class Prioridade(str, Enum):
    alta = "alta"
    media = "media"
    baixa = "baixa"


class StatusPedido(str, Enum):
    pendente = "pendente"
    entregue = "entregue"
    atrasado = "atrasado"


class NivelAlerta(str, Enum):
    vermelho = "vermelho"
    amarelo = "amarelo"
    verde = "verde"


class StatusObra(str, Enum):
    planejada = "planejada"
    em_andamento = "em_andamento"
    concluida = "concluida"
    pausada = "pausada"


class StatusVaga(str, Enum):
    aberta = "aberta"
    pausada = "pausada"
    encerrada = "encerrada"


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    perfil: Mapped[PerfilUsuario] = mapped_column(SQLEnum(PerfilUsuario), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


class Obra(Base):
    __tablename__ = "obras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    endereco: Mapped[str] = mapped_column(String(220), nullable=False)
    status: Mapped[StatusObra] = mapped_column(SQLEnum(StatusObra), default=StatusObra.em_andamento)
    prioridade: Mapped[Prioridade] = mapped_column(SQLEnum(Prioridade), default=Prioridade.media)
    data_inicio: Mapped[date | None] = mapped_column(Date, nullable=True)

    pedidos: Mapped[list["Pedido"]] = relationship(back_populates="obra")


class Fornecedor(Base):
    __tablename__ = "fornecedores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    contato: Mapped[str] = mapped_column(String(160), nullable=False)
    media_atraso_dias: Mapped[float] = mapped_column(Float, default=0.0)
    taxa_atraso: Mapped[float] = mapped_column(Float, default=0.0)
    total_pedidos: Mapped[int] = mapped_column(Integer, default=0)
    desvio_atraso_dias: Mapped[float] = mapped_column(Float, default=0.0)
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)

    pedidos: Mapped[list["Pedido"]] = relationship(back_populates="fornecedor")
    historicos: Mapped[list["HistoricoEntrega"]] = relationship(back_populates="fornecedor")


class HistoricoEntrega(Base):
    __tablename__ = "historico_entregas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    fornecedor_id: Mapped[int] = mapped_column(ForeignKey("fornecedores.id"), nullable=False)
    dias_atraso: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo_insumo: Mapped[str] = mapped_column(String(100), nullable=False)
    mes_referencia: Mapped[date] = mapped_column(Date, nullable=False)

    fornecedor: Mapped[Fornecedor] = relationship(back_populates="historicos")


class Pedido(Base):
    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    data_pedido: Mapped[date] = mapped_column(Date, nullable=False)
    data_prevista: Mapped[date] = mapped_column(Date, nullable=False)
    data_real_entrega: Mapped[date | None] = mapped_column(Date, nullable=True)
    tipo_insumo: Mapped[str] = mapped_column(String(100), nullable=False)
    fornecedor_id: Mapped[int] = mapped_column(ForeignKey("fornecedores.id"), nullable=False)
    obra_id: Mapped[int] = mapped_column(ForeignKey("obras.id"), nullable=False)
    prioridade: Mapped[Prioridade] = mapped_column(SQLEnum(Prioridade), default=Prioridade.media)
    status: Mapped[StatusPedido] = mapped_column(SQLEnum(StatusPedido), default=StatusPedido.pendente)
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    prob_atraso: Mapped[float] = mapped_column(Float, default=0.0)
    nivel_alerta: Mapped[NivelAlerta] = mapped_column(SQLEnum(NivelAlerta), default=NivelAlerta.verde)
    texto_alerta: Mapped[str] = mapped_column(Text, default="")

    fornecedor: Mapped[Fornecedor] = relationship(back_populates="pedidos")
    obra: Mapped[Obra] = relationship(back_populates="pedidos")


class Vaga(Base):
    __tablename__ = "vagas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    titulo: Mapped[str] = mapped_column(String(160), nullable=False)
    tipo_obra: Mapped[str] = mapped_column(String(120), nullable=False)
    requisitos: Mapped[str] = mapped_column(Text, nullable=False)
    habilidades: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[StatusVaga] = mapped_column(SQLEnum(StatusVaga), default=StatusVaga.aberta)


class Candidato(Base):
    __tablename__ = "candidatos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(180), nullable=False)
    cargo: Mapped[str | None] = mapped_column(String(120), nullable=True)
    experiencia_anos: Mapped[float] = mapped_column(Float, default=0.0)
    habilidades: Mapped[str] = mapped_column(Text, default="")
    curriculo_texto: Mapped[str] = mapped_column(Text, default="")
    resumo: Mapped[str] = mapped_column(Text, default="")
