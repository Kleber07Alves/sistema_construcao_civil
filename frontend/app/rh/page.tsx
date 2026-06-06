"use client";
// frontend/app/rh/page.tsx
import { useCallback, useEffect, useState } from "react";
import { apiJson } from "@/lib/api";
import { usePerfil } from "@/components/ProtectedRoute";
import type { Candidato, RankingCandidato, StatusVaga, Vaga } from "@/types";

// ─── Helpers visuais ──────────────────────────────────────────────────────────
const STATUS_VAGA_LABEL: Record<StatusVaga, string> = {
  aberta:    "Aberta",
  pausada:   "Pausada",
  encerrada: "Encerrada",
};

const STATUS_VAGA_STYLE: Record<StatusVaga, React.CSSProperties> = {
  aberta:    { background: "#dcfce7", color: "#166534" },
  pausada:   { background: "#fef3c7", color: "#92400e" },
  encerrada: { background: "#f3f4f6", color: "#6b7280" },
};

const BADGE_STATUS: React.CSSProperties = {
  display: "inline-block",
  padding: "3px 10px",
  borderRadius: 999,
  fontSize: 12,
  fontWeight: 700,
};

// ─── Componente ───────────────────────────────────────────────────────────────
export default function RhPage() {
  const podeGerenciar = usePerfil(["gestor", "rh"]);

  const [vagas,      setVagas]      = useState<Vaga[]>([]);
  const [candidatos, setCandidatos] = useState<Candidato[]>([]);
  const [ranking,    setRanking]    = useState<RankingCandidato[]>([]);
  const [vagaAtiva,  setVagaAtiva]  = useState<number | null>(null); // vaga selecionada para ranking

  const [carregando, setCarregando] = useState(false);
  const [salvando,   setSalvando]   = useState(false);
  const [erro,       setErro]       = useState("");
  const [sucesso,    setSucesso]    = useState("");

  // Status sendo alterado inline (id da vaga sendo editada, ou null)
  const [alterandoStatus, setAlterandoStatus] = useState<number | null>(null);

  function msg(e?: string, s?: string) { setErro(e ?? ""); setSucesso(s ?? ""); }

  // ── Carregar ranking ────────────────────────────────────────────────────
  const carregarRanking = useCallback(async (vagaId: number) => {
    try {
      setRanking(await apiJson<RankingCandidato[]>(`/rh/vagas/${vagaId}/ranking`));
    } catch {
      setRanking([]);
    }
  }, []);

  // ── Carregar tudo ───────────────────────────────────────────────────────
  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const [vagasData, candidatosData] = await Promise.all([
        apiJson<Vaga[]>("/rh/vagas"),
        apiJson<Candidato[]>("/rh/candidatos"),
      ]);
      setVagas(vagasData);
      setCandidatos(candidatosData);

      // Usa a vaga já selecionada pelo usuário, ou a primeira disponível
      const primId = vagasData[0]?.id ?? null;
      const idUsado = vagaAtiva ?? primId;
      if (idUsado) {
        setVagaAtiva(idUsado);
        await carregarRanking(idUsado);
      } else {
        setRanking([]);
      }
      msg();
    } catch (e) {
      msg(e instanceof Error ? e.message : "Erro ao carregar módulo de RH.");
    } finally {
      setCarregando(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [carregarRanking]);

  useEffect(() => { void carregar(); }, [carregar]);

  // ── Selecionar vaga para ranking ────────────────────────────────────────
  async function selecionarVaga(id: number) {
    setVagaAtiva(id);
    msg();
    await carregarRanking(id);
  }

  // ── Alterar status da vaga ──────────────────────────────────────────────
  async function alterarStatus(vagaId: number, novoStatus: StatusVaga) {
    setAlterandoStatus(vagaId);
    msg();
    try {
      await apiJson(`/rh/vagas/${vagaId}`, {
        method: "PUT",
        body: JSON.stringify({ status: novoStatus }),
      });
      msg(undefined, `Status da vaga atualizado para "${STATUS_VAGA_LABEL[novoStatus]}".`);
      await carregar();
    } catch (e) {
      msg(e instanceof Error ? e.message : "Erro ao alterar status.");
    } finally {
      setAlterandoStatus(null);
    }
  }

  // ── Excluir vaga ────────────────────────────────────────────────────────
  async function excluirVaga(vaga: Vaga) {
    if (!confirm(
      `Excluir a vaga "${vaga.titulo}"?\n\n` +
      `Recomendação: encerre a vaga com status "Encerrada" antes de excluir fisicamente.`,
    )) return;
    msg();
    setSalvando(true);
    try {
      await apiJson(`/rh/vagas/${vaga.id}`, { method: "DELETE" });
      // Se era a vaga ativa no ranking, limpa a seleção
      if (vagaAtiva === vaga.id) { setVagaAtiva(null); setRanking([]); }
      msg(undefined, `Vaga "${vaga.titulo}" excluída.`);
      await carregar();
    } catch (e) {
      msg(e instanceof Error ? e.message : "Erro ao excluir vaga.");
    } finally {
      setSalvando(false);
    }
  }

  // ── Excluir candidato ───────────────────────────────────────────────────
  async function excluirCandidato(candidato: Candidato) {
    if (!confirm(
      `Excluir permanentemente o candidato "${candidato.nome}"?\n` +
      `Esta ação remove o currículo e o resumo do sistema.`,
    )) return;
    msg();
    setSalvando(true);
    try {
      await apiJson(`/rh/candidatos/${candidato.id}`, { method: "DELETE" });
      msg(undefined, `Candidato "${candidato.nome}" removido.`);
      // Recalcula ranking se o candidato fazia parte do ranking ativo
      if (vagaAtiva) await carregarRanking(vagaAtiva);
      await carregar();
    } catch (e) {
      msg(e instanceof Error ? e.message : "Erro ao excluir candidato.");
    } finally {
      setSalvando(false);
    }
  }

  // ── Render ──────────────────────────────────────────────────────────────
  const vagaRankingNome = vagas.find((v) => v.id === vagaAtiva)?.titulo;

  return (
    <main className="container">

      {/* Cabeçalho */}
      <section className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
          <div>
            <h1 style={{ margin: 0 }}>Módulo de RH</h1>
            <p className="muted" style={{ margin: "4px 0 0" }}>
              Vagas, triagem de candidatos e ranking por compatibilidade.
            </p>
          </div>
          <button className="button secondary" onClick={carregar} disabled={carregando}>
            {carregando ? "Carregando…" : "Atualizar"}
          </button>
        </div>
        {erro    && <p className="error"   style={{ marginTop: 12 }}>{erro}</p>}
        {sucesso && <p className="success" style={{ marginTop: 12 }}>{sucesso}</p>}
      </section>

      {/* Vagas */}
      <h2 className="section-title">
        Vagas{" "}
        <span className="muted" style={{ fontSize: 14, fontWeight: 400 }}>({vagas.length})</span>
      </h2>
      <div style={{ overflowX: "auto" }}>
        <table className="table">
          <thead>
            <tr>
              <th>Título</th>
              <th>Tipo de obra</th>
              <th>Requisitos</th>
              <th>Habilidades</th>
              <th>Status</th>
              {podeGerenciar && <th>Alterar status</th>}
              <th>Ranking</th>
              {podeGerenciar && <th>Excluir</th>}
            </tr>
          </thead>
          <tbody>
            {vagas.length === 0 && (
              <tr>
                <td colSpan={8} style={{ textAlign: "center", color: "var(--muted)", padding: 28 }}>
                  Nenhuma vaga cadastrada.
                </td>
              </tr>
            )}
            {vagas.map((vaga) => (
              <tr key={vaga.id} style={{ opacity: vaga.status === "encerrada" ? 0.65 : 1 }}>
                <td><strong>{vaga.titulo}</strong></td>
                <td>{vaga.tipo_obra}</td>
                <td style={{ fontSize: 13 }}>{vaga.requisitos}</td>
                <td style={{ fontSize: 13 }}>{vaga.habilidades}</td>
                <td>
                  <span style={{ ...BADGE_STATUS, ...STATUS_VAGA_STYLE[vaga.status as StatusVaga] }}>
                    {STATUS_VAGA_LABEL[vaga.status as StatusVaga] ?? vaga.status}
                  </span>
                </td>
                {/* Alterar status — dropdown inline para gestor/rh */}
                {podeGerenciar && (
                  <td>
                    <select
                      className="select"
                      style={{ padding: "4px 8px", fontSize: 12 }}
                      value={vaga.status}
                      disabled={alterandoStatus === vaga.id || salvando}
                      onChange={(e) => alterarStatus(vaga.id, e.target.value as StatusVaga)}
                    >
                      <option value="aberta">Aberta</option>
                      <option value="pausada">Pausada</option>
                      <option value="encerrada">Encerrada</option>
                    </select>
                  </td>
                )}
                {/* Selecionar para ranking */}
                <td>
                  <button
                    className={vagaAtiva === vaga.id ? "button" : "button secondary"}
                    style={{ padding: "5px 10px", fontSize: 12 }}
                    onClick={() => selecionarVaga(vaga.id)}
                  >
                    {vagaAtiva === vaga.id ? "✓ Selecionada" : "Ver ranking"}
                  </button>
                </td>
                {/* Excluir vaga */}
                {podeGerenciar && (
                  <td>
                    <button
                      className="button danger"
                      style={{ padding: "5px 10px", fontSize: 12 }}
                      onClick={() => excluirVaga(vaga)}
                      disabled={salvando}
                    >
                      Excluir
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Ranking da vaga selecionada */}
      <h2 className="section-title">
        Ranking{vagaRankingNome ? ` — ${vagaRankingNome}` : ""}
        {!vagaAtiva && (
          <span className="muted" style={{ fontSize: 14, fontWeight: 400 }}>
            {" "}(selecione uma vaga acima)
          </span>
        )}
      </h2>
      <table className="table">
        <thead>
          <tr>
            <th>#</th>
            <th>Candidato</th>
            <th>Cargo</th>
            <th>Experiência</th>
            <th>Score</th>
            <th>Motivos</th>
          </tr>
        </thead>
        <tbody>
          {ranking.length === 0 && (
            <tr>
              <td colSpan={6} style={{ textAlign: "center", color: "var(--muted)", padding: 20 }}>
                {vagaAtiva ? "Nenhum candidato encontrado para esta vaga." : "Selecione uma vaga para ver o ranking."}
              </td>
            </tr>
          )}
          {ranking.map((item, idx) => (
            <tr key={item.candidato.id}>
              <td style={{ color: "var(--muted)", fontSize: 13 }}>#{idx + 1}</td>
              <td><strong>{item.candidato.nome}</strong></td>
              <td>{item.candidato.cargo ?? "—"}</td>
              <td>{item.candidato.experiencia_anos.toFixed(1)}a</td>
              <td>
                <span
                  style={{
                    fontWeight: 700,
                    color: item.score >= 70 ? "var(--success)" :
                           item.score >= 40 ? "var(--warning)" : "var(--danger)",
                  }}
                >
                  {item.score}%
                </span>
              </td>
              <td style={{ fontSize: 12, color: "var(--muted)" }}>{item.motivos.join(" · ")}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Candidatos */}
      <h2 className="section-title">
        Candidatos{" "}
        <span className="muted" style={{ fontSize: 14, fontWeight: 400 }}>({candidatos.length})</span>
      </h2>
      <div className="grid">
        {candidatos.length === 0 && (
          <p className="muted">Nenhum candidato cadastrado.</p>
        )}
        {candidatos.map((c) => (
          <article className="card" key={c.id}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <h3 style={{ margin: "0 0 2px" }}>{c.nome}</h3>
                <p className="muted" style={{ margin: 0, fontSize: 13 }}>{c.email}</p>
              </div>
              {/* Botão de exclusão — visível apenas para gestor/rh */}
              {podeGerenciar && (
                <button
                  className="button danger"
                  style={{ padding: "4px 10px", fontSize: 12, flexShrink: 0 }}
                  onClick={() => excluirCandidato(c)}
                  disabled={salvando}
                  title="Excluir candidato permanentemente"
                >
                  Excluir
                </button>
              )}
            </div>

            <p style={{ margin: "10px 0 4px" }}>
              <strong>Cargo:</strong> {c.cargo ?? "—"}
            </p>
            <p style={{ margin: "0 0 4px", fontSize: 13 }}>
              <strong>Exp.:</strong> {c.experiencia_anos.toFixed(1)} ano(s)
            </p>
            <p style={{ margin: "0 0 4px", fontSize: 13 }}>
              <strong>Habilidades:</strong> {c.habilidades || "—"}
            </p>
            {c.resumo && (
              <p style={{ margin: "8px 0 0", fontSize: 13, color: "var(--muted)", borderTop: "1px solid var(--border)", paddingTop: 8 }}>
                {c.resumo}
              </p>
            )}
          </article>
        ))}
      </div>

    </main>
  );
}
