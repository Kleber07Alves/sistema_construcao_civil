"""
Serviço de Ciência de Dados e ML para o Módulo Logístico.

Pipeline:
  1. calcular_estatisticas_fornecedores() — agrega histórico via Pandas
  2. calcular_probabilidade_atraso()      — heurística ponderada por pedido
  3. classificar_alerta()                 — aplica regras de negócio (prioridade)
  4. montar_texto_alerta()                — texto legível para o dashboard
  5. recalcular_alertas()                 — orquestra 1→4 para todos os pedidos ativos
  6. registrar_entrega()                  — fecha o pedido e dispara recálculo
"""
from __future__ import annotations

import math
from datetime import date

import pandas as pd
from sqlalchemy.orm import Session

from ..models import Fornecedor, HistoricoEntrega, NivelAlerta, Pedido, Prioridade, StatusPedido

# =============================================================================
# Utilitários internos
# =============================================================================

def _safe_float(val: object, default: float = 0.0) -> float:
    """
    Converte val para float de forma segura.

    Protege contra os três casos problemáticos do pipeline Pandas→SQLAlchemy:
      • None / NaN  → pandas.std() com n=1 retorna NaN; float('nan') é truthy,
                      então `float(nan) or 0` retorna NaN silenciosamente.
      • inf         → divisões por zero em DataFrames mal formados.
      • TypeError   → valores não numéricos em colunas inesperadas.

    Exemplos:
      _safe_float(None)         → 0.0
      _safe_float(float('nan')) → 0.0
      _safe_float(float('inf')) → 0.0
      _safe_float(5.3)          → 5.3
      _safe_float(-2)           → -2.0  (negativo é válido para dias_atraso)
    """
    try:
        f = float(val)  # type: ignore[arg-type]
        return default if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return default


def _normalizar_dias(dias: float, escala_max: float = 15.0) -> float:
   
    if dias <= 0.0:
        return 0.0
    return min(1.0, math.log1p(max(dias, 0.0)) / math.log1p(escala_max))


# =============================================================================
# 1. Cálculo de estatísticas agregadas por fornecedor
# =============================================================================

def calcular_estatisticas_fornecedores(db: Session) -> None:
    """
    Agrega o histórico de entregas via Pandas e atualiza os campos calculados
    de cada Fornecedor: media_atraso_dias, desvio_atraso_dias, taxa_atraso,
    total_pedidos.

    Roda diariamente via APScheduler e após cada registrar_entrega().
    """
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
        desvio_atraso_dias=("dias_atraso", "std"),   # NaN quando n=1 — protegido abaixo
        taxa_atraso=("atrasou", "mean"),
        total_pedidos=("dias_atraso", "count"),
    )

    for fornecedor_id, row in agrupado.iterrows():
        fornecedor = db.get(Fornecedor, int(fornecedor_id))

        if not fornecedor:
            continue

        fornecedor.media_atraso_dias = round(_safe_float(row["media_atraso_dias"]), 2)
        # _safe_float é essencial aqui: std() de série com n=1 retorna NaN,
        # e `float(nan) or 0` retornaria NaN (NaN é truthy).
        fornecedor.desvio_atraso_dias = round(_safe_float(row["desvio_atraso_dias"]), 2)
        fornecedor.taxa_atraso = round(_safe_float(row["taxa_atraso"]), 4)
        fornecedor.total_pedidos = int(_safe_float(row["total_pedidos"]))

    db.commit()


# =============================================================================
# 2. Cálculo de probabilidade de atraso por pedido
# =============================================================================

def calcular_probabilidade_atraso(pedido: Pedido, fornecedor: Fornecedor) -> float:
    """
    Calcula a probabilidade de atraso de um pedido via heurística ponderada.

    Decisão de design — prioridade FORA deste cálculo:
      A prioridade do pedido não aumenta a probabilidade de atraso. Um pedido
      de alta prioridade com um fornecedor excelente não tem maior chance de
      atrasar por isso. A prioridade é uma variável de negócio que amplifica
      o NÍVEL DE ALERTA em classificar_alerta(), não a probabilidade física.
      Manter os dois conceitos separados evita viés nos dados e torna o modelo
      mais interpretável.

    Componentes e pesos (somam exatamente 1.00):
      taxa_atraso      0.45  — frequência histórica de atrasos (indicador mais confiável)
      media_atraso     0.25  — magnitude típica do atraso (normalizada via log)
      desvio_atraso    0.10  — imprevisibilidade / inconsistência do fornecedor
      risco_prazo      0.20  — urgência: quanto mais próxima a data, maior o risco

    Returns:
        float em [0.00, 0.99] — nunca retorna 1.0 (certeza absoluta é reservada
        para auditoria humana, não para modelo automático).
    """
    hoje = date.today()
    dias_ate_entrega = (pedido.data_prevista - hoje).days

    # ── Componentes baseados no histórico do fornecedor ───────────────────
    taxa_atraso   = min(max(_safe_float(fornecedor.taxa_atraso), 0.0), 1.0)
    # Escala 15 dias para média: fornecedor com 15d de atraso médio = risco máximo
    media_atraso  = _normalizar_dias(_safe_float(fornecedor.media_atraso_dias), 15.0)
    # Escala 10 dias para desvio: desvios > 10d indicam fornecedor altamente imprevisível
    desvio_atraso = _normalizar_dias(_safe_float(fornecedor.desvio_atraso_dias), 10.0)

    # ── Componente de prazo ───────────────────────────────────────────────
    # Quanto mais próxima (ou passada) a data de entrega, maior o risco,
    # pois há menos tempo para intervenção e o pedido já está "em curso".
    if dias_ate_entrega <= 0:
        risco_prazo = 1.00   # data prevista já passou — pedido potencialmente atrasado
    elif dias_ate_entrega <= 3:
        risco_prazo = 0.85   # janela crítica: menos de 3 dias úteis
    elif dias_ate_entrega <= 7:
        risco_prazo = 0.55   # atenção elevada
    elif dias_ate_entrega <= 15:
        risco_prazo = 0.30   # monitoramento normal
    else:
        risco_prazo = 0.10   # prazo confortável

    probabilidade = (
        taxa_atraso   * 0.45
        + media_atraso  * 0.25
        + desvio_atraso * 0.10
        + risco_prazo   * 0.20
    )  # soma dos pesos = 1.00

    return round(max(0.0, min(probabilidade, 0.99)), 2)


