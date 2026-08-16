import Link from "next/link";
import { notFound } from "next/navigation";

import { getItem, getItemMetadataValidation, getItemSuggestions, getSimilarItems, getSuggestionHistory } from "@/lib/api";
import { getCatalogingContract } from "@/lib/cataloging-contract";

import { generateSuggestions, recordReviewDecision } from "./actions";
import { DraftEditor } from "./draft-editor";
import { SuggestionDecisionForm } from "./suggestion-decision-form";

const REVIEW_LABELS = {
  confirmed: "Confirmado",
  dismissed: "Descartado",
  deferred: "Pospuesto",
} as const;
const VALIDATION_LABELS = {
  no_vocabulary: "Sin vocabulario",
  no_values: "Sin valores",
  valid: "Válido",
  invalid: "Fuera del vocabulario",
} as const;
const SUGGESTION_DECISION_LABELS = {
  accepted: "Aceptada",
  corrected: "Corregida",
  rejected: "Rechazada",
  deferred: "Pospuesta",
} as const;


const REVIEW_MESSAGES: Record<string, string> = {
  saved: "La decisión local quedó registrada en el historial.",
  error: "No fue posible registrar la decisión. Revisa los datos e inténtalo de nuevo.",
  unavailable: "La revisión local está deshabilitada porque falta la configuración segura.",
};

const DRAFT_MESSAGES: Record<string, string> = {
  saved: "El borrador local quedó guardado como una nueva revisión.",
  conflict: "El registro fuente o la versión del borrador cambió. Recarga antes de continuar.",
  error: "No fue posible guardar el borrador. Revisa los valores e inténtalo de nuevo.",
  unavailable: "Los borradores están deshabilitados porque falta la configuración segura.",
  "contract-unavailable": "No se pudo cargar el contrato maestro. No se modificó el borrador.",
};
const SUGGESTION_MESSAGES: Record<string, string> = {
  saved: "Las sugerencias vigentes quedaron registradas como evidencia auditable.",
  error: "No fue posible generar sugerencias persistidas.",
  unavailable: "La generación está deshabilitada porque falta la configuración segura.",
};
const SUGGESTION_DECISION_MESSAGES: Record<string, string> = {
  saved: "La decisión sobre la sugerencia quedó registrada localmente.",
  conflict: "La sugerencia o el registro fuente cambió. Recarga antes de continuar.",
  error: "No fue posible registrar la decisión sobre la sugerencia.",
  unavailable: "Las decisiones están deshabilitadas porque falta la configuración segura.",
};

