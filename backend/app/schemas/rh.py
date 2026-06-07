"""Schemas do domínio de RH — Vagas, Candidatos e Ranking."""
from pydantic import BaseModel, ConfigDict, EmailStr

from ..models import StatusVaga


# =============================================================================
# Vaga
# =============================================================================

class VagaBase(BaseModel):
    titulo:      str
    tipo_obra:   str
    requisitos:  str
    habilidades: str
    status:      StatusVaga = StatusVaga.aberta


class VagaCriar(VagaBase):
    pass


class VagaSaida(VagaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class VagaAtualizar(BaseModel):
    """
    Atualização parcial de vaga.
    O campo status permite mover a vaga entre os estados do ciclo de vida:
    aberta → pausada → encerrada.
    """
    titulo:      str | None        = None
    tipo_obra:   str | None        = None
    requisitos:  str | None        = None
    habilidades: str | None        = None
    status:      StatusVaga | None = None


# =============================================================================
# Candidato
# =============================================================================

class CandidatoBase(BaseModel):
    nome:             str
    email:            EmailStr
    cargo:            str | None = None
    experiencia_anos: float      = 0.0
    habilidades:      str        = ""
    curriculo_texto:  str        = ""


class CandidatoCriar(CandidatoBase):
    pass


class CandidatoSaida(CandidatoBase):
    model_config = ConfigDict(from_attributes=True)
    id:     int
    resumo: str


# =============================================================================
# Ranking
# =============================================================================

class RankingCandidato(BaseModel):
    candidato: CandidatoSaida
    score:     float
    motivos:   list[str]