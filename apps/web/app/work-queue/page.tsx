import Link from "next/link";

import { getWorkQueue } from "@/lib/api";

type QueueParams = {
  q?: string;
  severity?: string;
  finding_code?: string;
  review?: string;
  draft?: string;
  suggestions?: string;
  page?: string;
};

const PRIORITY_LABELS = {
  critical: "Error pendiente",
  suggestion: "Sugerencia pendiente",
  high: "Revisión pendiente",
  rebase: "Borrador obsoleto",
  draft: "Borrador abierto",
  approved: "Borrador aprobado",
  rejected: "Borrador rechazado",
  reviewed: "Revisado",
} as const;

export default async function WorkQueuePage({
  searchParams,
}: {
  searchParams: Promise<QueueParams>;
}) {
  const params = await searchParams;
  const page = Math.max(0, Number.parseInt(params.page ?? "0", 10) || 0);
  let queue: Awaited<ReturnType<typeof getWorkQueue>> | null = null;
  try {
    queue = await getWorkQueue({ ...params, page: String(page) });
  } catch {
    // Keep a clear degraded state when the operational index is unavailable.
  }

  if (queue === null) {
    return (
      <div className="shell">
        <Link href="/" className="back-link">← Volver a registros</Link>
        <section className="notice" role="status">
          <strong>La cola de trabajo no está disponible.</strong>
          <span>Verifica PostgreSQL y la API local antes de volver a cargar.</span>
        </section>
      </div>
    );
  }

  const freshness = queue.latest_sync_finished_at
    ? new Intl.DateTimeFormat("es-MX", { dateStyle: "medium", timeStyle: "short" }).format(
        new Date(queue.latest_sync_finished_at),
      )
    : "Sin sincronización registrada";
  const summaryCards = [
    ["Atención", queue.summary.attention_items, "Hallazgo vigente o borrador"],
    ["Pendientes", queue.summary.pending_review_items, "Al menos un hallazgo sin decisión"],
    ["Sugerencias", queue.summary.pending_suggestions, "Propuestas pendientes de decisión"],
    ["Revisados", queue.summary.reviewed_items, "Todos los hallazgos con decisión"],
    ["Abiertos", queue.summary.open_draft_items, "Sin decisión sobre la última revisión"],
    ["Aprobados", queue.summary.approved_draft_items, "Última revisión aprobada"],
    ["Rechazados", queue.summary.rejected_draft_items, "Última revisión rechazada"],
    ["Sustituidos", queue.summary.superseded_draft_items, "Revisión nueva tras una decisión"],
    ["Obsoletos", queue.summary.stale_draft_items, "Fuente modificada desde la apertura"],
  ] as const;
  const pageHref = (nextPage: number) => {
    const next = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value && key !== "page") next.set(key, value);
    }
    next.set("page", String(nextPage));
    return `/work-queue?${next.toString()}`;
  };
  const hasNext = (page + 1) * queue.size < queue.total;

  return (
    <div className="shell queue-dashboard">
      <Link href="/" className="back-link">← Volver a registros</Link>
      <header className="profile-hero">
        <p className="eyebrow">Operación catalográfica · colección piloto</p>
        <h1>Cola de trabajo</h1>
        <p>
          Prioriza revisión y borradores usando únicamente evidencia local vigente. Esta vista no
          agrega reglas ni modifica DSpace.
        </p>
        <dl className="profile-source">
          <div><dt>Fuente</dt><dd>{queue.source}</dd></div>
          <div><dt>Grano</dt><dd>{queue.grain}</dd></div>
          <div><dt>Frescura</dt><dd>{freshness}</dd></div>
        </dl>
      </header>

      <section aria-labelledby="queue-summary-heading">
        <div className="section-heading">
          <h2 id="queue-summary-heading">Estado de la colección</h2>
          <span>Denominador: {queue.summary.active_items} ítems activos</span>
        </div>
        <div className="queue-summary">
          {summaryCards.map(([label, metric, definition]) => (
            <article className="queue-metric" key={label}>
              <p>{label}</p>
              <strong>{metric}</strong>
              <small>{definition}</small>
            </article>
          ))}
        </div>
      </section>

      <section aria-labelledby="queue-list-heading">
        <div className="section-heading">
          <h2 id="queue-list-heading">Trabajo priorizado</h2>
          <span>{queue.total} ítems con los filtros actuales</span>
        </div>
        <form className="queue-filters" action="/work-queue">
          <label>
            Buscar
            <input name="q" defaultValue={params.q} placeholder="Título o handle" />
          </label>
          <label>
            Severidad
            <select name="severity" defaultValue={params.severity ?? ""}>
              <option value="">Todas</option>
              <option value="error">Error</option>
              <option value="warning">Advertencia</option>
            </select>
          </label>
          <label>
            Regla
            <select name="finding_code" defaultValue={params.finding_code ?? ""}>
              <option value="">Todas</option>
              {queue.available_finding_codes.map((code) => (
                <option value={code} key={code}>{code}</option>
              ))}
            </select>
          </label>
          <label>
            Revisión
            <select name="review" defaultValue={params.review ?? ""}>
              <option value="">Cualquier estado</option>
              <option value="pending">Pendiente</option>
              <option value="reviewed">Revisado</option>
            </select>
          </label>
          <label>
            Sugerencias
            <select name="suggestions" defaultValue={params.suggestions ?? ""}>
              <option value="">Cualquier estado</option>
              <option value="pending">Pendientes</option>
              <option value="none">Sin pendientes</option>
            </select>
          </label>
          <label>
            Borrador
            <select name="draft" defaultValue={params.draft ?? ""}>
              <option value="">Cualquier estado</option>
              <option value="none">Sin borrador</option>
              <option value="open">Abierto</option>
              <option value="stale">Obsoleto</option>
            </select>
              <option value="approved">Aprobado</option>
              <option value="rejected">Rechazado</option>
              <option value="superseded">Sustituido</option>
          </label>
          <div className="queue-filter-actions">
            <button type="submit">Aplicar filtros</button>
            <Link href="/work-queue">Limpiar</Link>
          </div>
        </form>

        {queue.items.length ? (
          <div className="queue-list">
            {queue.items.map((item) => (
              <Link
                className="queue-item"
                href={item.finding_codes.includes("CAT-LING-003") ? "/items/" + item.uuid + "?prepare=deduplicate#draft-heading" : "/items/" + item.uuid}
                key={item.uuid}
              >
                <div className="queue-item-main">
                  <span className={`priority-badge ${item.priority}`}>
                    {PRIORITY_LABELS[item.priority]}
                  </span>
                  <h3>{item.name}</h3>
                  <p>{item.handle ?? item.uuid}</p>
                </div>
                  {item.finding_codes.includes("CAT-LING-003") ? (
                    <p>Preparar deduplicación en borrador local</p>
                  ) : null}
                <dl className="queue-item-stats">
                  <div><dt>Hallazgos</dt><dd>{item.finding_count}</dd></div>
                  <div><dt>Pendientes</dt><dd>{item.pending_finding_count}</dd></div>
                  <div><dt>Pospuestos</dt><dd>{item.deferred_finding_count}</dd></div>
                  <div><dt>Sugerencias</dt><dd>{item.pending_suggestion_count}</dd></div>
                  <div>
                    <dt>Borrador</dt>
                    <dd>
                      {item.latest_draft_version && item.draft_state
                        ? `v${item.latest_draft_version} · ${item.draft_state}`
                        : "No"}
                    </dd>
                  </div>
                </dl>
                <p className="queue-codes">{item.finding_codes.join(" · ") || "Sin reglas"}</p>
              </Link>
            ))}
          </div>
        ) : (
          <div className="diagnostic-notice">
            No hay ítems que coincidan con los filtros seleccionados.
          </div>
        )}

        <nav className="pagination" aria-label="Paginación de la cola">
          {page > 0 ? <Link href={pageHref(page - 1)}>← Anterior</Link> : <span />}
          <span>Página {page + 1}</span>
          {hasNext ? <Link href={pageHref(page + 1)}>Siguiente →</Link> : <span />}
        </nav>
      </section>

      <aside className="evidence-caveat">
        <strong>Límite de interpretación</strong>
        <p>
          La prioridad organiza trabajo operativo; no representa confianza del agente ni
          autorización para cambiar metadatos.
        </p>
      </aside>
    </div>
  );
}
