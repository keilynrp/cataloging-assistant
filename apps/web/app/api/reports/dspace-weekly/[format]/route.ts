import { NextRequest, NextResponse } from "next/server";

import { API_URL } from "@/lib/api";
import {
  configuredWebOrigin,
  hasValidReportAccessConfiguration,
  isTrustedReportDownloadRequest,
  REPORT_ACCESS_COOKIE,
  verifyReportAccessCookie,
} from "@/lib/report-access";
import {
  getCatalogReportAccessToken,
  getCatalogReviewToken,
  getCatalogWebOrigin,
} from "@/lib/server-secrets";

const REPORT_FORMATS = new Set(["csv", "xlsx", "pdf"]);

export const dynamic = "force-dynamic";

function noStoreHeaders(): Headers {
  return new Headers({
    "Cache-Control": "no-store",
    Vary: "Sec-Fetch-Site, Origin",
  });
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ format: string }> },
): Promise<Response> {
  const { format } = await params;
  if (!REPORT_FORMATS.has(format)) {
    return NextResponse.json({ detail: "Unsupported report format" }, { status: 404, headers: noStoreHeaders() });
  }

  const reviewToken = getCatalogReviewToken();
  const reportAccessToken = getCatalogReportAccessToken();
  const webOrigin = configuredWebOrigin(getCatalogWebOrigin());
  if (!webOrigin || !reviewToken || !hasValidReportAccessConfiguration(reportAccessToken, reviewToken)) {
    return NextResponse.json({ detail: "Report access is not configured" }, { status: 503, headers: noStoreHeaders() });
  }
  if (
    !isTrustedReportDownloadRequest(request.headers, webOrigin) ||
    !verifyReportAccessCookie(request.cookies.get(REPORT_ACCESS_COOKIE)?.value, reportAccessToken)
  ) {
    return NextResponse.json({ detail: "Report access is required" }, { status: 401, headers: noStoreHeaders() });
  }

  const requestUrl = new URL(request.url);
  const query = new URLSearchParams();
  for (const parameter of ["from", "to"]) {
    const value = requestUrl.searchParams.get(parameter);
    if (value !== null) query.set(parameter, value);
  }
  let upstream: Response;
  try {
    upstream = await fetch(
      `${API_URL}/api/reports/dspace-weekly.${format}?${query.toString()}`,
      {
        headers: { "X-Catalog-Review-Token": reviewToken },
        cache: "no-store",
      },
    );
  } catch {
    return NextResponse.json({ detail: "Report service is unavailable" }, { status: 502, headers: noStoreHeaders() });
  }

  const headers = noStoreHeaders();
  for (const header of ["Content-Type", "Content-Disposition"]) {
    const value = upstream.headers.get(header);
    if (value) headers.set(header, value);
  }
  return new NextResponse(await upstream.arrayBuffer(), {
    status: upstream.status,
    headers,
  });
}
