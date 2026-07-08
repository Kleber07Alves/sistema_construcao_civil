import logging
import smtplib
from email.message import EmailMessage

from sqlalchemy.orm import Session

from ..config import settings
from ..models import NivelAlerta, Pedido, StatusPedido
from ..schemas import EmailAlerta

logger = logging.getLogger(__name__)


def montar_emails_alerta(db: Session) -> list[EmailAlerta]:
    pedidos = (
        db.query(Pedido)
        .filter(Pedido.status == StatusPedido.pendente)
        .filter(Pedido.nivel_alerta.in_([NivelAlerta.vermelho, NivelAlerta.amarelo]))
        .all()
    )

    emails = []
    for pedido in pedidos:
        assunto = f"Alerta {pedido.nivel_alerta.value.upper()} — {pedido.tipo_insumo}"
        corpo = (
            f"Obra: {pedido.obra.nome}\n"
            f"Fornecedor: {pedido.fornecedor.nome}\n"
            f"Insumo: {pedido.tipo_insumo}\n"
            f"Previsão de entrega: {pedido.data_prevista}\n"
            f"Probabilidade de atraso: {pedido.prob_atraso * 100:.0f}%\n\n"
            f"{pedido.texto_alerta}"
        )
        emails.append(
            EmailAlerta(
                assunto=assunto,
                destinatario=settings.smtp_destinatario_padrao,
                corpo=corpo,
            )
        )
    return emails


def enviar_email_real(email: EmailAlerta) -> bool:
    """
    Envia o e-mail via SMTP quando configurado.

    Nunca levanta exceção: retorna False quando o SMTP não está configurado
    (modo simulado) ou quando o envio falha. A falha é registrada no log —
    assim nem o endpoint de notificações nem o job diário do APScheduler
    quebram por indisponibilidade do servidor de e-mail.
    """
    if not settings.smtp_configurado:
        return False

    msg = EmailMessage()
    msg["Subject"] = email.assunto
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = email.destinatario
    msg.set_content(email.corpo)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        return True
    except Exception as exc:
        logger.error(
            "Falha ao enviar e-mail '%s' para %s: %s",
            email.assunto,
            email.destinatario,
            exc,
        )
        return False
