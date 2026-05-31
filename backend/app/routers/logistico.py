from fastapi import APIRouter, Depends, HTTPException
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


@router.get("/fornecedores", response_model=list[FornecedorSaida])
def listar_fornecedores(
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
):
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
def listar_pedidos(
    status: StatusPedido | None = None,
    obra_id: int | None = None,
    fornecedor_id: int | None = None,
    nivel_alerta: NivelAlerta | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
):
    query = db.query(Pedido)

    if status:
        query = query.filter(Pedido.status == status)

    if obra_id:
        query = query.filter(Pedido.obra_id == obra_id)

    if fornecedor_id:
        query = query.filter(Pedido.fornecedor_id == fornecedor_id)

    if nivel_alerta:
        query = query.filter(Pedido.nivel_alerta == nivel_alerta)

    return query.order_by(Pedido.data_prevista).all()


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
def editar_pedido(
    pedido_id: int,
    dados: PedidoCriar,
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir_perfis(PerfilUsuario.gestor, PerfilUsuario.operador)),
):
    pedido = db.get(Pedido, pedido_id)

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")

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

    pedido.data_pedido = dados.data_pedido
    pedido.data_prevista = dados.data_prevista
    pedido.tipo_insumo = dados.tipo_insumo
    pedido.fornecedor_id = dados.fornecedor_id
    pedido.obra_id = dados.obra_id
    pedido.prioridade = dados.prioridade
    pedido.observacao = dados.observacao

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

    if dados.data_real_entrega < pedido.data_pedido:
        raise HTTPException(
            status_code=400,
            detail="A data de entrega não pode ser anterior à data do pedido.",
        )

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
    nivel_alerta: NivelAlerta | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
):
    query = db.query(Pedido).filter(Pedido.status == StatusPedido.pendente)

    if obra_id:
        query = query.filter(Pedido.obra_id == obra_id)

    if nivel_alerta:
        query = query.filter(Pedido.nivel_alerta == nivel_alerta)

    pedidos = query.order_by(Pedido.data_prevista).all()

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
def dashboard_logistico(
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
):
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