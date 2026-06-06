"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { apiJson } from "@/lib/api";
import { usePerfil } from "@/components/ProtectedRoute";
import type { Fornecedor, Obra, Pedido, NivelAlerta, StatusPedido } from "@/types";

// ─── Modal styles ────────────────────────────────────────────────────────────
const S = {
  overlay: {
    position: "fixed" as const,
    inset: 0,
    background: "rgba(0,0,0,0.45)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 1000,
  },
  modal: {
    background: "var(--card)",
    borderRadius: 16,
    padding: 28,
    width: "min(460px, calc(100vw - 32px))",
    boxShadow: "0 20px 60px rgba(0,0,0,0.25)",
    display: "flex",
    flexDirection: "column" as const,
    gap: 12,
  },
  modalHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 4,
  },
} as const;

const hoje = new Date().toISOString().slice(0, 10);

// ─── Tipo do formulário de edição de fornecedor ──────────────────────────────
// Apenas os 3 campos editáveis — campos ML (media_atraso_dias, taxa_atraso, etc.)
// não estão aqui e nunca são enviados ao backend.
type FornecedorEditForm = { nome: string; contato: string; observacao: string };

// ─── Componente ──────────────────────────────────────────────────────────────
export default function LogisticoPage() {
  const podeGerenciar = usePerfil(["gestor", "operador"]);

  const [fornecedores,  setFornecedores]  = useState<Fornecedor[]>([]);
  const [pedidos,       setPedidos]       = useState<Pedido[]>([]);
  const [obras,         setObras]         = useState<Obra[]>([]);
  const [carregando,    setCarregando]    = useState(false);
  const [salvando,      setSalvando]      = useState(false);
  const [erro,          setErro]          = useState("");
  const [sucesso,       setSucesso]       = useState("");

  // ── Filtros ──────────────────────────────────────────────────────────────
  const [filtroStatus,  setFiltroStatus]  = useState("");
  const [filtroAlerta,  setFiltroAlerta]  = useState("");
  const [filtroObraId,  setFiltroObraId]  = useState("");

  // ── Formulário de novo fornecedor ────────────────────────────────────────
  const [fornecedorForm, setFornecedorForm] = useState({ nome: "", contato: "", observacao: "" });

  // ── Modal de edição de fornecedor ────────────────────────────────────────
  const [editando,     setEditando]     = useState<Fornecedor | null>(null);
  const [editForm,     setEditForm]     = useState<FornecedorEditForm>({ nome: "", contato: "", observacao: "" });

  // ── Formulário de novo pedido ────────────────────────────────────────────
  const [pedidoForm, setPedidoForm] = useState({
    data_pedido:   hoje,
    data_prevista: hoje,
    tipo_insumo:   "",
    fornecedor_id: "",
    obra_id:       "",
    prioridade:    "media",
    observacao:    "",
  });

  // ── Helpers ──────────────────────────────────────────────────────────────
  function msg(e?: string, s?: string) { setErro(e ?? ""); setSucesso(s ?? ""); }

  function abrirEditFornecedor(f: Fornecedor) {
    setEditando(f);
    setEditForm({ nome: f.nome, contato: f.contato, observacao: f.observacao ?? "" });
    msg();
  }

  function fecharEditFornecedor() { setEditando(null); }

  // ── Carregar dados ───────────────────────────────────────────────────────
  const carregar = useCallback(async (
    status  = filtroStatus,
    alerta  = filtroAlerta,
    obraId  = filtroObraId,
  ) => {
    setCarregando(true);
    try {
      const params = new URLSearchParams();
      if (status)  params.set("status",       status);
      if (alerta)  params.set("nivel_alerta", alerta);
      if (obraId)  params.set("obra_id",      obraId);
      const q = params.toString();

      const [fData, pData, oData] = await Promise.all([
        apiJson<Fornecedor[]>("/logistico/fornecedores"),
        apiJson<Pedido[]>(`/logistico/pedidos${q ? `?${q}` : ""}`),
        apiJson<Obra[]>("/core/obras"),
      ]);
      setFornecedores(fData);
      setPedidos(pData);
      setObras(oData);
      msg();
    } catch (e) {
      msg(e instanceof Error ? e.message : "Erro ao carregar módulo logístico.");
    } finally {
      setCarregando(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { void carregar(); }, [carregar]);

  function aplicarFiltros() { void carregar(filtroStatus, filtroAlerta, filtroObraId); }

  function limparFiltros() {
    setFiltroStatus("");
    setFiltroAlerta("");
    setFiltroObraId("");
    void carregar("", "", "");
  }

  // ── Recalcular alertas ───────────────────────────────────────────────────
  async function recalcular() {
    msg();
    try {
      await apiJson("/logistico/recalcular-alertas", { method: "POST" });
      msg(undefined, "Alertas recalculados.");
      await carregar(filtroStatus, filtroAlerta, filtroObraId);
    } catch (e) {
      msg(e instanceof Error ? e.message : "Erro ao recalcular.");
    }
  }

  // ── Criar fornecedor ─────────────────────────────────────────────────────
  async function criarFornecedor(e: FormEvent) {
    e.preventDefault();
    setSalvando(true);
    try {
      await apiJson("/logistico/fornecedores", { method: "POST", body: JSON.stringify(fornecedorForm) });
      setFornecedorForm({ nome: "", contato: "", observacao: "" });
      msg(undefined, "Fornecedor cadastrado.");
      await carregar(filtroStatus, filtroAlerta, filtroObraId);
    } catch (err) {
      msg(err instanceof Error ? err.message : "Erro ao cadastrar fornecedor.");
    } finally {
      setSalvando(false);
    }
  }

  // ── Editar fornecedor ────────────────────────────────────────────────────
  // Envia apenas nome, contato, observacao.
  // Campos ML (media_atraso_dias, taxa_atraso, etc.) são intocados pelo backend.
  async function salvarFornecedor(e: FormEvent) {
    e.preventDefault();
    if (!editando) return;
    setSalvando(true);
    try {
      await apiJson(`/logistico/fornecedores/${editando.id}`, {
        method: "PUT",
        body: JSON.stringify(editForm),
      });
      fecharEditFornecedor();
      msg(undefined, "Fornecedor atualizado.");
      await carregar(filtroStatus, filtroAlerta, filtroObraId);
    } catch (err) {
      msg(err instanceof Error ? err.message : "Erro ao atualizar fornecedor.");
    } finally {
      setSalvando(false);
    }
  }

  // ── Criar pedido ─────────────────────────────────────────────────────────
  async function criarPedido(e: FormEvent) {
    e.preventDefault();
    setSalvando(true);
    try {
      await apiJson("/logistico/pedidos", {
        method: "POST",
        body: JSON.stringify({
          data_pedido:   pedidoForm.data_pedido,
          data_prevista: pedidoForm.data_prevista,
          tipo_insumo:   pedidoForm.tipo_insumo,
          fornecedor_id: Number(pedidoForm.fornecedor_id),
          obra_id:       Number(pedidoForm.obra_id),
          prioridade:    pedidoForm.prioridade,
          observacao:    pedidoForm.observacao || null,
        }),
      });
      setPedidoForm({ data_pedido: hoje, data_prevista: hoje, tipo_insumo: "",
                      fornecedor_id: "", obra_id: "", prioridade: "media", observacao: "" });
      msg(undefined, "Pedido cadastrado.");
      await carregar(filtroStatus, filtroAlerta, filtroObraId);
    } catch (err) {
      msg(err instanceof Error ? err.message : "Erro ao cadastrar pedido.");
    } finally {
      setSalvando(false);
    }
  }

  // ── Registrar entrega ────────────────────────────────────────────────────
  async function entregarHoje(id: number) {
    msg();
    try {
      await apiJson(`/logistico/pedidos/${id}/entregar`, {
        method: "PUT",
        body: JSON.stringify({ data_real_entrega: hoje }),
      });
      msg(undefined, "Entrega registrada.");
      await carregar(filtroStatus, filtroAlerta, filtroObraId);
    } catch (e) {
      msg(e instanceof Error ? e.message : "Erro ao registrar entrega.");
    }
  }

  // ── Excluir pedido ───────────────────────────────────────────────────────
  // Apenas pedidos com status "pendente" podem ser excluídos (validado também
  // no backend, que retorna 400 para outros status).
  async function excluirPedido(id: number) {
    if (!confirm("Excluir este pedido? Esta ação é irreversível.")) return;
    msg();
    try {
      await apiJson(`/logistico/pedidos/${id}`, { method: "DELETE" });
      msg(undefined, "Pedido excluído.");
      await carregar(filtroStatus, filtroAlerta, filtroObraId);
    } catch (e) {
      msg(e instanceof Error ? e.message : "Erro ao excluir pedido.");
    }
  }

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <main className="container">

      {/* Cabeçalho */}
      <section className="card">
        <h1 style={{ margin: 0 }}>Módulo Logístico</h1>
        <p className="muted">Controle de pedidos, fornecedores e risco de atraso.</p>
        {erro    && <p className="error"   style={{ marginTop: 8 }}>{erro}</p>}
        {sucesso && <p className="success" style={{ marginTop: 8 }}>{sucesso}</p>}
        <div className="actions" style={{ marginTop: 12 }}>
          {podeGerenciar && (
            <button className="button" onClick={recalcular} disabled={carregando}>
              Recalcular alertas
            </button>
          )}
          <button className="button secondary" onClick={() => void carregar(filtroStatus, filtroAlerta, filtroObraId)} disabled={carregando}>
            {carregando ? "Carregando…" : "Atualizar"}
          </button>
        </div>
      </section>

      {/* Formulários de cadastro — visíveis apenas para gestor/operador */}
      {podeGerenciar && (
        <div className="grid" style={{ marginTop: 20 }}>
          {/* Novo fornecedor */}
          <section className="card">
            <h2 style={{ marginTop: 0 }}>Novo fornecedor</h2>
            <form className="form" onSubmit={criarFornecedor}>
              <input className="input" placeholder="Nome *" value={fornecedorForm.nome}
                onChange={(e) => setFornecedorForm({ ...fornecedorForm, nome: e.target.value })} required />
              <input className="input" placeholder="Contato *" value={fornecedorForm.contato}
                onChange={(e) => setFornecedorForm({ ...fornecedorForm, contato: e.target.value })} required />
              <textarea className="textarea" placeholder="Observação" value={fornecedorForm.observacao}
                onChange={(e) => setFornecedorForm({ ...fornecedorForm, observacao: e.target.value })} />
              <button className="button" type="submit" disabled={salvando}>
                {salvando ? "Salvando…" : "Cadastrar fornecedor"}
              </button>
            </form>
          </section>

          {/* Novo pedido */}
          <section className="card">
            <h2 style={{ marginTop: 0 }}>Novo pedido</h2>
            <form className="form" onSubmit={criarPedido}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div>
                  <label className="muted" style={{ fontSize: 12 }}>Data do pedido</label>
                  <input className="input" type="date" value={pedidoForm.data_pedido}
                    onChange={(e) => setPedidoForm({ ...pedidoForm, data_pedido: e.target.value })} required />
                </div>
                <div>
                  <label className="muted" style={{ fontSize: 12 }}>Entrega prevista</label>
                  <input className="input" type="date" value={pedidoForm.data_prevista}
                    onChange={(e) => setPedidoForm({ ...pedidoForm, data_prevista: e.target.value })} required />
                </div>
              </div>
              <input className="input" placeholder="Tipo de insumo (ex: cimento, aço)" value={pedidoForm.tipo_insumo}
                onChange={(e) => setPedidoForm({ ...pedidoForm, tipo_insumo: e.target.value })} required />
              <select className="select" value={pedidoForm.fornecedor_id}
                onChange={(e) => setPedidoForm({ ...pedidoForm, fornecedor_id: e.target.value })} required>
                <option value="">Selecione o fornecedor</option>
                {fornecedores.map((f) => <option key={f.id} value={f.id}>{f.nome}</option>)}
              </select>
              <select className="select" value={pedidoForm.obra_id}
                onChange={(e) => setPedidoForm({ ...pedidoForm, obra_id: e.target.value })} required>
                <option value="">Selecione a obra</option>
                {obras.map((o) => <option key={o.id} value={o.id}>{o.nome}</option>)}
              </select>
              <select className="select" value={pedidoForm.prioridade}
                onChange={(e) => setPedidoForm({ ...pedidoForm, prioridade: e.target.value })}>
                <option value="alta">Alta</option>
                <option value="media">Média</option>
                <option value="baixa">Baixa</option>
              </select>
              <textarea className="textarea" placeholder="Observação (opcional)" value={pedidoForm.observacao}
                onChange={(e) => setPedidoForm({ ...pedidoForm, observacao: e.target.value })} />
              <button className="button" type="submit" disabled={salvando}>
                {salvando ? "Salvando…" : "Cadastrar pedido"}
              </button>
            </form>
          </section>
        </div>
      )}

      {/* Filtros */}
      <section className="card" style={{ marginTop: 20 }}>
        <h2 style={{ marginTop: 0 }}>Filtros</h2>
        <div className="grid">
          <select className="select" value={filtroStatus} onChange={(e) => setFiltroStatus(e.target.value)}>
            <option value="">Todos os status</option>
            <option value="pendente">Pendente</option>
            <option value="entregue">Entregue</option>
            <option value="atrasado">Atrasado</option>
          </select>
          <select className="select" value={filtroAlerta} onChange={(e) => setFiltroAlerta(e.target.value)}>
            <option value="">Todos os alertas</option>
            <option value="vermelho">🔴 Vermelho</option>
            <option value="amarelo">🟡 Amarelo</option>
            <option value="verde">🟢 Verde</option>
          </select>
          <select className="select" value={filtroObraId} onChange={(e) => setFiltroObraId(e.target.value)}>
            <option value="">Todas as obras</option>
            {obras.map((o) => <option key={o.id} value={o.id}>{o.nome}</option>)}
          </select>
        </div>
        <div className="actions" style={{ marginTop: 12 }}>
          <button className="button" onClick={aplicarFiltros} disabled={carregando}>Aplicar filtros</button>
          <button className="button secondary" onClick={limparFiltros} disabled={carregando}>Limpar</button>
        </div>
      </section>

      {/* Tabela de pedidos */}
      <h2 className="section-title">
        Pedidos e alertas{" "}
        <span className="muted" style={{ fontSize: 14, fontWeight: 400 }}>({pedidos.length})</span>
      </h2>
      <div style={{ overflowX: "auto" }}>
        <table className="table">
          <thead>
            <tr>
              <th>Insumo</th>
              <th>Obra</th>
              <th>Previsão</th>
              <th>Prioridade</th>
              <th>Status</th>
              <th>Prob.</th>
              <th>Alerta</th>
              <th>Mensagem</th>
              {podeGerenciar && <th>Ações</th>}
            </tr>
          </thead>
          <tbody>
            {pedidos.length === 0 && (
              <tr>
                <td colSpan={9} style={{ textAlign: "center", color: "var(--muted)", padding: 28 }}>
                  Nenhum pedido encontrado para os filtros selecionados.
                </td>
              </tr>
            )}
            {pedidos.map((p) => {
              const obraNome = obras.find((o) => o.id === p.obra_id)?.nome ?? `#${p.obra_id}`;
              return (
                <tr key={p.id}>
                  <td>{p.tipo_insumo}</td>
                  <td>{obraNome}</td>
                  <td>{p.data_prevista}</td>
                  <td>{p.prioridade}</td>
                  <td>{p.status}</td>
                  <td>{Math.round(p.prob_atraso * 100)}%</td>
                  <td>
                    <span className={`badge ${p.nivel_alerta as NivelAlerta}`}>
                      {p.nivel_alerta}
                    </span>
                  </td>
                  <td style={{ fontSize: 13, maxWidth: 260 }}>{p.texto_alerta}</td>
                  {podeGerenciar && (
                    <td>
                      <div className="actions">
                        {(p.status as StatusPedido) === "pendente" && (
                          <>
                            <button
                              className="button secondary"
                              style={{ padding: "5px 10px", fontSize: 12 }}
                              onClick={() => entregarHoje(p.id)}
                            >
                              Entregar
                            </button>
                            <button
                              className="button danger"
                              style={{ padding: "5px 10px", fontSize: 12 }}
                              onClick={() => excluirPedido(p.id)}
                            >
                              Excluir
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Tabela de fornecedores */}
      <h2 className="section-title">
        Fornecedores{" "}
        <span className="muted" style={{ fontSize: 14, fontWeight: 400 }}>({fornecedores.length})</span>
      </h2>
      <div style={{ overflowX: "auto" }}>
        <table className="table">
          <thead>
            <tr>
              <th>Nome</th>
              <th>Contato</th>
              <th>Média atraso</th>
              <th>Taxa atraso</th>
              <th>Histórico</th>
              <th>Observação</th>
              {podeGerenciar && <th>Ações</th>}
            </tr>
          </thead>
          <tbody>
            {fornecedores.length === 0 && (
              <tr>
                <td colSpan={7} style={{ textAlign: "center", color: "var(--muted)", padding: 28 }}>
                  Nenhum fornecedor cadastrado.
                </td>
              </tr>
            )}
            {fornecedores.map((f) => (
              <tr key={f.id}>
                <td><strong>{f.nome}</strong></td>
                <td>{f.contato}</td>
                <td
                  style={{
                    color: f.media_atraso_dias > 5 ? "var(--danger)" :
                           f.media_atraso_dias > 2 ? "var(--warning)" : "var(--success)",
                    fontWeight: 600,
                  }}
                >
                  {f.media_atraso_dias.toFixed(1)}d
                </td>
                <td>{Math.round(f.taxa_atraso * 100)}%</td>
                <td>{f.total_pedidos} entrega(s)</td>
                <td style={{ fontSize: 13, color: "var(--muted)" }}>{f.observacao ?? "—"}</td>
                {podeGerenciar && (
                  <td>
                    <button
                      className="button secondary"
                      style={{ padding: "5px 10px", fontSize: 12 }}
                      onClick={() => abrirEditFornecedor(f)}
                    >
                      Editar
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Modal — editar fornecedor */}
      {editando && (
        <div style={S.overlay} onClick={fecharEditFornecedor}>
          <div style={S.modal} onClick={(e) => e.stopPropagation()}>
            <div style={S.modalHeader}>
              <h2 style={{ margin: 0 }}>Editar fornecedor</h2>
              <button onClick={fecharEditFornecedor}
                style={{ background: "none", border: "none", fontSize: 20, cursor: "pointer", color: "var(--muted)" }}>
                ✕
              </button>
            </div>
            <p className="muted" style={{ margin: 0, fontSize: 13 }}>
              Campos de desempenho (média de atraso, taxa) são calculados automaticamente
              pelo sistema e não podem ser editados aqui.
            </p>
            <form className="form" onSubmit={salvarFornecedor}>
              <input className="input" placeholder="Nome *" value={editForm.nome}
                onChange={(e) => setEditForm({ ...editForm, nome: e.target.value })} required />
              <input className="input" placeholder="Contato *" value={editForm.contato}
                onChange={(e) => setEditForm({ ...editForm, contato: e.target.value })} required />
              <textarea className="textarea" placeholder="Observação (ex: evitar em dezembro)"
                value={editForm.observacao}
                onChange={(e) => setEditForm({ ...editForm, observacao: e.target.value })} />
              <div className="actions">
                <button className="button" type="submit" disabled={salvando}>
                  {salvando ? "Salvando…" : "Salvar"}
                </button>
                <button className="button secondary" type="button" onClick={fecharEditFornecedor} disabled={salvando}>
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </main>
  );
}
