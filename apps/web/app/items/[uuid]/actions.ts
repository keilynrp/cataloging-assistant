"use server";

import { randomUUID } from "node:crypto";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";

import { API_URL } from "@/lib/api";
import { getCatalogReviewToken } from "@/lib/server-secrets";

const DECISIONS = new Set(["confirmed", "dismissed", "deferred"]);
const SUGGESTION_DECISIONS = new Set(["accepted", "corrected", "rejected", "deferred"]);
const LINGUISTIC_FIELDS = [
  "dc.subject.linguisticFamily",
  "dc.subject.linguisticBranch",
  "dc.subject.linguiscgroup",
  "dc.subject.linguisticVariant",
  "dc.description.registeredLanguage",
] as const;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function value(formData: FormData, key: string): string {
  const candidate = formData.get(key);
  return typeof candidate === "string" ? candidate.trim() : "";
}

export async function generateSuggestions(formData: FormData): Promise<never> {
  const itemUuid = value(formData, "item_uuid");
  let outcome = "error";
  if (UUID_PATTERN.test(itemUuid)) {
    const token = getCatalogReviewToken();
    if (!token) outcome = "unavailable";
    else {
      try {
        const response = await fetch(
          `${API_URL}/api/items/${encodeURIComponent(itemUuid)}/suggestions/generate`,
          { method: "POST", headers: { "X-Catalog-Review-Token": token }, cache: "no-store" },
        );
        outcome = response.ok ? "saved" : "error";
      } catch {
        outcome = "error";
      }
    }
  }
  if (outcome === "saved") {
    revalidatePath(`/items/${itemUuid}`);
    revalidatePath("/work-queue");
  }
  redirect(`/items/${encodeURIComponent(itemUuid)}?suggestions=${outcome}`);
}

export async function recordSuggestionDecision(formData: FormData): Promise<never> {
  const itemUuid = value(formData, "item_uuid");
  const suggestionId = value(formData, "suggestion_id");
  const decision = value(formData, "decision");
  const correctedValue = value(formData, "corrected_value");
  const reviewer = value(formData, "reviewer");
  const note = value(formData, "note");
  let outcome = "error";
  if (
    UUID_PATTERN.test(itemUuid) && UUID_PATTERN.test(suggestionId) &&
    SUGGESTION_DECISIONS.has(decision) && (decision !== "corrected" || correctedValue.length > 0) &&
    reviewer.length >= 2 && reviewer.length <= 120 && note.length >= 1 && note.length <= 2000
  ) {
    const token = getCatalogReviewToken();
    if (!token) outcome = "unavailable";
    else {
      try {
        const response = await fetch(
          `${API_URL}/api/suggestions/${encodeURIComponent(suggestionId)}/decisions`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-Catalog-Review-Token": token },
            body: JSON.stringify({
              request_id: randomUUID(), decision,
              corrected_value: decision === "corrected" ? correctedValue : null,
              reviewer, note,
            }),
            cache: "no-store",
          },
        );
        outcome = response.ok ? "saved" : response.status === 409 ? "conflict" : "error";
      } catch {
        outcome = "error";
      }
    }
  }
  if (outcome === "saved") {
    revalidatePath(`/items/${itemUuid}`);
    revalidatePath("/work-queue");
  }
  redirect(`/items/${encodeURIComponent(itemUuid)}?suggestionDecision=${outcome}`);
}

export async function recordReviewDecision(formData: FormData): Promise<never> {
  const itemUuid = value(formData, "item_uuid");
  const findingId = value(formData, "finding_id");
  const decision = value(formData, "decision");
  const reviewer = value(formData, "reviewer");
  const note = value(formData, "note");
  let outcome = "error";

  if (
    UUID_PATTERN.test(itemUuid) &&
    UUID_PATTERN.test(findingId) &&
    DECISIONS.has(decision) &&
    reviewer.length >= 2 &&
    reviewer.length <= 120 &&
    note.length >= 1 &&
    note.length <= 2000
  ) {
    const token = getCatalogReviewToken();
    if (!token) {
      outcome = "unavailable";
    } else {
      try {
        const response = await fetch(
          `${API_URL}/api/items/${encodeURIComponent(itemUuid)}/findings/${encodeURIComponent(findingId)}/decisions`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-Catalog-Review-Token": token,
            },
            body: JSON.stringify({
              request_id: randomUUID(),
              decision,
              reviewer,
              note,
            }),
            cache: "no-store",
          },
        );
        outcome = response.ok ? "saved" : "error";
      } catch {
        outcome = "error";
      }
    }
  }

  if (outcome === "saved") {
    revalidatePath(`/items/${itemUuid}`);
  }
  redirect(`/items/${encodeURIComponent(itemUuid)}?review=${outcome}`);
}


