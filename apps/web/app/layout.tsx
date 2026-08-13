import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AgentWidget } from "./agent-widget";
import { NotificationBell } from "./notification-bell";
import { Sidebar } from "./sidebar";

import "./globals.css";

export const metadata: Metadata = {
  title: "Asistencia catalográfica · P'UHREPECHA",
  description: "Explorador local con DSpace de solo lectura y revisión humana auditable",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="es">
      <body className="antialiased">
        <div className="flex min-h-screen">
          <Sidebar />
          <div className="flex min-h-screen flex-1 flex-col">
            <header className="sticky top-0 z-30 flex items-center justify-end gap-3 border-b border-line bg-surface px-4 py-3 md:px-8">
              <AgentWidget />
              <NotificationBell />
            </header>
            <main className="flex-1">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