export default async function ItemPage({
  params,
  searchParams,
}: {
  params: Promise<{ uuid: string }>;
  searchParams: Promise<{ review?: string; draft?: string; suggestions?: string; suggestionDecision?: string; prepare?: string }>;
}) {
  const { uuid } = await params;
  const { review, draft: draftOutcome, suggestions: suggestionsOutcome, suggestionDecision, prepare } = await searchParams;
  const [itemResult, similarResult, validationResult, suggestionResult, historyResult, contractResult] =
    await Promise.allSettled([
      getItem(uuid),
      getSimilarItems(uuid),
      getItemMetadataValidation(uuid),
      getItemSuggestions(uuid),
      getSuggestionHistory(uuid),
      getCatalogingContract(),
    ]);
  if (itemResult.status === "rejected") {
    notFound();
  }
  const item = itemResult.value;
  const similar = similarResult.status === "fulfilled" ? similarResult.value : null;
  const vocabularyValidation =
    validationResult.status === "fulfilled" ? validationResult.value : null;
  const suggestions = suggestionResult.status === "fulfilled" ? suggestionResult.value : null;
  const suggestionHistory = historyResult.status === "fulfilled" ? historyResult.value : null;
  const linguisticFields =
    contractResult.status === "fulfilled"
      ? contractResult.value.fields.filter((field) => field.runtime_draftable)
      : [];
  const latestReviews = new Map(
    item.review_decisions.map((decision) => [decision.finding_fingerprint, decision]),
  );
  const localDraft = item.drafts[0] ?? null;
  const latestDraftRevision = localDraft?.revisions.at(-1) ?? null;
  const draftValues = Object.fromEntries(
    linguisticFields.map((field) => [
      field.metadata_field,
      latestDraftRevision?.metadata_patch[field.metadata_field] ?? item.metadata[field.metadata_field] ?? [],
    ]),
  );
  const duplicateFields = item.diagnostics.findings
    .filter((finding) => finding.code === "CAT-LING-003")
    .flatMap((finding) => finding.affected_fields)
    .filter((field, index, fields) => fields.indexOf(field) === index);
  const preparedDuplicateFields = prepare === "deduplicate" ? duplicateFields : [];


  return (
    <article className="shell detail">
      <Link href="/" className="back-link">← Volver a registros</Link>
      {review && REVIEW_MESSAGES[review] ? (
        <div
          className={review === "saved" ? "review-status" : "review-status error"}
          role="status"
        >
          {REVIEW_MESSAGES[review]}
        </div>
      ) : null}
      {draftOutcome && DRAFT_MESSAGES[draftOutcome] ? (
        <div
          className={draftOutcome === "saved" ? "review-status" : "review-status error"}
          role="status"
        >
          {DRAFT_MESSAGES[draftOutcome]}
        </div>
      ) : null}
      {suggestionsOutcome && SUGGESTION_MESSAGES[suggestionsOutcome] ? (
        <div className={suggestionsOutcome === "saved" ? "review-status" : "review-status error"} role="status">
          {SUGGESTION_MESSAGES[suggestionsOutcome]}
        </div>
      ) : null}
      {suggestionDecision && SUGGESTION_DECISION_MESSAGES[suggestionDecision] ? (
        <div className={suggestionDecision === "saved" ? "review-status" : "review-status error"} role="status">
          {SUGGESTION_DECISION_MESSAGES[suggestionDecision]}
        </div>
      ) : null}
      <header className="detail-header">
        <p className="eyebrow">Ficha catalográfica sincronizada</p>
        <h1>{item.name}</h1>
        <dl className="identity-grid">
          <div><dt>Handle</dt><dd>{item.handle ?? "No disponible"}</dd></div>
          <div><dt>UUID</dt><dd>{item.uuid}</dd></div>
          <div><dt>Última modificación</dt><dd>{item.last_modified ?? "No disponible"}</dd></div>
        </dl>
      </header>

      <section aria-labelledby="diagnostics-heading">
        <div className="section-heading">
          <h2 id="diagnostics-heading">Diagnóstico catalográfico</h2>
          <span>{item.diagnostics.findings.length} hallazgos</span>
        </div>
        {item.diagnostics.status === "stale" ? (
          <div className="diagnostic-notice stale" role="status">
            El diagnóstico todavía no corresponde a la versión actual del registro o del perfil.
          </div>
        ) : null}
        {item.diagnostics.findings.length ? (
          <div className="diagnostic-list">
            {item.diagnostics.findings.map((finding) => (
              <article
                className={`diagnostic-card ${finding.severity}`}
                key={finding.finding_id}
              >
                <div className="diagnostic-title">
                  <strong>{finding.code}</strong>
                  <span>{finding.severity === "error" ? "Error" : "Advertencia"}</span>
                </div>
                <p>{finding.explanation}</p>
                <p className="diagnostic-fields">
                  Campos: {finding.affected_fields.join(", ")}
                </p>
                {latestReviews.get(finding.fingerprint) ? (
                  <p className="review-latest">
                    Última decisión:{" "}
                    <strong>
                      {REVIEW_LABELS[latestReviews.get(finding.fingerprint)!.decision]}
                    </strong>
                    {" · "}
                    {latestReviews.get(finding.fingerprint)!.reviewer}
                  </p>
                ) : null}
                {finding.code === "CAT-LING-003" ? (
                  <Link
                    href={"/items/" + item.uuid + "?prepare=deduplicate#draft-heading"}
                  >
                    Preparar corrección en borrador local
                  </Link>
                ) : null}
                <form action={recordReviewDecision} className="review-form">
                  <input type="hidden" name="item_uuid" value={item.uuid} />
                  <input type="hidden" name="finding_id" value={finding.finding_id} />
                  <label>
                    Decisión local
                    <select name="decision" defaultValue="confirmed" required>
                      <option value="confirmed">Confirmar hallazgo</option>
                      <option value="dismissed">Descartar hallazgo</option>
                      <option value="deferred">Posponer revisión</option>
                    </select>
                  </label>
                  <label>
                    Revisor
                    <input
                      name="reviewer"
                      minLength={2}
                      maxLength={120}
                      autoComplete="name"
                      required
                    />
                  </label>
                  <label className="review-note">
                    Nota y evidencia
                    <textarea name="note" minLength={1} maxLength={2000} required />
                  </label>
                  <button type="submit">Registrar decisión</button>
                  <small>Se guarda sólo localmente; no modifica DSpace.</small>
                </form>
              </article>
            ))}
          </div>
        ) : (
          <div className="diagnostic-notice">
            Sin hallazgos para las reglas activas. Esto no sustituye la revisión catalográfica.
          </div>
        )}
        {item.review_decisions.length ? (
          <details className="review-history">
            <summary>Historial de revisión ({item.review_decisions.length})</summary>
            <ol>
              {item.review_decisions.toReversed().map((decision) => (
                <li key={decision.decision_id}>
                  <div>
                    <strong>{REVIEW_LABELS[decision.decision]}</strong>
                    <span>{decision.finding_code}</span>
                  </div>
                  <p>{decision.note}</p>
                  <small>
                    {decision.reviewer} ·{" "}
                    {new Intl.DateTimeFormat("es-MX", {
                      dateStyle: "medium",
                      timeStyle: "short",
                    }).format(new Date(decision.created_at))}
                  </small>
                </li>
              ))}
            </ol>
          </details>
        ) : null}
        <p className="diagnostic-profile">
          Perfil: {item.diagnostics.profile_version ?? "pendiente de ejecución"}
        </p>
      </section>

      <section>
        <h2>Campos lingüísticos</h2>
        {contractResult.status === "rejected" ? (
          <div className="diagnostic-notice stale" role="status">
            No se pudo cargar el contrato maestro. Los campos lingüísticos no están disponibles
            temporalmente.
          </div>
        ) : (
          <div className="field-grid">
            {linguisticFields.map((field) => {
              const values = item.metadata[field.metadata_field] ?? [];
              return (
                <div
                  className={values.length ? "field-card" : "field-card missing"}
                  key={field.binding_id}
                >
                  <h3>{field.ui_label}</h3>
                  {values.length ? (
                    <ul>{values.map((value) => <li key={`${value.place}-${value.value}`}>{value.value}</li>)}</ul>
                  ) : <p>Ausente</p>}
                </div>
              );
            })}
          </div>
        )}
      </section>
      <section aria-labelledby="vocabulary-validation-heading">
        <div className="section-heading">
          <h2 id="vocabulary-validation-heading">Validación con vocabularios aprobados</h2>
          <span>
            {vocabularyValidation
              ? vocabularyValidation.status === "not_configured"
                ? "No configurada"
                : vocabularyValidation.status === "valid"
                  ? "Valores aprobados"
                  : "Requiere revisión"
              : "No disponible"}
          </span>
        </div>
        {vocabularyValidation === null ? (
          <div className="diagnostic-notice stale" role="status">
            La validación local no está disponible temporalmente.
          </div>
        ) : vocabularyValidation.status === "not_configured" ? (
          <div className="diagnostic-notice">
            Ningún campo tiene vocabulario aprobado.{" "}
            <Link href="/controlled-terms">Consulta o registra la procedencia institucional.</Link>
          </div>
        ) : (
          <div className="vocabulary-validation-grid">
            {vocabularyValidation.fields.map((field) => (
              <article
                className={`vocabulary-validation-card ${field.status}`}
                key={field.field}
              >
                <div className="diagnostic-title">
                  <strong>{field.field}</strong>
                  <span>{VALIDATION_LABELS[field.status]}</span>
                </div>
                {field.vocabulary ? (
                  <p className="validation-source">
                    {field.vocabulary.name} · {field.vocabulary.version_label} · aprobado por{" "}
                    {field.vocabulary.approved_by}
                  </p>
                ) : (
                  <p className="validation-source">Sin fuente aprobada para este campo.</p>
                )}
                {field.values.length ? (
                  <ul className="validation-values">
                    {field.values.map((entry) => (
                      <li className={entry.approved ? "approved" : "unapproved"} key={entry.value}>
                        <span>{entry.value}</span>
                        <strong>{entry.approved ? "Aprobado" : "No coincide literalmente"}</strong>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <small>El registro no contiene valores en este campo.</small>
                )}
              </article>
            ))}
          </div>
        )}
        <p className="diagnostic-profile">
          La comparación es literal y conserva la fuente de cada revisión; no propone reemplazos.
        </p>
      </section>

      <section aria-labelledby="draft-heading">
        <div className="section-heading">
          <h2 id="draft-heading">Borrador catalográfico local</h2>
          <span>
            {latestDraftRevision ? `Versión ${latestDraftRevision.version}` : "Sin borrador"}
          </span>
        </div>
        <p className="draft-intro">
          Prepare valores humanos para los {linguisticFields.length} campos lingüísticos del
          contrato maestro. Una línea representa un valor repetible; no se aplicará a DSpace.
        </p>
        {localDraft?.stale ? (
          <div className="diagnostic-notice stale" role="status">
            El ítem sincronizado cambió desde que se abrió este borrador. No se permiten nuevas
            revisiones hasta definir una operación explícita de rebase.
          </div>
        ) : null}
        <DraftEditor
          itemUuid={item.uuid}
          draftId={localDraft?.draft_id ?? null}
          expectedVersion={latestDraftRevision?.version ?? null}
          initialValues={Object.fromEntries(
            linguisticFields.map((field) => [
              field.metadata_field,
              draftValues[field.metadata_field].map((entry) => entry.value).join("\n"),
            ]),
          )}
          stale={localDraft?.stale ?? false}
          validation={vocabularyValidation}
          suggestions={suggestions}
          deduplicateFields={preparedDuplicateFields}
        />
        <form action={generateSuggestions} className="review-form">
          <input type="hidden" name="item_uuid" value={item.uuid} />
          <button type="submit">Generar y registrar sugerencias</button>
          <small>Congela la evidencia local vigente; no escribe en DSpace.</small>
        </form>
        <details className="draft-history">
          <summary>Historial de sugerencias ({suggestionHistory?.entries.length ?? 0})</summary>
          {suggestionHistory === null ? <p>No disponible temporalmente.</p> : suggestionHistory.entries.length ? <ol>
            {suggestionHistory.entries.toReversed().map((entry) => <li key={entry.suggestion_id}>
              <div><strong>{entry.field}: {entry.proposed_value}</strong><span>{entry.source_stale ? "Fuente obsoleta" : `${Math.round(entry.confidence * 100)}%`}</span></div>
              <p>{entry.explanation}</p>
              {entry.decisions.length ? <ul>{entry.decisions.map((decision) => <li key={decision.decision_id}><strong>{SUGGESTION_DECISION_LABELS[decision.decision]}</strong> · {decision.reviewer} · {decision.note}{decision.corrected_value ? ` · ${decision.corrected_value}` : ""}{decision.draft_revision_id ? ` · revisión ${decision.draft_revision_id}` : ""}</li>)}</ul> : <small>Pendiente de decisión humana.</small>}
              {!entry.source_stale ? <SuggestionDecisionForm itemUuid={item.uuid} suggestionId={entry.suggestion_id} /> : <small>No se puede decidir sobre evidencia obsoleta.</small>}
            </li>)}
          </ol> : <p>Aún no hay sugerencias persistidas.</p>}
        </details>
        {localDraft ? (
          <details className="draft-history">
            <summary>Historial del borrador ({localDraft.revisions.length})</summary>
            <ol>
              {localDraft.revisions.toReversed().map((revision) => (
                <li key={revision.revision_id}>
                  <div>
                    <strong>Versión {revision.version}</strong>
                    <span>{revision.author}</span>
                  </div>
                  <p>{revision.note}</p>
                  <small>Validación registrada: {revision.validation_snapshot.status}</small>
                  <small>
                    {new Intl.DateTimeFormat("es-MX", {
                      dateStyle: "medium",
                      timeStyle: "short",
                    }).format(new Date(revision.created_at))}
                  </small>
                </li>
              ))}
            </ol>
          </details>
        ) : null}
      </section>

      <section aria-labelledby="similar-heading">
        <div className="section-heading">
          <h2 id="similar-heading">Registros similares</h2>
          <span>{similar?.items.length ?? 0} vecinos</span>
        </div>
        {similar === null ? (
          <div className="diagnostic-notice stale" role="status">
            La recuperación de registros similares no está disponible temporalmente.
          </div>
        ) : similar.items.length ? (
          <div className="similar-list">
            {similar.items.map((neighbor) => (
              <article className="similar-card" key={neighbor.uuid}>
                <div className="similar-heading">
                  <div>
                    <h3><Link href={`/items/${neighbor.uuid}`}>{neighbor.name}</Link></h3>
                    <p>{neighbor.handle ?? neighbor.uuid}</p>
                  </div>
                  <span>Puntaje {neighbor.score.toFixed(2)}</span>
                </div>
                <ul className="evidence-list">
                  {neighbor.evidence.map((evidence) => (
                    <li key={`${evidence.kind}-${evidence.field}-${evidence.values.join("-")}`}>
                      <strong>{evidence.field ?? evidence.kind}</strong>: {evidence.values.join(", ")}
                      <span> +{evidence.contribution.toFixed(2)}</span>
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        ) : (
          <div className="diagnostic-notice">
            No se encontraron coincidencias con la evidencia estructurada disponible.
          </div>
        )}
        {similar ? (
          <p className="diagnostic-profile">
            Método {similar.method}; {similar.candidates_evaluated} candidatos evaluados.
            {similar.truncated ? " La búsqueda alcanzó su límite interno." : ""}
          </p>
        ) : null}
      </section>

      <section>
        <h2>Todos los metadatos</h2>
        <div className="metadata-table">
          {Object.entries(item.metadata).sort(([a], [b]) => a.localeCompare(b)).map(([field, values]) => (
            <div className="metadata-row" key={field}>
              <strong>{field}</strong>
              <ul>{values.map((value) => <li key={`${value.place}-${value.value}`}>{value.value}</li>)}</ul>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2>Bundles y bitstreams</h2>
        {item.bundles.length ? item.bundles.map((bundle) => (
          <div className="bundle" key={bundle.uuid}>
            <h3>{bundle.name}</h3>
            <ul>{bundle.bitstreams.map((file) => <li key={file.uuid}>{file.name}</li>)}</ul>
          </div>
        )) : <p>No se registraron bundles públicos.</p>}
      </section>
    </article>
  );
}
