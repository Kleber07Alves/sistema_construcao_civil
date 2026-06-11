"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode, 
} from "react";
import { useRouter } from "next/navigation";
import type { LoginResponse, PerfilUsuario, UsuarioLogado } from "@/types";

const LS_TOKEN      = "token";
const LS_NOME       = "usuario";
const LS_PERFIL     = "perfil";
const COOKIE_KEY    = "auth_token";
const TOKEN_MAX_AGE = 8 * 60 * 60; // 8h — alinhado com ACCESS_TOKEN_EXPIRE_MINUTES=480

// =============================================================================
// Tipos do contexto
// =============================================================================

interface AuthContextType {
  token:        string | null;
  usuario:      UsuarioLogado | null;
  loading:      boolean;
  autenticado:  boolean;
  login:        (email: string, senha: string) => Promise<void>;
  logout:       () => void;
}

// =============================================================================
// Helpers de storage (browser-only)
// =============================================================================

function salvarAuth(token: string, nome: string, perfil: PerfilUsuario): void {
  localStorage.setItem(LS_TOKEN,  token);
  localStorage.setItem(LS_NOME,   nome);
  localStorage.setItem(LS_PERFIL, perfil);
  document.cookie =
    `${COOKIE_KEY}=${token}; path=/; max-age=${TOKEN_MAX_AGE}; SameSite=Lax`;
}

function limparAuth(): void {
  localStorage.removeItem(LS_TOKEN);
  localStorage.removeItem(LS_NOME);
  localStorage.removeItem(LS_PERFIL);
  document.cookie = `${COOKIE_KEY}=; path=/; max-age=0; SameSite=Lax`;
}

function lerAuthSalva(): { token: string; usuario: UsuarioLogado } | null {
  const token  = localStorage.getItem(LS_TOKEN);
  const nome   = localStorage.getItem(LS_NOME);
  const perfil = localStorage.getItem(LS_PERFIL) as PerfilUsuario | null;
  if (!token || !nome || !perfil) return null;
  return { token, usuario: { nome, perfil } };
}

// =============================================================================
// Contexto e Provider
// =============================================================================

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token,   setToken]   = useState<string | null>(null);
  const [usuario, setUsuario] = useState<UsuarioLogado | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const salva = lerAuthSalva();
    if (salva) {
      setToken(salva.token);
      setUsuario(salva.usuario);
      document.cookie =
        `${COOKIE_KEY}=${salva.token}; path=/; max-age=${TOKEN_MAX_AGE}; SameSite=Lax`;
    }
    setLoading(false);
  }, []);

  const login = useCallback(async (email: string, senha: string) => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const res = await fetch(`${apiUrl}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, senha }),
    });
    if (!res.ok) {
      const body: { detail?: string } = await res.json().catch(() => ({}));
      throw new Error(body.detail ?? `Erro ${res.status}: credenciais inválidas.`);
    }
    const data = (await res.json()) as LoginResponse;
    salvarAuth(data.access_token, data.nome, data.perfil);
    setToken(data.access_token);
    setUsuario({ nome: data.nome, perfil: data.perfil });
  }, []);

  const logout = useCallback(() => {
    limparAuth();
    setToken(null);
    setUsuario(null);
    router.push("/login");
  }, [router]);

  return (
    <AuthContext.Provider
      value={{ token, usuario, loading, autenticado: token !== null, login, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// =============================================================================
// Hook de consumo
// =============================================================================

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error(
      "useAuth() deve ser usado dentro de <AuthProvider>. " +
      "Verifique se Providers.tsx está envolvendo o layout raiz.",
    );
  }
  return ctx;
}