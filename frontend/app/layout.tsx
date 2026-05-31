import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sistema de Gestão — Construção Civil",
  description: "MVP de gestão para construção civil",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        <header className="header">
          <div className="header-content">
            <strong>Sistema de Gestão — Construção Civil</strong>
            <nav className="nav">
              <Link href="/">Dashboard</Link>
              <Link href="/obras">Obras</Link>
              <Link href="/logistico">Logística</Link>
              <Link href="/rh">RH</Link>
            </nav>
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}