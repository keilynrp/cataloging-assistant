import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AgentWidget } from "./agent-widget";
import { NotificationBell } from "./notification-bell";
import { Sidebar } from "./sidebar";
import { ThemeToggle } from "./theme-toggle";
import { UserMenu } from "./user-menu";

import "./globals.css";

export const metadata: Metadata = {
  title: "Asistencia catalográfica · P'UHREPECHA",
  description: "Explorador local con DSpace de solo lectura y revisión humana auditable",
};

const THEME_INIT_SCRIPT = `
(function () {
  try {
    var stored = localStorage.getItem("theme");
    var dark = stored ? stored === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
    if (dark) document.documentElement.classList.add("dark");
  } catch (error) {}
})();
`;

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="es">
      <body className="antialiased">
        {/* Runs before paint so the toggle's stored preference applies with
            no flash of the wrong theme; must stay a plain inline script, not
            a hook, since React only runs after hydration. */}
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
        <div className="flex min-h-screen">
          <Sidebar />
          <div className="flex min-h-screen flex-1 flex-col">
            <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-line bg-surface px-4 py-3 md:px-8">
              <form
                action="/"
                className="hidden max-w-md flex-1 items-center gap-2 rounded-lg border border-line bg-paper px-3 py-2 sm:flex"
              >
                <svg
                  viewBox="0 0 24 24"
                  width="16"
                  height="16"
                  aria-hidden="true"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={1.8}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="shrink-0 text-muted"
                >
                  <circle cx="11" cy="11" r="7" />
                  <path d="m20 20-3.5-3.5" />
                </svg>
                <input
                  type="search"
                  name="q"
                  placeholder="Buscar ítems por título o handle…"
                  className="w-full bg-transparent text-sm text-ink placeholder:text-muted focus:outline-none"
                />
              </form>
              <div className="ml-auto flex items-center gap-3">
                <NotificationBell />
                <UserMenu />
                <ThemeToggle />
              </div>
            </header>
            <main className="flex-1">{children}</main>
          </div>
        </div>
        <AgentWidget />
      </body>
    </html>
  );
}
