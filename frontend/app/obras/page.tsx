"use client";

import {
  useCallback,
  useEffect,
  useState,
  type Dispatch,
  type FormEvent,
  type SetStateAction,
} from "react";
import { apiJson } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { usePerfil } from "@/components/ProtectedRoute";
import type { Obra, StatusObra, PrioridadeObra } from "@/types";

// ─── Estilos inline do modal (sem dependências externas) ────────────────────
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
    width: "min(480px, calc(100vw - 32px))",
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
  statusBadge: (status: StatusObra) => {
    const map: Record<StatusObra, { bg: string; color: string }> = {
      planejada:    { bg: "#e0e7ff", color: "#3730a3" },
      em_andamento: { bg: "#dbeafe", color: "#1d4ed8" },
      concluida:    { bg: "#dcfce7", color: "#166534" },
      pausada:      { bg: "#fef3c7", color: "#92400e" },
    };
    const { bg, color } = map[status] ?? { bg: "#f3f4f6", color: "#374151" };
    return {
      display: "inline-block",
      padding: "3px 10px",
      borderRadius: 999,
      fontSize: 12,
      fontWeight: 700,
      background: bg,
      color,
    };
  },
  priorBadge: (p: PrioridadeObra) => {
    const map: Record<PrioridadeObra, string> = {
      alta: "#991b1b",
      media: "#92400e",
      baixa: "#166534",
    };
    return { color: map[p], fontWeight: 700 as const };
  },
} as const;

// ─── Tipo do formulário (sem id — usado para criar e editar) ─────────────────
type ObraForm = Omit<Obra, "id">;

const FORM_VAZIO: ObraForm = {
  nome:        "",
  endereco:    "",
  status:      "planejada",
  prioridade:  "media",
  data_inicio: null,
};

