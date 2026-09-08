"use client";

import { useRef, useState } from "react";
import { useFormStatus } from "react-dom";
import type { EvidenceSession } from "@/lib/evidence";
import { copyEvidenceToDraft, extractEvidence, fetchRemoteEvidence, uploadPdfEvidence } from "../actions";
import { EvidenceInspector, SourceDetails, sourceTitle } from "./evidence-inspector";
import { EXTRACTION_STATUS_LABELS } from "./status-messages";
import styles from "./workspace.module.css";

type Props = {
  evidence: EvidenceSession;
  title: string;
  bindingLabels: Record<string, string>;
  copyableCandidateIds: string[];
  localDraft: { draft_id: string } | null;
  expectedVersion: number | null;
};

function ConfirmCopy({ blocked }: { blocked: boolean }) {
  const { pending } = useFormStatus();
  return <button type="submit" className={styles.primary} disabled={blocked || pending}>
    {pending ? "Copiando…" : "Confirmar copia al borrador"}
  </button>;
}

export function EvidenceWorkspace({ evidence, title, bindingLabels, copyableCandidateIds, localDraft, expectedVersion }: Props) {
  const [focusedId, setFocusedId] = useState<string | null>(null);
  const [sourceId, setSourceId] = useState<string | null>(null);
  const [selection, setSelection] = useState<string[]>([]);
  const [filter, setFilter] = useState("");
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const inspector = useRef<HTMLHeadingElement>(null);
  const inspectionTrigger = useRef<HTMLButtonElement | null>(null);
  const filterInput = useRef<HTMLInputElement>(null);
  const allowed = new Set(copyableCandidateIds);
  // Derive submitted IDs in canonical server order, including filtered-out selections.
  const selected = evidence.candidates.filter(candidate =>
    selection.includes(candidate.candidate_id) && allowed.has(candidate.candidate_id),
  );
  const candidate = evidence.candidates.find(value => value.candidate_id === focusedId);
  const source = evidence.sources.find(value => value.source_id === (candidate?.source_id ?? sourceId));
  const visible = evidence.candidates.filter(value =>
    [bindingLabels[value.binding_id], value.binding_id, value.metadata_field, value.value]
      .join(" ").toLocaleLowerCase().includes(filter.toLocaleLowerCase()),
  );
  const blocked = evidence.stale || !evidence.item_uuid || selected.length === 0;

  function closeReview() { dialog.current?.close(); }
  function restoreFocus() { trigger.current?.focus(); }
  function inspectCandidate(id: string) { setFocusedId(id); setSourceId(null); }
  function trapReviewFocus(event: React.KeyboardEvent<HTMLDialogElement>) {
    if (event.key !== "Tab") return;
    const root = dialog.current;
    if (!root) return;
    const controls = Array.from(root.querySelectorAll<HTMLElement>(
      'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    )).filter(control => !control.hasAttribute("hidden"));
    const first = controls[0];
    const last = controls.at(-1);
    if (!first || !last) return;
    const active = document.activeElement;
    if (event.shiftKey && (active === first || !root.contains(active))) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && (active === last || !root.contains(active))) {
      event.preventDefault();
      first.focus();
    }
  }

  return (
    <>
      <header className={styles.header}>
        <div className={styles.identity}>
          <p className={styles.eyebrow}>Evidencias · {evidence.contract_version}</p>
          <h1>{title}</h1>
          <p>Sesión <code>{evidence.session_id}</code> · {evidence.created_by}</p>
          <p>{evidence.item_uuid ? <>Ítem <code>{evidence.item_uuid}</code></> : "Sin vínculo a un ítem DSpace"} · {evidence.created_at}</p>
          <span className={styles.badge}>DSpace · SOLO LECTURA</span>
        </div>
        <div className={styles.actions}>
          {candidate || source ? <button type="button" onClick={() => inspector.current?.focus()}>Ir al Inspector</button> : null}
          <span role="status">{selected.length} seleccionados · {copyableCandidateIds.length} elegibles</span>
          <button ref={trigger} type="button" className={styles.primary} disabled={blocked} onClick={() => dialog.current?.showModal()}>
            Copiar selección al borrador
          </button>
        </div>
      </header>
      {evidence.stale ? <p role="status" className={styles.notice}>El registro DSpace cambió desde la captura. La sesión conserva evidencia histórica; la extracción y la copia están bloqueadas.</p> : null}
      {!evidence.item_uuid ? <p className={styles.notice}>Sesión sin ítem vinculado: los candidatos se pueden inspeccionar, pero no copiar a un borrador.</p> : null}

      <div className={styles.panes}>
        <section className={styles.pane} aria-labelledby="sources-heading">
          <header className={styles.paneHeader}><h2 id="sources-heading">Fuentes de evidencia</h2><span>{evidence.sources.length}</span></header>
          {evidence.sources.length === 0 ? <p className={styles.empty}>Todavía no hay fuentes. Añade un PDF o una URL.</p> : null}
          <div className={styles.cards}>
            {evidence.sources.map(value => (
              <article key={value.source_id} className={styles.source}>
                <button type="button" className={styles.inspect} aria-pressed={!candidate && sourceId === value.source_id}
                  onClick={event => { inspectionTrigger.current = event.currentTarget; setSourceId(value.source_id); setFocusedId(null); }}>
                  <strong>{sourceTitle(value)}</strong>
                  <span>{value.kind} · {value.media_type ?? "Tipo no informado"}</span>
                  <span>{EXTRACTION_STATUS_LABELS[value.extraction_status] ?? value.extraction_status}{value.page_count !== null ? " · " + value.page_count + " páginas" : ""}</span>
                  <code>SHA-256: {value.content_hash}</code>
                </button>
              </article>
            ))}
          </div>
          <details className={styles.addEvidence}>
            <summary>Añadir evidencia</summary>
            <form action={uploadPdfEvidence} className={styles.form}>
              <input type="hidden" name="session_id" value={evidence.session_id} />
              <label>PDF local (máximo 25 MB, sin OCR)<input type="file" name="file" accept="application/pdf" required disabled={evidence.stale} /></label>
              <label>Catalogador<input name="author" minLength={2} maxLength={120} autoComplete="name" required disabled={evidence.stale} /></label>
              <button type="submit" disabled={evidence.stale}>Subir PDF</button>
              <small>El PDF se guarda localmente; nunca se ejecuta su contenido ni se siguen sus enlaces.</small>
            </form>
            <form action={fetchRemoteEvidence} className={styles.form}>
              <input type="hidden" name="session_id" value={evidence.session_id} />
              <label>Obtener evidencia desde URL<input type="url" name="url" placeholder="https://…" maxLength={4000} required disabled={evidence.stale} /></label>
              <label>Catalogador<input name="author" minLength={2} maxLength={120} autoComplete="name" required disabled={evidence.stale} /></label>
              <button type="submit" disabled={evidence.stale}>Obtener desde URL</button>
              <small>La solicitud se realiza desde el servidor, sin autenticación ni cookies y sólo hacia destinos públicos. No se siguen enlaces del contenido. Requiere que el fetch remoto esté habilitado.</small>
            </form>
          </details>
        </section>

        <section className={styles.pane} aria-labelledby="proposal-heading">
          <header className={styles.paneHeader}><h2 id="proposal-heading">Propuesta de catálogo</h2><span>{visible.length}/{evidence.candidates.length}</span></header>
          <label className={styles.filter}>Filtrar candidatos<input ref={filterInput} type="search" value={filter} onChange={event => setFilter(event.target.value)} placeholder="Campo, binding o valor" /></label>
          {evidence.candidates.length === 0 ? (
            <div className={styles.empty}>
              <p>La sesión todavía no tiene extracción. El extractor determinista reconoce líneas del contrato, DOI, ISSN, ISBN, la URL aportada y texto de PDF. Para claves compartidas usa el binding del contrato.</p>
              <form action={extractEvidence}><input type="hidden" name="session_id" value={evidence.session_id} /><button disabled={evidence.stale} type="submit">Extraer candidatos</button></form>
            </div>
          ) : visible.length === 0 ? <p className={styles.empty}>Ningún candidato coincide. La selección se conserva.</p> : null}
          <div className={styles.cards}>
            {visible.map(value => {
              const label = bindingLabels[value.binding_id] ?? value.binding_id;
              const reason = evidence.stale ? "Sesión desactualizada."
                : !evidence.item_uuid ? "Sin ítem vinculado."
                : value.validation_json.status === "invalid" ? "Valor inválido para el vocabulario."
                : !allowed.has(value.candidate_id) ? "Campo fuera del borrador lingüístico actual." : null;
              return (
                <article key={value.candidate_id} className={styles.candidate} data-focused={focusedId === value.candidate_id}>
                  <input type="checkbox" aria-label={"Seleccionar " + label + ": " + value.value}
                    aria-describedby={reason ? "reason-" + value.candidate_id : undefined}
                    checked={selection.includes(value.candidate_id)} disabled={Boolean(reason)}
                    onChange={event => setSelection(current => event.target.checked ? [...current, value.candidate_id] : current.filter(id => id !== value.candidate_id))} />
                  <div className={styles.candidateBody}>
                    <button type="button" className={styles.inspect} aria-pressed={focusedId === value.candidate_id}
                      onFocus={event => { inspectionTrigger.current = event.currentTarget; inspectCandidate(value.candidate_id); }}
                      onClick={() => inspectCandidate(value.candidate_id)}>
                      <strong>{label}</strong>
                      <code>{value.metadata_field} · binding: {value.binding_id}</code>
                      <span className={styles.value}>{value.value}</span>
                      <span className={styles.states}><span className={styles.badge}>{value.evidence_state}</span><span>Validación: {String(value.validation_json.status ?? "sin estado")}</span></span>
                    </button>
                    {reason ? <p id={"reason-" + value.candidate_id} className={styles.reason}>No elegible: {reason} Disponible para inspección.</p> : null}
                  </div>
                </article>
              );
            })}
          </div>
          <p className={styles.footer}>La selección no cambia evidencia ni validación. La copia requiere confirmación humana y afecta sólo al borrador local.</p>
        </section>

        <aside className={styles.pane} aria-labelledby="inspector-heading">
          <header className={styles.paneHeader}><h2 id="inspector-heading" ref={inspector} tabIndex={-1}>Contexto y QA</h2></header>
          {candidate ? <EvidenceInspector candidate={candidate} source={source} label={bindingLabels[candidate.binding_id] ?? candidate.binding_id} />
            : source ? <SourceDetails source={source} />
            : <p className={styles.empty}>Enfoca un candidato o selecciona una fuente para inspeccionar identidad, procedencia y validación.</p>}
          {candidate || source ? <button type="button" onClick={() => {
            if (inspectionTrigger.current?.isConnected) inspectionTrigger.current.focus();
            else filterInput.current?.focus();
          }}>Volver a la inspección</button> : null}
        </aside>
      </div>

      <dialog ref={dialog} className={styles.review} aria-labelledby="review-title" aria-describedby="review-description" onClose={restoreFocus} onKeyDown={trapReviewFocus}>
        <div className={styles.paneHeader}>
          <h2 id="review-title">Revisar copia al borrador</h2>
          <button type="button" aria-label="Cerrar revisión" onClick={closeReview}>×</button>
        </div>
        <p id="review-description">Se copiarán {selected.length} candidatos a una revisión del borrador local. DSpace permanece en solo lectura.</p>
        <ol>{selected.map(value => <li key={value.candidate_id}><strong>{bindingLabels[value.binding_id] ?? value.binding_id}</strong>: {value.value}<br /><code>{value.metadata_field} · {value.binding_id}</code></li>)}</ol>
        <form action={copyEvidenceToDraft} className={styles.form}>
          <input type="hidden" name="session_id" value={evidence.session_id} />
          <input type="hidden" name="item_uuid" value={evidence.item_uuid ?? ""} />
          <input type="hidden" name="draft_id" value={localDraft?.draft_id ?? ""} />
          <input type="hidden" name="expected_version" value={expectedVersion ?? ""} />
          {selected.map(value => <input key={value.candidate_id} type="hidden" name="candidate_id" value={value.candidate_id} />)}
          <label>Catalogador<input name="author" minLength={2} maxLength={120} required disabled={blocked} /></label>
          <label>Justificación<textarea name="note" minLength={1} maxLength={2000} required disabled={blocked} /></label>
          <div className={styles.actions}>
            <button type="button" onClick={closeReview}>Cancelar</button>
            <ConfirmCopy blocked={blocked} />
          </div>
        </form>
      </dialog>
    </>
  );
}
