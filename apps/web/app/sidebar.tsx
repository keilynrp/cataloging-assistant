"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { useState } from "react";

type IconProps = { className?: string };

function IconBase({ className, children }: IconProps & { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

function IconHome(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M4 11.5 12 4l8 7.5" />
      <path d="M6 10v9h5v-6h2v6h5v-9" />
    </IconBase>
  );
}
function IconQueue(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M9 6h11M9 12h11M9 18h11" />
      <path d="M4 6h.01M4 12h.01M4 18h.01" />
    </IconBase>
  );
}
function IconChart(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M4 20V10M12 20V4M20 20v-7" />
    </IconBase>
  );
}
function IconReport(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M6 3h9l3 3v15H6z" />
      <path d="M14 3v4h4M9 11h6M9 15h6M9 19h4" />
    </IconBase>
  );
}
function IconTag(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M11 4h6a2 2 0 0 1 2 2v6a2 2 0 0 1-.59 1.41l-7 7a2 2 0 0 1-2.82 0l-6-6a2 2 0 0 1 0-2.82l7-7A2 2 0 0 1 11 4Z" />
      <path d="M15.5 8.5h.01" />
    </IconBase>
  );
}
function IconClock(props: IconProps) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="12" r="8" />
      <path d="M12 8v4l3 2" />
    </IconBase>
  );
}
function IconBell(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M12 3a6 6 0 0 0-6 6v3.09c0 .58-.2 1.14-.57 1.59L4 15.5c-.4.5-.05 1.5.6 1.5h14.8c.65 0 1-.99.6-1.5l-1.43-1.82A2.5 2.5 0 0 1 18 12.09V9a6 6 0 0 0-6-6Z" />
      <path d="M9.5 19a2.5 2.5 0 0 0 5 0" />
    </IconBase>
  );
}
function IconChat(props: IconProps) {
  return (
    <IconBase {...props}>
      <path d="M4 12c0-4.42 3.58-8 8-8s8 3.58 8 8-3.58 8-8 8c-.9 0-1.77-.1-2.6-.28-.9.7-2.28 1.52-4.15 2.02a.5.5 0 0 1-.55-.77c.9-1.3 1.3-2.5 1.4-3.48A7.94 7.94 0 0 1 4 12Z" />
    </IconBase>
  );
}
function IconSettings(props: IconProps) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15 1.65 1.65 0 0 0 3.17 14H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" />
    </IconBase>
  );
}

const NAV_ITEMS: Array<{ href: string; label: string; icon: (props: IconProps) => ReactNode }> = [
  { href: "/", label: "Registros", icon: IconHome },
  { href: "/work-queue", label: "Cola de trabajo", icon: IconQueue },
  { href: "/catalog-profile", label: "Evidencia", icon: IconChart },
  { href: "/reports/dspace-weekly", label: "Reporte semanal", icon: IconReport },
  { href: "/controlled-terms", label: "Vocabularios", icon: IconTag },
  { href: "/deferred-drafts", label: "Pospuestos", icon: IconClock },
  { href: "/notifications", label: "Notificaciones", icon: IconBell },
  { href: "/asistente", label: "Asistente", icon: IconChat },
  { href: "/settings", label: "Configuración", icon: IconSettings },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Sidebar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        className="fixed left-4 top-4 z-40 inline-flex h-10 w-10 items-center justify-center rounded-lg border border-line bg-surface text-ink md:hidden"
        aria-label="Abrir navegación"
        aria-expanded={mobileOpen}
        onClick={() => setMobileOpen(true)}
      >
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
          <path fill="currentColor" d="M3 6h18v2H3zm0 5h18v2H3zm0 5h18v2H3z" />
        </svg>
      </button>

      {mobileOpen ? (
        <button
          type="button"
          aria-label="Cerrar navegación"
          className="fixed inset-0 z-40 bg-black/30 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      ) : null}

      <aside
        className={[
          "fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-line bg-surface transition-transform duration-200",
          "md:sticky md:top-0 md:z-auto md:h-screen md:translate-x-0 md:shrink-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
        ].join(" ")}
      >
        <div className="flex items-center gap-3 px-5 py-5">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-500 font-bold text-white">
            AC
          </span>
          <div className="flex min-w-0 flex-col">
            <strong className="truncate text-sm leading-tight text-ink">
              Asistencia catalográfica
            </strong>
            <small className="truncate text-xs text-muted">P&apos;UHREPECHA · solo lectura</small>
          </div>
          <button
            type="button"
            className="ml-auto shrink-0 text-muted md:hidden"
            aria-label="Cerrar navegación"
            onClick={() => setMobileOpen(false)}
          >
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
              <path
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                fill="none"
                d="m6 6 12 12M18 6 6 18"
              />
            </svg>
          </button>
        </div>
        <nav
          className="flex flex-1 flex-col gap-1 overflow-y-auto px-3 pb-6"
          aria-label="Navegación principal"
        >
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
            const active = isActive(pathname, href);
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setMobileOpen(false)}
                aria-current={active ? "page" : undefined}
                className={[
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  active ? "bg-brand-100 text-brand-700" : "text-muted hover:bg-paper hover:text-ink",
                ].join(" ")}
              >
                <Icon className="h-[18px] w-[18px] shrink-0" />
                {label}
              </Link>
            );
          })}
        </nav>
      </aside>
    </>
  );
}