// ─── Formulário compartilhado (criar/editar) ─────────────────────────────────
// DECLARADO FORA de ObrasPage de propósito: um componente definido dentro de
// outro é recriado (nova identidade) a cada render do pai — o React desmonta
// e remonta o formulário a cada tecla digitada, fazendo o input perder o foco.
function FormObra({
  form,
  setForm,
  salvando,
  onSubmit,
  onCancel,
}: {
  form: ObraForm;
  setForm: Dispatch<SetStateAction<ObraForm>>;
  salvando: boolean;
  onSubmit: (e: FormEvent) => Promise<void>;
  onCancel: () => void;
}) {
  return (
    <form className="form" onSubmit={onSubmit}>
      <input
        className="input"
        placeholder="Nome da obra *"
        value={form.nome}
        onChange={(e) => setForm({ ...form, nome: e.target.value })}
        required
      />
      <input
        className="input"
        placeholder="Endereço *"
        value={form.endereco}
        onChange={(e) => setForm({ ...form, endereco: e.target.value })}
        required
      />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <select
          className="select"
          value={form.status}
          onChange={(e) => setForm({ ...form, status: e.target.value as StatusObra })}
        >
          <option value="planejada">Planejada</option>
          <option value="em_andamento">Em andamento</option>
          <option value="concluida">Concluída</option>
          <option value="pausada">Pausada</option>
        </select>
        <select
          className="select"
          value={form.prioridade}
          onChange={(e) => setForm({ ...form, prioridade: e.target.value as PrioridadeObra })}
        >
          <option value="alta">Alta</option>
          <option value="media">Média</option>
          <option value="baixa">Baixa</option>
        </select>
      </div>
      <label style={{ fontSize: 13, color: "var(--muted)" }}>
        Data de início (opcional)
        <input
          className="input"
          type="date"
          value={form.data_inicio ?? ""}
          onChange={(e) => setForm({ ...form, data_inicio: e.target.value || null })}
          style={{ marginTop: 4 }}
        />
      </label>
      <div className="actions" style={{ marginTop: 4 }}>
        <button className="button" type="submit" disabled={salvando}>
          {salvando ? "Salvando…" : "Salvar"}
        </button>
        <button
          className="button secondary"
          type="button"
          onClick={onCancel}
          disabled={salvando}
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}

// ─── Componente ──────────────────────────────────────────────────────────────
export default function ObrasPage() {
  const { autenticado } = useAuth();
  const podeEditar  = usePerfil(["gestor", "operador"]);
  const podeExcluir = usePerfil(["gestor"]);

  const [obras,     setObras]     = useState<Obra[]>([]);
  const [carregando, setCarregando] = useState(false);
  const [salvando,  setSalvando]  = useState(false);
  const [erro,      setErro]      = useState("");
  const [sucesso,   setSucesso]   = useState("");

  // modal: null | "criar" | "editar"
  const [modal,      setModal]      = useState<"criar" | "editar" | null>(null);
  const [selecionada, setSelecionada] = useState<Obra | null>(null);
  const [form,       setForm]       = useState<ObraForm>(FORM_VAZIO);

  // ── Helpers ────────────────────────────────────────────────────────────
  function msg(e?: string, s?: string) {
    setErro(e ?? "");
    setSucesso(s ?? "");
  }

  function abrirCriar() {
    setForm(FORM_VAZIO);
    setModal("criar");
    msg();
  }

  function abrirEditar(obra: Obra) {
    setSelecionada(obra);
    setForm({ nome: obra.nome, endereco: obra.endereco, status: obra.status,
              prioridade: obra.prioridade, data_inicio: obra.data_inicio });
    setModal("editar");
    msg();
  }

  function fecharModal() {
    setModal(null);
    setSelecionada(null);
  }

  // ── Carregar ───────────────────────────────────────────────────────────
  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      setObras(await apiJson<Obra[]>("/core/obras"));
      msg();
    } catch (e) {
      msg(e instanceof Error ? e.message : "Erro ao carregar obras.");
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => { void carregar(); }, [carregar]);

  // ── Criar ──────────────────────────────────────────────────────────────
  async function salvarNova(e: FormEvent) {
    e.preventDefault();
    setSalvando(true);
    try {
      await apiJson<Obra>("/core/obras", {
        method: "POST",
        body: JSON.stringify(form),
      });
      fecharModal();
      msg(undefined, "Obra criada com sucesso.");
      await carregar();
    } catch (err) {
      msg(err instanceof Error ? err.message : "Erro ao criar obra.");
    } finally {
      setSalvando(false);
    }
  }

  // ── Editar ─────────────────────────────────────────────────────────────
  async function salvarEdicao(e: FormEvent) {
    e.preventDefault();
    if (!selecionada) return;
    setSalvando(true);
    try {
      await apiJson<Obra>(`/core/obras/${selecionada.id}`, {
        method: "PUT",
        body: JSON.stringify(form),
      });
      fecharModal();
      msg(undefined, "Obra atualizada com sucesso.");
      await carregar();
    } catch (err) {
      msg(err instanceof Error ? err.message : "Erro ao atualizar obra.");
    } finally {
      setSalvando(false);
    }
  }

  // ── Excluir ────────────────────────────────────────────────────────────
  // O backend retorna 400 com detail descritivo se houver pedidos associados.
  // O apiJson propaga o detail como Error.message — exibido diretamente.
  async function excluir(obra: Obra) {
    if (!confirm(`Excluir a obra "${obra.nome}"? Esta ação é irreversível.`)) return;
    msg();
    try {
      await apiJson(`/core/obras/${obra.id}`, { method: "DELETE" });
      msg(undefined, `Obra "${obra.nome}" excluída.`);
      await carregar();
    } catch (err) {
      // Preserva a mensagem do backend (ex: "possui 3 pedido(s) associado(s)")
      msg(err instanceof Error ? err.message : "Erro ao excluir obra.");
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────
  return (
    <main className="container">

      {/* Cabeçalho */}
      <section className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
          <div>
            <h1 style={{ margin: 0 }}>Obras</h1>
            <p className="muted" style={{ margin: "4px 0 0" }}>
              Gestão completa das obras cadastradas.
            </p>
          </div>
          <div className="actions">
            {podeEditar && (
              <button className="button" onClick={abrirCriar}>
                + Nova obra
              </button>
            )}
            <button
              className="button secondary"
              onClick={carregar}
              disabled={carregando}
            >
              {carregando ? "Carregando…" : "Atualizar"}
            </button>
          </div>
        </div>

        {erro   && <p className="error"   style={{ marginTop: 12 }}>{erro}</p>}
        {sucesso && <p className="success" style={{ marginTop: 12 }}>{sucesso}</p>}
      </section>

      {/* Tabela */}
      <div style={{ marginTop: 20, overflowX: "auto" }}>
        <table className="table">
          <thead>
            <tr>
              <th>Nome</th>
              <th>Endereço</th>
              <th>Status</th>
              <th>Prioridade</th>
              <th>Início</th>
              {(podeEditar || podeExcluir) && <th>Ações</th>}
            </tr>
          </thead>
          <tbody>
            {obras.length === 0 && (
              <tr>
                <td colSpan={6} style={{ textAlign: "center", color: "var(--muted)", padding: 32 }}>
                  {autenticado ? "Nenhuma obra cadastrada." : "Faça login para ver as obras."}
                </td>
              </tr>
            )}
            {obras.map((obra) => (
              <tr key={obra.id}>
                <td><strong>{obra.nome}</strong></td>
                <td>{obra.endereco}</td>
                <td><span style={S.statusBadge(obra.status)}>{obra.status.replace("_", " ")}</span></td>
                <td><span style={S.priorBadge(obra.prioridade)}>{obra.prioridade}</span></td>
                <td>{obra.data_inicio ?? "—"}</td>
                {(podeEditar || podeExcluir) && (
                  <td>
                    <div className="actions">
                      {podeEditar && (
                        <button
                          className="button secondary"
                          style={{ padding: "6px 10px", fontSize: 13 }}
                          onClick={() => abrirEditar(obra)}
                        >
                          Editar
                        </button>
                      )}
                      {podeExcluir && (
                        <button
                          className="button danger"
                          style={{ padding: "6px 10px", fontSize: 13 }}
                          onClick={() => excluir(obra)}
                        >
                          Excluir
                        </button>
                      )}
                    </div>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Modal — criar */}
      {modal === "criar" && (
        <div style={S.overlay} onClick={fecharModal}>
          <div style={S.modal} onClick={(e) => e.stopPropagation()}>
            <div style={S.modalHeader}>
              <h2 style={{ margin: 0 }}>Nova obra</h2>
              <button
                onClick={fecharModal}
                style={{ background: "none", border: "none", fontSize: 20, cursor: "pointer", color: "var(--muted)" }}
              >
                ✕
              </button>
            </div>
            <FormObra
              form={form}
              setForm={setForm}
              salvando={salvando}
              onSubmit={salvarNova}
              onCancel={fecharModal}
            />
          </div>
        </div>
      )}

      {/* Modal — editar */}
      {modal === "editar" && selecionada && (
        <div style={S.overlay} onClick={fecharModal}>
          <div style={S.modal} onClick={(e) => e.stopPropagation()}>
            <div style={S.modalHeader}>
              <h2 style={{ margin: 0 }}>Editar obra</h2>
              <button
                onClick={fecharModal}
                style={{ background: "none", border: "none", fontSize: 20, cursor: "pointer", color: "var(--muted)" }}
              >
                ✕
              </button>
            </div>
            <p className="muted" style={{ margin: "0 0 4px" }}>ID #{selecionada.id}</p>
            <FormObra
              form={form}
              setForm={setForm}
              salvando={salvando}
              onSubmit={salvarEdicao}
              onCancel={fecharModal}
            />
          </div>
        </div>
      )}

    </main>
  );
}