# =============================================================================
# 3. Classificação do nível de alerta
# =============================================================================

def classificar_alerta(probabilidade: float, prioridade: Prioridade) -> NivelAlerta:
    """
    Converte probabilidade + prioridade de negócio em nível de alerta.

    É AQUI que a prioridade age — ela amplifica o alerta para pedidos
    críticos à obra, mesmo que a probabilidade seja moderada.

    Regras (conforme escopo — limiares configuráveis após validação com dados reais):
      VERMELHO: prob >= 85% (qualquer prioridade) OU prob >= 65% com prioridade alta
      AMARELO:  40% <= prob <= 64% com prioridade média ou alta
      VERDE:    demais casos
    """
    if probabilidade >= 0.85:
        return NivelAlerta.vermelho

    if probabilidade >= 0.65 and prioridade == Prioridade.alta:
        return NivelAlerta.vermelho

    if 0.40 <= probabilidade <= 0.64 and prioridade in (Prioridade.media, Prioridade.alta):
        return NivelAlerta.amarelo

    return NivelAlerta.verde


# =============================================================================
# 4. Texto de alerta para exibição no dashboard
# =============================================================================

def montar_texto_alerta(
    pedido: Pedido,
    fornecedor: Fornecedor,
    nivel: NivelAlerta,
    probabilidade: float,
) -> str:
    """Gera o texto descritivo do alerta exibido no painel de gestão."""
    percentual = int(round(probabilidade * 100))

    if nivel == NivelAlerta.vermelho:
        return (
            f"Atenção: {pedido.tipo_insumo} para a {pedido.obra.nome} tem "
            f"{percentual}% de chance de atrasar. "
            f"Fornecedor {fornecedor.nome} tem média de "
            f"{fornecedor.media_atraso_dias:.1f} dias de atraso no histórico."
        )

    if nivel == NivelAlerta.amarelo:
        return (
            f"Monitorar: {pedido.tipo_insumo} para a {pedido.obra.nome} tem "
            f"{percentual}% de chance de atraso. "
            f"Histórico do fornecedor {fornecedor.nome} indica taxa de atraso "
            f"de {fornecedor.taxa_atraso * 100:.0f}%."
        )

    return (
        f"Normal: {pedido.tipo_insumo} para a {pedido.obra.nome}. "
        f"Fornecedor {fornecedor.nome} tem taxa de atraso de "
        f"{fornecedor.taxa_atraso * 100:.0f}% no histórico."
    )


# =============================================================================
# 5. Orquestrador principal — roda via APScheduler (job diário)
# =============================================================================

def recalcular_alertas(db: Session) -> None:
    """
    Pipeline completo: recalcula estatísticas dos fornecedores e depois
    atualiza prob_atraso, nivel_alerta e texto_alerta de todos os pedidos
    com status 'pendente'.

    Chamado:
      • Pelo job diário do APScheduler (jobs.py)
      • Após criar_pedido(), criar_historico() e registrar_entrega()
    """
    calcular_estatisticas_fornecedores(db)

    pedidos_pendentes = (
        db.query(Pedido)
        .filter(Pedido.status == StatusPedido.pendente)
        .all()
    )

    for pedido in pedidos_pendentes:
        fornecedor = pedido.fornecedor
        probabilidade = calcular_probabilidade_atraso(pedido, fornecedor)
        nivel = classificar_alerta(probabilidade, pedido.prioridade)

        pedido.prob_atraso = probabilidade
        pedido.nivel_alerta = nivel
        pedido.texto_alerta = montar_texto_alerta(pedido, fornecedor, nivel, probabilidade)

    db.commit()


# =============================================================================
# 6. Registro de entrega — fecha o ciclo de vida do pedido
# =============================================================================

def registrar_entrega(db: Session, pedido: Pedido, data_real_entrega: date) -> Pedido:
    """
    Marca o pedido como entregue (ou atrasado), cria o registro de histórico
    e dispara o recálculo de alertas para os pedidos que ainda estão pendentes.
    """
    pedido.data_real_entrega = data_real_entrega

    dias_atraso = (data_real_entrega - pedido.data_prevista).days
    pedido.status = StatusPedido.atrasado if dias_atraso > 0 else StatusPedido.entregue

    historico = HistoricoEntrega(
        fornecedor_id=pedido.fornecedor_id,
        dias_atraso=dias_atraso,
        tipo_insumo=pedido.tipo_insumo,
        # Captura o mês de referência para análise de sazonalidade
        mes_referencia=pedido.data_prevista.replace(day=1),
    )

    db.add(historico)
    db.commit()
    db.refresh(pedido)

    # Recalcula alertas dos demais pedidos pendentes com o histórico atualizado
    recalcular_alertas(db)

    return pedido
