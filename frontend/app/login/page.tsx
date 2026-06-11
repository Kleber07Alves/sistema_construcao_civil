"use client";
// frontend/app/login/page.tsx

// REGRA DO NEXT.JS 16 (App Router + output: standalone):
// Durante o build estático, o Next.js pré-renderiza todas as páginas sem URL.
// useSearchParams() depende de uma URL — se chamado fora de um <Suspense>,
// o build falha com: "useSearchParams() should be wrapped in a suspense boundary".

// SOLUÇÃO: separar em dois componentes no mesmo arquivo:
//   LoginForm  (inner)  — contém useSearchParams(), fica dentro do <Suspense>
//   LoginPage  (outer)  — default export, envolve LoginForm com <Suspense>

import { Suspense, useState, type FormEvent } from "react";
import { useRouter, useSearchParams }         from "next/navigation";
import { useAuth }                             from "@/contexts/AuthContext";


// LoginForm — componente interno que usa useSearchParams()
// Renderiza apenas no cliente após a hidratação (correto para search params)

function LoginForm() {
  const { login }     = useAuth();
  const router        = useRouter();
  const searchParams  = useSearchParams(); // seguro aqui — dentro do <Suspense>

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
      // Redireciona para o destino original ou para o dashboard
      const redirect = searchParams.get("redirect") ?? "/";
      router.replace(redirect);
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Falha no login.");
    } finally {
      setCarregando(false);
    }
  }

  const inputStyle = {
    width:        "100%",
    padding:      "8px 12px",
    border:       "1px solid #cbd5e1",
    borderRadius: 6,
    fontSize:     14,
    boxSizing:    "border-box" as const,
  };

  return (
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
            style={inputStyle}
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
            style={inputStyle}
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
  );
}

export default function LoginPage() {
  return (
    <main className="container" style={{ maxWidth: 420, paddingTop: 80 }}>
      {/*
        O fallback é exibido brevemente durante a hidratação inicial no cliente.
        Mantê-lo visualmente alinhado ao card evita layout shift.
      */}
      <Suspense
        fallback={
          <div className="card" style={{ textAlign: "center", padding: 32 }}>
            <p className="muted">Carregando...</p>
          </div>
        }
      >
        <LoginForm />
      </Suspense>
    </main>
  );
}