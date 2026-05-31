"use client";

import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { apiJson, getUsuario, loginDemo, logout } from "../lib/api";

type Dashboard = {
  total_pedidos_ativos: number;
  alertas_vermelhos: number;
  alertas_amarelos: number;
  alertas_verdes: number;
  alertas: Array<{
    pedido_id: number;
    obra: string;
    fornecedor: string;
    tipo_insumo: string;
    prioridade: string;
    prob_atraso: number;
    nivel_alerta: string;
    texto_alerta: string;
  }>;
};

type Obra = { id: number; nome: string; endereco: string; status: string; prioridade: string };
type Vaga = { id: number; titulo: string; tipo_obra: string; status: string };

export default function Home() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [obras, setObras] = useState<Obra[]>([]);
  const [vagas, setVagas] = useState<Vaga[]>([]);
  const [erro, setErro] = useState<string>("");
  const [usuario, setUsuario] = useState<string>("");
  const [carregando, setCarregando] = useState(false);

  async function carregar() {
    setCarregando(true);
    try {
      const [dash, obrasData, vagasData] = await Promise.all([
        apiJson<Dashboard>("/logistico/dashboard"),
        apiJson<Obra[]>("/core/obras"),
        apiJson<Vaga[]>("/rh/vagas"),
      ]);
      setDashboard(dash);
      setObras(obrasData);
      setVagas(vagasData);
      setUsuario(getUsuario() || "Gestor Demo");
      setErro("");
    } catch (e) {
      setDashboard(null);
      setErro(e instanceof Error ? e.message : "Faça login para carregar os dados.");
    } finally {
      setCarregando(false);
    }
  }

  async function entrarDemo() {
    setCarregando(true);
    setErro("");
    try {
      const login = await loginDemo();
      setUsuario(login.nome);
      await carregar();
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha ao fazer login.");
    } finally {
      setCarregando(false);
    }
  }

  function sair() {
    logout();
    setUsuario("");
    setDashboard(null);
    setObras([]);
    setVagas([]);
    setErro("Login removido. Clique novamente para entrar com o usuário de demonstração.");
  }

  useEffect(() => {
    carregar();
  }, []);

  const dadosGrafico = dashboard
    ? [
        { nome: "Vermelho", total: dashboard.alertas_vermelhos },
        { nome: "Amarelo", total: dashboard.alertas_amarelos },
        { nome: "Verde", total: dashboard.alertas_verdes },
      ]
    : [];

  return (
    <main className="container">
      <section className="card">
        <h1>Dashboard Geral</h1>
        <p className="muted">Painel consolidado de obras, alertas logísticos e vagas abertas.</p>
        {usuario && <p>Usuário logado: <strong>{usuario}</strong></p>}
        {erro && <p className="error">{erro}</p>}
        <div className="actions">
          {!dashboard && <button className="button" onClick={entrarDemo} disabled={carregando}>{carregando ? "Entrando..." : "Entrar com login de demonstração"}</button>}
          {dashboard && <button className="button secondary" onClick={sair}>Sair</button>}
          <button className="button secondary" onClick={carregar} disabled={carregando}>{carregando ? "Carregando..." : "Atualizar dados"}</button>
        </div>
      </section>

      {dashboard && (
        <>
          <section className="grid section-title">
            <div className="card"><h3>Pedidos ativos</h3><strong style={{ fontSize: 32 }}>{dashboard.total_pedidos_ativos}</strong></div>
            <div className="card"><h3>Alertas vermelhos</h3><strong style={{ fontSize: 32 }}>{dashboard.alertas_vermelhos}</strong></div>
            <div className="card"><h3>Obras cadastradas</h3><strong style={{ fontSize: 32 }}>{obras.length}</strong></div>
            <div className="card"><h3>Vagas abertas</h3><strong style={{ fontSize: 32 }}>{vagas.length}</strong></div>
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
              {dashboard.alertas.slice(0, 4).map((alerta) => (
                <p key={alerta.pedido_id}>
                  <span className={`badge ${alerta.nivel_alerta}`}>{alerta.nivel_alerta}</span>{" "}
                  {alerta.texto_alerta}
                </p>
              ))}
            </div>
          </section>
        </>
      )}
    </main>
  );
}
