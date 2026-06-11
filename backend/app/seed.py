
"""
Seed de dados iniciais de demonstração.

Idempotente: verifica a existência de usuários antes de inserir qualquer dado.
Cada bloco de inserção tem tratamento de erro independente para que a falha
em um candidato (ex: spaCy indisponível) não impeça o resto do seed.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy.orm import Session

from .auth import criar_hash_senha
from .models import (
    Candidato,
    Fornecedor,
    HistoricoEntrega,
    Obra,
    Pedido,
    PerfilUsuario,
    Prioridade,
    StatusObra,
    StatusPedido,
    Usuario,
    Vaga,
)
from .services.logistico_ml import recalcular_alertas
from .services.rh_nlp import processar_curriculo

logger = logging.getLogger(__name__)


def criar_dados_iniciais(db: Session) -> None:
    """
    Popula o banco com dados de demonstração se estiver vazio.

    Levanta exceção em caso de falha — o chamador (main._executar_seed)
    faz o rollback e registra o erro sem derrubar o servidor.
    """
    # ── Guarda de idempotência ────────────────────────────────────────────
    try:
        if db.query(Usuario).first():
            logger.info("Seed: banco já possui dados — nenhuma ação necessária.")
            return
    except Exception as exc:
        # As tabelas podem não existir se o Alembic ainda não rodou.
        raise RuntimeError(
            f"Seed: não foi possível consultar a tabela 'usuarios'. "
            f"Verifique se 'alembic upgrade head' foi executado. Detalhe: {exc}"
        ) from exc

    logger.info("Seed: banco vazio — criando dados iniciais de demonstração.")

    # ── Usuários ──────────────────────────────────────────────────────────
    usuarios = [
        Usuario(
            nome="Gestor Demo",
            email="gestor@empresa.com",
            senha_hash=criar_hash_senha("123456"),
            perfil=PerfilUsuario.gestor,
        ),
        Usuario(
            nome="Operador Demo",
            email="operador@empresa.com",
            senha_hash=criar_hash_senha("123456"),
            perfil=PerfilUsuario.operador,
        ),
        Usuario(
            nome="RH Demo",
            email="rh@empresa.com",
            senha_hash=criar_hash_senha("123456"),
            perfil=PerfilUsuario.rh,
        ),
    ]
    db.add_all(usuarios)

    # ── Obras ─────────────────────────────────────────────────────────────
    obra_a = Obra(
        nome="Obra A — Residencial Jardim",
        endereco="Rua das Palmeiras, 100",
        status=StatusObra.em_andamento,
        prioridade=Prioridade.alta,
        data_inicio=date.today() - timedelta(days=45),
    )
    obra_b = Obra(
        nome="Obra B — Galpão Industrial",
        endereco="Av. Central, 900",
        status=StatusObra.em_andamento,
        prioridade=Prioridade.media,
        data_inicio=date.today() - timedelta(days=30),
    )
    db.add_all([obra_a, obra_b])

    # ── Fornecedores ──────────────────────────────────────────────────────
    fornecedor_x = Fornecedor(
        nome="Fornecedor X Materiais",
        contato="compras@fornecedorx.com",
        observacao="Histórico de atraso em cimento.",
    )
    fornecedor_y = Fornecedor(
        nome="Fornecedor Y Aços",
        contato="vendas@fornecedory.com",
        observacao="Monitorar em dezembro.",
    )
    fornecedor_z = Fornecedor(
        nome="Fornecedor Z Acabamentos",
        contato="contato@fornecedorz.com",
        observacao="Baixa taxa de atraso.",
    )
    db.add_all([fornecedor_x, fornecedor_y, fornecedor_z])

    # Commit intermediário para gerar IDs dos fornecedores e obras
    db.commit()
    logger.info("Seed: usuários, obras e fornecedores criados.")

    # ── Histórico de entregas ─────────────────────────────────────────────
    historicos = [
        HistoricoEntrega(fornecedor_id=fornecedor_x.id, dias_atraso=6,  tipo_insumo="cimento",     mes_referencia=date(2025, 10, 1)),
        HistoricoEntrega(fornecedor_id=fornecedor_x.id, dias_atraso=8,  tipo_insumo="cimento",     mes_referencia=date(2025, 11, 1)),
        HistoricoEntrega(fornecedor_id=fornecedor_x.id, dias_atraso=4,  tipo_insumo="cimento",     mes_referencia=date(2025, 12, 1)),
        HistoricoEntrega(fornecedor_id=fornecedor_x.id, dias_atraso=0,  tipo_insumo="tinta",       mes_referencia=date(2026,  1, 1)),
        HistoricoEntrega(fornecedor_id=fornecedor_y.id, dias_atraso=2,  tipo_insumo="aço",         mes_referencia=date(2025, 10, 1)),
        HistoricoEntrega(fornecedor_id=fornecedor_y.id, dias_atraso=5,  tipo_insumo="aço",         mes_referencia=date(2025, 11, 1)),
        HistoricoEntrega(fornecedor_id=fornecedor_y.id, dias_atraso=-1, tipo_insumo="aço",         mes_referencia=date(2026,  1, 1)),
        HistoricoEntrega(fornecedor_id=fornecedor_z.id, dias_atraso=0,  tipo_insumo="tinta",       mes_referencia=date(2025, 11, 1)),
        HistoricoEntrega(fornecedor_id=fornecedor_z.id, dias_atraso=-2, tipo_insumo="tinta",       mes_referencia=date(2025, 12, 1)),
        HistoricoEntrega(fornecedor_id=fornecedor_z.id, dias_atraso=1,  tipo_insumo="revestimento",mes_referencia=date(2026,  1, 1)),
    ]
    db.add_all(historicos)

    # ── Pedidos ───────────────────────────────────────────────────────────
    pedidos = [
        Pedido(
            data_pedido=date.today() - timedelta(days=2),
            data_prevista=date.today() + timedelta(days=3),
            tipo_insumo="cimento",
            fornecedor_id=fornecedor_x.id,
            obra_id=obra_a.id,
            prioridade=Prioridade.alta,
            status=StatusPedido.pendente,
            observacao="Pedido crítico para concretagem.",
        ),
        Pedido(
            data_pedido=date.today() - timedelta(days=5),
            data_prevista=date.today() + timedelta(days=7),
            tipo_insumo="aço",
            fornecedor_id=fornecedor_y.id,
            obra_id=obra_b.id,
            prioridade=Prioridade.media,
            status=StatusPedido.pendente,
            observacao="Material para estrutura metálica.",
        ),
        Pedido(
            data_pedido=date.today() - timedelta(days=1),
            data_prevista=date.today() + timedelta(days=12),
            tipo_insumo="tinta",
            fornecedor_id=fornecedor_z.id,
            obra_id=obra_a.id,
            prioridade=Prioridade.baixa,
            status=StatusPedido.pendente,
            observacao="Acabamento interno.",
        ),
    ]
    db.add_all(pedidos)

    # ── Vaga ──────────────────────────────────────────────────────────────
    vaga = Vaga(
        titulo="Pedreiro para obra residencial",
        tipo_obra="Residencial",
        requisitos="alvenaria, concreto, leitura de projetos",
        habilidades="pedreiro, alvenaria, concreto, acabamento",
    )
    db.add(vaga)
    db.commit()
    logger.info("Seed: pedidos e vaga criados.")

    # ── Candidatos (NLP tolerante a falha) ────────────────────────────────
    # processar_curriculo pode falhar se spaCy não estiver disponível.
    # Cada candidato é processado de forma independente para que a falha em
    # um não impeça a criação dos demais.
    textos_candidatos = [
        (
            "João da Silva",
            "joao@email.com",
            "Pedreiro com 6 anos de experiência em alvenaria, concreto, "
            "acabamento e leitura de projetos.",
        ),
        (
            "Maria Oliveira",
            "maria@email.com",
            "Mestre de obras com 9 anos de experiência em gestão de equipe, "
            "segurança do trabalho e leitura de projetos.",
        ),
        (
            "Carlos Pereira",
            "carlos@email.com",
            "Servente com 2 anos de experiência em apoio de obra, "
            "pintura e acabamento.",
        ),
    ]

    candidatos_criados = 0
    for nome, email, texto in textos_candidatos:
        try:
            dados = processar_curriculo(nome, texto)
            db.add(
                Candidato(
                    nome=nome,
                    email=email,
                    cargo=dados.cargo,
                    experiencia_anos=dados.experiencia_anos,
                    habilidades=", ".join(dados.habilidades),
                    curriculo_texto=texto,
                    resumo=dados.resumo,
                )
            )
            candidatos_criados += 1
        except Exception as exc:
            logger.warning(
                "Seed: falha ao processar candidato '%s' (NLP): %s — "
                "criando com dados mínimos.",
                nome, exc,
            )
            # Cria o candidato sem processamento NLP para não perder o registro
            db.add(
                Candidato(
                    nome=nome,
                    email=email,
                    cargo=None,
                    experiencia_anos=0.0,
                    habilidades="",
                    curriculo_texto=texto,
                    resumo=f"Resumo de {nome} — processamento automático indisponível no momento.",
                )
            )
            candidatos_criados += 1

    db.commit()
    logger.info("Seed: %d candidato(s) criado(s).", candidatos_criados)

    # ── Recalcular alertas logísticos com base no histórico semeado ───────
    try:
        recalcular_alertas(db)
        logger.info("Seed: alertas logísticos recalculados.")
    except Exception as exc:
        logger.warning("Seed: falha ao recalcular alertas: %s", exc)

    logger.info(
        "Seed concluído: 3 usuários, 2 obras, 3 fornecedores, "
        "3 pedidos, 1 vaga, %d candidato(s).",
        candidatos_criados,
    )