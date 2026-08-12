"use client";

import { useMemo, useState } from "react";
import type { CatalogSuggestions, ItemMetadataValidation } from "@/lib/api";
import { recordLocalDraft } from "./actions";

const FIELDS = [
  "dc.subject.linguisticFamily",
  "dc.subject.linguisticBranch",
  "dc.subject.linguiscgroup",
  "dc.description.registeredLanguage",
] as const;

type Props = {
  itemUuid: string;
  draftId: string | null;
  expectedVersion: number | null;
  initialValues: Record<string, string>;
  stale: boolean;
  validation: ItemMetadataValidation | null;
  suggestions: CatalogSuggestions | null;
  deduplicateFields: string[];
};
type Status = "unavailable" | "no_vocabulary" | "no_values" | "valid" | "invalid";
type Preview = { status: Status; source: string | null; values: Array<{ value: string; approved: boolean | null }> };
const LABELS: Record<Status, string> = {
  unavailable: "No disponible", no_vocabulary: "Sin vocabulario activo", no_values: "Sin valores propuestos",
  valid: "Coincidencia literal", invalid: "Requiere revisión",
};

function getPreview(field: string, text: string, validation: ItemMetadataValidation | null): Preview {
  const values = text.split("\n").map((entry) => entry.trim()).filter(Boolean);
  if (!validation) return { status: "unavailable", source: null, values: values.map((value) => ({ value, approved: null })) };
  const configured = validation.fields.find((entry) => entry.field === field);
  if (!configured?.vocabulary) return { status: "no_vocabulary", source: null, values: values.map((value) => ({ value, approved: null })) };
  const allowed = new Set(configured.vocabulary.terms.map((term) => term.value));
  const evidence = values.map((value) => ({ value, approved: allowed.has(value) }));
  return {
    status: evidence.length === 0 ? "no_values" : evidence.every((entry) => entry.approved) ? "valid" : "invalid",
    source: `${configured.vocabulary.name} · ${configured.vocabulary.version_label} · aprobado por ${configured.vocabulary.approved_by}`,
    values: evidence,
  };
}

function deduplicateText(text: string): string {
  const seen = new Set<string>();
  return text
    .split("\n")
    .map((entry) => entry.trim())
    .filter((entry) => {
      if (!entry) return false;
      const normalized = entry.normalize("NFKC").toLocaleLowerCase("es");
      if (seen.has(normalized)) return false;
      seen.add(normalized);
      return true;
    })
    .join("\n");
}

export function DraftEditor({ itemUuid, draftId, expectedVersion, initialValues, stale, validation, suggestions, deduplicateFields }: Props) {
  const [values, setValues] = useState(() => Object.fromEntries(
    Object.entries(initialValues).map(([field, value]) => [
      field,
      deduplicateFields.includes(field) ? deduplicateText(value) : value,
    ]),
  ));
  const previews = useMemo(() => Object.fromEntries(FIELDS.map((field) => [field, getPreview(field, values[field] ?? "", validation)])), [validation, values]);
  const statuses = Object.values(previews).map((preview) => preview.status);
  const hasInvalid = statuses.includes("invalid");
  const hasVocabulary = statuses.some((status) => !["unavailable", "no_vocabulary"].includes(status));

  return <>
    <section aria-labelledby="suggestions-heading">
      <div className="section-heading">
        <h2 id="suggestions-heading">Sugerencias supervisadas</h2>
        <span>{suggestions?.suggestions.length ?? 0} propuestas</span>
      </div>
      {suggestions === null ? <div className="diagnostic-notice stale">Las sugerencias no están disponibles temporalmente.</div> : suggestions.suggestions.length ? <div className="suggestion-list">
        {suggestions.suggestions.map((suggestion) => <article className="suggestion-card" key={`${suggestion.field}:${suggestion.value}`}>
          <div className="diagnostic-title"><strong>{suggestion.field}</strong><span>Confianza {Math.round(suggestion.confidence * 100)}%</span></div>
          <p>Valor propuesto: <strong>{suggestion.value}</strong></p>
          <p>{suggestion.explanation}</p>
          <details><summary>Evidencia ({suggestion.supporting_item_uuids.length} registros)</summary><ul>{suggestion.supporting_item_uuids.map((uuid) => <li key={uuid}><a href={`/items/${uuid}`}>{uuid}</a></li>)}</ul></details>
          <button type="button" onClick={() => setValues((current) => ({ ...current, [suggestion.field]: suggestion.value }))}>Copiar al editor local</button>
          <small>Esta acción sólo actualiza el formulario en el navegador; todavía debe revisarlo y guardarlo.</small>
        </article>)}
      </div> : <div className="diagnostic-notice">No hay evidencia suficiente para proponer valores.</div>}
    </section>
    <form action={recordLocalDraft} className="draft-editor">
      <input type="hidden" name="item_uuid" value={itemUuid} />
      <input type="hidden" name="draft_id" value={draftId ?? ""} />
      <input type="hidden" name="expected_version" value={expectedVersion ?? ""} />
      <fieldset disabled={stale}>
        <legend>Valores propuestos</legend>
        {deduplicateFields.length ? <div className="diagnostic-notice" role="status">
          Se preparó una propuesta local conservando la primera aparición de cada valor en{" "}
          <strong>{deduplicateFields.join(", ")}</strong>. Revise el resultado y guárdelo
          explícitamente si es correcto.
        </div> : null}
        <div className={`draft-validation-preview${hasInvalid ? " invalid" : ""}`} aria-live="polite">
          <strong>Validación previa de vocabulario</strong>
          <p>{!validation ? "La validación no está disponible. El borrador puede guardarse y se evaluará en el servidor." : !hasVocabulary ? "No hay vocabularios aprobados activos. El borrador puede guardarse; la revisión quedará como no configurada." : hasInvalid ? "Hay valores sin coincidencia literal. El borrador puede guardarse y conservará esta evidencia para revisión humana." : "Los valores con vocabulario activo coinciden literalmente con su revisión aprobada."}</p>
        </div>
        <div className="draft-field-grid">
          {FIELDS.map((field) => {
            const preview = previews[field];
            return <div className="draft-field" key={field}>
              <label htmlFor={`draft-${field}`}>{field}</label>
              <textarea id={`draft-${field}`} name={field} value={values[field] ?? ""} onChange={(event) => setValues((current) => ({ ...current, [field]: event.target.value }))} maxLength={20000} />
              <div className={`draft-field-preview ${preview.status}`}>
                <strong>{LABELS[preview.status]}</strong>
                {preview.source ? <small>{preview.source}</small> : null}
                {preview.values.length ? <ul>{preview.values.map((entry) => <li key={entry.value}><span>{entry.value}</span><em>{entry.approved === true ? "Aprobado" : entry.approved === false ? "No coincide literalmente" : "Sin vocabulario"}</em></li>)}</ul> : <small>Una línea equivale a un valor repetible.</small>}
              </div>
            </div>;
          })}
        </div>
        <div className="draft-attribution">
          <label>Catalogador<input name="author" minLength={2} maxLength={120} autoComplete="name" required /></label>
          <label>Justificación y evidencia<textarea name="note" minLength={1} maxLength={2000} required /></label>
        </div>
        <button type="submit">{draftId ? "Guardar nueva revisión" : "Crear borrador local"}</button>
      </fieldset>
      <small>Guardar siempre crea una revisión local con la evidencia de vocabulario vigente. No modifica DSpace ni convierte valores humanos en términos autorizados.</small>
    </form>
  </>;
}
