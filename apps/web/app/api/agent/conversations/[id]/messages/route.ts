import { NextResponse } from "next/server";

import { API_URL } from "@/lib/api";
import { getCatalogReviewToken } from "@/lib/server-secrets";

export const dynamic = "force-dynamic";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
): Promise<Response> {
  const { id } = await params;
  const token = getCatalogReviewToken();
  if (!token) {
    return NextResponse.json({ detail: "Local review writes are not configured" }, { status: 503 });
  }

  const body = await request.text();
  const upstream = await fetch(
    `${API_URL}/api/agent/conversations/${encodeURIComponent(id)}/messages`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Catalog-Review-Token": token },
      body,
      cache: "no-store",
    },
  );

  if (!upstream.body) {
    return new NextResponse(await upstream.text(), { status: upstream.status });
  }

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
