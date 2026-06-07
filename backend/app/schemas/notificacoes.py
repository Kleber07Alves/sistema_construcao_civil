"""Schemas do módulo de Notificações."""
from pydantic import BaseModel


class EmailAlerta(BaseModel):
    assunto:      str
    destinatario: str
    corpo:        str