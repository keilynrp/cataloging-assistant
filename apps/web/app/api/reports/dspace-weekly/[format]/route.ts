import { NextResponse } from "next/server";

import { API_URL } from "@/lib/api";
import { getCatalogReviewToken } from "@/lib/server-secrets";

const REPORT_FORMATS = new Set(["csv", "xlsx", "pdf"]);

export const dynamic = "force-dynamic";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ format: string }> },
): Promise<Response> {
  const { format } = await params;
  if (!REPORT_FORMATS.has(format)) {
    return NextResponse.json({ detail: "Unsupported report format" }, { status: 404 });
  }

  const token = getCatalogReviewToken();
  if (!token) {
    return NextResponse.json({ detail: "Local review access is not configured" }, { status: 503 });
  }

  const requestUrl = new URL(request.url);
  const query = new URLSearchParams();
  for (const parameter of ["from", "to"]) {
    const value = requestUrl.searchParams.get(parameter);
    if (value !== null) query.set(parameter, value);
  }
  const upstream = await fetch(
    `${API_URL}/api/reports/dspace-weekly.${format}?${query.toString()}`,
    {
      headers: { "X-Catalog-Review-Token": token },
      cache: "no-store",
    },
  );

  const headers = new Headers({ "Cache-Control": "no-store" });
  for (const header of ["Content-Type", "Content-Disposition"]) {
    const value = upstream.headers.get(header);
    if (value) headers.set(header, value);
  }
  return new NextResponse(await upstream.arrayBuffer(), {
    status: upstream.status,
    headers,
  });
}
