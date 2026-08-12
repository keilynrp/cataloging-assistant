"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { PUBLIC_API_URL } from "@/lib/api";
import type { Notification, NotificationList, NotificationPreference, NotificationPreferenceList } from "@/lib/api";

const RECONNECT_DELAYS_MS = [1000, 2000, 5000, 10000, 30000];
const POLL_INTERVAL_MS = 30000;
const MESSAGE_TIMEOUT_MS = 65000;
const PANEL_LIMIT = 10;

type ConnectionStatus = "connecting" | "online" | "offline" | "reconnecting";

const STATUS_LABEL: Record<ConnectionStatus, string> = {
  connecting: "Actualizando",
  online: "Actualizado",
  offline: "Sin conexión",
  reconnecting: "Reconectando",
};
const STATE_LABEL: Record<string, string> = { unread: "Sin leer", read: "Leída", archived: "Archivada" };
const EVENT_TYPE_LABEL: Record<string, string> = {
  "sync.completed": "Sincronización completada",
  "sync.failed": "Sincronización fallida",
  "items.changed": "Ítems nuevos o modificados",
  "diagnostics.changed": "Nuevos hallazgos de diagnóstico",
  "draft.stale": "Borrador local obsoleto",
  "review.deferred": "Revisión pospuesta",
  "suggestion.pending": "Sugerencia pendiente",
  "vocabulary.promoted": "Vocabulario controlado actualizado",
};
const RELATIVE_TIME = new Intl.RelativeTimeFormat("es", { numeric: "auto" });

function wsUrl(): string {
  return `${PUBLIC_API_URL.replace(/^http/, "ws")}/ws/notifications`;
}

function jitter(delayMs: number): number {
  const spread = delayMs * 0.2;
  return delayMs - spread + Math.random() * spread * 2;
}

function formatAge(iso: string): string {
  const diffMinutes = Math.round((new Date(iso).getTime() - Date.now()) / 60000);
  if (Math.abs(diffMinutes) < 60) return RELATIVE_TIME.format(diffMinutes, "minute");
  const diffHours = Math.round(diffMinutes / 60);
  if (Math.abs(diffHours) < 24) return RELATIVE_TIME.format(diffHours, "hour");
  return RELATIVE_TIME.format(Math.round(diffHours / 24), "day");
}

