from datetime import date
from math import sqrt

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
            fornecedor.media_atraso_dias = float(row["media_atraso_dias"] or 0)
            fornecedor.desvio_atraso_dias = float(row["desvio_atraso_dias"] or 0)
            fornecedor.taxa_atraso = round(float(row["taxa_atraso"] or 0), 4)
            fornecedor.total_pedidos = int(row["total_pedidos"] or 0)

    db.commit()


def _prioridade_peso(prioridade: Prioridade) -> float:
    pesos = {
        Prioridade.alta: 0.20,
        Prioridade.media: 0.10,
        Prioridade.baixa: 0.00,
    }
    return pesos.get(prioridade, 0.0)


def _probabilidade_heuristica(pedido: Pedido, fornecedor: Fornecedor) -> float:
    hoje = date.today()
    dias_ate_entrega = (pedido.data_prevista - hoje).days

    base = fornecedor.taxa_atraso
    ajuste_media = min(max(fornecedor.media_atraso_dias / 20, 0), 0.25)
    ajuste_desvio = min(max(fornecedor.desvio_atraso_dias / 30, 0), 0.15)
    ajuste_prazo = 0.20 if dias_ate_entrega <= 3 else 0.10 if dias_ate_entrega <= 7 else 0.0
    ajuste_prioridade = _prioridade_peso(pedido.prioridade)

    prob = base + ajuste_media + ajuste_desvio + ajuste_prazo + ajuste_prioridade
    return round(max(0.0, min(prob, 0.99)), 2)


def _probabilidade_modelo_simples(db: Session, pedido: Pedido, fornecedor: Fornecedor) -> float | None:
    historicos = db.query(HistoricoEntrega).all()
    if len(historicos) < 8:
        return None

    fornecedores = {f.id: f for f in db.query(Fornecedor).all()}
    linhas = []
    for h in historicos:
        f = fornecedores.get(h.fornecedor_id)
        if not f:
            continue
        linhas.append(
            {
                "media": f.media_atraso_dias,
                "taxa": f.taxa_atraso,
                "desvio": f.desvio_atraso_dias,
                "mes": h.mes_referencia.month,
                "tipo_insumo": h.tipo_insumo,
                "atrasou": 1 if h.dias_atraso > 0 else 0,
            }
        )

    if not linhas:
        return None

    df = pd.DataFrame(linhas)
    if df["atrasou"].nunique() < 2:
        return None

    try:
        from sklearn.compose import ColumnTransformer
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import OneHotEncoder

        X = df[["media", "taxa", "desvio", "mes", "tipo_insumo"]]
        y = df["atrasou"]

        preprocess = ColumnTransformer(
            transformers=[
                ("cat", OneHotEncoder(handle_unknown="ignore"), ["tipo_insumo"]),
                ("num", "passthrough", ["media", "taxa", "desvio", "mes"]),
            ]
        )
        modelo = Pipeline(
            steps=[
                ("preprocess", preprocess),
                ("classifier", RandomForestClassifier(n_estimators=80, random_state=42)),
            ]
        )
        modelo.fit(X, y)
        entrada = pd.DataFrame(
            [
                {
                    "media": fornecedor.media_atraso_dias,
                    "taxa": fornecedor.taxa_atraso,
                    "desvio": fornecedor.desvio_atraso_dias,
                    "mes": pedido.data_prevista.month,
                    "tipo_insumo": pedido.tipo_insumo,
                }
            ]
        )
        prob = float(modelo.predict_proba(entrada)[0][1])
        prob = min(0.99, max(0.01, prob + _prioridade_peso(pedido.prioridade) / 2))
        return round(prob, 2)
    except Exception:
        return None


def classificar_alerta(probabilidade: float, prioridade: Prioridade) -> NivelAlerta:
    if probabilidade >= 0.85:
        return NivelAlerta.vermelho
    if probabilidade >= 0.65 and prioridade == Prioridade.alta:
        return NivelAlerta.vermelho
    if 0.40 <= probabilidade <= 0.64 and prioridade in [Prioridade.media, Prioridade.alta]:
        return NivelAlerta.amarelo
    return NivelAlerta.verde


def montar_texto_alerta(pedido: Pedido, fornecedor: Fornecedor, nivel: NivelAlerta, prob: float) -> str:
    percentual = int(round(prob * 100))
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
    pedidos = db.query(Pedido).filter(Pedido.status == StatusPedido.pendente).all()

    for pedido in pedidos:
        fornecedor = pedido.fornecedor
        prob = _probabilidade_modelo_simples(db, pedido, fornecedor)
        if prob is None:
            prob = _probabilidade_heuristica(pedido, fornecedor)
        nivel = classificar_alerta(prob, pedido.prioridade)
        pedido.prob_atraso = prob
        pedido.nivel_alerta = nivel
        pedido.texto_alerta = montar_texto_alerta(pedido, fornecedor, nivel, prob)

    db.commit()


def registrar_entrega(db: Session, pedido: Pedido, data_real_entrega: date) -> Pedido:
    pedido.data_real_entrega = data_real_entrega
    dias_atraso = (data_real_entrega - pedido.data_prevista).days
    pedido.status = StatusPedido.atrasado if dias_atraso > 0 else StatusPedido.entregue

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
