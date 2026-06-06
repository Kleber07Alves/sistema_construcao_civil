"use client";
// ─────────────────────────────────────────────────────────────────────────────
// Barra de navegação com dados do usuário logado e botão de logout.
// Extraída do layout.tsx porque consome useAuth() (Client Component).
// ─────────────────────────────────────────────────────────────────────────────
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";

export function NavHeader() {
  const { usuario, logout, autenticado } = useAuth();

  return (
    <header className="header">
      <div className="header-content">
        <strong>Sistema de Gestão — Construção Civil</strong>

        <nav className="nav">
          <Link href="/">Dashboard</Link>
          <Link href="/obras">Obras</Link>
          <Link href="/logistico">Logística</Link>
          <Link href="/rh">RH</Link>
        </nav>

        {autenticado && usuario && (
          <div className="nav" style={{ gap: 12, alignItems: "center" }}>
            <span className="muted" style={{ fontSize: 13 }}>
              {usuario.nome}{" "}
              <span
                style={{
                  background: "#e2e8f0",
                  borderRadius: 4,
                  padding: "2px 6px",
                  fontSize: 11,
                  textTransform: "uppercase",
                }}
              >
                {usuario.perfil}
              </span>
            </span>
            <button
              className="button secondary"
              style={{ padding: "4px 10px", fontSize: 13 }}
              onClick={logout}
            >
              Sair
            </button>
          </div>
        )}
      </div>
    </header>
  );
}