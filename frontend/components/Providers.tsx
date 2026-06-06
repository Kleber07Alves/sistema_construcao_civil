"use client";
// ─────────────────────────────────────────────────────────────────────────────
// Wrapper "use client" que permite ao layout.tsx (Server Component) envolver
// toda a árvore com providers do React sem se tornar um Client Component.
// ─────────────────────────────────────────────────────────────────────────────

import { AuthProvider } from "@/contexts/AuthContext";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      {children}
    </AuthProvider>
  );
}