"use client";

import { useEffect, useState } from "react";
import { apiJson, loginDemo } from "../../lib/api";

type Fornecedor = {
  id: number;
  nome: string;
  contato: string;
  media_atraso_dias: number;
  taxa_atraso: number;
  total_pedidos: number;
  observacao: string | null;
};

type Pedido = {
  id: number;
  data_pedido: string;
  data_prevista: string;
  data_real_entrega: string | null;
  tipo_insumo: string;
  fornecedor_id: number;
  obra_id: number;
  prioridade: string;
  status: string;
  prob_atraso: number;
  nivel_alerta: string;
  texto_alerta: string;
};

export default function LogisticoPage() {
  const [fornecedores, setFornecedores] = useState<Fornecedor[]>([]);
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);

  async function carregar() {
    setCarregando(true);
    try {
      const [f, p] = await Promise.all([
        apiJson<Fornecedor[]>("/logistico/fornecedores"),
        apiJson<Pedido[]>("/logistico/pedidos"),
      ]);
      setFornecedores(f);
      setPedidos(p);
      setErro("");
    } catch (e) {
      setFornecedores([]);
      setPedidos([]);
      setErro(e instanceof Error ? e.message : "Faça login para visualizar a logística.");
    } finally {
      setCarregando(false);
    }
  }

  async function entrar() {
    setCarregando(true);
    setErro("");
    try {
      await loginDemo();
      await carregar();
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha ao fazer login.");
    } finally {
      setCarregando(false);
    }
  }

  async function recalcular() {
    setCarregando(true);
    try {
      await apiJson("/logistico/recalcular-alertas", { method: "POST" });
      await carregar();
      setErro("");
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não foi possível recalcular os alertas.");
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    carregar();
  }, []);

  return (
    <main className="container">
      <section className="card">
        <h1>Módulo Logístico</h1>
        <p className="muted">Controle de pedidos, fornecedores, estatísticas e risco de atraso.</p>
        {erro && <p className="error">{erro}</p>}
        {erro ? (
          <button className="button" onClick={entrar} disabled={carregando}>{carregando ? "Entrando..." : "Entrar com login de demonstração"}</button>
        ) : (
          <button className="button" onClick={recalcular} disabled={carregando}>{carregando ? "Processando..." : "Recalcular alertas"}</button>
        )}
      </section>

      <h2 className="section-title">Pedidos e alertas</h2>
      <table className="table">
        <thead>
          <tr>
            <th>Insumo</th>
            <th>Previsão</th>
            <th>Prioridade</th>
            <th>Status</th>
            <th>Prob.</th>
            <th>Alerta</th>
            <th>Mensagem</th>
          </tr>
        </thead>
        <tbody>
          {pedidos.map((pedido) => (
            <tr key={pedido.id}>
              <td>{pedido.tipo_insumo}</td>
              <td>{pedido.data_prevista}</td>
              <td>{pedido.prioridade}</td>
              <td>{pedido.status}</td>
              <td>{Math.round(pedido.prob_atraso * 100)}%</td>
              <td><span className={`badge ${pedido.nivel_alerta}`}>{pedido.nivel_alerta}</span></td>
              <td>{pedido.texto_alerta}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 className="section-title">Fornecedores</h2>
      <table className="table">
        <thead>
          <tr>
            <th>Nome</th>
            <th>Contato</th>
            <th>Média atraso</th>
            <th>Taxa atraso</th>
            <th>Total histórico</th>
            <th>Observação</th>
          </tr>
        </thead>
        <tbody>
          {fornecedores.map((f) => (
            <tr key={f.id}>
              <td>{f.nome}</td>
              <td>{f.contato}</td>
              <td>{f.media_atraso_dias.toFixed(1)} dia(s)</td>
              <td>{Math.round(f.taxa_atraso * 100)}%</td>
              <td>{f.total_pedidos}</td>
              <td>{f.observacao || "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