export async function recordLocalDraft(formData: FormData): Promise<never> {
  const itemUuid = value(formData, "item_uuid");
  const draftId = value(formData, "draft_id");
  const expectedVersion = Number(value(formData, "expected_version"));
  const author = value(formData, "author");
  const note = value(formData, "note");
  const changes = Object.fromEntries(
    LINGUISTIC_FIELDS.map((field) => [
      field,
      value(formData, field)
        .split("\n")
        .map((entry) => entry.trim())
        .filter(Boolean),
    ]),
  );
  let outcome = "error";

  if (
    UUID_PATTERN.test(itemUuid) &&
    (!draftId || UUID_PATTERN.test(draftId)) &&
    (!draftId || Number.isInteger(expectedVersion)) &&
    author.length >= 2 &&
    author.length <= 120 &&
    note.length >= 1 &&
    note.length <= 2000
  ) {
    const token = getCatalogReviewToken();
    if (!token) {
      outcome = "unavailable";
    } else {
      const path = draftId
        ? `/api/items/${encodeURIComponent(itemUuid)}/drafts/${encodeURIComponent(draftId)}/revisions`
        : `/api/items/${encodeURIComponent(itemUuid)}/drafts`;
      try {
        const response = await fetch(`${API_URL}${path}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Catalog-Review-Token": token,
          },
          body: JSON.stringify({
            request_id: randomUUID(),
            author,
            note,
            changes,
            ...(draftId ? { expected_version: expectedVersion } : {}),
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
    revalidatePath(`/items/${itemUuid}`);
  }
  redirect(`/items/${encodeURIComponent(itemUuid)}?draft=${outcome}`);
}

export async function decideLocalDraftRevision(formData: FormData): Promise<never> {
  const itemUuid = value(formData, "item_uuid");
  const draftId = value(formData, "draft_id");
  const revisionId = value(formData, "revision_id");
  const decision = value(formData, "decision");
  const reviewer = value(formData, "reviewer");
  const note = value(formData, "note");
  const validationOverride = value(formData, "validation_override") === "true";
  let outcome = "error";

  if (
    UUID_PATTERN.test(itemUuid) &&
    UUID_PATTERN.test(draftId) &&
    UUID_PATTERN.test(revisionId) &&
    ["approved", "rejected"].includes(decision) &&
    reviewer.length >= 2 &&
    reviewer.length <= 120 &&
    note.length >= 1 &&
    note.length <= 2000
  ) {
    const token = getCatalogReviewToken();
    if (!token) outcome = "unavailable";
    else {
      try {
        const response = await fetch(
          `${API_URL}/api/items/${encodeURIComponent(itemUuid)}/drafts/${encodeURIComponent(draftId)}/decisions`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-Catalog-Review-Token": token,
            },
            body: JSON.stringify({
              request_id: randomUUID(),
              revision_id: revisionId,
              decision,
              reviewer,
              note,
              validation_override: validationOverride,
            }),
            cache: "no-store",
          },
        );
        outcome = response.ok
          ? "saved"
          : response.status === 409
            ? "conflict"
            : response.status === 422
              ? "blocked"
              : "error";
      } catch {
        outcome = "error";
      }
    }
  }
  revalidatePath(`/items/${itemUuid}`);
  revalidatePath("/deferred-drafts");
  revalidatePath("/work-queue");
  redirect(`/deferred-drafts?decision=${outcome}`);
}
