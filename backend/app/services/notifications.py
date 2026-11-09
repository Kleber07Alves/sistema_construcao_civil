import logging
import smtplib
from email.message import EmailMessage

from sqlalchemy.orm import Session, joinedload

from ..config import settings
from ..models import Candidato, NivelAlerta, Pedido, StatusPedido, StatusVaga, Vaga
from ..schemas import EmailAlerta
from .rh_nlp import calcular_score

logger = logging.getLogger(__name__)

# Score mínimo de compatibilidade candidato × vaga para entrar no alerta
# "candidatos disponíveis". Limiar de negócio — ajustar após validação
# com dados reais da empresa.
SCORE_MINIMO_ALERTA = 60.0

# Máximo de candidatos listados por vaga no corpo do e-mail
MAX_CANDIDATOS_POR_EMAIL = 5


def montar_emails_alerta(db: Session) -> list[EmailAlerta]:
    """E-mails de alerta logístico: pedidos pendentes em risco (vermelho/amarelo)."""
    pedidos = (
        db.query(Pedido)
        # joinedload evita N+1: obra e fornecedor são acessados por pedido abaixo
        .options(joinedload(Pedido.obra), joinedload(Pedido.fornecedor))
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


def montar_emails_candidatos(db: Session) -> list[EmailAlerta]:
    """
    E-mails de alerta de RH: "candidatos disponíveis" (item do escopo original).

    Para cada vaga ABERTA, calcula o score de compatibilidade de todos os
    candidatos (mesma régua do ranking em /rh/vagas/{id}/ranking) e gera um
    e-mail quando há candidatos com score >= SCORE_MINIMO_ALERTA — vagas sem
    candidatos compatíveis não geram ruído na caixa de entrada do gestor.
    """
    vagas = db.query(Vaga).filter(Vaga.status == StatusVaga.aberta).all()
    if not vagas:
        return []

    candidatos = db.query(Candidato).all()
    if not candidatos:
        return []

    emails = []
    for vaga in vagas:
        compativeis: list[tuple[float, Candidato]] = []
        for candidato in candidatos:
            score, _ = calcular_score(
                vaga_habilidades=vaga.habilidades,
                vaga_requisitos=vaga.requisitos,
                candidato_habilidades=candidato.habilidades,
                experiencia_anos=candidato.experiencia_anos,
            )
            if score >= SCORE_MINIMO_ALERTA:
                compativeis.append((score, candidato))

        if not compativeis:
            continue

        compativeis.sort(key=lambda item: item[0], reverse=True)
        linhas = [
            f"• {candidato.nome} — score {score:.0f}% — "
            f"{candidato.cargo or 'cargo não identificado'} — {candidato.email}"
            for score, candidato in compativeis[:MAX_CANDIDATOS_POR_EMAIL]
        ]
        corpo = (
            f"Vaga: {vaga.titulo} ({vaga.tipo_obra})\n"
            f"Candidatos compatíveis (score >= {SCORE_MINIMO_ALERTA:.0f}%): "
            f"{len(compativeis)}\n\n" + "\n".join(linhas)
        )
        emails.append(
            EmailAlerta(
                assunto=f"Candidatos disponíveis — {vaga.titulo}",
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
