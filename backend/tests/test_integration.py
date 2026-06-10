"""
test_integration.py

Cobertura:
  1. Login (sucesso e senha errada)
  2. Listar obras
  3. Criar fornecedor
  4. Criar pedido (sucesso e data inválida)
  5. Recalcular alertas
  6. Dashboard logístico (estrutura + ordenação por severidade)
  7. Criar vaga
  8. Criar candidato
  9. Ranking de vaga (score decrescente)
  +  Filtros de pedidos por status, obra_id, fornecedor_id, nivel_alerta

Dados semeados pelo criar_dados_iniciais() disponíveis em todos os testes:
  • gestor@empresa.com  / 123456  (perfil: gestor)
  • operador@empresa.com / 123456 (perfil: operador)
  • rh@empresa.com / 123456       (perfil: rh)
  • Obra A (id=1, prioridade=alta)   | Obra B (id=2, prioridade=media)
  • Fornecedor X (id=1) | Y (id=2) | Z (id=3)
  • 3 pedidos pendentes (cimento, aço, tinta)
  • 1 vaga + 3 candidatos
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest


# =============================================================================
# 1. Login
# =============================================================================

class TestLogin:
    def test_login_gestor_retorna_token(self, client):
        r = client.post(
            "/auth/login",
            json={"email": "gestor@empresa.com", "senha": "123456"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["perfil"] == "gestor"
        assert data["nome"] == "Gestor Demo"

    def test_login_senha_errada_retorna_401(self, client):
        r = client.post(
            "/auth/login",
            json={"email": "gestor@empresa.com", "senha": "senha_errada"},
        )
        assert r.status_code == 401

    def test_login_email_inexistente_retorna_401(self, client):
        r = client.post(
            "/auth/login",
            json={"email": "naoexiste@empresa.com", "senha": "123456"},
        )
        assert r.status_code == 401

    def test_endpoint_protegido_sem_token_retorna_403(self, client):
        r = client.get("/core/obras")
        assert r.status_code == 403


# =============================================================================
# 2. Listar obras
# =============================================================================

class TestObras:
    def test_listar_obras_retorna_lista(self, client, headers):
        r = client.get("/core/obras", headers=headers)
        assert r.status_code == 200
        obras = r.json()
        assert isinstance(obras, list)
        assert len(obras) >= 2

    def test_listar_obras_contem_campos_obrigatorios(self, client, headers):
        r = client.get("/core/obras", headers=headers)
        assert r.status_code == 200
        for obra in r.json():
            assert "id"         in obra
            assert "nome"       in obra
            assert "status"     in obra
            assert "prioridade" in obra

    def test_criar_obra(self, client, headers):
        payload = {
            "nome":       "Obra Teste Integration",
            "endereco":   "Rua dos Testes, 42",
            "status":     "planejada",
            "prioridade": "baixa",
        }
        r = client.post("/core/obras", json=payload, headers=headers)
        assert r.status_code == 201
        data = r.json()
        assert data["nome"] == "Obra Teste Integration"
        assert "id" in data


# =============================================================================
# 3. Criar fornecedor
# =============================================================================

class TestFornecedores:
    def test_criar_fornecedor_retorna_201(self, client, headers):
        payload = {
            "nome":       "Fornecedor Integration Test",
            "contato":    "integration@test.com",
            "observacao": "Criado pelos testes automatizados.",
        }
        r = client.post("/logistico/fornecedores", json=payload, headers=headers)
        assert r.status_code == 201
        data = r.json()
        assert data["nome"] == "Fornecedor Integration Test"
        assert "id" in data
        assert data["media_atraso_dias"] == 0.0
        assert data["taxa_atraso"]       == 0.0
        assert data["total_pedidos"]     == 0

    def test_listar_fornecedores(self, client, headers):
        r = client.get("/logistico/fornecedores", headers=headers)
        assert r.status_code == 200
        assert len(r.json()) >= 3

    def test_atualizar_fornecedor_parcial(self, client, headers):
        r_criar = client.post(
            "/logistico/fornecedores",
            json={"nome": "Fornecedor Para Atualizar", "contato": "upd@test.com"},
            headers=headers,
        )
        assert r_criar.status_code == 201
        forn_id = r_criar.json()["id"]

        r_upd = client.put(
            f"/logistico/fornecedores/{forn_id}",
            json={"nome": "Fornecedor Atualizado"},
            headers=headers,
        )
        assert r_upd.status_code == 200
        assert r_upd.json()["nome"]    == "Fornecedor Atualizado"
        assert r_upd.json()["contato"] == "upd@test.com"

    def test_fornecedor_inexistente_retorna_404(self, client, headers):
        r = client.put(
            "/logistico/fornecedores/99999",
            json={"nome": "X"},
            headers=headers,
        )
        assert r.status_code == 404


# =============================================================================
# 4. Criar pedido
# =============================================================================

class TestPedidos:
    def test_criar_pedido_retorna_201(self, client, headers):
        payload = {
            "data_pedido":   str(date.today()),
            "data_prevista": str(date.today() + timedelta(days=10)),
            "tipo_insumo":   "tijolo",
            "fornecedor_id": 1,
            "obra_id":       1,
            "prioridade":    "media",
            "observacao":    "Pedido criado pelo teste de integração.",
        }
        r = client.post("/logistico/pedidos", json=payload, headers=headers)
        assert r.status_code == 201
        data = r.json()
        assert data["tipo_insumo"] == "tijolo"
        assert data["status"]      == "pendente"
        assert "id"           in data
        assert "prob_atraso"  in data
        assert "nivel_alerta" in data

    def test_criar_pedido_data_prevista_anterior_retorna_400(self, client, headers):
        payload = {
            "data_pedido":   str(date.today()),
            "data_prevista": str(date.today() - timedelta(days=1)),
            "tipo_insumo":   "areia",
            "fornecedor_id": 1,
            "obra_id":       1,
        }
        r = client.post("/logistico/pedidos", json=payload, headers=headers)
        assert r.status_code == 400

    def test_criar_pedido_fornecedor_inexistente_retorna_404(self, client, headers):
        payload = {
            "data_pedido":   str(date.today()),
            "data_prevista": str(date.today() + timedelta(days=5)),
            "tipo_insumo":   "ferro",
            "fornecedor_id": 99999,
            "obra_id":       1,
        }
        r = client.post("/logistico/pedidos", json=payload, headers=headers)
        assert r.status_code == 404

    def test_criar_pedido_obra_inexistente_retorna_404(self, client, headers):
        payload = {
            "data_pedido":   str(date.today()),
            "data_prevista": str(date.today() + timedelta(days=5)),
            "tipo_insumo":   "ferro",
            "fornecedor_id": 1,
            "obra_id":       99999,
        }
        r = client.post("/logistico/pedidos", json=payload, headers=headers)
        assert r.status_code == 404


# =============================================================================
# 5. Recalcular alertas
# =============================================================================

class TestRecalcularAlertas:
    def test_recalcular_alertas_retorna_200(self, client, headers):
        r = client.post("/logistico/recalcular-alertas", headers=headers)
        assert r.status_code == 200
        assert "mensagem" in r.json()

    def test_recalcular_alertas_sem_token_retorna_403(self, client):
        r = client.post("/logistico/recalcular-alertas")
        assert r.status_code == 403


# =============================================================================
# 6. Dashboard logístico
# =============================================================================

class TestDashboard:
    def test_dashboard_retorna_estrutura_correta(self, client, headers):
        r = client.get("/logistico/dashboard", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert "total_pedidos_ativos" in data
        assert "alertas_vermelhos"    in data
        assert "alertas_amarelos"     in data
        assert "alertas_verdes"       in data
        assert "alertas"              in data
        assert "fornecedores"         in data
        assert isinstance(data["alertas"],      list)
        assert isinstance(data["fornecedores"], list)

    def test_dashboard_contadores_nao_negativos(self, client, headers):
        r = client.get("/logistico/dashboard", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["total_pedidos_ativos"] >= 0
        assert data["alertas_vermelhos"]    >= 0
        assert data["alertas_amarelos"]     >= 0
        assert data["alertas_verdes"]       >= 0

    def test_dashboard_alertas_ordenados_por_severidade(self, client, headers):
        """
        CORREÇÃO verificada: vermelho(0) → amarelo(1) → verde(2).
        A ordenação antiga (Pedido.nivel_alerta direto) era alfabética:
        amarelo → verde → vermelho — ERRADA.
        """
        r = client.get("/logistico/dashboard", headers=headers)
        assert r.status_code == 200
        alertas = r.json()["alertas"]
        if len(alertas) < 2:
            pytest.skip("Menos de 2 alertas — ordenação não verificável")

        prioridade = {"vermelho": 0, "amarelo": 1, "verde": 2}
        niveis = [a["nivel_alerta"] for a in alertas]
        for i in range(len(niveis) - 1):
            assert prioridade[niveis[i]] <= prioridade[niveis[i + 1]], (
                f"Ordem errada na pos {i}: '{niveis[i]}' antes de '{niveis[i+1]}'. "
                f"Sequência: {niveis}"
            )

    def test_dashboard_soma_alertas_confere_com_total(self, client, headers):
        r = client.get("/logistico/dashboard", headers=headers)
        assert r.status_code == 200
        data = r.json()
        soma = (
            data["alertas_vermelhos"]
            + data["alertas_amarelos"]
            + data["alertas_verdes"]
        )
        assert soma == data["total_pedidos_ativos"]


# =============================================================================
# 7. Criar vaga
# =============================================================================

class TestVagas:
    def test_criar_vaga_retorna_201(self, client, headers):
        payload = {
            "titulo":      "Engenheiro Civil Sênior",
            "tipo_obra":   "residencial",
            "requisitos":  "CREA ativo, 5 anos de experiência em alvenaria",
            "habilidades": "AutoCAD, gestão de equipes, concreto armado",
            "status":      "aberta",
        }
        r = client.post("/rh/vagas", json=payload, headers=headers)
        assert r.status_code == 201
        data = r.json()
        assert data["titulo"] == "Engenheiro Civil Sênior"
        assert data["status"] == "aberta"
        assert "id" in data

    def test_listar_vagas(self, client, headers):
        r = client.get("/rh/vagas", headers=headers)
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_atualizar_status_vaga(self, client, headers):
        r_criar = client.post(
            "/rh/vagas",
            json={
                "titulo":      "Pedreiro Teste Atualização",
                "tipo_obra":   "industrial",
                "requisitos":  "alvenaria",
                "habilidades": "pedreiro",
            },
            headers=headers,
        )
        assert r_criar.status_code == 201
        vaga_id = r_criar.json()["id"]

        r_upd = client.put(
            f"/rh/vagas/{vaga_id}",
            json={"status": "pausada"},
            headers=headers,
        )
        assert r_upd.status_code == 200
        assert r_upd.json()["status"] == "pausada"

    def test_vaga_inexistente_retorna_404(self, client, headers):
        r = client.get("/rh/vagas/99999/ranking", headers=headers)
        assert r.status_code == 404


# =============================================================================
# 8. Criar candidato
# =============================================================================

class TestCandidatos:
    def test_criar_candidato_retorna_201(self, client, headers):
        payload = {
            "nome":             "Ana Paula Teste",
            "email":            "ana.paula.integration@test.com",
            "cargo":            "Mestre de Obras",
            "experiencia_anos": 7,
            "habilidades":      "alvenaria, concreto, gestão de equipe",
            "curriculo_texto":  (
                "Mestre de obras com 7 anos de experiência em gestão de equipe, "
                "alvenaria e concreto armado. Segurança do trabalho."
            ),
        }
        r = client.post("/rh/candidatos", json=payload, headers=headers)
        assert r.status_code == 201
        data = r.json()
        assert data["nome"]             == "Ana Paula Teste"
        assert data["experiencia_anos"] == 7.0
        assert "id"     in data
        assert "resumo" in data

    def test_listar_candidatos(self, client, headers):
        r = client.get("/rh/candidatos", headers=headers)
        assert r.status_code == 200
        assert len(r.json()) >= 3

    def test_criar_candidato_campos_minimos(self, client, headers):
        payload = {
            "nome":  "Candidato Mínimo",
            "email": "candidato.minimo.integration@test.com",
        }
        r = client.post("/rh/candidatos", json=payload, headers=headers)
        assert r.status_code == 201
        assert r.json()["experiencia_anos"] == 0.0


# =============================================================================
# 9. Ranking de vaga
# =============================================================================

class TestRankingVaga:
    def test_ranking_retorna_lista_ordenada_por_score(self, client, headers):
        r_vaga = client.post(
            "/rh/vagas",
            json={
                "titulo":      "Eletricista Industrial para Ranking Test",
                "tipo_obra":   "industrial",
                "requisitos":  "elétrica, 3 anos de experiência",
                "habilidades": "eletricista, elétrica, segurança do trabalho",
            },
            headers=headers,
        )
        assert r_vaga.status_code == 201
        vaga_id = r_vaga.json()["id"]

        client.post(
            "/rh/candidatos",
            json={
                "nome":             "Ricardo Elet Ranking",
                "email":            "ricardo.elet.ranking@test.com",
                "cargo":            "eletricista",
                "experiencia_anos": 4,
                "habilidades":      "eletricista, elétrica, segurança do trabalho",
                "curriculo_texto":  "4 anos de experiência em elétrica industrial.",
            },
            headers=headers,
        )

        r = client.get(f"/rh/vagas/{vaga_id}/ranking", headers=headers)
        assert r.status_code == 200

        ranking = r.json()
        assert isinstance(ranking, list)
        assert len(ranking) >= 1

        for item in ranking:
            assert "candidato" in item
            assert "score"     in item
            assert "motivos"   in item
            assert isinstance(item["motivos"], list)

        scores = [item["score"] for item in ranking]
        assert scores == sorted(scores, reverse=True), (
            f"Ranking fora de ordem decrescente: {scores}"
        )

    def test_ranking_vaga_inexistente_retorna_404(self, client, headers):
        r = client.get("/rh/vagas/99999/ranking", headers=headers)
        assert r.status_code == 404


# =============================================================================
# Extras: Filtros de pedidos (CORREÇÃO verificada)
# =============================================================================

class TestFiltrosPedidos:
    def test_filtro_status_pendente(self, client, headers):
        r = client.get("/logistico/pedidos?status=pendente", headers=headers)
        assert r.status_code == 200
        for p in r.json():
            assert p["status"] == "pendente"

    def test_filtro_obra_id(self, client, headers):
        r = client.get("/logistico/pedidos?obra_id=1", headers=headers)
        assert r.status_code == 200
        for p in r.json():
            assert p["obra_id"] == 1

    def test_filtro_fornecedor_id(self, client, headers):
        r = client.get("/logistico/pedidos?fornecedor_id=1", headers=headers)
        assert r.status_code == 200
        for p in r.json():
            assert p["fornecedor_id"] == 1

    def test_filtro_nivel_alerta_verde(self, client, headers):
        r = client.get("/logistico/pedidos?nivel_alerta=verde", headers=headers)
        assert r.status_code == 200
        for p in r.json():
            assert p["nivel_alerta"] == "verde"

    def test_filtro_combinado_status_obra(self, client, headers):
        r = client.get("/logistico/pedidos?status=pendente&obra_id=1", headers=headers)
        assert r.status_code == 200
        for p in r.json():
            assert p["status"]  == "pendente"
            assert p["obra_id"] == 1

    def test_sem_filtro_retorna_todos(self, client, headers):
        r = client.get("/logistico/pedidos", headers=headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_alertas_com_filtro_nivel(self, client, headers):
        r = client.get("/logistico/alertas?nivel_alerta=verde", headers=headers)
        assert r.status_code == 200
        for a in r.json():
            assert a["nivel_alerta"] == "verde"