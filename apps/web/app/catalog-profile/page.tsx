import Link from "next/link";

import { getCatalogProfile } from "@/lib/api";

const FIELD_LABELS: Record<string, string> = {
  "dc.subject.linguisticFamily": "Familia",
  "dc.subject.linguisticBranch": "Rama",
  "dc.subject.linguiscgroup": "Agrupación",
  "dc.description.registeredLanguage": "Lengua registrada",
};

const percent = (value: number) => `${(value * 100).toFixed(1)}%`;

function ProgressBar({ value, label }: { value: number; label: string }) {
  const width = Math.min(100, Math.max(0, value * 100));
  return (
    <div
      role="progressbar"
      aria-valuenow={Math.round(width)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label}
      className="h-2 w-full overflow-hidden rounded-full bg-paper"
    >
      <div className="h-full rounded-full bg-brand-500" style={{ width: `${width}%` }} />
    </div>
  );
}

export default async function CatalogProfilePage() {
  let profile: Awaited<ReturnType<typeof getCatalogProfile>> | null = null;
  try {
    profile = await getCatalogProfile();
  } catch {
    // The page keeps an explicit degraded state when the local index is unavailable.
  }

  if (profile === null) {
    return (
      <div className="min-h-screen bg-paper">
        <div className="mx-auto max-w-6xl px-6 py-10">
          <Link href="/" className="text-sm font-semibold text-brand-600 hover:text-brand-700">
            ← Volver a registros
          </Link>
          <div className="mt-6 rounded-xl bg-brand-50 p-5" role="status">
            <p className="font-semibold text-ink">La evidencia del perfil no está disponible.</p>
            <p className="mt-1 text-sm text-muted">
              Verifica PostgreSQL y la API local antes de volver a cargar.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const freshness = profile.latest_sync_finished_at
    ? new Intl.DateTimeFormat("es-MX", { dateStyle: "medium", timeStyle: "short" }).format(
        new Date(profile.latest_sync_finished_at),
      )
    : "Sin sincronización registrada";

  return (
    <div className="min-h-screen bg-paper">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <Link href="/" className="text-sm font-semibold text-brand-600 hover:text-brand-700">
          ← Volver a registros
        </Link>

        <header className="mt-6 max-w-3xl">
          <p className="text-xs font-bold uppercase tracking-wider text-brand-600">
            Evidencia de la colección piloto
          </p>
          <h1 className="mt-2 text-3xl font-bold text-ink sm:text-4xl">Perfil catalográfico</h1>
          <p className="mt-3 text-muted">
            Cobertura y relaciones observadas en {profile.collection_name}. Esta vista ayuda a
            decidir reglas; no convierte los datos históricos en vocabulario autorizado.
          </p>
          <dl className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
            {[
              ["Fuente", profile.source],
              ["Grano", profile.grain],
              ["Frescura", freshness],
            ].map(([term, value]) => (
              <div key={term} className="rounded-lg border border-line bg-surface px-4 py-3">
                <dt className="text-xs font-semibold uppercase text-muted">{term}</dt>
                <dd className="mt-1 text-sm text-ink">{value}</dd>
              </div>
            ))}
          </dl>
        </header>

        <section className="mt-10" aria-labelledby="coverage-heading">
          <div className="flex items-baseline justify-between">
            <h2 id="coverage-heading" className="text-lg font-semibold text-ink">
              Cobertura de campos
            </h2>
            <span className="text-sm text-muted">
              Denominador: {profile.active_items} ítems activos
            </span>
          </div>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {profile.fields.map((field) => (
              <article
                key={field.field}
                className="rounded-xl border border-line bg-surface p-5 shadow-sm"
              >
                <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                  {field.label}
                </p>
                <strong className="mt-2 block text-3xl font-bold text-ink">
                  {percent(field.coverage_rate)}
                </strong>
                <div className="mt-3">
                  <ProgressBar value={field.coverage_rate} label={`Cobertura de ${field.label}`} />
                </div>
                <p className="mt-3 text-sm text-ink">
                  {field.item_count} presentes · {field.missing_item_count} ausentes
                </p>
                <small className="mt-1 block text-xs text-muted">
                  {field.value_count} valores · {field.distinct_value_count} distintos
                </small>
              </article>
            ))}
          </div>
        </section>

        <section className="mt-10" aria-labelledby="values-heading">
          <div className="flex items-baseline justify-between">
            <h2 id="values-heading" className="text-lg font-semibold text-ink">
              Valores más observados
            </h2>
            <span className="text-sm text-muted">
              Porcentaje sobre {profile.active_items} ítems activos
            </span>
          </div>
          <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
            {profile.fields.map((field) => (
              <article
                key={field.field}
                className="rounded-xl border border-line bg-surface p-5 shadow-sm"
              >
                <h3 className="font-semibold text-ink">{field.label}</h3>
                <p className="mt-0.5 text-xs text-muted">{field.field}</p>
                <ol className="mt-4 flex flex-col gap-3">
                  {field.top_values.slice(0, 6).map((entry) => (
                    <li key={entry.value}>
                      <div className="flex items-baseline justify-between gap-3 text-sm">
                        <span className="truncate text-ink">{entry.value}</span>
                        <strong className="shrink-0 text-ink">{entry.item_count}</strong>
                      </div>
                      <div className="mt-1.5">
                        <ProgressBar
                          value={entry.item_rate}
                          label={`${entry.value}: ${percent(entry.item_rate)}`}
                        />
                      </div>
                    </li>
                  ))}
                </ol>
              </article>
            ))}
          </div>
        </section>

        <section className="mt-10" aria-labelledby="patterns-heading">
          <div className="flex items-baseline justify-between">
            <h2 id="patterns-heading" className="text-lg font-semibold text-ink">
              Patrones de completitud
            </h2>
            <span className="text-sm text-muted">
              Combinaciones de presencia, no validación semántica
            </span>
          </div>
          <div className="mt-4 flex flex-col gap-3">
            {profile.completeness_patterns.map((pattern) => (
              <article
                key={pattern.fields_present.join("|") || "none"}
                className="rounded-lg border border-line bg-surface p-4"
              >
                <div className="flex items-baseline justify-between gap-3">
                  <strong className="text-sm text-ink">
                    {pattern.fields_present.length
                      ? pattern.fields_present.map((field) => FIELD_LABELS[field] ?? field).join(" + ")
                      : "Sin campos lingüísticos"}
                  </strong>
                  <span className="shrink-0 text-sm text-muted">{percent(pattern.rate)}</span>
                </div>
                <div className="mt-2">
                  <ProgressBar value={pattern.rate} label={`${pattern.item_count} ítems`} />
                </div>
                <small className="mt-1.5 block text-xs text-muted">{pattern.item_count} ítems</small>
              </article>
            ))}
          </div>
        </section>

        <section className="mt-10" aria-labelledby="relationships-heading">
          <div className="flex items-baseline justify-between">
            <h2 id="relationships-heading" className="text-lg font-semibold text-ink">
              Relaciones observadas
            </h2>
            <span className="text-sm text-muted">Hasta 25 pares por relación</span>
          </div>
          <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
            {profile.relationships.map((relationship) => (
              <article
                key={`${relationship.from_field}-${relationship.to_field}`}
                className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm"
              >
                <div className="p-5 pb-3">
                  <h3 className="font-semibold text-ink">
                    {FIELD_LABELS[relationship.from_field]} → {FIELD_LABELS[relationship.to_field]}
                  </h3>
                  <p className="mt-0.5 text-sm text-muted">
                    {relationship.observed_pairs} pares distintos observados
                  </p>
                </div>
                <div className="overflow-x-auto">
                  <table
                    className="w-full min-w-[420px] text-left text-sm"
                    aria-label={`Relación ${relationship.from_field} a ${relationship.to_field}`}
                  >
                    <thead>
                      <tr className="border-y border-line bg-paper text-xs font-semibold uppercase tracking-wide text-muted">
                        <th className="px-5 py-2">{FIELD_LABELS[relationship.from_field]}</th>
                        <th className="px-2 py-2" aria-hidden="true" />
                        <th className="px-2 py-2">{FIELD_LABELS[relationship.to_field]}</th>
                        <th className="px-5 py-2 text-right">Ítems</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-line">
                      {relationship.pairs.slice(0, 10).map((pair) => (
                        <tr key={`${pair.from_value}-${pair.to_value}`}>
                          <td className="px-5 py-2 text-ink">{pair.from_value}</td>
                          <td className="px-2 py-2 text-muted" aria-hidden="true">
                            →
                          </td>
                          <td className="px-2 py-2 text-ink">{pair.to_value}</td>
                          <td className="px-5 py-2 text-right font-semibold text-ink">
                            {pair.item_count}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </article>
            ))}
          </div>
        </section>

        <aside className="mt-10 rounded-xl bg-amber-50 p-5 text-sm text-amber-900 dark:bg-amber-500/10 dark:text-amber-200">
          <strong className="block font-semibold">Límite de interpretación</strong>
          <p className="mt-1">{profile.interpretation}</p>
        </aside>
      </div>
    </div>
  );
}
