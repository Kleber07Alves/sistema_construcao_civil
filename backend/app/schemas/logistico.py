
"""Schemas do domínio Logístico — Fornecedores, Pedidos, Alertas e Dashboard."""
from datetime import date

from pydantic import BaseModel, ConfigDict

from ..models import NivelAlerta, Prioridade, StatusPedido


# =============================================================================
# Fornecedor
# =============================================================================

class FornecedorBase(BaseModel):
    nome:      str
    contato:   str
    observacao:str | None = None


class FornecedorCriar(FornecedorBase):
    pass


class FornecedorSaida(FornecedorBase):
    model_config = ConfigDict(from_attributes=True)
    id:                 int
    media_atraso_dias:  float
    taxa_atraso:        float
    total_pedidos:      int
    desvio_atraso_dias: float


class FornecedorAtualizar(BaseModel):
    """
    Apenas campos editáveis manualmente.
    media_atraso_dias, taxa_atraso, total_pedidos e desvio_atraso_dias
    são gerenciados pelo pipeline ML (APScheduler) e não estão aqui.
    """
    nome:      str | None = None
    contato:   str | None = None
    observacao:str | None = None


# =============================================================================
# Histórico de Entregas
# =============================================================================

class HistoricoCriar(BaseModel):
    fornecedor_id:  int
    dias_atraso:    int
    tipo_insumo:    str
    mes_referencia: date


class HistoricoSaida(HistoricoCriar):
    model_config = ConfigDict(from_attributes=True)
    id: int


# =============================================================================
# Pedido
# =============================================================================

class PedidoBase(BaseModel):
    data_pedido:   date
    data_prevista: date
    tipo_insumo:   str
    fornecedor_id: int
    obra_id:       int
    prioridade:    Prioridade  = Prioridade.media
    observacao:    str | None  = None


class PedidoCriar(PedidoBase):
    pass


class PedidoAtualizar(BaseModel):
    """
    Atualização parcial de pedido — apenas pedidos com status 'pendente'.

    Campos calculados (prob_atraso, nivel_alerta, texto_alerta) e o status
    não são editáveis aqui: são gerenciados pelo pipeline de alertas e pelo
    endpoint de entrega.
    """
    data_pedido:   date | None       = None
    data_prevista: date | None       = None
    tipo_insumo:   str | None        = None
    fornecedor_id: int | None        = None
    obra_id:       int | None        = None
    prioridade:    Prioridade | None = None
    observacao:    str | None        = None


class PedidoEntregar(BaseModel):
    data_real_entrega: date


class PedidoSaida(PedidoBase):
    model_config = ConfigDict(from_attributes=True)
    id:                int
    data_real_entrega: date | None
    status:            StatusPedido
    prob_atraso:       float
    nivel_alerta:      NivelAlerta
    texto_alerta:      str


# =============================================================================
# Alertas e Dashboard
# =============================================================================

class AlertaSaida(BaseModel):
    pedido_id:    int
    obra:         str
    fornecedor:   str
    tipo_insumo:  str
    prioridade:   Prioridade
    data_prevista:date
    prob_atraso:  float
    nivel_alerta: NivelAlerta
    texto_alerta: str


class DashboardLogistico(BaseModel):
    total_pedidos_ativos: int
    alertas_vermelhos:    int
    alertas_amarelos:     int
    alertas_verdes:       int
    fornecedores:         list[FornecedorSaida]
    alertas:              list[AlertaSaida]