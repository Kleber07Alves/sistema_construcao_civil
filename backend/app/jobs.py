from apscheduler.schedulers.background import BackgroundScheduler

from .database import SessionLocal
from .services.logistico_ml import recalcular_alertas

scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")


def job_diario_alertas() -> None:
    db = SessionLocal()
    try:
        recalcular_alertas(db)
    finally:
        db.close()


def iniciar_jobs() -> None:
    if scheduler.running:
        return
    scheduler.add_job(job_diario_alertas, "cron", hour=7, minute=0, id="recalcular_alertas_diario", replace_existing=True)
    scheduler.start()


def parar_jobs() -> None:
    if scheduler.running:
        scheduler.shutdown()
