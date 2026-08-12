import Link from "next/link";

import { getCatalogProfile } from "@/lib/api";

const FIELD_LABELS: Record<string, string> = {
  "dc.subject.linguisticFamily": "Familia",
  "dc.subject.linguisticBranch": "Rama",
  "dc.subject.linguiscgroup": "Agrupación",
  "dc.description.registeredLanguage": "Lengua registrada",
};

const percent = (value: number) => `${(value * 100).toFixed(1)}%`;

export default async function CatalogProfilePage() {
  let profile: Awaited<ReturnType<typeof getCatalogProfile>> | null = null;
  try {
    profile = await getCatalogProfile();
  } catch {
    // The page keeps an explicit degraded state when the local index is unavailable.
  }

  if (profile === null) {
    return (
      <div className="shell">
        <Link href="/" className="back-link">← Volver a registros</Link>
        <section className="notice" role="status">
          <strong>La evidencia del perfil no está disponible.</strong>
          <span>Verifica PostgreSQL y la API local antes de volver a cargar.</span>
        </section>
      </div>
    );
  }

  const freshness = profile.latest_sync_finished_at
    ? new Intl.DateTimeFormat("es-MX", { dateStyle: "medium", timeStyle: "short" }).format(
        new Date(profile.latest_sync_finished_at),
      )
    : "Sin sincronización registrada";

  return (
    <div className="shell profile-dashboard">
      <Link href="/" className="back-link">← Volver a registros</Link>
      <header className="profile-hero">
        <p className="eyebrow">Evidencia de la colección piloto</p>
        <h1>Perfil catalográfico</h1>
        <p>
          Cobertura y relaciones observadas en {profile.collection_name}. Esta vista ayuda a
          decidir reglas; no convierte los datos históricos en vocabulario autorizado.
        </p>
        <dl className="profile-source">
          <div><dt>Fuente</dt><dd>{profile.source}</dd></div>
          <div><dt>Grano</dt><dd>{profile.grain}</dd></div>
          <div><dt>Frescura</dt><dd>{freshness}</dd></div>
        </dl>
      </header>

      <section aria-labelledby="coverage-heading">
        <div className="section-heading">
          <h2 id="coverage-heading">Cobertura de campos</h2>
          <span>Denominador: {profile.active_items} ítems activos</span>
        </div>
        <div className="coverage-grid">
          {profile.fields.map((field) => (
            <article className="coverage-card" key={field.field}>
              <p className="metric-label">{field.label}</p>
              <strong className="metric-value">{percent(field.coverage_rate)}</strong>
              <progress value={field.coverage_rate} max={1} aria-label={`Cobertura de ${field.label}`} />
              <p>{field.item_count} presentes · {field.missing_item_count} ausentes</p>
              <small>{field.value_count} valores · {field.distinct_value_count} distintos</small>
            </article>
          ))}
        </div>
      </section>

      <section aria-labelledby="values-heading">
        <div className="section-heading">
          <h2 id="values-heading">Valores más observados</h2>
          <span>Porcentaje sobre {profile.active_items} ítems activos</span>
        </div>
        <div className="value-panels">
          {profile.fields.map((field) => (
            <article className="value-panel" key={field.field}>
              <h3>{field.label}</h3>
              <p className="field-key">{field.field}</p>
              <ol className="ranked-values">
                {field.top_values.slice(0, 6).map((entry) => (
                  <li key={entry.value}>
                    <div><span>{entry.value}</span><strong>{entry.item_count}</strong></div>
                    <progress value={entry.item_rate} max={1} aria-label={`${entry.value}: ${percent(entry.item_rate)}`} />
                  </li>
                ))}
              </ol>
            </article>
          ))}
        </div>
      </section>

      <section aria-labelledby="patterns-heading">
        <div className="section-heading">
          <h2 id="patterns-heading">Patrones de completitud</h2>
          <span>Combinaciones de presencia, no validación semántica</span>
        </div>
        <div className="pattern-list">
          {profile.completeness_patterns.map((pattern) => (
            <article className="pattern-row" key={pattern.fields_present.join("|") || "none"}>
              <div>
                <strong>
                  {pattern.fields_present.length
                    ? pattern.fields_present.map((field) => FIELD_LABELS[field] ?? field).join(" + ")
                    : "Sin campos lingüísticos"}
                </strong>
                <span>{percent(pattern.rate)}</span>
              </div>
              <progress value={pattern.rate} max={1} />
              <small>{pattern.item_count} ítems</small>
            </article>
          ))}
        </div>
      </section>

      <section aria-labelledby="relationships-heading">
        <div className="section-heading">
          <h2 id="relationships-heading">Relaciones observadas</h2>
          <span>Hasta 25 pares por relación</span>
        </div>
        <div className="relationship-grid">
          {profile.relationships.map((relationship) => (
            <article className="relationship-panel" key={`${relationship.from_field}-${relationship.to_field}`}>
              <h3>{FIELD_LABELS[relationship.from_field]} → {FIELD_LABELS[relationship.to_field]}</h3>
              <p>{relationship.observed_pairs} pares distintos observados</p>
              <div className="relationship-table" role="table" aria-label={`Relación ${relationship.from_field} a ${relationship.to_field}`}>
                {relationship.pairs.slice(0, 10).map((pair) => (
                  <div role="row" key={`${pair.from_value}-${pair.to_value}`}>
                    <span role="cell">{pair.from_value}</span>
                    <span role="cell" aria-hidden="true">→</span>
                    <span role="cell">{pair.to_value}</span>
                    <strong role="cell">{pair.item_count}</strong>
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>

      <aside className="evidence-caveat">
        <strong>Límite de interpretación</strong>
        <p>{profile.interpretation}</p>
      </aside>
    </div>
  );
}
