"use client";
// frontend/components/ProtectedRoute.tsx
import type { ReactNode } from "react";
import { useAuth } from "@/contexts/AuthContext";
import type { PerfilUsuario } from "@/types";

interface ProtectedRouteProps {
  perfisPermitidos: PerfilUsuario[];
  children: ReactNode;
  fallback?: ReactNode;
}

export function ProtectedRoute({
  perfisPermitidos,
  children,
  fallback,
}: ProtectedRouteProps) {
  const { usuario, loading } = useAuth();

  if (loading) return null;

  const temAcesso =
    usuario !== null && perfisPermitidos.includes(usuario.perfil);

  if (!temAcesso) {
    if (fallback === null) return null;
    if (fallback !== undefined) return <>{fallback}</>;

    return (
      <div className="card" style={{ borderLeft: "4px solid #ef4444" }}>
        <h3 style={{ marginBottom: 8 }}>Acesso restrito</h3>
        <p className="muted" style={{ marginBottom: 4 }}>
          Seu perfil <strong>{usuario?.perfil ?? "desconhecido"}</strong> não tem
          permissão para visualizar este conteúdo.
        </p>
        <p className="muted" style={{ fontSize: 13 }}>
          Perfis autorizados: <strong>{perfisPermitidos.join(", ")}</strong>
        </p>
      </div>
    );
  }

  return <>{children}</>;
}

/** Hook auxiliar para verificações imperativas em lógica condicional inline. */
export function usePerfil(perfisPermitidos: PerfilUsuario[]): boolean {
  const { usuario, loading } = useAuth();
  if (loading || !usuario) return false;
  return perfisPermitidos.includes(usuario.perfil);
}