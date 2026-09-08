import Link from "next/link";
import { notFound } from "next/navigation";

import { getItem } from "@/lib/api";
import { getCatalogingContract } from "@/lib/cataloging-contract";
import { getEvidenceSession } from "@/lib/evidence";
import { EvidenceWorkspace } from "./evidence-workspace";
import { COPY_MESSAGES, EXTRACT_MESSAGES, PDF_MESSAGES, REMOTE_MESSAGES } from "./status-messages";
import styles from "./workspace.module.css";

const messages = { extract: EXTRACT_MESSAGES, copy: COPY_MESSAGES, pdf: PDF_MESSAGES, remote: REMOTE_MESSAGES };

export default async function EvidenceSessionPage({
  params, searchParams,
}: {
  params: Promise<{ sessionId: string }>;
  searchParams: Promise<{ extract?: string; copy?: string; pdf?: string; remote?: string }>;
}) {
  const { sessionId } = await params;
  const query = await searchParams;
  const [sessionResult, contractResult] = await Promise.allSettled([
    getEvidenceSession(sessionId), getCatalogingContract(),
  ]);
  if (sessionResult.status === "rejected") notFound();
  const evidence = sessionResult.value;
  const contract = contractResult.status === "fulfilled" ? contractResult.value : null;
  const draftableFields = new Set(contract?.runtime.draftable_fields ?? []);
  const copyableCandidateIds = evidence.candidates.filter(candidate =>
    draftableFields.has(candidate.metadata_field) && candidate.validation_json.status !== "invalid",
  ).map(candidate => candidate.candidate_id);
  const item = evidence.item_uuid ? await getItem(evidence.item_uuid).catch(() => null) : null;
  const draft = item?.drafts[0] ?? null;
  const revision = draft?.revisions.at(-1) ?? null;

  return (
    <div className={styles.workspace} data-evidence-workspace>
      <Link href="/evidence" className={styles.back}>← Nueva sesión</Link>
      {(Object.keys(messages) as Array<keyof typeof messages>).map(kind => {
        const value = query[kind];
        const message = value && (messages[kind][value] ?? (kind === "remote" ? REMOTE_MESSAGES.error : null));
        return message ? <p key={kind} role="status" className={styles.notice}>{message}</p> : null;
      })}
      {!contract ? <p role="status" className={styles.notice}>El contrato maestro no está disponible; la copia queda bloqueada.</p> : null}
      <EvidenceWorkspace
        key={evidence.session_id + ":" + evidence.stale}
        evidence={evidence}
        title={item?.name ?? "Sesión de evidencia"}
        bindingLabels={Object.fromEntries(contract?.fields.map(field => [field.binding_id, field.assistant_label]) ?? [])}
        copyableCandidateIds={copyableCandidateIds}
        localDraft={draft ? { draft_id: draft.draft_id } : null}
        expectedVersion={revision?.version ?? null}
      />
    </div>
  );
}
