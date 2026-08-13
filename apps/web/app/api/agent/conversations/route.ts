import { NextResponse } from "next/server";

import { API_URL } from "@/lib/api";
import { getCatalogReviewToken } from "@/lib/server-secrets";

export const dynamic = "force-dynamic";

export async function POST(request: Request): Promise<Response> {
  const token = getCatalogReviewToken();
  if (!token) {
    return NextResponse.json({ detail: "Local review writes are not configured" }, { status: 503 });
  }

  const body = await request.text();
  const upstream = await fetch(`${API_URL}/api/agent/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Catalog-Review-Token": token },
    body,
    cache: "no-store",
  });

  return new NextResponse(await upstream.text(), {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}
