import Link from "next/link";
import { notFound } from "next/navigation";

import { getItem } from "@/lib/api";
import { getCatalogingContract } from "@/lib/cataloging-contract";
import { getEvidenceSession } from "@/lib/evidence";

import { copyEvidenceToDraft, extractEvidence, uploadPdfEvidence } from "../actions";

const EXTRACT_MESSAGES: Record<string, string> = {
  saved: "La extracción determinista quedó congelada como evidencia local.",
  stale: "El registro DSpace cambió desde la captura. Reabre una sesión con la versión vigente.",
  error: "No fue posible extraer candidatos.",
  unavailable: "La extracción está deshabilitada porque falta la configuración segura.",
};

const PDF_MESSAGES: Record<string, string> = {
  saved: "El PDF quedó capturado como fuente de evidencia local.",
  too_large: "El PDF supera el máximo permitido de 25 MB.",
  invalid_type: "Sólo se aceptan archivos application/pdf con extensión .pdf.",
  rejected: "El PDF no pudo procesarse (cifrado, corrupto o no es un PDF real).",
  stale: "El registro DSpace cambió desde la captura. Reabre una sesión con la versión vigente.",
  invalid: "Verifica el catalogador y selecciona un archivo PDF antes de enviar.",
  error: "No fue posible subir el PDF.",
  unavailable: "La subida está deshabilitada porque falta la configuración segura.",
};

const EXTRACTION_STATUS_LABELS: Record<string, string> = {
  extracted: "Texto extraído",
  no_extractable_text: "Sin texto útil (requiere OCR, no soportado)",
  pending: "Pendiente",
  rejected: "Rechazado",
};

const COPY_MESSAGES: Record<string, string> = {
  saved: "Los candidatos seleccionados se copiaron a una revisión del borrador local.",
  conflict: "El borrador o el registro fuente cambió. Recarga antes de continuar.",
  invalid: "Algún candidato no es copiable al borrador lingüístico o no supera la validación.",
  error: "No fue posible copiar los candidatos al borrador.",
  unavailable: "La copia está deshabilitada porque falta la configuración segura.",
};

