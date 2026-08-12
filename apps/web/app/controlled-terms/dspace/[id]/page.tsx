import Link from "next/link";
import { notFound } from "next/navigation";

import { getDSpaceVocabularyComparison } from "@/lib/api";
import { promoteDSpaceVocabulary } from "../../actions";

const LABELS = { exact: "Coincidencia literal", normalized: "Coincidencia normalizada", outside: "Fuera de lista" } as const;

export default async function DSpaceVocabularyComparisonPage({ params, searchParams }: { params: Promise<{ id: string }>; searchParams: Promise<{ promotion?: string }> }) {
  const { id } = await params;
  const comparison = await getDSpaceVocabularyComparison(id).catch(() => null);
  const { promotion } = await searchParams;
  if (!comparison) notFound();
  return <main className="shell vocabulary-page">
    <Link href="/controlled-terms" className="back-link">← Volver a vocabularios</Link>
    {promotion ? <div className={promotion === "saved" ? "review-status" : "review-status error"}>{promotion === "saved" ? "La instantánea quedó aprobada como revisión local." : promotion === "blocked" ? "Promoción bloqueada por duplicados o datos inválidos." : "No fue posible promover la instantánea."}</div> : null}
    <header className="profile-hero"><p className="eyebrow">Comparación de sólo lectura</p><h1>{comparison.vocabulary_id}</h1><p>Contraste con {comparison.field}; una coincidencia normalizada es una inferencia, no una equivalencia aprobada.</p></header>
    <section><div className="queue-summary">
      {[['Entradas', comparison.term_count], ['Términos distintos', comparison.distinct_term_count], ['Duplicados literales', comparison.duplicate_term_count], ['Colisiones normalizadas', comparison.normalized_duplicate_count], ['Valores observados', comparison.observed_value_count], ['Literales', comparison.exact_count], ['Normalizados', comparison.normalized_count], ['Fuera de lista', comparison.outside_count], ['No utilizados', comparison.unused_term_count]].map(([label, value]) => <article className="queue-metric" key={String(label)}><p>{label}</p><strong>{value}</strong></article>)}
    </div></section>
    <section><h2>Valores usados en P’URHEPECHA</h2><div className="metadata-table">{comparison.values.map((entry) => <div className="metadata-row" key={entry.value}><strong>{entry.value}</strong><span>{LABELS[entry.status]} · {entry.item_count} ítems{entry.candidates.length && entry.status !== 'exact' ? ` · candidato: ${entry.candidates.join(', ')}` : ''}</span></div>)}</div></section>
    <details className="draft-history"><summary>Términos sin uso observado ({comparison.unused_term_count})</summary><ul>{comparison.unused_terms.map((term) => <li key={term}>{term}</li>)}</ul></details>
    {comparison.duplicate_terms.length ? <details className="draft-history"><summary>Valores duplicados en DSpace ({comparison.duplicate_terms.length})</summary><ul>{comparison.duplicate_terms.map((term) => <li key={term}>{term}</li>)}</ul></details> : null}
    {comparison.normalized_duplicate_terms.length ? <details className="draft-history"><summary>Colisiones después de normalizar ({comparison.normalized_duplicate_count})</summary><ul>{comparison.normalized_duplicate_terms.map((terms) => <li key={terms.join("|")}>{terms.join(" ↔ ")}</li>)}</ul></details> : null}
    <section><h2>Promoción supervisada</h2><form action={promoteDSpaceVocabulary} className="vocabulary-form">
      <input type="hidden" name="vocabulary_id" value={comparison.vocabulary_id} />
      {comparison.normalized_duplicate_terms.filter((terms) => new Set(terms).size > 1).map((terms, index) => <label key={terms.join("|")}>Forma autorizada para colisión ambigua {index + 1}<select name="collision_choice" required defaultValue=""><option value="" disabled>Seleccione una forma</option>{[...new Set(terms)].map((term) => <option value={term} key={term}>{term}</option>)}</select></label>)}
      <label>Aprobado por<input name="approved_by" minLength={2} maxLength={120} required /></label>
      <label className="vocabulary-wide">Evidencia de aprobación<textarea name="approval_note" minLength={1} maxLength={2000} required /></label>
      <button type="submit">Crear revisión aprobada local</button>
      <small>Los duplicados literales idénticos se colapsan conservando la primera posición y registrando las posiciones de origen. Las formas distintas requieren elección humana. DSpace no cambia.</small>
    </form></section>
  </main>;
}
