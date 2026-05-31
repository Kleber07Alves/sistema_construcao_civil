"use client";

import { useEffect, useState } from "react";
import { apiJson, loginDemo } from "../../lib/api";

type Vaga = {
  id: number;
  titulo: string;
  tipo_obra: string;
  requisitos: string;
  habilidades: string;
  status: string;
};

type Candidato = {
  id: number;
  nome: string;
  email: string;
  cargo: string | null;
  experiencia_anos: number;
  habilidades: string;
  resumo: string;
};

type Ranking = {
  candidato: Candidato;
  score: number;
  motivos: string[];
};

export default function RhPage() {
  const [vagas, setVagas] = useState<Vaga[]>([]);
  const [candidatos, setCandidatos] = useState<Candidato[]>([]);
  const [ranking, setRanking] = useState<Ranking[]>([]);
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);

  async function carregar() {
    setCarregando(true);
    try {
      const [vagasData, candidatosData] = await Promise.all([
        apiJson<Vaga[]>("/rh/vagas"),
        apiJson<Candidato[]>("/rh/candidatos"),
      ]);
      setVagas(vagasData);
      setCandidatos(candidatosData);
      if (vagasData[0]) {
        setRanking(await apiJson<Ranking[]>(`/rh/vagas/${vagasData[0].id}/ranking`));
      } else {
        setRanking([]);
      }
      setErro("");
    } catch (e) {
      setVagas([]);
      setCandidatos([]);
      setRanking([]);
      setErro(e instanceof Error ? e.message : "Faça login para visualizar o módulo de RH.");
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

  useEffect(() => {
    carregar();
  }, []);

  return (
    <main className="container">
      <section className="card">
        <h1>Módulo de RH</h1>
        <p className="muted">Triagem de currículos, extração de habilidades e ranking por vaga.</p>
        {erro && <p className="error">{erro}</p>}
        {erro ? (
          <button className="button" onClick={entrar} disabled={carregando}>{carregando ? "Entrando..." : "Entrar com login de demonstração"}</button>
        ) : (
          <button className="button secondary" onClick={carregar} disabled={carregando}>{carregando ? "Carregando..." : "Atualizar dados"}</button>
        )}
      </section>

      <h2 className="section-title">Vagas</h2>
      <table className="table">
        <thead>
          <tr>
            <th>Título</th>
            <th>Tipo de obra</th>
            <th>Requisitos</th>
            <th>Habilidades</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {vagas.map((vaga) => (
            <tr key={vaga.id}>
              <td>{vaga.titulo}</td>
              <td>{vaga.tipo_obra}</td>
              <td>{vaga.requisitos}</td>
              <td>{vaga.habilidades}</td>
              <td>{vaga.status}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 className="section-title">Ranking da primeira vaga</h2>
      <table className="table">
        <thead>
          <tr>
            <th>Candidato</th>
            <th>Cargo</th>
            <th>Experiência</th>
            <th>Score</th>
            <th>Motivos</th>
          </tr>
        </thead>
        <tbody>
          {ranking.map((item) => (
            <tr key={item.candidato.id}>
              <td>{item.candidato.nome}</td>
              <td>{item.candidato.cargo || "-"}</td>
              <td>{item.candidato.experiencia_anos.toFixed(1)} ano(s)</td>
              <td><strong>{item.score}%</strong></td>
              <td>{item.motivos.join(" ")}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 className="section-title">Candidatos</h2>
      <div className="grid">
        {candidatos.map((candidato) => (
          <article className="card" key={candidato.id}>
            <h3>{candidato.nome}</h3>
            <p className="muted">{candidato.email}</p>
            <p><strong>Cargo:</strong> {candidato.cargo || "-"}</p>
            <p><strong>Habilidades:</strong> {candidato.habilidades || "-"}</p>
            <p>{candidato.resumo}</p>
          </article>
        ))}
      </div>
    </main>
  );
}
