
"""Schemas do domínio Core — Usuários e Obras."""
from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from ..models import PerfilUsuario, Prioridade, StatusObra


# =============================================================================
# Usuário
# =============================================================================

class UsuarioBase(BaseModel):
    nome:   str
    email:  EmailStr
    perfil: PerfilUsuario
    ativo:  bool = True


class UsuarioCriar(UsuarioBase):
    senha: str = Field(min_length=6)


class UsuarioSaida(UsuarioBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class UsuarioAtualizar(BaseModel):
    """
    Atualização parcial de usuário.
    model_dump(exclude_unset=True) garante que apenas os campos
    enviados na requisição são aplicados no banco.
    """
    nome:   str | None = None
    email:  EmailStr | None = None
    perfil: PerfilUsuario | None = None
    ativo:  bool | None = None
    senha:  str | None = Field(default=None, min_length=6)


# =============================================================================
# Obra
# =============================================================================

class ObraBase(BaseModel):
    nome:        str
    endereco:    str
    status:      StatusObra  = StatusObra.em_andamento
    prioridade:  Prioridade  = Prioridade.media
    data_inicio: date | None = None


class ObraCriar(ObraBase):
    pass


class ObraSaida(ObraBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ObraAtualizar(BaseModel):
    nome:        str | None        = None
    endereco:    str | None        = None
    status:      StatusObra | None = None
    prioridade:  Prioridade | None = None
    data_inicio: date | None       = None