# backend/app/models/__init__.py
"""
Pacote de modelos — re-exporta todos os símbolos dos submódulos de domínio.
A ordem de importação é obrigatória para evitar erros circulares de runtime.
"""

# 1. Core (Base estável sem dependências)
from .core import (
    Obra,
    PerfilUsuario,
    Prioridade,
    StatusObra,
    Usuario,
)

# 2. Logístico (Depende do Core)
from .logistico import (
    Fornecedor,
    HistoricoEntrega,
    NivelAlerta,
    Pedido,
    StatusPedido,
)

# 3. RH (Independente)
from .rh import (
    Candidato,
    StatusVaga,
    Vaga,
)

__all__ = [
    "PerfilUsuario", "Prioridade", "StatusObra", "Usuario", "Obra",
    "StatusPedido", "NivelAlerta", "Fornecedor", "HistoricoEntrega", "Pedido",
    "StatusVaga", "Vaga", "Candidato",
]