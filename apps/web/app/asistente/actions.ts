"use server";

import { redirect } from "next/navigation";

import { API_URL } from "@/lib/api";
import { getCatalogReviewToken } from "@/lib/server-secrets";

function value(formData: FormData, key: string): string {
  const candidate = formData.get(key);
  return typeof candidate === "string" ? candidate.trim() : "";
}

export async function startConversation(formData: FormData): Promise<never> {
  const startedBy = value(formData, "started_by");
  let outcome = "error";
  let conversationId = "";

  if (startedBy.length >= 2 && startedBy.length <= 120) {
    const token = getCatalogReviewToken();
    if (!token) {
      outcome = "unavailable";
    } else {
      try {
        const response = await fetch(`${API_URL}/api/agent/conversations`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Catalog-Review-Token": token },
          body: JSON.stringify({ started_by: startedBy }),
          cache: "no-store",
        });
        if (response.ok) {
          const conversation = await response.json();
          conversationId = conversation.conversation_id;
          outcome = "saved";
        } else if (response.status === 503) {
          outcome = "unavailable";
        }
      } catch {
        outcome = "error";
      }
    }
  }

  if (outcome === "saved" && conversationId) {
    redirect(`/asistente/${conversationId}`);
  }
  redirect(`/asistente?error=${outcome}`);
}
