"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { API_URL } from "@/lib/api";
import { getCatalogReviewToken } from "@/lib/server-secrets";

function value(formData: FormData, key: string): string {
  const candidate = formData.get(key);
  return typeof candidate === "string" ? candidate.trim() : "";
}

export async function createProviderCredential(formData: FormData): Promise<never> {
  const provider = value(formData, "provider");
  const label = value(formData, "label");
  const model = value(formData, "model");
  const apiKey = value(formData, "api_key");
  const createdBy = value(formData, "created_by");
  const activate = formData.get("activate") === "true";
  let outcome = "invalid";

  if (
    provider &&
    label.length >= 2 &&
    model.length >= 1 &&
    apiKey.length >= 8 &&
    createdBy.length >= 2
  ) {
    const token = getCatalogReviewToken();
    if (!token) {
      outcome = "unavailable";
    } else {
      try {
        const response = await fetch(`${API_URL}/api/agent/settings/credentials`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Catalog-Review-Token": token },
          body: JSON.stringify({
            provider,
            label,
            model,
            api_key: apiKey,
            created_by: createdBy,
            activate,
          }),
          cache: "no-store",
        });
        outcome = response.ok ? "saved" : response.status === 422 ? "invalid" : "error";
      } catch {
        outcome = "error";
      }
    }
  }

  if (outcome === "saved") {
    revalidatePath("/settings");
  }
  redirect(`/settings?save=${outcome}`);
}

async function postCredentialAction(
  formData: FormData,
  buildPath: (id: string) => string,
  successOutcome: string,
): Promise<never> {
  const credentialId = value(formData, "credential_id");
  let outcome = "error";
  const token = getCatalogReviewToken();
  if (!token) {
    outcome = "unavailable";
  } else if (credentialId) {
    try {
      const response = await fetch(`${API_URL}${buildPath(credentialId)}`, {
        method: "POST",
        headers: { "X-Catalog-Review-Token": token },
        cache: "no-store",
      });
      outcome = response.ok ? successOutcome : "error";
    } catch {
      outcome = "error";
    }
  }
  if (outcome === successOutcome) {
    revalidatePath("/settings");
  }
  redirect(`/settings?save=${outcome}`);
}

export async function activateProviderCredential(formData: FormData): Promise<never> {
  return postCredentialAction(
    formData,
    (id) => `/api/agent/settings/credentials/${encodeURIComponent(id)}/activate`,
    "activated",
  );
}

export async function deactivateProviderCredential(formData: FormData): Promise<never> {
  return postCredentialAction(
    formData,
    (id) => `/api/agent/settings/credentials/${encodeURIComponent(id)}/deactivate`,
    "deactivated",
  );
}

export async function deleteProviderCredential(formData: FormData): Promise<never> {
  const credentialId = value(formData, "credential_id");
  let outcome = "error";
  const token = getCatalogReviewToken();
  if (!token) {
    outcome = "unavailable";
  } else if (credentialId) {
    try {
      const response = await fetch(
        `${API_URL}/api/agent/settings/credentials/${encodeURIComponent(credentialId)}`,
        {
          method: "DELETE",
          headers: { "X-Catalog-Review-Token": token },
          cache: "no-store",
        },
      );
      outcome = response.ok ? "deleted" : "error";
    } catch {
      outcome = "error";
    }
  }
  if (outcome === "deleted") {
    revalidatePath("/settings");
  }
  redirect(`/settings?save=${outcome}`);
}
