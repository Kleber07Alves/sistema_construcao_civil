"""
Pacote de schemas — re-exporta todos os símbolos dos submódulos de domínio.

OBJETIVO: zero alteração nos arquivos consumidores.
"""

# ── Auth ─────────────────────────────────────────────────────────────────────
from .auth import (
    LoginEntrada,
    Token,
)

# ── Core ─────────────────────────────────────────────────────────────────────
from .core import (
    ObraAtualizar,
    ObraBase,
    ObraCriar,
    ObraSaida,
    UsuarioAtualizar,
    UsuarioBase,
    UsuarioCriar,
    UsuarioSaida,
)

# ── Logístico ────────────────────────────────────────────────────────────────
from .logistico import (
    AlertaSaida,
    DashboardLogistico,
    FornecedorAtualizar,
    FornecedorBase,
    FornecedorCriar,
    FornecedorSaida,
    HistoricoCriar,
    HistoricoSaida,
    PedidoAtualizar,
    PedidoBase,
    PedidoCriar,
    PedidoEntregar,
    PedidoSaida,
)

# ── RH ───────────────────────────────────────────────────────────────────────
from .rh import (
    CandidatoBase,
    CandidatoCriar,
    CandidatoSaida,
    RankingCandidato,
    VagaAtualizar,
    VagaBase,
    VagaCriar,
    VagaSaida,
)

# ── Notificações ─────────────────────────────────────────────────────────────
from .notificacoes import (
    EmailAlerta,
)

__all__ = [
    # auth
    "LoginEntrada", "Token",
    # core
    "UsuarioBase", "UsuarioCriar", "UsuarioSaida", "UsuarioAtualizar",
    "ObraBase", "ObraCriar", "ObraSaida", "ObraAtualizar",
    # logistico
    "FornecedorBase", "FornecedorCriar", "FornecedorSaida", "FornecedorAtualizar",
    "HistoricoCriar", "HistoricoSaida",
    "PedidoBase", "PedidoCriar", "PedidoSaida", "PedidoEntregar", "PedidoAtualizar",
    "AlertaSaida", "DashboardLogistico",
    # rh
    "VagaBase", "VagaCriar", "VagaSaida", "VagaAtualizar",
    "CandidatoBase", "CandidatoCriar", "CandidatoSaida", "RankingCandidato",
    # notificacoes
    "EmailAlerta",
]