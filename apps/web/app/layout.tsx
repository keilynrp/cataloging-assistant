import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import { NotificationBell } from "./notification-bell";

import "./globals.css";

export const metadata: Metadata = {
  title: "Asistencia catalográfica · P'UHREPECHA",
  description: "Explorador local con DSpace de solo lectura y revisión humana auditable",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="es">
      <body>
        <header className="site-header">
          <Link href="/" className="brand">
            <span className="brand-mark">AC</span>
            <span>
              <strong>Asistencia catalográfica</strong>
              <small>P&apos;UHREPECHA · DSpace solo lectura</small>
            </span>
          </Link>
          <nav className="site-nav" aria-label="Navegación principal">
            <Link href="/">Registros</Link>
            <Link href="/work-queue">Cola</Link>
            <Link href="/catalog-profile">Evidencia</Link>
            <Link href="/controlled-terms">Vocabularios</Link>
            <Link href="/deferred-drafts">Pospuestos</Link>
          </nav>
          <NotificationBell />
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}

