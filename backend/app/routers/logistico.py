#Router do Módulo Logístico.

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import case
from sqlalchemy.orm import Session

from ..auth import exigir_perfis, usuario_atual
from ..database import get_db
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
    FornecedorCriar,
    FornecedorSaida,
    HistoricoCriar,
    HistoricoSaida,
    PedidoCriar,
    PedidoEntregar,
    PedidoSaida,
)
from ..services.logistico_ml import recalcular_alertas, registrar_entrega

router = APIRouter(prefix="/logistico", tags=["Módulo Logístico"])


# =============================================================================
# Utilitário interno — compartilhado entre /alertas e /dashboard
# =============================================================================

def _nivel_alerta_order():
   
    return case(
        (Pedido.nivel_alerta == NivelAlerta.vermelho, 1),
        (Pedido.nivel_alerta == NivelAlerta.amarelo,  2),
        else_=3,
    )


def _buscar_alertas_pedidos(
    db: Session,
    obra_id: int | None = None,
) -> list[AlertaSaida]:
    """
    Busca pedidos pendentes e os serializa como AlertaSaida, ordenados por
    severidade (vermelho → amarelo → verde) e depois por data prevista.

    Função interna extraída para que listar_alertas() e dashboard_logistico()
    compartilhem a mesma lógica sem que um endpoint chame o outro diretamente
    (antipadrão: chamada direta de função de rota bypassa o ciclo FastAPI e
    torna o código frágil a mudanças de dependências).

    Args:
        db: sessão do banco de dados.
        obra_id: filtro opcional por obra.
    """
    query = db.query(Pedido).filter(Pedido.status == StatusPedido.pendente)

    if obra_id is not None:
        query = query.filter(Pedido.obra_id == obra_id)

    pedidos = query.order_by(_nivel_alerta_order(), Pedido.data_prevista).all()

    return [
        AlertaSaida(
            pedido_id=p.id,
            obra=p.obra.nome,
            fornecedor=p.fornecedor.nome,
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
):
    return db.query(Fornecedor).order_by(Fornecedor.id).all()


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
def editar_fornecedor(
    fornecedor_id: int,
    dados: FornecedorCriar,
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor, PerfilUsuario.operador)),
):
    fornecedor = db.get(Fornecedor, fornecedor_id)

    if not fornecedor:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado.")

    fornecedor.nome = dados.nome
    fornecedor.contato = dados.contato
    fornecedor.observacao = dados.observacao

    db.commit()
    db.refresh(fornecedor)
    return fornecedor


@router.delete("/fornecedores/{fornecedor_id}")
def excluir_fornecedor(
    fornecedor_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor)),
):
    fornecedor = db.get(Fornecedor, fornecedor_id)

    if not fornecedor:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado.")

    possui_pedidos = db.query(Pedido).filter(Pedido.fornecedor_id == fornecedor_id).first()
    possui_historico = db.query(HistoricoEntrega).filter(HistoricoEntrega.fornecedor_id == fornecedor_id).first()

    if possui_pedidos or possui_historico:
        raise HTTPException(
            status_code=400,
            detail="Não é possível excluir fornecedor com pedidos ou histórico vinculado.",
        )

    db.delete(fornecedor)
    db.commit()

    return {"mensagem": "Fornecedor excluído com sucesso."}


# =============================================================================
# Histórico de entregas
# =============================================================================

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
def listar_pedidos(db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return db.query(Pedido).order_by(Pedido.id).all()


@router.post("/pedidos", response_model=PedidoSaida, status_code=201)
def criar_pedido(
    dados: PedidoCriar,
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor, PerfilUsuario.operador)),
):
    fornecedor = db.get(Fornecedor, dados.fornecedor_id)
    obra = db.get(Obra, dados.obra_id)
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


@router.delete("/pedidos/{pedido_id}")
def excluir_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor, PerfilUsuario.operador)),
):
    pedido = db.get(Pedido, pedido_id)

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")

    if pedido.status != StatusPedido.pendente:
        raise HTTPException(
            status_code=400,
            detail="Só é possível excluir pedidos pendentes.",
        )

    db.delete(pedido)
    db.commit()

    recalcular_alertas(db)

    return {"mensagem": "Pedido excluído com sucesso."}


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
    return registrar_entrega(db, pedido, dados.data_real_entrega)


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
    return Response(status_code=204)


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
    obra_id: int | None = None,
    nivel_alerta: NivelAlerta | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
):
    query = db.query(Pedido).filter(Pedido.status == StatusPedido.pendente)
    if obra_id:
        query = query.filter(Pedido.obra_id == obra_id)
    pedidos = query.order_by(Pedido.nivel_alerta, Pedido.data_prevista).all()
    return [
        AlertaSaida(
            pedido_id=p.id,
            obra=p.obra.nome,
            fornecedor=p.fornecedor.nome,
            tipo_insumo=p.tipo_insumo,
            prioridade=p.prioridade,
            data_prevista=p.data_prevista,
            prob_atraso=p.prob_atraso,
            nivel_alerta=p.nivel_alerta,
            texto_alerta=p.texto_alerta,
        )
        for p in pedidos
    ]


@router.get("/dashboard", response_model=DashboardLogistico)
def dashboard_logistico(db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    pedidos_ativos = db.query(Pedido).filter(Pedido.status == StatusPedido.pendente).all()
    alertas = listar_alertas(db=db, _=_)
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