export function NotificationBell() {
  const [unreadCount, setUnreadCount] = useState(0);
  const [items, setItems] = useState<Notification[]>([]);
  const [panelOpen, setPanelOpen] = useState(false);
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const [preferencesOpen, setPreferencesOpen] = useState(false);
  const [preferences, setPreferences] = useState<NotificationPreference[]>([]);
  const socketRef = useRef<WebSocket | null>(null);
  const mounted = useRef(true);

  const refresh = useCallback(async () => {
    try {
      const response = await fetch(`${PUBLIC_API_URL}/api/notifications?limit=${PANEL_LIMIT}`, {
        cache: "no-store",
      });
      if (!response.ok) throw new Error(`status ${response.status}`);
      const data: NotificationList = await response.json();
      if (!mounted.current) return;
      setItems(data.items);
      setUnreadCount(data.unread_count);
    } catch {
      // Keep the last known state; the connection indicator already reflects degradation.
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    let reconnectAttempt = 0;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let watchdog: ReturnType<typeof setTimeout> | null = null;

    const armWatchdog = (socket: WebSocket) => {
      if (watchdog) clearTimeout(watchdog);
      watchdog = setTimeout(() => socket.close(), MESSAGE_TIMEOUT_MS);
    };

    const scheduleReconnect = () => {
      if (reconnectTimer) return;
      const delay = RECONNECT_DELAYS_MS[Math.min(reconnectAttempt, RECONNECT_DELAYS_MS.length - 1)];
      reconnectAttempt += 1;
      if (mounted.current) setStatus("reconnecting");
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        connect();
      }, jitter(delay));
    };

    const connect = () => {
      let socket: WebSocket;
      try {
        socket = new WebSocket(wsUrl());
      } catch {
        scheduleReconnect();
        return;
      }
      socketRef.current = socket;
      socket.onopen = () => {
        reconnectAttempt = 0;
        if (mounted.current) setStatus("online");
        armWatchdog(socket);
        void refresh();
      };
      socket.onmessage = () => {
        armWatchdog(socket);
        void refresh();
      };
      socket.onclose = () => {
        if (watchdog) clearTimeout(watchdog);
        if (!mounted.current) return;
        setStatus("offline");
        scheduleReconnect();
      };
      socket.onerror = () => socket.close();
    };

    void refresh();
    connect();

    const poll = setInterval(() => {
      if (socketRef.current?.readyState !== WebSocket.OPEN) void refresh();
    }, POLL_INTERVAL_MS);
    const onVisible = () => {
      if (document.visibilityState === "visible") void refresh();
    };
    document.addEventListener("visibilitychange", onVisible);
    window.addEventListener("focus", onVisible);

    return () => {
      mounted.current = false;
      clearInterval(poll);
      document.removeEventListener("visibilitychange", onVisible);
      window.removeEventListener("focus", onVisible);
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (watchdog) clearTimeout(watchdog);
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [refresh]);

  const act = useCallback(
    async (path: string) => {
      try {
        await fetch(path, { method: "POST" });
      } finally {
        void refresh();
      }
    },
    [refresh],
  );

  const loadPreferences = useCallback(async () => {
    try {
      const response = await fetch(`${PUBLIC_API_URL}/api/notifications/preferences`, {
        cache: "no-store",
      });
      if (!response.ok) throw new Error(`status ${response.status}`);
      const data: NotificationPreferenceList = await response.json();
      if (mounted.current) setPreferences(data.preferences);
    } catch {
      // Preferences stay at their last known state; the toggle can retry.
    }
  }, []);

  const togglePreference = useCallback(
    async (eventType: string, muted: boolean) => {
      try {
        await fetch(`/api/notifications/preferences/${encodeURIComponent(eventType)}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ muted }),
        });
      } finally {
        void loadPreferences();
      }
    },
    [loadPreferences],
  );

  const badge = unreadCount > 99 ? "99+" : String(unreadCount);

  return (
    <div className="notification-bell">
      <button
        type="button"
        className="bell-trigger"
        aria-haspopup="true"
        aria-expanded={panelOpen}
        aria-label={`Notificaciones, ${unreadCount} sin leer`}
        onClick={() => setPanelOpen((open) => !open)}
      >
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">
          <path
            fill="currentColor"
            d="M12 2a6 6 0 0 0-6 6v3.09c0 .58-.2 1.14-.57 1.59L4 14.5c-.86 1.03-.14 2.5 1.19 2.5h13.62c1.33 0 2.05-1.47 1.19-2.5l-1.43-1.82A2.5 2.5 0 0 1 18 11.09V8a6 6 0 0 0-6-6Zm0 20a2.5 2.5 0 0 0 2.45-2h-4.9A2.5 2.5 0 0 0 12 22Z"
          />
        </svg>
        {unreadCount > 0 ? <span className="bell-badge">{badge}</span> : null}
      </button>
      {panelOpen ? (
        <div className="notification-panel" role="dialog" aria-label="Notificaciones">
          <div className="notification-panel-header">
            <strong>Notificaciones</strong>
            <span className={`connection-status ${status}`}>{STATUS_LABEL[status]}</span>
          </div>
          <div className="notification-panel-actions">
            <button
              type="button"
              onClick={() => void act("/api/notifications/read-all")}
              disabled={unreadCount === 0}
            >
              Marcar todos como leídos
            </button>
          </div>
          {items.length ? (
            <ul className="notification-list">
              {items.map((item) => (
                <li key={item.notification_id} className={`notification-item ${item.severity} ${item.state}`}>
                  <div className="notification-item-header">
                    <span className={`severity-dot ${item.severity}`} aria-hidden="true" />
                    <strong>{item.title}</strong>
                    <span className="notification-age">{formatAge(item.occurred_at)}</span>
                  </div>
                  <p>{item.summary}</p>
                  <div className="notification-item-footer">
                    <span className="notification-state-label">{STATE_LABEL[item.state]}</span>
                    <div className="notification-item-actions">
                      {item.state === "unread" ? (
                        <button
                          type="button"
                          onClick={() => void act(`/api/notifications/${item.notification_id}/read`)}
                        >
                          Marcar leído
                        </button>
                      ) : null}
                      {item.state !== "archived" ? (
                        <button
                          type="button"
                          onClick={() => void act(`/api/notifications/${item.notification_id}/archive`)}
                        >
                          Archivar
                        </button>
                      ) : null}
                      {item.target_path ? (
                        <a href={item.target_path} onClick={() => setPanelOpen(false)}>
                          Abrir
                        </a>
                      ) : null}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="notification-empty">Sin avisos operativos por ahora.</p>
          )}
          <div className="notification-panel-footer">
            <Link href="/notifications" onClick={() => setPanelOpen(false)}>
              Ver historial completo
            </Link>
            <button
              type="button"
              onClick={() => {
                setPreferencesOpen((open) => {
                  const next = !open;
                  if (next && preferences.length === 0) void loadPreferences();
                  return next;
                });
              }}
              aria-expanded={preferencesOpen}
            >
              Preferencias
            </button>
          </div>
          {preferencesOpen ? (
            <ul className="notification-preferences">
              {preferences.map((preference) => (
                <li key={preference.event_type}>
                  <label>
                    <input
                      type="checkbox"
                      checked={!preference.muted}
                      onChange={(event) =>
                        void togglePreference(preference.event_type, !event.target.checked)
                      }
                    />
                    {EVENT_TYPE_LABEL[preference.event_type] ?? preference.event_type}
                  </label>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
