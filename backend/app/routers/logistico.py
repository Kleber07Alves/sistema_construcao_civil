# Router do Módulo Logístico.
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import case
from sqlalchemy.orm import Session, joinedload

from ..auth import exigir_perfis, usuario_atual
from ..database import get_db
from ..dependencies import paginacao
from ..models import (
    Fornecedor,
    HistoricoEntrega,
    NivelAlerta,
    Obra,
    Pedido,
    PerfilUsuario,
    StatusPedido,
    Usuario,
)
from ..schemas import (
    AlertaSaida,
    DashboardLogistico,
    FornecedorAtualizar,
    FornecedorCriar,
    FornecedorSaida,
    HistoricoCriar,
    HistoricoSaida,
    PedidoAtualizar,
    PedidoCriar,
    PedidoEntregar,
    PedidoSaida,
)
from ..services.logistico_ml import recalcular_alertas, registrar_entrega

router = APIRouter(prefix="/logistico", tags=["Módulo Logístico"])


# =============================================================================
# Utilitário interno — ordenação por severidade de alerta
# =============================================================================

def _nivel_alerta_order():
    """
    Expressão SQLAlchemy para ordenar alertas por severidade real:
      vermelho (1) → amarelo (2) → verde (3).

    Necessário porque ordenar por Pedido.nivel_alerta usa ordem alfabética:
      amarelo → verde → vermelho — que é a ordem ERRADA.
    """
    return case(
        (Pedido.nivel_alerta == NivelAlerta.vermelho, 1),
        (Pedido.nivel_alerta == NivelAlerta.amarelo,  2),
        else_=3,
    )


# =============================================================================
# Utilitário interno — busca de alertas compartilhada
# =============================================================================

def _buscar_alertas_pedidos(
    db: Session,
    obra_id: int | None = None,
    nivel_alerta: NivelAlerta | None = None,
) -> list[AlertaSaida]:
    """
    Busca pedidos pendentes e serializa como AlertaSaida, ordenados por
    severidade (vermelho → amarelo → verde) e depois por data prevista.

    Função interna extraída para que listar_alertas() e dashboard_logistico()
    compartilhem a mesma lógica sem que um endpoint chame o outro diretamente
    (antipadrão: chamada direta de função de rota bypassa o ciclo FastAPI e
    torna o código frágil a mudanças de dependências).

    Args:
        db: sessão do banco de dados.
        obra_id: filtro opcional por obra.
        nivel_alerta: filtro opcional por nível de alerta.
    """
    # joinedload evita N+1: sem ele, cada pedido dispararia 2 queries extras
    # (obra e fornecedor) na serialização abaixo.
    query = (
        db.query(Pedido)
        .options(joinedload(Pedido.obra), joinedload(Pedido.fornecedor))
        .filter(Pedido.status == StatusPedido.pendente)
    )

    if obra_id is not None:
        query = query.filter(Pedido.obra_id == obra_id)

    if nivel_alerta is not None:
        query = query.filter(Pedido.nivel_alerta == nivel_alerta)

    pedidos = query.order_by(_nivel_alerta_order(), Pedido.data_prevista).all()

    return [
        AlertaSaida(
            pedido_id=p.id,
            obra=p.obra.nome,
            fornecedor=p.fornecedor.nome,   # requer relationship Pedido→Fornecedor
            tipo_insumo=p.tipo_insumo,
            prioridade=p.prioridade,
            data_prevista=p.data_prevista,
            prob_atraso=p.prob_atraso,
            nivel_alerta=p.nivel_alerta,
            texto_alerta=p.texto_alerta,
        )
        for p in pedidos
    ]


# =============================================================================
# Fornecedores
# =============================================================================

@router.get("/fornecedores", response_model=list[FornecedorSaida])
def listar_fornecedores(
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
    pag: dict[str, int] = Depends(paginacao),
):
    return (
        db.query(Fornecedor)
        .order_by(Fornecedor.id)
        .offset(pag["skip"])
        .limit(pag["limit"])
        .all()
    )


@router.post("/fornecedores", response_model=FornecedorSaida, status_code=201)
def criar_fornecedor(
    dados: FornecedorCriar,
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor, PerfilUsuario.operador)),
):
    fornecedor = Fornecedor(**dados.model_dump())
    db.add(fornecedor)
    db.commit()
    db.refresh(fornecedor)
    return fornecedor



@router.put("/fornecedores/{fornecedor_id}", response_model=FornecedorSaida)
def atualizar_fornecedor(
    fornecedor_id: int,
    dados: FornecedorAtualizar,
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor, PerfilUsuario.operador)),
):
  
    fornecedor = db.get(Fornecedor, fornecedor_id)
    if not fornecedor:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado.")

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(fornecedor, campo, valor)

    db.commit()
    db.refresh(fornecedor)
    return fornecedor


