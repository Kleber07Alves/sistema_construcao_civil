from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import exigir_perfis, usuario_atual
from ..database import get_db
from ..models import Fornecedor, HistoricoEntrega, NivelAlerta, Obra, Pedido, PerfilUsuario, StatusPedido, Usuario
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


@router.get("/fornecedores", response_model=list[FornecedorSaida])
def listar_fornecedores(db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return db.query(Fornecedor).order_by(Fornecedor.id).all()


@router.post("/fornecedores", response_model=FornecedorSaida)
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


@router.post("/historico", response_model=HistoricoSaida)
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


@router.get("/pedidos", response_model=list[PedidoSaida])
def listar_pedidos(db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)):
    return db.query(Pedido).order_by(Pedido.id).all()


@router.post("/pedidos", response_model=PedidoSaida)
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

    pedido = Pedido(**dados.model_dump(), status=StatusPedido.pendente)
    db.add(pedido)
    db.commit()
    db.refresh(pedido)
    recalcular_alertas(db)
    db.refresh(pedido)
    return pedido


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


@router.post("/recalcular-alertas")
def recalcular(
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor, PerfilUsuario.operador)),
):
    recalcular_alertas(db)
    return {"mensagem": "Estatísticas e alertas recalculados com sucesso."}


@router.get("/alertas", response_model=list[AlertaSaida])
def listar_alertas(
    obra_id: int | None = None,
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
        alertas_vermelhos=sum(1 for p in pedidos_ativos if p.nivel_alerta == NivelAlerta.vermelho),
        alertas_amarelos=sum(1 for p in pedidos_ativos if p.nivel_alerta == NivelAlerta.amarelo),
        alertas_verdes=sum(1 for p in pedidos_ativos if p.nivel_alerta == NivelAlerta.verde),
        fornecedores=db.query(Fornecedor).order_by(Fornecedor.id).all(),
        alertas=alertas,
    )
