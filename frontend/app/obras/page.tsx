"use client";

import { useEffect, useState } from "react";
import { apiJson, loginDemo } from "../../lib/api";

type Obra = {
  id: number;
  nome: string;
  endereco: string;
  status: string;
  prioridade: string;
  data_inicio: string | null;
};

export default function ObrasPage() {
  const [obras, setObras] = useState<Obra[]>([]);
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);

  async function carregar() {
    setCarregando(true);
    try {
      setObras(await apiJson<Obra[]>("/core/obras"));
      setErro("");
    } catch (e) {
      setObras([]);
      setErro(e instanceof Error ? e.message : "Faça login para visualizar as obras.");
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
        <h1>Obras</h1>
        <p className="muted">Listagem das obras cadastradas no módulo Core.</p>
        {erro && <p className="error">{erro}</p>}
        {erro ? (
          <button className="button" onClick={entrar} disabled={carregando}>{carregando ? "Entrando..." : "Entrar com login de demonstração"}</button>
        ) : (
          <button className="button secondary" onClick={carregar} disabled={carregando}>{carregando ? "Carregando..." : "Atualizar dados"}</button>
        )}
      </section>

      <section className="section-title">
        <table className="table">
          <thead>
            <tr>
              <th>Nome</th>
              <th>Endereço</th>
              <th>Status</th>
              <th>Prioridade</th>
              <th>Início</th>
            </tr>
          </thead>
          <tbody>
            {obras.map((obra) => (
              <tr key={obra.id}>
                <td>{obra.nome}</td>
                <td>{obra.endereco}</td>
                <td>{obra.status}</td>
                <td>{obra.prioridade}</td>
                <td>{obra.data_inicio || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
