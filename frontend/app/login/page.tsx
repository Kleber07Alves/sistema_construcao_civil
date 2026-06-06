"use client";
// ─────────────────────────────────────────────────────────────────────────────
// Página de login do ecossistema Next.js.
// ─────────────────────────────────────────────────────────────────────────────

import { type FormEvent, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const router        = useRouter();
  const searchParams  = useSearchParams();

  const [email,      setEmail]      = useState("");
  const [senha,      setSenha]      = useState("");
  const [erro,       setErro]       = useState("");
  const [carregando, setCarregando] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setErro("");

    if (!email.trim() || !senha.trim()) {
      setErro("Preencha e-mail e senha.");
      return;
    }

    setCarregando(true);
    try {
      await login(email.trim(), senha);
      const redirect = searchParams.get("redirect") ?? "/";
      router.replace(redirect);
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Falha no login.");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <main className="container" style={{ maxWidth: 420, paddingTop: 80 }}>
      <div className="card">
        <h1 style={{ marginBottom: 4 }}>Entrar</h1>
        <p className="muted" style={{ marginBottom: 24 }}>
          Sistema de Gestão — Construção Civil
        </p>

        {erro && (
          <p className="error" style={{ marginBottom: 16 }}>
            {erro}
          </p>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: "block", marginBottom: 4, fontWeight: 500 }}>
              E-mail
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="gestor@empresa.com"
              autoComplete="email"
              autoFocus
              required
              style={{
                width: "100%",
                padding: "8px 12px",
                border: "1px solid #cbd5e1",
                borderRadius: 6,
                fontSize: 14,
                boxSizing: "border-box",
              }}
            />
          </div>

          <div style={{ marginBottom: 24 }}>
            <label style={{ display: "block", marginBottom: 4, fontWeight: 500 }}>
              Senha
            </label>
            <input
              type="password"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              placeholder="••••••"
              autoComplete="current-password"
              required
              style={{
                width: "100%",
                padding: "8px 12px",
                border: "1px solid #cbd5e1",
                borderRadius: 6,
                fontSize: 14,
                boxSizing: "border-box",
              }}
            />
          </div>

          <button
            type="submit"
            className="button"
            disabled={carregando}
            style={{ width: "100%" }}
          >
            {carregando ? "Entrando…" : "Entrar"}
          </button>
        </form>
      </div>
    </main>
  );
}