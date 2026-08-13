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

const PRIORITY_BADGE_STYLES: Record<keyof typeof PRIORITY_LABELS, string> = {
  critical: "bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300",
  high: "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300",
  suggestion: "bg-brand-100 text-brand-700",
  rebase: "bg-violet-100 text-violet-700 dark:bg-violet-500/15 dark:text-violet-300",
  draft: "bg-sky-100 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300",
  approved: "bg-brand-100 text-brand-700",
  rejected: "bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300",
  reviewed: "bg-slate-100 text-slate-600 dark:bg-slate-500/15 dark:text-slate-300",
};

function PriorityBadge({ priority }: { priority: keyof typeof PRIORITY_LABELS }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${PRIORITY_BADGE_STYLES[priority]}`}
    >
      {PRIORITY_LABELS[priority]}
    </span>
  );
}

const inputClass =
  "rounded-lg border border-line px-3 py-2 text-sm font-normal text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand-500";
const labelClass = "flex flex-col gap-1 text-xs font-semibold text-muted";

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
      <div className="min-h-screen bg-paper">
        <div className="mx-auto max-w-6xl px-6 py-10">
          <Link href="/" className="text-sm font-semibold text-brand-600 hover:text-brand-700">
            ← Volver a registros
          </Link>
          <div className="mt-6 rounded-xl bg-brand-50 p-5" role="status">
            <p className="font-semibold text-ink">La cola de trabajo no está disponible.</p>
            <p className="mt-1 text-sm text-muted">
              Verifica PostgreSQL y la API local antes de volver a cargar.
            </p>
          </div>
        </div>
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
    <div className="min-h-screen bg-paper">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <Link href="/" className="text-sm font-semibold text-brand-600 hover:text-brand-700">
          ← Volver a registros
        </Link>

        <header className="mt-6 max-w-3xl">
          <p className="text-xs font-bold uppercase tracking-wider text-brand-600">
            Operación catalográfica · colección piloto
          </p>
          <h1 className="mt-2 text-3xl font-bold text-ink sm:text-4xl">Cola de trabajo</h1>
          <p className="mt-3 text-muted">
            Prioriza revisión y borradores usando únicamente evidencia local vigente. Esta vista no
            agrega reglas ni modifica DSpace.
          </p>
          <dl className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
            {[
              ["Fuente", queue.source],
              ["Grano", queue.grain],
              ["Frescura", freshness],
            ].map(([term, value]) => (
              <div key={term} className="rounded-lg border border-line bg-surface px-4 py-3">
                <dt className="text-xs font-semibold uppercase text-muted">{term}</dt>
                <dd className="mt-1 text-sm text-ink">{value}</dd>
              </div>
            ))}
          </dl>
        </header>

        <section className="mt-10" aria-labelledby="queue-summary-heading">
          <div className="flex items-baseline justify-between">
            <h2 id="queue-summary-heading" className="text-lg font-semibold text-ink">
              Estado de la colección
            </h2>
            <span className="text-sm text-muted">
              Denominador: {queue.summary.active_items} ítems activos
            </span>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
            {summaryCards.map(([label, metric, definition]) => (
              <article key={label} className="rounded-xl border border-line bg-surface p-4 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</p>
                <strong className="mt-2 block text-2xl font-bold text-ink">{metric}</strong>
                <small className="mt-1 block text-xs text-muted">{definition}</small>
              </article>
            ))}
          </div>
        </section>

        <section className="mt-10" aria-labelledby="queue-list-heading">
          <div className="flex items-baseline justify-between">
            <h2 id="queue-list-heading" className="text-lg font-semibold text-ink">
              Trabajo priorizado
            </h2>
            <span className="text-sm text-muted">{queue.total} ítems con los filtros actuales</span>
          </div>

          <form
            action="/work-queue"
            className="mt-4 grid grid-cols-2 items-end gap-3 rounded-xl border border-line bg-surface p-4 sm:grid-cols-3 lg:grid-cols-6"
          >
            <label className={labelClass}>
              Buscar
              <input name="q" defaultValue={params.q} placeholder="Título o handle" className={inputClass} />
            </label>
            <label className={labelClass}>
              Severidad
              <select name="severity" defaultValue={params.severity ?? ""} className={inputClass}>
                <option value="">Todas</option>
                <option value="error">Error</option>
                <option value="warning">Advertencia</option>
              </select>
            </label>
            <label className={labelClass}>
              Regla
              <select name="finding_code" defaultValue={params.finding_code ?? ""} className={inputClass}>
                <option value="">Todas</option>
                {queue.available_finding_codes.map((code) => (
                  <option value={code} key={code}>
                    {code}
                  </option>
                ))}
              </select>
            </label>
            <label className={labelClass}>
              Revisión
              <select name="review" defaultValue={params.review ?? ""} className={inputClass}>
                <option value="">Cualquier estado</option>
                <option value="pending">Pendiente</option>
                <option value="reviewed">Revisado</option>
              </select>
            </label>
            <label className={labelClass}>
              Sugerencias
              <select name="suggestions" defaultValue={params.suggestions ?? ""} className={inputClass}>
                <option value="">Cualquier estado</option>
                <option value="pending">Pendientes</option>
                <option value="none">Sin pendientes</option>
              </select>
            </label>
            <label className={labelClass}>
              Borrador
              <select name="draft" defaultValue={params.draft ?? ""} className={inputClass}>
                <option value="">Cualquier estado</option>
                <option value="none">Sin borrador</option>
                <option value="open">Abierto</option>
                <option value="stale">Obsoleto</option>
                <option value="approved">Aprobado</option>
                <option value="rejected">Rechazado</option>
                <option value="superseded">Sustituido</option>
              </select>
            </label>
            <div className="col-span-2 flex items-center gap-4 sm:col-span-3 lg:col-span-6">
              <button
                type="submit"
                className="rounded-lg bg-brand-500 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-600"
              >
                Aplicar filtros
              </button>
              <Link href="/work-queue" className="text-sm font-semibold text-brand-600 hover:text-brand-700">
                Limpiar
              </Link>
            </div>
          </form>

          {queue.items.length ? (
            <div className="mt-4 overflow-hidden rounded-xl border border-line bg-surface">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-line bg-paper text-xs font-semibold uppercase tracking-wide text-muted">
                      <th className="px-4 py-3">Ítem</th>
                      <th className="px-4 py-3">Prioridad</th>
                      <th className="px-4 py-3 text-center">Hallazgos</th>
                      <th className="px-4 py-3 text-center">Pendientes</th>
                      <th className="px-4 py-3 text-center">Pospuestos</th>
                      <th className="px-4 py-3 text-center">Sugerencias</th>
                      <th className="px-4 py-3">Borrador</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {queue.items.map((item) => (
                      <tr key={item.uuid} className="transition-colors hover:bg-paper">
                        <td className="px-4 py-3 align-top">
                          <Link
                            href={
                              item.finding_codes.includes("CAT-LING-003")
                                ? `/items/${item.uuid}?prepare=deduplicate#draft-heading`
                                : `/items/${item.uuid}`
                            }
                            className="font-semibold text-ink hover:text-brand-600"
                          >
                            {item.name}
                          </Link>
                          <p className="mt-0.5 text-xs text-muted">{item.handle ?? item.uuid}</p>
                          {item.finding_codes.includes("CAT-LING-003") ? (
                            <p className="mt-0.5 text-xs font-medium text-brand-600">
                              Preparar deduplicación en borrador local
                            </p>
                          ) : null}
                          {item.finding_codes.length ? (
                            <p className="mt-1 text-xs text-muted">{item.finding_codes.join(" · ")}</p>
                          ) : null}
                        </td>
                        <td className="px-4 py-3 align-top">
                          <PriorityBadge priority={item.priority} />
                        </td>
                        <td className="px-4 py-3 text-center align-top text-ink">
                          {item.finding_count}
                        </td>
                        <td className="px-4 py-3 text-center align-top text-ink">
                          {item.pending_finding_count}
                        </td>
                        <td className="px-4 py-3 text-center align-top text-ink">
                          {item.deferred_finding_count}
                        </td>
                        <td className="px-4 py-3 text-center align-top text-ink">
                          {item.pending_suggestion_count}
                        </td>
                        <td className="px-4 py-3 align-top text-ink">
                          {item.latest_draft_version && item.draft_state
                            ? `v${item.latest_draft_version} · ${item.draft_state}`
                            : "No"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="mt-4 rounded-xl bg-brand-50 p-5 text-sm text-ink">
              No hay ítems que coincidan con los filtros seleccionados.
            </div>
          )}

          <nav
            className="mt-4 flex items-center justify-between text-sm font-semibold"
            aria-label="Paginación de la cola"
          >
            {page > 0 ? (
              <Link href={pageHref(page - 1)} className="text-brand-600 hover:text-brand-700">
                ← Anterior
              </Link>
            ) : (
              <span />
            )}
            <span className="text-muted">Página {page + 1}</span>
            {hasNext ? (
              <Link href={pageHref(page + 1)} className="text-brand-600 hover:text-brand-700">
                Siguiente →
              </Link>
            ) : (
              <span />
            )}
          </nav>
        </section>

        <aside className="mt-10 rounded-xl bg-amber-50 p-5 text-sm text-amber-900 dark:bg-amber-500/10 dark:text-amber-200">
          <strong className="block font-semibold">Límite de interpretación</strong>
          <p className="mt-1">
            La prioridad organiza trabajo operativo; no representa confianza del agente ni
            autorización para cambiar metadatos.
          </p>
        </aside>
      </div>
    </div>
  );
}
