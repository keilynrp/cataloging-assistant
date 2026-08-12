import { NextResponse } from "next/server";

import { API_URL } from "@/lib/api";
import { getCatalogReviewToken } from "@/lib/server-secrets";

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
): Promise<NextResponse> {
  const { id } = await params;
  const token = getCatalogReviewToken();
  if (!token) {
    return NextResponse.json({ detail: "Local review writes are not configured" }, { status: 503 });
  }
  const response = await fetch(`${API_URL}/api/notifications/${encodeURIComponent(id)}/archive`, {
    method: "POST",
    headers: { "X-Catalog-Review-Token": token },
    cache: "no-store",
  });
  const body = await response.text();
  return new NextResponse(body, {
    status: response.status,
    headers: { "Content-Type": "application/json" },
  });
}
