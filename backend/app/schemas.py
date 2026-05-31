from datetime import date
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import NivelAlerta, PerfilUsuario, Prioridade, StatusObra, StatusPedido, StatusVaga


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    perfil: PerfilUsuario
    nome: str


class LoginEntrada(BaseModel):
    email: EmailStr
    senha: str


class UsuarioBase(BaseModel):
    nome: str
    email: EmailStr
    perfil: PerfilUsuario
    ativo: bool = True


class UsuarioCriar(UsuarioBase):
    senha: str = Field(min_length=6)


class UsuarioSaida(UsuarioBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ObraBase(BaseModel):
    nome: str
    endereco: str
    status: StatusObra = StatusObra.em_andamento
    prioridade: Prioridade = Prioridade.media
    data_inicio: date | None = None


class ObraCriar(ObraBase):
    pass


class ObraSaida(ObraBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class FornecedorBase(BaseModel):
    nome: str
    contato: str
    observacao: str | None = None


class FornecedorCriar(FornecedorBase):
    pass


class FornecedorSaida(FornecedorBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    media_atraso_dias: float
    taxa_atraso: float
    total_pedidos: int
    desvio_atraso_dias: float


class HistoricoCriar(BaseModel):
    fornecedor_id: int
    dias_atraso: int
    tipo_insumo: str
    mes_referencia: date


class HistoricoSaida(HistoricoCriar):
    model_config = ConfigDict(from_attributes=True)
    id: int


class PedidoBase(BaseModel):
    data_pedido: date
    data_prevista: date
    tipo_insumo: str
    fornecedor_id: int
    obra_id: int
    prioridade: Prioridade = Prioridade.media
    observacao: str | None = None


class PedidoCriar(PedidoBase):
    pass


class PedidoEntregar(BaseModel):
    data_real_entrega: date


class PedidoSaida(PedidoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    data_real_entrega: date | None
    status: StatusPedido
    prob_atraso: float
    nivel_alerta: NivelAlerta
    texto_alerta: str


class AlertaSaida(BaseModel):
    pedido_id: int
    obra: str
    fornecedor: str
    tipo_insumo: str
    prioridade: Prioridade
    data_prevista: date
    prob_atraso: float
    nivel_alerta: NivelAlerta
    texto_alerta: str


class DashboardLogistico(BaseModel):
    total_pedidos_ativos: int
    alertas_vermelhos: int
    alertas_amarelos: int
    alertas_verdes: int
    fornecedores: list[FornecedorSaida]
    alertas: list[AlertaSaida]


class VagaBase(BaseModel):
    titulo: str
    tipo_obra: str
    requisitos: str
    habilidades: str
    status: StatusVaga = StatusVaga.aberta


class VagaCriar(VagaBase):
    pass


class VagaSaida(VagaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class CandidatoBase(BaseModel):
    nome: str
    email: EmailStr
    cargo: str | None = None
    experiencia_anos: float = 0.0
    habilidades: str = ""
    curriculo_texto: str = ""


class CandidatoCriar(CandidatoBase):
    pass


class CandidatoSaida(CandidatoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    resumo: str


class RankingCandidato(BaseModel):
    candidato: CandidatoSaida
    score: float
    motivos: list[str]


class EmailAlerta(BaseModel):
    assunto: str
    destinatario: str
    corpo: str
