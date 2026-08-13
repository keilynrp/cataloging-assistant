"use client";

import { useState } from "react";

/** Placeholder for when real authentication exists. Today the app has no
 * login — every mutation (review decision, draft, agent conversation)
 * self-declares its author's name at the moment of the action instead of
 * reading it from a session, so this panel says exactly that rather than
 * implying a session that doesn't exist. */
export function UserMenu() {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        type="button"
        className="bell-trigger"
        aria-haspopup="true"
        aria-expanded={open}
        aria-label="Perfil de usuario"
        onClick={() => setOpen((value) => !value)}
      >
        <svg
          viewBox="0 0 24 24"
          width="20"
          height="20"
          aria-hidden="true"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.8}
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="8" r="4" />
          <path d="M4 20c0-3.5 3.5-6 8-6s8 2.5 8 6" />
        </svg>
      </button>
      {open ? (
        <div className="notification-panel" role="dialog" aria-label="Perfil de usuario">
          <div className="notification-panel-header">
            <strong>Sin autenticación</strong>
          </div>
          <p style={{ color: "var(--muted)" }} className="text-sm">
            Este piloto no tiene inicio de sesión. Cada acción (revisión, borrador, conversación)
            declara su propio nombre en el momento; todavía no hay una sesión de usuario
            persistente.
          </p>
        </div>
      ) : null}
    </div>
  );
}
