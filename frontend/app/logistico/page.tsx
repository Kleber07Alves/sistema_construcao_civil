"use client";

import { useEffect, useState, type FormEvent } from "react";
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

type Obra = {
  id: number;
  nome: string;
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

const hoje = new Date().toISOString().slice(0, 10);

export default function LogisticoPage() {
  const [fornecedores, setFornecedores] = useState<Fornecedor[]>([]);
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [obras, setObras] = useState<Obra[]>([]);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const [carregando, setCarregando] = useState(false);

  const [filtroStatus, setFiltroStatus] = useState("");
  const [filtroAlerta, setFiltroAlerta] = useState("");
  const [filtroObraId, setFiltroObraId] = useState("");

  const [fornecedorForm, setFornecedorForm] = useState({
    nome: "",
    contato: "",
    observacao: "",
  });

  const [pedidoForm, setPedidoForm] = useState({
    data_pedido: hoje,
    data_prevista: hoje,
    tipo_insumo: "",
    fornecedor_id: "",
    obra_id: "",
    prioridade: "media",
    observacao: "",
  });

  async function carregar() {
    setCarregando(true);

    try {
      const params = new URLSearchParams();

      if (filtroStatus) params.set("status", filtroStatus);
      if (filtroAlerta) params.set("nivel_alerta", filtroAlerta);
      if (filtroObraId) params.set("obra_id", filtroObraId);

      const query = params.toString();

      const [fornecedoresData, pedidosData, obrasData] = await Promise.all([
        apiJson<Fornecedor[]>("/logistico/fornecedores"),
        apiJson<Pedido[]>(`/logistico/pedidos${query ? `?${query}` : ""}`),
        apiJson<Obra[]>("/core/obras"),
      ]);

      setFornecedores(fornecedoresData);
      setPedidos(pedidosData);
      setObras(obrasData);
      setErro("");
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao carregar logística.");
    } finally {
      setCarregando(false);
    }
  }

  async function entrar() {
    try {
      await loginDemo();
      await carregar();
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha ao fazer login.");
    }
  }

  async function recalcular() {
    try {
      await apiJson("/logistico/recalcular-alertas", { method: "POST" });
      setSucesso("Alertas recalculados com sucesso.");
      await carregar();
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao recalcular alertas.");
    }
  }

  async function criarFornecedor(e: FormEvent) {
    e.preventDefault();

    try {
      await apiJson("/logistico/fornecedores", {
        method: "POST",
        body: JSON.stringify(fornecedorForm),
      });

      setFornecedorForm({ nome: "", contato: "", observacao: "" });
      setSucesso("Fornecedor cadastrado com sucesso.");
      await carregar();
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao cadastrar fornecedor.");
    }
  }

  async function criarPedido(e: FormEvent) {
    e.preventDefault();

    try {
      await apiJson("/logistico/pedidos", {
        method: "POST",
        body: JSON.stringify({
          data_pedido: pedidoForm.data_pedido,
          data_prevista: pedidoForm.data_prevista,
          tipo_insumo: pedidoForm.tipo_insumo,
          fornecedor_id: Number(pedidoForm.fornecedor_id),
          obra_id: Number(pedidoForm.obra_id),
          prioridade: pedidoForm.prioridade,
          observacao: pedidoForm.observacao,
        }),
      });

      setPedidoForm({
        data_pedido: hoje,
        data_prevista: hoje,
        tipo_insumo: "",
        fornecedor_id: "",
        obra_id: "",
        prioridade: "media",
        observacao: "",
      });

      setSucesso("Pedido cadastrado com sucesso.");
      await carregar();
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao cadastrar pedido.");
    }
  }

  async function excluirPedido(id: number) {
    const confirmar = confirm("Deseja realmente excluir este pedido?");

    if (!confirmar) return;

    try {
      await apiJson(`/logistico/pedidos/${id}`, { method: "DELETE" });
      setSucesso("Pedido excluído com sucesso.");
      await carregar();
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao excluir pedido.");
    }
  }

  async function entregarHoje(id: number) {
    try {
      await apiJson(`/logistico/pedidos/${id}/entregar`, {
        method: "PUT",
        body: JSON.stringify({ data_real_entrega: hoje }),
      });

      setSucesso("Pedido marcado como entregue.");
      await carregar();
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao entregar pedido.");
    }
  }

  useEffect(() => {
    carregar();
  }, []);

  return (
    <main className="container">
      <section className="card">
        <h1>Módulo Logístico</h1>
        <p className="muted">
          Controle de pedidos, fornecedores, estatísticas e risco de atraso.
        </p>

        {erro && <p className="error">{erro}</p>}
        {sucesso && <p className="success">{sucesso}</p>}

        <div className="actions">
          <button className="button" onClick={recalcular} disabled={carregando}>
            Recalcular alertas
          </button>

          <button className="button secondary" onClick={carregar} disabled={carregando}>
            Atualizar dados
          </button>

          {erro && (
            <button className="button secondary" onClick={entrar}>
              Entrar com login de demonstração
            </button>
          )}
        </div>
      </section>

      <section className="card section-title">
        <h2>Cadastrar fornecedor</h2>

        <form className="form" onSubmit={criarFornecedor}>
          <input
            className="input"
            placeholder="Nome do fornecedor"
            value={fornecedorForm.nome}
            onChange={(e) =>
              setFornecedorForm({ ...fornecedorForm, nome: e.target.value })
            }
            required
          />

          <input
            className="input"
            placeholder="Contato"
            value={fornecedorForm.contato}
            onChange={(e) =>
              setFornecedorForm({ ...fornecedorForm, contato: e.target.value })
            }
            required
          />

          <textarea
            className="textarea"
            placeholder="Observação"
            value={fornecedorForm.observacao}
            onChange={(e) =>
              setFornecedorForm({ ...fornecedorForm, observacao: e.target.value })
            }
          />

          <button className="button" type="submit">
            Cadastrar fornecedor
          </button>
        </form>
      </section>

      <section className="card section-title">
        <h2>Cadastrar pedido</h2>

        <form className="form" onSubmit={criarPedido}>
          <input
            className="input"
            type="date"
            value={pedidoForm.data_pedido}
            onChange={(e) =>
              setPedidoForm({ ...pedidoForm, data_pedido: e.target.value })
            }
            required
          />

          <input
            className="input"
            type="date"
            value={pedidoForm.data_prevista}
            onChange={(e) =>
              setPedidoForm({ ...pedidoForm, data_prevista: e.target.value })
            }
            required
          />

          <input
            className="input"
            placeholder="Tipo de insumo. Ex: cimento, aço, tinta"
            value={pedidoForm.tipo_insumo}
            onChange={(e) =>
              setPedidoForm({ ...pedidoForm, tipo_insumo: e.target.value })
            }
            required
          />

          <select
            className="select"
            value={pedidoForm.fornecedor_id}
            onChange={(e) =>
              setPedidoForm({ ...pedidoForm, fornecedor_id: e.target.value })
            }
            required
          >
            <option value="">Selecione o fornecedor</option>
            {fornecedores.map((f) => (
              <option key={f.id} value={f.id}>
                {f.nome}
              </option>
            ))}
          </select>

          <select
            className="select"
            value={pedidoForm.obra_id}
            onChange={(e) =>
              setPedidoForm({ ...pedidoForm, obra_id: e.target.value })
            }
            required
          >
            <option value="">Selecione a obra</option>
            {obras.map((obra) => (
              <option key={obra.id} value={obra.id}>
                {obra.nome}
              </option>
            ))}
          </select>

          <select
            className="select"
            value={pedidoForm.prioridade}
            onChange={(e) =>
              setPedidoForm({ ...pedidoForm, prioridade: e.target.value })
            }
          >
            <option value="alta">Alta</option>
            <option value="media">Média</option>
            <option value="baixa">Baixa</option>
          </select>

          <textarea
            className="textarea"
            placeholder="Observação"
            value={pedidoForm.observacao}
            onChange={(e) =>
              setPedidoForm({ ...pedidoForm, observacao: e.target.value })
            }
          />

          <button className="button" type="submit">
            Cadastrar pedido
          </button>
        </form>
      </section>

      <section className="card section-title">
        <h2>Filtros</h2>

        <div className="grid">
          <select
            className="select"
            value={filtroStatus}
            onChange={(e) => setFiltroStatus(e.target.value)}
          >
            <option value="">Todos os status</option>
            <option value="pendente">Pendente</option>
            <option value="entregue">Entregue</option>
            <option value="atrasado">Atrasado</option>
          </select>

          <select
            className="select"
            value={filtroAlerta}
            onChange={(e) => setFiltroAlerta(e.target.value)}
          >
            <option value="">Todos os alertas</option>
            <option value="vermelho">Vermelho</option>
            <option value="amarelo">Amarelo</option>
            <option value="verde">Verde</option>
          </select>

          <select
            className="select"
            value={filtroObraId}
            onChange={(e) => setFiltroObraId(e.target.value)}
          >
            <option value="">Todas as obras</option>
            {obras.map((obra) => (
              <option key={obra.id} value={obra.id}>
                {obra.nome}
              </option>
            ))}
          </select>
        </div>

        <div className="actions" style={{ marginTop: 12 }}>
          <button className="button" onClick={carregar}>
            Aplicar filtros
          </button>

          <button
            className="button secondary"
            onClick={() => {
              setFiltroStatus("");
              setFiltroAlerta("");
              setFiltroObraId("");
            }}
          >
            Limpar filtros
          </button>
        </div>
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
            <th>Ações</th>
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
              <td>
                <span className={`badge ${pedido.nivel_alerta}`}>
                  {pedido.nivel_alerta}
                </span>
              </td>
              <td>{pedido.texto_alerta}</td>
              <td>
                <div className="actions">
                  {pedido.status === "pendente" && (
                    <button
                      className="button secondary"
                      onClick={() => entregarHoje(pedido.id)}
                    >
                      Entregar
                    </button>
                  )}

                  {pedido.status === "pendente" && (
                    <button
                      className="button danger"
                      onClick={() => excluirPedido(pedido.id)}
                    >
                      Excluir
                    </button>
                  )}
                </div>
              </td>
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