"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { apiJson } from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

type Dashboard = {
  total_pedidos_ativos: number;
  alertas_vermelhos:    number;
  alertas_amarelos:     number;
  alertas_verdes:       number;
  alertas: Array<{
    pedido_id:    number;
    obra:         string;
    fornecedor:   string;
    tipo_insumo:  string;
    prioridade:   string;
    prob_atraso:  number;
    nivel_alerta: string;
    texto_alerta: string;
  }>;
};

type Obra = { id: number; nome: string; endereco: string; status: string; prioridade: string };
type Vaga = { id: number; titulo: string; tipo_obra: string; status: string };

// ─── Componente ──────────────────────────────────────────────────────────────

export default function Home() {
  
  const { autenticado, usuario, loading: authLoading, logout } = useAuth();
  const router = useRouter();

  const [dashboard,  setDashboard]  = useState<Dashboard | null>(null);
  const [obras,      setObras]      = useState<Obra[]>([]);
  const [vagas,      setVagas]      = useState<Vaga[]>([]);
  const [erro,       setErro]       = useState<string>("");
  const [carregando, setCarregando] = useState(false);

  async function carregar() {
    setCarregando(true);
    setErro("");
    try {
      const [dash, obrasData, vagasData] = await Promise.all([
        apiJson<Dashboard>("/logistico/dashboard"),
        apiJson<Obra[]>("/core/obras"),
        apiJson<Vaga[]>("/rh/vagas"),
      ]);
      setDashboard(dash);
      setObras(obrasData);
      setVagas(vagasData);
    } catch (e) {
      setDashboard(null);
      setErro(e instanceof Error ? e.message : "Erro ao carregar os dados.");
    } finally {
      setCarregando(false);
    }
  }

  
  useEffect(() => {
    if (!authLoading && autenticado) {
      void carregar();
    }
  }, [authLoading, autenticado]);

  const dadosGrafico = dashboard
    ? [
        { nome: "Vermelho", total: dashboard.alertas_vermelhos },
        { nome: "Amarelo",  total: dashboard.alertas_amarelos  },
        { nome: "Verde",    total: dashboard.alertas_verdes    },
      ]
    : [];

  // ── Estados de renderização ────────────────────────────────────────────

  
  if (authLoading) {
    return (
      <main className="container">
        <section className="card">
          <p className="muted">Verificando autenticação…</p>
        </section>
      </main>
    );
  }

  if (!autenticado) {
    return (
      <main className="container">
        <section className="card">
          <h1>Dashboard Geral</h1>
          <p className="muted">
            Painel consolidado de obras, alertas logísticos e vagas abertas.
          </p>
          <p className="muted" style={{ marginTop: 8 }}>
            Faça login para acessar o painel de gestão.
          </p>
          <div className="actions" style={{ marginTop: 16 }}>
            <button className="button" onClick={() => router.push("/login")}>
              Ir para o login
            </button>
          </div>
        </section>
      </main>
    );
  }

  // ── Dashboard autenticado ──────────────────────────────────────────────
  return (
    <main className="container">
      <section className="card">
        <h1>Dashboard Geral</h1>
        <p className="muted">Painel consolidado de obras, alertas logísticos e vagas abertas.</p>
        {usuario && (
          <p>
            Usuário logado:{" "}
            <strong>
              {usuario.nome} ({usuario.perfil})
            </strong>
          </p>
        )}
        {erro && <p className="error">{erro}</p>}
        <div className="actions">
          <button
            className="button secondary"
            onClick={() => void carregar()}
            disabled={carregando}
          >
            {carregando ? "Carregando…" : "Atualizar dados"}
          </button>
          <button className="button secondary" onClick={logout}>
            Sair
          </button>
        </div>
      </section>

      {dashboard && (
        <>
          <section className="grid section-title">
            <div className="card">
              <h3>Pedidos ativos</h3>
              <strong style={{ fontSize: 32 }}>{dashboard.total_pedidos_ativos}</strong>
            </div>
            <div className="card">
              <h3>Alertas vermelhos</h3>
              <strong style={{ fontSize: 32 }}>{dashboard.alertas_vermelhos}</strong>
            </div>
            <div className="card">
              <h3>Obras cadastradas</h3>
              <strong style={{ fontSize: 32 }}>{obras.length}</strong>
            </div>
            <div className="card">
              <h3>Vagas abertas</h3>
              <strong style={{ fontSize: 32 }}>
                {vagas.filter((v) => v.status === "aberta").length}
              </strong>
            </div>
          </section>

          <section className="grid">
            <div className="card">
              <h2>Alertas por nível</h2>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={dadosGrafico}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="nome" />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="total" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="card">
              <h2>Principais alertas</h2>
              {dashboard.alertas.length === 0 ? (
                <p className="muted">Nenhum alerta pendente.</p>
              ) : (
                dashboard.alertas.slice(0, 4).map((alerta) => (
                  <p key={alerta.pedido_id}>
                    <span className={`badge ${alerta.nivel_alerta}`}>
                      {alerta.nivel_alerta}
                    </span>{" "}
                    {alerta.texto_alerta}
                  </p>
                ))
              )}
            </div>
          </section>
        </>
      )}

      {!dashboard && !carregando && !erro && (
        <section className="card">
          <p className="muted">Sem dados para exibir. Clique em "Atualizar dados".</p>
        </section>
      )}
    </main>
  );
}