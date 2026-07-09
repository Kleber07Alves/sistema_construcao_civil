import logging

from apscheduler.schedulers.background import BackgroundScheduler

from .config import settings
from .database import SessionLocal
from .services.logistico_ml import recalcular_alertas
from .services.notifications import (
    enviar_email_real,
    montar_emails_alerta,
    montar_emails_candidatos,
)

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")


def job_diario_alertas() -> None:
    """07:00 — recalcula estatísticas dos fornecedores e alertas dos pedidos."""
    db = SessionLocal()
    try:
        recalcular_alertas(db)
    finally:
        db.close()


def job_envio_alertas() -> None:
    """
    07:15 — envia por e-mail os alertas do dia (logísticos + RH).

    Roda 15 min após o recálculo para trabalhar com os dados atualizados.
    Sem SMTP configurado, apenas registra no log quantos alertas existiriam
    (modo simulado) — o envio real é habilitado pelas variáveis SMTP_*.
    """
    db = SessionLocal()
    try:
        emails = montar_emails_alerta(db) + montar_emails_candidatos(db)

        if not emails:
            logger.info("Job de envio: nenhum alerta para enviar hoje.")
            return

        if not settings.smtp_configurado:
            logger.info(
                "Job de envio: SMTP não configurado — %d alerta(s) em modo simulado.",
                len(emails),
            )
            return

        enviados = sum(1 for email in emails if enviar_email_real(email))
        logger.info(
            "Job de envio: %d/%d e-mail(s) de alerta enviados.",
            enviados,
            len(emails),
        )
    finally:
        db.close()


def iniciar_jobs() -> None:
    if scheduler.running:
        return
    scheduler.add_job(
        job_diario_alertas, "cron", hour=7, minute=0,
        id="recalcular_alertas_diario", replace_existing=True,
    )
    scheduler.add_job(
        job_envio_alertas, "cron", hour=7, minute=15,
        id="envio_alertas_email", replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Jobs agendados: recálculo de alertas (07:00) e envio de e-mails (07:15)."
    )


def parar_jobs() -> None:
    if scheduler.running:
        scheduler.shutdown()
