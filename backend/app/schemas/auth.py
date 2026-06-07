# backend/app/schemas/auth.py
"""Schemas de autenticação — Token JWT e payload de login."""
from pydantic import BaseModel, EmailStr

from ..models import PerfilUsuario


class LoginEntrada(BaseModel):
    email: EmailStr
    senha: str


class Token(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    perfil:       PerfilUsuario
    nome:         str