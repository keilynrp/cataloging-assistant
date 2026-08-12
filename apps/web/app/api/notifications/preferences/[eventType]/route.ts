import { NextResponse } from "next/server";

import { API_URL } from "@/lib/api";
import { getCatalogReviewToken } from "@/lib/server-secrets";

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ eventType: string }> },
): Promise<NextResponse> {
  const { eventType } = await params;
  const token = getCatalogReviewToken();
  if (!token) {
    return NextResponse.json({ detail: "Local review writes are not configured" }, { status: 503 });
  }
  const body = await request.text();
  const response = await fetch(
    `${API_URL}/api/notifications/preferences/${encodeURIComponent(eventType)}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json", "X-Catalog-Review-Token": token },
      body,
      cache: "no-store",
    },
  );
  const responseBody = await response.text();
  return new NextResponse(responseBody, {
    status: response.status,
    headers: { "Content-Type": "application/json" },
  });
}
