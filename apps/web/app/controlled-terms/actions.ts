"use server";

import { randomUUID } from "node:crypto";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { API_URL } from "@/lib/api";
import { getCatalogReviewToken } from "@/lib/server-secrets";

const CONTROLLED_FIELDS = new Set([
  "dc.subject.linguisticFamily",
  "dc.subject.linguisticBranch",
  "dc.subject.linguiscgroup",
  "dc.description.registeredLanguage",
]);

function value(formData: FormData, key: string): string {
  const candidate = formData.get(key);
  return typeof candidate === "string" ? candidate.trim() : "";
}

export async function recordVocabularyRevision(formData: FormData): Promise<never> {
  const field = value(formData, "field");
  const name = value(formData, "name");
  const sourceUri = value(formData, "source_uri");
  const versionLabel = value(formData, "version_label");
  const approvedBy = value(formData, "approved_by");
  const approvalNote = value(formData, "approval_note");
  const terms = value(formData, "terms")
    .split("\n")
    .map((term) => term.trim())
    .filter(Boolean);
  let outcome = "error";

  if (
    CONTROLLED_FIELDS.has(field) &&
    name.length >= 2 &&
    sourceUri.length >= 3 &&
    versionLabel.length >= 1 &&
    approvedBy.length >= 2 &&
    approvalNote.length >= 1 &&
    terms.length >= 1 &&
    terms.length <= 5000
  ) {
    const token = getCatalogReviewToken();
    if (!token) {
      outcome = "unavailable";
    } else {
      try {
        const response = await fetch(`${API_URL}/api/controlled-vocabularies`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Catalog-Review-Token": token,
          },
          body: JSON.stringify({
            request_id: randomUUID(),
            field,
            name,
            source_uri: sourceUri,
            version_label: versionLabel,
            approved_by: approvedBy,
            approval_note: approvalNote,
            terms: terms.map((term) => ({
              value: term,
              authority: null,
              language: null,
            })),
          }),
          cache: "no-store",
        });
        outcome = response.ok ? "saved" : response.status === 409 ? "conflict" : "error";
      } catch {
        outcome = "error";
      }
    }
  }

  if (outcome === "saved") {
    revalidatePath("/controlled-terms");
  }
  redirect(`/controlled-terms?save=${outcome}`);
}

export async function promoteDSpaceVocabulary(formData: FormData): Promise<never> {
  const vocabularyId = value(formData, "vocabulary_id");
  const approvedBy = value(formData, "approved_by");
  const approvalNote = value(formData, "approval_note");
  const collisionChoices = formData.getAll("collision_choice").filter((choice): choice is string => typeof choice === "string");
  let outcome = "error";
  const token = getCatalogReviewToken();
  if (!token) outcome = "unavailable";
  else if (vocabularyId && approvedBy.length >= 2 && approvalNote) {
    try {
      const response = await fetch(`${API_URL}/api/dspace-vocabularies/${encodeURIComponent(vocabularyId)}/promotions`, {
        method: "POST", headers: { "Content-Type": "application/json", "X-Catalog-Review-Token": token },
        body: JSON.stringify({ request_id: randomUUID(), approved_by: approvedBy, approval_note: approvalNote, collision_choices: collisionChoices }), cache: "no-store",
      });
      outcome = response.ok ? "saved" : response.status === 422 ? "blocked" : "error";
    } catch { outcome = "error"; }
  }
  if (outcome === "saved") revalidatePath("/controlled-terms");
  redirect(`/controlled-terms/dspace/${encodeURIComponent(vocabularyId)}?promotion=${outcome}`);
}
