import Link from "next/link";

import { getControlledVocabularies, getDSpaceVocabularies } from "@/lib/api";
import { getCatalogingContract } from "@/lib/cataloging-contract";

import { recordVocabularyRevision } from "./actions";

const SAVE_MESSAGES: Record<string, string> = {
  saved: "La revisión aprobada quedó activa y la versión anterior permanece en el historial.",
  conflict: "Otra revisión cambió el estado o el identificador ya fue usado. Recarga la página.",
  error: "No fue posible guardar el vocabulario. Revisa términos, duplicados y procedencia.",
  unavailable: "La administración local está deshabilitada porque falta la configuración segura.",
  "contract-unavailable": "No se pudo cargar el contrato maestro; no se modificó ningún vocabulario.",
};

export default async function ControlledTermsPage({
  searchParams,
}: {
  searchParams: Promise<{ save?: string }>;
}) {
  const { save } = await searchParams;
  const [revisionsResult, contractResult, dspaceResult] = await Promise.allSettled([
    getControlledVocabularies(true),
    getCatalogingContract(),
    getDSpaceVocabularies(),
  ]);

  if (revisionsResult.status === "rejected") {
    return (
      <div className="shell">
        <Link href="/" className="back-link">← Volver a registros</Link>
        <section className="notice" role="status">
          <strong>Los vocabularios locales no están disponibles.</strong>
          <span>Verifica PostgreSQL y la API local antes de volver a cargar.</span>
        </section>
      </div>
    );
  }

  const revisions = revisionsResult.value.revisions;
  const contract = contractResult.status === "fulfilled" ? contractResult.value : null;
  const dspaceMirror = dspaceResult.status === "fulfilled" ? dspaceResult.value : null;
  const controlledFields = contract?.fields.filter((field) => field.runtime_vocabularied) ?? [];
  const fieldLabels = Object.fromEntries(
    controlledFields.map((field) => [field.metadata_field, field.assistant_label]),
  );
  const active = revisions.filter((revision) => revision.is_active);
  const history = revisions.filter((revision) => !revision.is_active);

  return (
    <div className="shell vocabulary-page">
      <Link href="/" className="back-link">← Volver a registros</Link>
      {save && SAVE_MESSAGES[save] ? (
        <div className={save === "saved" ? "review-status" : "review-status error"} role="status">
          {SAVE_MESSAGES[save]}
        </div>
      ) : null}
      <header className="profile-hero">
        <p className="eyebrow">Gobernanza local · aprobación humana</p>
        <h1>Vocabularios controlados</h1>
        <p>
          Registra únicamente fuentes institucionales aprobadas. Los términos se comparan de forma
          literal; esta configuración no modifica DSpace ni genera valores nuevos.
        </p>
        {contract ? (
          <small>Contrato activo: {contract.contract_version} · {contract.field_count} bindings DSpace.</small>
        ) : (
          <div className="diagnostic-notice stale">El contrato maestro no está disponible; las acciones dependientes quedan bloqueadas.</div>
        )}
      </header>

      <section aria-labelledby="active-vocabularies-heading">
        <div className="section-heading">
          <h2 id="active-vocabularies-heading">Revisiones activas</h2>
          <span>{active.length} de {controlledFields.length || "?"} campos configurados</span>
        </div>
        {active.length ? (
          <div className="vocabulary-grid">
            {active.map((revision) => (
              <article className="vocabulary-card" key={revision.revision_id}>
                <p className="eyebrow">{fieldLabels[revision.field] ?? revision.field}</p>
                <h3>{revision.name}</h3>
                <dl>
                  <div><dt>Versión</dt><dd>{revision.version_label}</dd></div>
                  <div><dt>Aprobó</dt><dd>{revision.approved_by}</dd></div>
                  <div><dt>Fuente</dt><dd>{revision.source_uri}</dd></div>
                </dl>
                <ul className="term-list">
                  {revision.terms.slice(0, 20).map((term) => (
                    <li key={term.term_id}>{term.value}</li>
                  ))}
                </ul>
                {revision.terms.length > 20 ? (
                  <small>Se muestran 20 de {revision.terms.length} términos.</small>
                ) : (
                  <small>{revision.terms.length} términos aprobados.</small>
                )}
              </article>
            ))}
          </div>
        ) : (
          <div className="diagnostic-notice">
            No hay vocabularios aprobados. La validación permanece explícitamente no configurada.
          </div>
        )}
      </section>

      <section aria-labelledby="dspace-vocabularies-heading">
        <div className="section-heading">
          <h2 id="dspace-vocabularies-heading">Referencia sincronizada desde DSpace</h2>
          <span>{dspaceMirror ? `${dspaceMirror.total} listas · ${dspaceMirror.entry_total} entradas` : "No disponible"}</span>
        </div>
        <div className="diagnostic-notice">
          Estas listas son evidencia de solo lectura y no están aprobadas automáticamente. Variante lingüística puede administrarse como vocabulario local aunque la instancia no exponga una lista DSpace promocionable para ese campo.
        </div>
        {dspaceMirror ? <div className="vocabulary-grid">
          {dspaceMirror.vocabularies.map((vocabulary) => <article className="vocabulary-card" key={vocabulary.vocabulary_id}>
            <p className="eyebrow">Fuente DSpace</p>
            <h3>{vocabulary.name}</h3>
            {["linguisticFamilyPairs", "linguisticBranchPairs", "linguiscgroupPairs", "registeredLanguagePairs"].includes(vocabulary.vocabulary_id) ? <p><Link href={`/controlled-terms/dspace/${vocabulary.vocabulary_id}`}>Comparar con la colección piloto →</Link></p> : null}
            <dl><div><dt>Entradas</dt><dd>{vocabulary.entry_count}</dd></div><div><dt>Tipo</dt><dd>{vocabulary.hierarchical ? "Jerárquico" : "Plano"}</dd></div></dl>
            <small>Sincronizado {new Intl.DateTimeFormat("es-MX", { dateStyle: "medium", timeStyle: "short" }).format(new Date(vocabulary.synced_at))}</small>
          </article>)}
        </div> : null}
      </section>

      <section aria-labelledby="new-vocabulary-heading">
        <h2 id="new-vocabulary-heading">Activar una revisión aprobada</h2>
        {contract ? (
          <form action={recordVocabularyRevision} className="vocabulary-form">
            <label>
              Campo
              <select name="field" required>
                {controlledFields.map((field) => (
                  <option value={field.metadata_field} key={field.binding_id}>
                    {field.assistant_label} · {field.metadata_field}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Nombre del vocabulario
              <input name="name" minLength={2} maxLength={500} required />
            </label>
            <label>
              Fuente o URI institucional
              <input name="source_uri" minLength={3} maxLength={2000} required />
            </label>
            <label>
              Versión de la fuente
              <input name="version_label" minLength={1} maxLength={120} required />
            </label>
            <label>
              Aprobado por
              <input name="approved_by" minLength={2} maxLength={120} required />
            </label>
            <label className="vocabulary-wide">
              Evidencia de aprobación
              <textarea name="approval_note" minLength={1} maxLength={2000} required />
            </label>
            <label className="vocabulary-wide">
              Términos aprobados · uno por línea
              <textarea name="terms" minLength={1} maxLength={100000} required />
            </label>
            <button type="submit">Activar revisión local</button>
            <small>
              Esta operación conserva el historial, pero cambia la revisión local usada para validar.
            </small>
          </form>
        ) : (
          <div className="diagnostic-notice stale">No se puede activar una revisión sin el contrato maestro runtime.</div>
        )}
      </section>

      {history.length ? (
        <section aria-labelledby="vocabulary-history-heading">
          <h2 id="vocabulary-history-heading">Historial reemplazado</h2>
          <div className="vocabulary-history">
            {history.map((revision) => (
              <details key={revision.revision_id}>
                <summary>
                  {fieldLabels[revision.field] ?? revision.field} · {revision.version_label}
                </summary>
                <p>{revision.name} · {revision.terms.length} términos</p>
                <small>{revision.approved_by} · {revision.approval_note}</small>
              </details>
            ))}
          </div>
        </section>
      ) : null}

      <aside className="evidence-caveat">
        <strong>Límite deliberado</strong>
        <p>
          Las frecuencias observadas en la colección no son fuentes autorizadas. Hasta recibir una
          aprobación humana documentada, cada campo permanece sin vocabulario activo.
        </p>
      </aside>
    </div>
  );
}
