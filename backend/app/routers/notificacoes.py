from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import exigir_perfis
from ..database import get_db
from ..models import PerfilUsuario, Usuario
from ..schemas import EmailAlerta
from ..services.notifications import enviar_email_real, montar_emails_alerta

router = APIRouter(prefix="/notificacoes", tags=["Módulo de Notificações"])


@router.get("/alertas-email", response_model=list[EmailAlerta])
def visualizar_emails_alerta(
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor, PerfilUsuario.operador)),
):
    return montar_emails_alerta(db)


@router.post("/enviar-alertas-simulados")
def enviar_alertas_simulados(
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor, PerfilUsuario.operador)),
):
    emails = montar_emails_alerta(db)
    enviados_reais = 0
    for email in emails:
        if enviar_email_real(email):
            enviados_reais += 1
    return {
        "mensagem": "Alertas processados.",
        "total_alertas": len(emails),
        "enviados_por_smtp": enviados_reais,
        "observacao": "Sem SMTP configurado, o endpoint funciona como simulação.",
    }
