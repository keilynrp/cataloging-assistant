import Link from "next/link";

import { getItem, getWorkQueue, type ItemDetail, type MetadataValue } from "@/lib/api";
import { decideLocalDraftRevision } from "../items/[uuid]/actions";

const LINGUISTIC_FIELDS = [
  "dc.subject.linguisticFamily",
  "dc.subject.linguisticBranch",
  "dc.subject.linguiscgroup",
  "dc.description.registeredLanguage",
] as const;

function literals(values: MetadataValue[] | undefined): string[] {
  return (values ?? []).map((entry) => entry.value);
}

function sameValues(left: string[], right: string[]): boolean {
  return left.length === right.length && left.every((value, index) => value === right[index]);
}

function deferredDecisions(item: ItemDetail) {
  const latest = new Map<string, ItemDetail["review_decisions"][number]>();
  for (const decision of item.review_decisions) {
    latest.set(decision.finding_fingerprint, decision);
  }
  return [...latest.values()].filter((decision) => decision.decision === "deferred");
}

export default async function DeferredDraftsPage({
  searchParams,
}: {
  searchParams: Promise<{ decision?: string }>;
}) {
  const { decision } = await searchParams;
  let queue: Awaited<ReturnType<typeof getWorkQueue>> | null = null;
  try {
    queue = await getWorkQueue({ review: "deferred", draft: "open", size: "100" });
  } catch {
    // Render an explicit degraded state without inventing operational data.
  }

  if (!queue) {
    return (
      <main className="shell">
        <Link href="/work-queue" className="back-link">← Volver a la cola</Link>
        <section className="notice" role="status">
          <strong>Los borradores pospuestos no están disponibles.</strong>
          <span>Verifica la API local y PostgreSQL antes de volver a cargar.</span>
        </section>
      </main>
    );
  }

  const details = await Promise.allSettled(queue.items.map((entry) => getItem(entry.uuid)));
  const items = details.flatMap((result) => result.status === "fulfilled" ? [result.value] : []);

  return (
    <main className="shell queue-dashboard">
      <Link href="/work-queue" className="back-link">← Volver a la cola</Link>
      {decision ? (
        <div className={decision === "saved" ? "review-status" : "review-status error"} role="status">
          {decision === "saved"
            ? "La decisión sobre la revisión quedó registrada localmente."
            : decision === "conflict"
              ? "La fuente o la revisión cambió; recarga antes de decidir."
              : decision === "blocked"
                ? "La aprobación requiere valores válidos o una excepción documentada."
                : "No fue posible registrar la decisión."}
        </div>
      ) : null}
      <header className="profile-hero">
        <p className="eyebrow">Revisión humana local</p>
        <h1>Borradores pospuestos</h1>
        <p>
          Compara la fuente sincronizada con la última propuesta local. Esta vista no modifica
          DSpace ni cambia decisiones al abrirla.
        </p>
        <dl className="profile-source">
          <div><dt>Pospuestos con borrador</dt><dd>{queue.total}</dd></div>
          <div><dt>Detalles disponibles</dt><dd>{items.length}</dd></div>
          <div><dt>Fuente</dt><dd>{queue.source}</dd></div>
        </dl>
      </header>

      {items.length ? (
        <div className="deferred-draft-list">
          {items.map((item) => {
            const draft = item.drafts[0];
            const revision = draft?.revisions.at(-1);
            if (!draft || !revision) return null;
            const decisions = deferredDecisions(item);
            const changedFields = LINGUISTIC_FIELDS.filter((field) => {
              const original = literals(draft.base_metadata[field]);
              const proposed = literals(revision.metadata_patch[field]);
              return !sameValues(original, proposed);
            });
            return (
              <article className="deferred-draft-card" key={item.uuid}>
                <header>
                  <div>
                    <span className="priority-badge high">Pospuesto</span>
                    <h2>{item.name}</h2>
                    <p>{item.handle ?? item.uuid}</p>
                  </div>
                  <dl>
                    <div><dt>Borrador</dt><dd>v{revision.version}</dd></div>
                    <div><dt>Validación</dt><dd>{revision.validation_snapshot.status}</dd></div>
                    <div><dt>Fuente</dt><dd>{draft.stale ? "Obsoleta" : "Vigente"}</dd></div>
                  </dl>
                </header>

                <section aria-label="Comparación de metadatos">
                  <h3>Original frente a propuesta</h3>
                  {changedFields.length ? (
                    <div className="draft-comparison">
                      {changedFields.map((field) => (
                        <div className="draft-comparison-row" key={field}>
                          <strong>{field}</strong>
                          <div>
                            <span>Original</span>
                            <ol>{literals(draft.base_metadata[field]).map((value, index) => <li key={index}>{value}</li>)}</ol>
                          </div>
                          <div>
                            <span>Propuesta local</span>
                            <ol>{literals(revision.metadata_patch[field]).map((value, index) => <li key={index}>{value}</li>)}</ol>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="diagnostic-notice">La última revisión no cambia los cuatro campos lingüísticos.</p>
                  )}
                </section>

                <section className="deferred-evidence" aria-label="Evidencia y autoría">
                  <div>
                    <h3>Evidencia del borrador</h3>
                    <p>{revision.note}</p>
                    <small>{revision.author} · revisión {revision.version}</small>
                  </div>
                  <div>
                    <h3>Decisión pospuesta</h3>
                    {decisions.map((decision) => (
                      <div key={decision.decision_id}>
                        <p>{decision.note}</p>
                        <small>{decision.reviewer} · {decision.finding_code}</small>
                      </div>
                    ))}
                  </div>
                </section>

                <nav className="deferred-actions" aria-label={"Acciones para " + (item.handle ?? item.uuid)}>
                  <Link href={"/items/" + item.uuid + "#diagnostics-heading"}>Confirmar o descartar</Link>
                  <Link href={"/items/" + item.uuid + "#draft-heading"}>Corregir borrador</Link>
                  <span>Mantener pospuesto no requiere acción</span>
                </nav>
                <form action={decideLocalDraftRevision} className="review-form">
                  <input type="hidden" name="item_uuid" value={item.uuid} />
                  <input type="hidden" name="draft_id" value={draft.draft_id} />
                  <input type="hidden" name="revision_id" value={revision.revision_id} />
                  <label>
                    Decisión sobre revisión v{revision.version}
                    <select name="decision" defaultValue="approved" required>
                      <option value="approved">Aprobar localmente</option>
                      <option value="rejected">Rechazar revisión</option>
                    </select>
                  </label>
                  <label>Revisor<input name="reviewer" minLength={2} maxLength={120} required /></label>
                  <label className="review-note">Evidencia<textarea name="note" minLength={1} maxLength={2000} required /></label>
                  {revision.validation_snapshot.status === "invalid" ? (
                    <label>
                      <input type="checkbox" name="validation_override" value="true" />
                      Aprobar mediante excepción humana documentada
                    </label>
                  ) : null}
                  <button type="submit">Registrar decisión local</button>
                  <small>No modifica DSpace. Una revisión posterior sustituirá operativamente esta decisión.</small>
                </form>
                {revision.decisions.length ? (
                  <details className="draft-history">
                    <summary>Decisiones de esta revisión ({revision.decisions.length})</summary>
                    <ol>{revision.decisions.toReversed().map((entry) => (
                      <li key={entry.decision_id}>
                        <strong>{entry.decision === "approved" ? "Aprobada" : "Rechazada"}</strong>
                        <p>{entry.note}</p>
                        <small>{entry.reviewer}{entry.validation_override ? " · excepción documentada" : ""}</small>
                      </li>
                    ))}</ol>
                  </details>
                ) : null}
              </article>
            );
          })}
        </div>
      ) : (
        <div className="diagnostic-notice">
          No hay borradores abiertos cuya decisión vigente esté pospuesta.
        </div>
      )}

      <aside className="evidence-caveat">
        <strong>Límite operativo</strong>
        <p>
          Confirmar o descartar registra una nueva decisión humana. Ninguna opción aplica el
          borrador a DSpace.
        </p>
      </aside>
    </main>
  );
}
