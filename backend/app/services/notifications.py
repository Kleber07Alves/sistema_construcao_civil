import os
import smtplib
from email.message import EmailMessage
from sqlalchemy.orm import Session

from ..models import NivelAlerta, Pedido, StatusPedido
from ..schemas import EmailAlerta


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
        emails.append(EmailAlerta(assunto=assunto, destinatario="gestor@empresa.com", corpo=corpo))
    return emails


def enviar_email_real(email: EmailAlerta) -> bool:
    host = os.getenv("SMTP_HOST")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM", user or "alertas@empresa.com")
    port = int(os.getenv("SMTP_PORT", "587"))

    if not host or not user or not password:
        return False

    msg = EmailMessage()
    msg["Subject"] = email.assunto
    msg["From"] = sender
    msg["To"] = email.destinatario
    msg.set_content(email.corpo)

    with smtplib.SMTP(host, port) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(msg)
    return True
