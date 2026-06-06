
// Permanece Server Component — não adicionar "use client" aqui.
import type { Metadata } from "next";
import { Providers } from "@/components/Providers";
import { NavHeader } from "@/components/NavHeader";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sistema de Gestão — Construção Civil",
  description: "MVP de gestão para construção civil",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        <Providers>
          <NavHeader />
          {children}
        </Providers>
      </body>
    </html>
  );
}