export default async function EvidenceSessionPage({
  params,
  searchParams,
}: {
  params: Promise<{ sessionId: string }>;
  searchParams: Promise<{ extract?: string; copy?: string; pdf?: string }>;
}) {
  const { sessionId } = await params;
  const { extract, copy, pdf } = await searchParams;

  const [evidenceResult, contractResult] = await Promise.allSettled([
    getEvidenceSession(sessionId),
    getCatalogingContract(),
  ]);
  if (evidenceResult.status === "rejected") notFound();

  const evidence = evidenceResult.value;
  const contract = contractResult.status === "fulfilled" ? contractResult.value : null;
  const draftableFields = new Set(contract?.runtime.draftable_fields ?? []);
  const bindingLabels = new Map(
    contract?.fields.map((field) => [field.binding_id, field.assistant_label]) ?? [],
  );

  const item = evidence.item_uuid
    ? await getItem(evidence.item_uuid).catch(() => null)
    : null;
  const localDraft = item?.drafts[0] ?? null;
  const latestRevision = localDraft?.revisions.at(-1) ?? null;
  const copyable = evidence.candidates.filter(
    (candidate) =>
      draftableFields.has(candidate.metadata_field) &&
      candidate.validation_json.status !== "invalid",
  );

  return (
    <div className="shell">
      <Link href="/evidence" className="back-link">← Nueva sesión</Link>
      <header className="profile-hero">
        <p className="eyebrow">Evidencia externa · {evidence.contract_version}</p>
        <h1>Sesión {evidence.session_id}</h1>
        <p>
          Capturada por {evidence.created_by}. {evidence.item_uuid
            ? `Vinculada al ítem ${evidence.item_uuid}.`
            : "Sin vínculo a un ítem DSpace."}
        </p>
      </header>

      {evidence.stale ? (
        <div className="diagnostic-notice stale" role="status">
          El `source_hash` del registro DSpace cambió. La sesión queda sólo como evidencia histórica
          y no puede extraerse ni copiarse a borrador.
        </div>
      ) : null}
      {extract && EXTRACT_MESSAGES[extract] ? (
        <div className={extract === "saved" ? "review-status" : "review-status error"} role="status">
          {EXTRACT_MESSAGES[extract]}
        </div>
      ) : null}
      {copy && COPY_MESSAGES[copy] ? (
        <div className={copy === "saved" ? "review-status" : "review-status error"} role="status">
          {COPY_MESSAGES[copy]}
        </div>
      ) : null}
      {pdf && PDF_MESSAGES[pdf] ? (
        <div className={pdf === "saved" ? "review-status" : "review-status error"} role="status">
          {PDF_MESSAGES[pdf]}
        </div>
      ) : null}

      <section>
        <div className="section-heading">
          <h2>Fuentes congeladas</h2>
          <span>{evidence.sources.length}</span>
        </div>
        <div className="item-list">
          {evidence.sources.map((source) => (
            <article className="item-card" key={source.source_id}>
              <div>
                <h3>
                  {source.kind === "url" ? "URL" : source.kind === "pdf" ? "PDF" : "Texto"}
                </h3>
                {source.kind === "pdf" ? (
                  <>
                    <p>{String(source.metadata_json.original_filename ?? "documento.pdf")}</p>
                    <p>
                      {EXTRACTION_STATUS_LABELS[source.extraction_status] ??
                        source.extraction_status}
                      {source.page_count !== null ? ` · ${source.page_count} páginas` : ""}
                    </p>
                  </>
                ) : (
                  <p>{source.locator ?? source.media_type ?? "Fuente textual"}</p>
                )}
                <small>SHA-256: {source.content_hash}</small>
              </div>
            </article>
          ))}
        </div>
        <form
          action={uploadPdfEvidence}
          className="review-form"
          encType="multipart/form-data"
        >
          <input type="hidden" name="session_id" value={evidence.session_id} />
          <label>
            Adjuntar PDF (máximo 25 MB, sólo texto extraíble; sin OCR)
            <input type="file" name="file" accept="application/pdf" required disabled={evidence.stale} />
          </label>
          <label>
            Catalogador
            <input name="author" minLength={2} maxLength={120} autoComplete="name" required />
          </label>
          <button type="submit" disabled={evidence.stale}>Subir PDF</button>
          <small>
            El PDF se guarda localmente; nunca se ejecuta su contenido ni se sigue ningún enlace
            que contenga.
          </small>
        </form>
      </section>

      <section>
        <div className="section-heading">
          <h2>Candidatos</h2>
          <span>{evidence.candidates.length}</span>
        </div>
        {!evidence.candidates.length ? (
          <>
            <div className="diagnostic-notice">
              La sesión todavía no tiene extracción. El extractor determinista reconoce líneas
              explícitas del contrato, DOI, ISSN, ISBN, la URL aportada y el texto extraído de
              cualquier PDF adjunto. Para claves compartidas como `dc.subject` o
              `dc.format.medium`, use el `binding_id` del contrato.
            </div>
            <form action={extractEvidence} className="review-form">
              <input type="hidden" name="session_id" value={evidence.session_id} />
              <button type="submit" disabled={evidence.stale}>Extraer candidatos</button>
            </form>
          </>
        ) : (
          <div className="vocabulary-validation-grid">
            {evidence.candidates.map((candidate) => (
              <article className="vocabulary-validation-card" key={candidate.candidate_id}>
                <div className="diagnostic-title">
                  <strong>{bindingLabels.get(candidate.binding_id) ?? candidate.binding_id}</strong>
                  <span>{candidate.evidence_state}</span>
                </div>
                <p><code>{candidate.binding_id}</code> · <code>{candidate.metadata_field}</code></p>
                <p><strong>{candidate.value}</strong></p>
                <p className="validation-source">
                  Validación: {String(candidate.validation_json.status ?? "sin estado")}
                </p>
                <details>
                  <summary>Evidencia capturada</summary>
                  <pre>{JSON.stringify(candidate.evidence_json, null, 2)}</pre>
                </details>
              </article>
            ))}
          </div>
        )}
      </section>

      {evidence.item_uuid && evidence.candidates.length ? (
        <section>
          <div className="section-heading">
            <h2>Copiar al borrador lingüístico</h2>
            <span>{copyable.length} candidatos elegibles</span>
          </div>
          {!contract ? (
            <div className="diagnostic-notice stale">
              El contrato maestro no está disponible; la copia queda bloqueada.
            </div>
          ) : copyable.length ? (
            <form action={copyEvidenceToDraft} className="review-form">
              <input type="hidden" name="session_id" value={evidence.session_id} />
              <input type="hidden" name="item_uuid" value={evidence.item_uuid} />
              <input type="hidden" name="draft_id" value={localDraft?.draft_id ?? ""} />
              <input type="hidden" name="expected_version" value={latestRevision?.version ?? ""} />
              <fieldset disabled={evidence.stale}>
                <legend>Candidatos aprobables</legend>
                {copyable.map((candidate) => (
                  <label key={candidate.candidate_id}>
                    <input type="checkbox" name="candidate_id" value={candidate.candidate_id} />
                    {bindingLabels.get(candidate.binding_id) ?? candidate.binding_id}: {candidate.value}
                  </label>
                ))}
              </fieldset>
              <label>
                Catalogador
                <input name="author" minLength={2} maxLength={120} required />
              </label>
              <label>
                Justificación
                <textarea name="note" minLength={1} maxLength={2000} required />
              </label>
              <button type="submit" disabled={evidence.stale}>Copiar selección</button>
              <small>
                Sólo crea o revisa el borrador PostgreSQL. Los candidatos bibliográficos no se
                copian porque el contrato local de borrador continúa limitado a campos lingüísticos.
              </small>
            </form>
          ) : (
            <div className="diagnostic-notice">
              No hay candidatos lingüísticos elegibles para copiar. Los demás permanecen como
              evidencia revisable.
            </div>
          )}
        </section>
      ) : null}
    </div>
  );
}
