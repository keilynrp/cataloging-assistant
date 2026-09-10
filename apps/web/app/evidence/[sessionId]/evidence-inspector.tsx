import type { EvidenceCandidate, EvidenceSource } from "@/lib/evidence";
import { EXTRACTION_STATUS_LABELS } from "./status-messages";
import styles from "./workspace.module.css";

export function sourceTitle(source: EvidenceSource): string {
  return String(source.metadata_json.original_filename ?? source.locator ?? source.media_type ?? "Fuente textual");
}

function Fact({ label, value }: { label: string; value: unknown }) {
  if (value === null || value === undefined) return null;
  return <div><dt>{label}</dt><dd>{typeof value === "object" ? JSON.stringify(value) : String(value)}</dd></div>;
}

export function SourceDetails({ source }: { source: EvidenceSource }) {
  const metadata = source.extraction_metadata_json;
  return (
    <section className={styles.inspectorSection} aria-label="Procedencia de la fuente">
      <h3>{sourceTitle(source)}</h3>
      <dl className={styles.facts}>
        <Fact label="Identificador de fuente" value={source.source_id} />
        <Fact label="Tipo" value={source.kind} />
        <Fact label="Tipo de contenido" value={source.media_type} />
        <Fact label="Capturada" value={source.created_at} />
        <Fact label="Extracción" value={EXTRACTION_STATUS_LABELS[source.extraction_status] ?? source.extraction_status} />
        <Fact label="Páginas" value={source.page_count} />
        <Fact label="Localizador / URL solicitada" value={metadata.requested_url ?? source.locator} />
        <Fact label="URL final" value={metadata.final_url} />
        <Fact label="Bytes" value={metadata.content_length} />
        <Fact label="Obtenida" value={metadata.fetched_at} />
        <Fact label="Redirecciones" value={Array.isArray(metadata.redirect_chain) ? metadata.redirect_chain.length : null} />
        <Fact label="SHA-256 de la fuente" value={source.content_hash} />
        <Fact label="SHA-256 del texto extraído" value={source.extracted_text_hash} />
        <Fact label="Extractor" value={metadata.extractor} />
      </dl>
      <details><summary>Detalles técnicos de la fuente</summary><pre>{JSON.stringify(source, null, 2)}</pre></details>
    </section>
  );
}

export function EvidenceInspector({ candidate, source, label }: {
  candidate: EvidenceCandidate; source?: EvidenceSource; label: string;
}) {
  const evidence = candidate.evidence_json;
  return (
    <div className={styles.inspectorSection}>
      <h3>{label}</h3>
      <p className={styles.value}>{candidate.value}</p>
      <dl className={styles.facts}>
        <Fact label="Metadata field" value={candidate.metadata_field} />
        <Fact label="Binding" value={candidate.binding_id} />
        <Fact label="Identificador de candidato" value={candidate.candidate_id} />
        <Fact label="Estado de evidencia" value={candidate.evidence_state} />
        <Fact label="Validación" value={candidate.validation_json.status ?? "sin estado"} />
        <Fact label="Revisión de vocabulario" value={candidate.validation_json.vocabulary_revision} />
        <Fact label="Página" value={evidence.page} />
        <Fact label="Línea" value={evidence.line} />
        <Fact label="Inicio del fragmento" value={evidence.start} />
        <Fact label="Fin del fragmento" value={evidence.end} />
        <Fact label="Método" value={evidence.kind} />
        <Fact label="Extractor" value={evidence.extractor} />
      </dl>
      <h3>Fragmento de evidencia</h3>
      {typeof evidence.quote === "string" ? <blockquote>{evidence.quote}</blockquote> : <p>No se recibió un fragmento textual para este candidato.</p>}
      {source ? <SourceDetails source={source} /> : <p>Fuente no disponible: {candidate.source_id}</p>}
      <details><summary>Detalles técnicos del candidato</summary><pre>{JSON.stringify(candidate, null, 2)}</pre></details>
    </div>
  );
}
