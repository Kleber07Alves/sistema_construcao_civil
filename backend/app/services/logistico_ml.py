from datetime import date

import pandas as pd
from sqlalchemy.orm import Session

from ..models import Fornecedor, HistoricoEntrega, NivelAlerta, Pedido, Prioridade, StatusPedido


def calcular_estatisticas_fornecedores(db: Session) -> None:
    historicos = db.query(HistoricoEntrega).all()

    if not historicos:
        return

    linhas = [
        {
            "fornecedor_id": h.fornecedor_id,
            "dias_atraso": h.dias_atraso,
            "atrasou": 1 if h.dias_atraso > 0 else 0,
        }
        for h in historicos
    ]

    df = pd.DataFrame(linhas)

    agrupado = df.groupby("fornecedor_id").agg(
        media_atraso_dias=("dias_atraso", "mean"),
        desvio_atraso_dias=("dias_atraso", "std"),
        taxa_atraso=("atrasou", "mean"),
        total_pedidos=("dias_atraso", "count"),
    )

    for fornecedor_id, row in agrupado.iterrows():
        fornecedor = db.get(Fornecedor, int(fornecedor_id))

        if fornecedor:
            fornecedor.media_atraso_dias = round(float(row["media_atraso_dias"] or 0), 2)
            fornecedor.desvio_atraso_dias = round(float(row["desvio_atraso_dias"] or 0), 2)
            fornecedor.taxa_atraso = round(float(row["taxa_atraso"] or 0), 4)
            fornecedor.total_pedidos = int(row["total_pedidos"] or 0)

    db.commit()


def _peso_prioridade(prioridade: Prioridade) -> float:
    if prioridade == Prioridade.alta:
        return 0.20
    if prioridade == Prioridade.media:
        return 0.10
    return 0.00


def calcular_probabilidade_atraso(pedido: Pedido, fornecedor: Fornecedor) -> float:
    hoje = date.today()
    dias_ate_entrega = (pedido.data_prevista - hoje).days

    taxa_atraso = min(max(fornecedor.taxa_atraso, 0), 1)
    media_atraso = min(max(fornecedor.media_atraso_dias / 10, 0), 1)
    desvio_atraso = min(max(fornecedor.desvio_atraso_dias / 10, 0), 1)

    if dias_ate_entrega <= 3:
        risco_prazo = 1.0
    elif dias_ate_entrega <= 7:
        risco_prazo = 0.6
    elif dias_ate_entrega <= 15:
        risco_prazo = 0.3
    else:
        risco_prazo = 0.1

    if pedido.prioridade == Prioridade.alta:
        risco_prioridade = 1.0
    elif pedido.prioridade == Prioridade.media:
        risco_prioridade = 0.5
    else:
        risco_prioridade = 0.1

    probabilidade = (
        taxa_atraso * 0.40
        + media_atraso * 0.20
        + desvio_atraso * 0.10
        + risco_prazo * 0.15
        + risco_prioridade * 0.15
    )

    return round(max(0.0, min(probabilidade, 0.99)), 2)

def classificar_alerta(probabilidade: float, prioridade: Prioridade) -> NivelAlerta:
    if probabilidade >= 0.85:
        return NivelAlerta.vermelho

    if probabilidade >= 0.65 and prioridade == Prioridade.alta:
        return NivelAlerta.vermelho

    if 0.40 <= probabilidade <= 0.64 and prioridade in [Prioridade.media, Prioridade.alta]:
        return NivelAlerta.amarelo

    return NivelAlerta.verde


def montar_texto_alerta(pedido: Pedido, fornecedor: Fornecedor, nivel: NivelAlerta, probabilidade: float) -> str:
    percentual = int(round(probabilidade * 100))

    if nivel == NivelAlerta.vermelho:
        return (
            f"Atenção: {pedido.tipo_insumo} para a {pedido.obra.nome} tem {percentual}% de chance de atrasar. "
            f"Fornecedor {fornecedor.nome} tem média de {fornecedor.media_atraso_dias:.1f} dias de atraso neste histórico."
        )

    if nivel == NivelAlerta.amarelo:
        return (
            f"Monitorar: {pedido.tipo_insumo} para a {pedido.obra.nome} tem {percentual}% de chance de atraso. "
            f"Histórico do fornecedor {fornecedor.nome} indica taxa de atraso de {fornecedor.taxa_atraso * 100:.0f}%."
        )

    return (
        f"Normal: {pedido.tipo_insumo} para a {pedido.obra.nome}. "
        f"Fornecedor {fornecedor.nome} tem taxa de atraso de {fornecedor.taxa_atraso * 100:.0f}% no histórico."
    )


def recalcular_alertas(db: Session) -> None:
    calcular_estatisticas_fornecedores(db)

    pedidos = (
        db.query(Pedido)
        .filter(Pedido.status == StatusPedido.pendente)
        .all()
    )

    for pedido in pedidos:
        fornecedor = pedido.fornecedor

        probabilidade = calcular_probabilidade_atraso(pedido, fornecedor)
        nivel = classificar_alerta(probabilidade, pedido.prioridade)

        pedido.prob_atraso = probabilidade
        pedido.nivel_alerta = nivel
        pedido.texto_alerta = montar_texto_alerta(pedido, fornecedor, nivel, probabilidade)

    db.commit()


def registrar_entrega(db: Session, pedido: Pedido, data_real_entrega: date) -> Pedido:
    pedido.data_real_entrega = data_real_entrega

    dias_atraso = (data_real_entrega - pedido.data_prevista).days

    if dias_atraso > 0:
        pedido.status = StatusPedido.atrasado
    else:
        pedido.status = StatusPedido.entregue

    historico = HistoricoEntrega(
        fornecedor_id=pedido.fornecedor_id,
        dias_atraso=dias_atraso,
        tipo_insumo=pedido.tipo_insumo,
        mes_referencia=pedido.data_prevista.replace(day=1),
    )

    db.add(historico)
    db.commit()
    db.refresh(pedido)

    recalcular_alertas(db)

    return pedido