@router.delete("/fornecedores/{fornecedor_id}", status_code=204)
def excluir_fornecedor(
    fornecedor_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor)),
) -> Response:
    fornecedor = db.get(Fornecedor, fornecedor_id)

    if not fornecedor:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado.")

    possui_pedidos  = db.query(Pedido).filter(Pedido.fornecedor_id == fornecedor_id).first()
    possui_historico = db.query(HistoricoEntrega).filter(
        HistoricoEntrega.fornecedor_id == fornecedor_id
    ).first()

    if possui_pedidos or possui_historico:
        raise HTTPException(
            status_code=400,
            detail="Não é possível excluir fornecedor com pedidos ou histórico vinculado.",
        )

    db.delete(fornecedor)
    db.commit()
    return Response(status_code=204)


# =============================================================================
# Histórico de entregas
# =============================================================================

@router.get("/historico", response_model=list[HistoricoSaida])
def listar_historico(
    fornecedor_id: int | None = None,
    tipo_insumo:   str | None = None,
    db: Session = Depends(get_db),
    _: Usuario  = Depends(usuario_atual),
    pag: dict[str, int] = Depends(paginacao),
):
    """
    Lista o histórico de entregas, do mês mais recente para o mais antigo.

    Query params:
      - fornecedor_id — filtra por fornecedor específico
      - tipo_insumo   — filtra por insumo (correspondência exata)

    Base para o gráfico de atrasos por mês do dashboard e para auditoria
    dos dados que alimentam as estatísticas dos fornecedores.
    """
    query = db.query(HistoricoEntrega)

    if fornecedor_id is not None:
        query = query.filter(HistoricoEntrega.fornecedor_id == fornecedor_id)

    if tipo_insumo:
        query = query.filter(HistoricoEntrega.tipo_insumo == tipo_insumo)

    return (
        query.order_by(HistoricoEntrega.mes_referencia.desc(), HistoricoEntrega.id.desc())
        .offset(pag["skip"])
        .limit(pag["limit"])
        .all()
    )


@router.post("/historico", response_model=HistoricoSaida, status_code=201)
def criar_historico(
    dados: HistoricoCriar,
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor, PerfilUsuario.operador)),
):
    fornecedor = db.get(Fornecedor, dados.fornecedor_id)

    if not fornecedor:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado.")

    historico = HistoricoEntrega(**dados.model_dump())
    db.add(historico)
    db.commit()
    db.refresh(historico)

    recalcular_alertas(db)

    return historico


# =============================================================================
# Pedidos
# =============================================================================


@router.get("/pedidos", response_model=list[PedidoSaida])
def listar_pedidos(
    status:       StatusPedido | None = None,
    nivel_alerta: NivelAlerta  | None = None,
    obra_id:      int          | None = None,
    fornecedor_id: int         | None = None,
    db: Session = Depends(get_db),
    _: Usuario  = Depends(usuario_atual),
    pag: dict[str, int] = Depends(paginacao),
):
    """
    Lista pedidos com filtros opcionais.

    Query params:
      - status        — pendente | entregue | atrasado
      - nivel_alerta  — vermelho | amarelo | verde
      - obra_id       — filtra por obra específica
      - fornecedor_id — filtra por fornecedor específico
    """
    query = db.query(Pedido)

    if status is not None:
        query = query.filter(Pedido.status == status)

    if nivel_alerta is not None:
        query = query.filter(Pedido.nivel_alerta == nivel_alerta)

    if obra_id is not None:
        query = query.filter(Pedido.obra_id == obra_id)

    if fornecedor_id is not None:
        query = query.filter(Pedido.fornecedor_id == fornecedor_id)

    return query.order_by(Pedido.id).offset(pag["skip"]).limit(pag["limit"]).all()


@router.post("/pedidos", response_model=PedidoSaida, status_code=201)
def criar_pedido(
    dados: PedidoCriar,
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor, PerfilUsuario.operador)),
):
    fornecedor = db.get(Fornecedor, dados.fornecedor_id)
    obra       = db.get(Obra, dados.obra_id)

    if not fornecedor:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado.")
    if not obra:
        raise HTTPException(status_code=404, detail="Obra não encontrada.")

    if dados.data_prevista < dados.data_pedido:
        raise HTTPException(
            status_code=400,
            detail="A data prevista não pode ser anterior à data do pedido.",
        )

    pedido = Pedido(**dados.model_dump(), status=StatusPedido.pendente)
    db.add(pedido)
    db.commit()
    db.refresh(pedido)
    recalcular_alertas(db)
    db.refresh(pedido)

    return pedido

