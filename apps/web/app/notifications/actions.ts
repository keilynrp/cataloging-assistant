"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";

import { API_URL } from "@/lib/api";
import { getCatalogReviewToken } from "@/lib/server-secrets";

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function value(formData: FormData, key: string): string {
  const candidate = formData.get(key);
  return typeof candidate === "string" ? candidate.trim() : "";
}

async function post(path: string): Promise<boolean> {
  const token = getCatalogReviewToken();
  if (!token) return false;
  try {
    const response = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: { "X-Catalog-Review-Token": token },
      cache: "no-store",
    });
    return response.ok;
  } catch {
    return false;
  }
}

export async function markNotificationRead(formData: FormData): Promise<never> {
  const id = value(formData, "notification_id");
  const back = value(formData, "back") || "/notifications";
  const outcome = UUID_PATTERN.test(id) ? (await post(`/api/notifications/${id}/read`)) : false;
  revalidatePath("/notifications");
  redirect(`${back}${back.includes("?") ? "&" : "?"}notification=${outcome ? "saved" : "error"}`);
}

export async function archiveNotification(formData: FormData): Promise<never> {
  const id = value(formData, "notification_id");
  const back = value(formData, "back") || "/notifications";
  const outcome = UUID_PATTERN.test(id) ? (await post(`/api/notifications/${id}/archive`)) : false;
  revalidatePath("/notifications");
  redirect(`${back}${back.includes("?") ? "&" : "?"}notification=${outcome ? "saved" : "error"}`);
}

export async function markAllNotificationsRead(formData: FormData): Promise<never> {
  const back = value(formData, "back") || "/notifications";
  const outcome = await post("/api/notifications/read-all");
  revalidatePath("/notifications");
  redirect(`${back}${back.includes("?") ? "&" : "?"}notification=${outcome ? "saved" : "error"}`);
}
