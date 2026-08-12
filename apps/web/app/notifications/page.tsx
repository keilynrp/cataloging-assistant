import Link from "next/link";

import { getNotifications } from "@/lib/api";
import { archiveNotification, markAllNotificationsRead, markNotificationRead } from "./actions";

type QueryParams = {
  state?: string;
  event_type?: string;
  cursor?: string;
  notification?: string;
};

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
const STATE_LABEL: Record<string, string> = { unread: "Sin leer", read: "Leída", archived: "Archivada" };
const OUTCOME_LABEL: Record<string, string> = {
  saved: "Cambio aplicado.",
  error: "No se pudo aplicar el cambio; verifica la conexión o el token local.",
};

function formatDate(iso: string): string {
  return new Intl.DateTimeFormat("es-MX", { dateStyle: "medium", timeStyle: "short" }).format(
    new Date(iso),
  );
}

export default async function NotificationsPage({
  searchParams,
}: {
  searchParams: Promise<QueryParams>;
}) {
  const params = await searchParams;
  let notifications: Awaited<ReturnType<typeof getNotifications>> | null = null;
  try {
    notifications = await getNotifications({
      state: params.state,
      event_type: params.event_type,
      cursor: params.cursor,
    });
  } catch {
    // Keep a clear degraded state below when the API is unavailable.
  }

  const currentQuery = new URLSearchParams();
  if (params.state) currentQuery.set("state", params.state);
  if (params.event_type) currentQuery.set("event_type", params.event_type);
  if (params.cursor) currentQuery.set("cursor", params.cursor);
  const backHref = `/notifications${currentQuery.toString() ? `?${currentQuery.toString()}` : ""}`;

  const nextHref = (() => {
    if (!notifications?.next_cursor) return null;
    const next = new URLSearchParams(currentQuery);
    next.set("cursor", notifications.next_cursor);
    return `/notifications?${next.toString()}`;
  })();
  const restartHref = (() => {
    const next = new URLSearchParams();
    if (params.state) next.set("state", params.state);
    if (params.event_type) next.set("event_type", params.event_type);
    return `/notifications${next.toString() ? `?${next.toString()}` : ""}`;
  })();

  return (
    <div className="shell">
      <Link href="/" className="back-link">← Volver a registros</Link>
      <header className="profile-hero">
        <p className="eyebrow">Notificaciones · colección piloto</p>
        <h1>Historial de notificaciones</h1>
        <p>
          Avisos operativos generados localmente. No representan evidencia catalográfica ni
          cambian hallazgos, borradores, sugerencias o DSpace.
        </p>
      </header>

      {params.notification ? (
        <section
          className={params.notification === "saved" ? "review-status" : "review-status error"}
          role="status"
        >
          {OUTCOME_LABEL[params.notification] ?? OUTCOME_LABEL.error}
        </section>
      ) : null}

      {notifications === null ? (
        <section className="notice" role="status">
          <strong>El historial de notificaciones no está disponible.</strong>
          <span>Verifica PostgreSQL y la API local antes de volver a cargar.</span>
        </section>
      ) : (
        <>
          <section aria-labelledby="notifications-filters-heading">
            <div className="section-heading">
              <h2 id="notifications-filters-heading">Filtros</h2>
              <span>{notifications.unread_count} sin leer</span>
            </div>
            <form className="queue-filters" action="/notifications">
              <label>
                Estado
                <select name="state" defaultValue={params.state ?? ""}>
                  <option value="">Cualquiera</option>
                  <option value="unread">Sin leer</option>
                  <option value="read">Leída</option>
                  <option value="archived">Archivada</option>
                </select>
              </label>
              <label>
                Tipo de evento
                <select name="event_type" defaultValue={params.event_type ?? ""}>
                  <option value="">Cualquiera</option>
                  {Object.entries(EVENT_TYPE_LABEL).map(([value, label]) => (
                    <option value={value} key={value}>{label}</option>
                  ))}
                </select>
              </label>
              <div className="queue-filter-actions">
                <button type="submit">Aplicar filtros</button>
                <Link href="/notifications">Limpiar</Link>
              </div>
            </form>
            <form action={markAllNotificationsRead}>
              <input type="hidden" name="back" value={backHref} />
              <button type="submit" disabled={notifications.unread_count === 0}>
                Marcar todos como leídos
              </button>
            </form>
          </section>

          <section aria-labelledby="notifications-list-heading">
            <div className="section-heading">
              <h2 id="notifications-list-heading">Avisos</h2>
            </div>
            {notifications.items.length ? (
              <div className="notification-history-list">
                {notifications.items.map((item) => (
                  <article
                    className={`diagnostic-card ${item.severity === "error" ? "error" : item.severity === "warning" ? "warning" : ""}`}
                    key={item.notification_id}
                  >
                    <div className="diagnostic-title">
                      <strong>{item.title}</strong>
                      <span>{STATE_LABEL[item.state]}</span>
                    </div>
                    <p>{item.summary}</p>
                    <p className="diagnostic-profile">
                      {EVENT_TYPE_LABEL[item.event_type] ?? item.event_type} · {formatDate(item.occurred_at)}
                    </p>
                    <div className="deferred-actions">
                      {item.state === "unread" ? (
                        <form action={markNotificationRead}>
                          <input type="hidden" name="notification_id" value={item.notification_id} />
                          <input type="hidden" name="back" value={backHref} />
                          <button type="submit">Marcar leído</button>
                        </form>
                      ) : null}
                      {item.state !== "archived" ? (
                        <form action={archiveNotification}>
                          <input type="hidden" name="notification_id" value={item.notification_id} />
                          <input type="hidden" name="back" value={backHref} />
                          <button type="submit">Archivar</button>
                        </form>
                      ) : null}
                      {item.target_path ? <Link href={item.target_path}>Abrir destino</Link> : null}
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="diagnostic-notice">No hay notificaciones con los filtros seleccionados.</div>
            )}

            <nav className="pagination" aria-label="Paginación de notificaciones">
              <Link href={restartHref}>↺ Reiniciar</Link>
              <span />
              {nextHref ? <Link href={nextHref}>Más antiguas →</Link> : <span />}
            </nav>
          </section>
        </>
      )}
    </div>
  );
}