@router.put("/pedidos/{pedido_id}", response_model=PedidoSaida)
def atualizar_pedido(
    pedido_id: int,
    dados: PedidoAtualizar,
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor, PerfilUsuario.operador)),
):
    """
    Atualização parcial de um pedido pendente.

    Regras:
      • Apenas pedidos com status 'pendente' podem ser editados — pedidos
        entregues/atrasados já geraram histórico e são imutáveis.
      • fornecedor_id / obra_id, se alterados, precisam existir.
      • A combinação final de datas precisa manter data_prevista >= data_pedido.
      • Mudanças em fornecedor, datas ou prioridade alteram o risco — o
        recálculo de alertas roda ao final.
    """
    pedido = db.get(Pedido, pedido_id)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")

    if pedido.status != StatusPedido.pendente:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Apenas pedidos 'pendente' podem ser editados. "
                f"Status atual: '{pedido.status.value}'."
            ),
        )

    update_data = dados.model_dump(exclude_unset=True)

    if not update_data:
        return pedido  # body vazio — nenhuma alteração, retorna estado atual

    if "fornecedor_id" in update_data and not db.get(Fornecedor, update_data["fornecedor_id"]):
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado.")

    if "obra_id" in update_data and not db.get(Obra, update_data["obra_id"]):
        raise HTTPException(status_code=404, detail="Obra não encontrada.")

    # Valida o PAR final de datas (campo alterado combinado com o existente)
    nova_data_pedido   = update_data.get("data_pedido", pedido.data_pedido)
    nova_data_prevista = update_data.get("data_prevista", pedido.data_prevista)
    if nova_data_prevista < nova_data_pedido:
        raise HTTPException(
            status_code=400,
            detail="A data prevista não pode ser anterior à data do pedido.",
        )

    for campo, valor in update_data.items():
        setattr(pedido, campo, valor)

    db.commit()
    recalcular_alertas(db)
    db.refresh(pedido)
    return pedido


@router.delete("/pedidos/{pedido_id}", status_code=204)
def excluir_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor, PerfilUsuario.operador)),
) -> Response:
    pedido = db.get(Pedido, pedido_id)

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")

    if pedido.status != StatusPedido.pendente:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Apenas pedidos 'pendente' podem ser excluídos. "
                f"Status atual: '{pedido.status.value}'."
            ),
        )

    db.delete(pedido)
    db.commit()
    recalcular_alertas(db)

    return Response(status_code=204)


@router.put("/pedidos/{pedido_id}/entregar", response_model=PedidoSaida)
def entregar_pedido(
    pedido_id: int,
    dados: PedidoEntregar,
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor, PerfilUsuario.operador)),
):
    pedido = db.get(Pedido, pedido_id)

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")

    # Guarda contra entrega dupla: registrar_entrega cria uma linha em
    # historico_entregas — entregar duas vezes duplicaria o histórico e
    # inflaria as estatísticas do fornecedor.
    if pedido.status != StatusPedido.pendente:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Apenas pedidos 'pendente' podem ser entregues. "
                f"Status atual: '{pedido.status.value}'."
            ),
        )

    if dados.data_real_entrega < pedido.data_pedido:
        raise HTTPException(
            status_code=400,
            detail="A data de entrega não pode ser anterior à data do pedido.",
        )

    return registrar_entrega(db, pedido, dados.data_real_entrega)


# =============================================================================
# Alertas e Dashboard
# =============================================================================

@router.post("/recalcular-alertas")
def recalcular(
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor, PerfilUsuario.operador)),
):
    """Dispara manualmente o recálculo de estatísticas e alertas."""
    recalcular_alertas(db)
    return {"mensagem": "Estatísticas e alertas recalculados com sucesso."}



@router.get("/alertas", response_model=list[AlertaSaida])
def listar_alertas(
    obra_id:      int          | None = None,
    nivel_alerta: NivelAlerta  | None = None,
    db: Session = Depends(get_db),
    _: Usuario  = Depends(usuario_atual),
):
    return _buscar_alertas_pedidos(db, obra_id=obra_id, nivel_alerta=nivel_alerta)



@router.get("/dashboard", response_model=DashboardLogistico)
def dashboard_logistico(
    db: Session = Depends(get_db),
    _: Usuario  = Depends(usuario_atual),
):
    pedidos_ativos = (
        db.query(Pedido)
        .filter(Pedido.status == StatusPedido.pendente)
        .all()
    )

    alertas = _buscar_alertas_pedidos(db)   # sem filtros — dashboard mostra tudo

    return DashboardLogistico(
        total_pedidos_ativos=len(pedidos_ativos),
        alertas_vermelhos=sum(
            1 for p in pedidos_ativos if p.nivel_alerta == NivelAlerta.vermelho
        ),
        alertas_amarelos=sum(
            1 for p in pedidos_ativos if p.nivel_alerta == NivelAlerta.amarelo
        ),
        alertas_verdes=sum(
            1 for p in pedidos_ativos if p.nivel_alerta == NivelAlerta.verde
        ),
        fornecedores=db.query(Fornecedor).order_by(Fornecedor.id).all(),
        alertas=alertas,
    )