"use server";

import { randomUUID } from "node:crypto";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { API_URL } from "@/lib/api";
import { getCatalogReviewToken } from "@/lib/server-secrets";

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function value(formData: FormData, key: string): string {
  const candidate = formData.get(key);
  return typeof candidate === "string" ? candidate.trim() : "";
}

export async function createEvidenceSession(formData: FormData): Promise<never> {
  const createdBy = value(formData, "created_by");
  const itemUuid = value(formData, "item_uuid");
  const url = value(formData, "url");
  const text = value(formData, "text");
  const token = getCatalogReviewToken();

  if (!token) redirect("/evidence?create=unavailable");
  if (createdBy.length < 2 || (!url && !text)) redirect("/evidence?create=invalid");
  if (itemUuid && !UUID_PATTERN.test(itemUuid)) redirect("/evidence?create=invalid");

  let sessionId: string | null = null;
  let outcome = "error";
  try {
    const response = await fetch(`${API_URL}/api/evidence-sessions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Catalog-Review-Token": token,
      },
      body: JSON.stringify({
        item_uuid: itemUuid || null,
        created_by: createdBy,
        url: url || null,
        text: text || null,
      }),
      cache: "no-store",
    });
    if (response.ok) {
      const payload = (await response.json()) as { session_id: string };
      sessionId = payload.session_id;
      outcome = "saved";
    } else {
      outcome = response.status === 422 ? "invalid" : "error";
    }
  } catch {
    outcome = "error";
  }

  if (outcome === "saved" && sessionId) {
    redirect(`/evidence/${encodeURIComponent(sessionId)}`);
  }
  redirect(`/evidence?create=${outcome}`);
}

export async function uploadPdfEvidence(formData: FormData): Promise<never> {
  const sessionId = value(formData, "session_id");
  const author = value(formData, "author");
  const file = formData.get("file");
  const token = getCatalogReviewToken();

  if (!token) redirect(`/evidence/${encodeURIComponent(sessionId)}?pdf=unavailable`);
  if (
    !UUID_PATTERN.test(sessionId) ||
    author.length < 2 ||
    author.length > 120 ||
    !(file instanceof File) ||
    file.size === 0
  ) {
    redirect(`/evidence/${encodeURIComponent(sessionId)}?pdf=invalid`);
  }

  let outcome = "error";
  try {
    const upload = new FormData();
    upload.append("file", file, file.name);
    upload.append("author", author);
    const response = await fetch(
      `${API_URL}/api/evidence-sessions/${encodeURIComponent(sessionId)}/sources/pdf`,
      {
        method: "POST",
        headers: { "X-Catalog-Review-Token": token },
        body: upload,
        cache: "no-store",
      },
    );
    outcome = response.ok
      ? "saved"
      : response.status === 413
        ? "too_large"
        : response.status === 415
          ? "invalid_type"
          : response.status === 409
            ? "stale"
            : response.status === 422
              ? "rejected"
              : "error";
  } catch {
    outcome = "error";
  }

  if (outcome === "saved") revalidatePath(`/evidence/${sessionId}`);
  redirect(`/evidence/${encodeURIComponent(sessionId)}?pdf=${outcome}`);
}

export async function extractEvidence(formData: FormData): Promise<never> {
  const sessionId = value(formData, "session_id");
  const token = getCatalogReviewToken();
  if (!token) redirect(`/evidence/${encodeURIComponent(sessionId)}?extract=unavailable`);
  if (!UUID_PATTERN.test(sessionId)) redirect("/evidence?create=invalid");

  let outcome = "error";
  try {
    const response = await fetch(
      `${API_URL}/api/evidence-sessions/${encodeURIComponent(sessionId)}/extract`,
      {
        method: "POST",
        headers: { "X-Catalog-Review-Token": token },
        cache: "no-store",
      },
    );
    outcome = response.ok ? "saved" : response.status === 409 ? "stale" : "error";
  } catch {
    outcome = "error";
  }
  if (outcome === "saved") revalidatePath(`/evidence/${sessionId}`);
  redirect(`/evidence/${encodeURIComponent(sessionId)}?extract=${outcome}`);
}

export async function copyEvidenceToDraft(formData: FormData): Promise<never> {
  const sessionId = value(formData, "session_id");
  const itemUuid = value(formData, "item_uuid");
  const author = value(formData, "author");
  const note = value(formData, "note");
  const draftId = value(formData, "draft_id");
  const expectedVersionRaw = value(formData, "expected_version");
  const candidateIds = formData
    .getAll("candidate_id")
    .filter((candidate): candidate is string => typeof candidate === "string")
    .filter((candidate) => UUID_PATTERN.test(candidate));
  const token = getCatalogReviewToken();

  if (!token) redirect(`/evidence/${encodeURIComponent(sessionId)}?copy=unavailable`);
  if (!UUID_PATTERN.test(sessionId) || !UUID_PATTERN.test(itemUuid) || candidateIds.length === 0) {
    redirect(`/evidence/${encodeURIComponent(sessionId)}?copy=invalid`);
  }

  let outcome = "error";
  try {
    const response = await fetch(
      `${API_URL}/api/evidence-sessions/${encodeURIComponent(sessionId)}/copy-to-draft`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Catalog-Review-Token": token,
        },
        body: JSON.stringify({
          request_id: randomUUID(),
          candidate_ids: candidateIds,
          author,
          note,
          draft_id: draftId || null,
          expected_version: draftId && expectedVersionRaw ? Number(expectedVersionRaw) : null,
        }),
        cache: "no-store",
      },
    );
    outcome = response.ok
      ? "saved"
      : response.status === 409
        ? "conflict"
        : response.status === 422
          ? "invalid"
          : "error";
  } catch {
    outcome = "error";
  }

  if (outcome === "saved") {
    revalidatePath(`/items/${itemUuid}`);
    revalidatePath(`/evidence/${sessionId}`);
  }
  redirect(`/evidence/${encodeURIComponent(sessionId)}?copy=${outcome}`);
}
