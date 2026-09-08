import { NextRequest, NextResponse } from "next/server";

import {
  configuredWebOrigin,
  constantTimeEqualText,
  hasValidReportAccessConfiguration,
  isAccessRequestFromConfiguredOrigin,
  issueReportAccessCookie,
  REPORT_ACCESS_COOKIE,
  REPORT_ACCESS_MAX_AGE_SECONDS,
  REPORT_ACCESS_PATH,
} from "@/lib/report-access";
import {
  getCatalogReportAccessToken,
  getCatalogReviewToken,
  getCatalogWebOrigin,
} from "@/lib/server-secrets";

export const dynamic = "force-dynamic";

function response(detail: string, status: number): NextResponse {
  return NextResponse.json(
    { detail },
    { status, headers: { "Cache-Control": "no-store", Vary: "Origin" } },
  );
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  const reportAccessToken = getCatalogReportAccessToken();
  const reviewToken = getCatalogReviewToken();
  const webOrigin = configuredWebOrigin(getCatalogWebOrigin());
  if (!webOrigin || !hasValidReportAccessConfiguration(reportAccessToken, reviewToken)) {
    return response("Report access is not configured", 503);
  }
  if (!isAccessRequestFromConfiguredOrigin(request.headers, webOrigin)) {
    return response("Report access is required", 401);
  }
  if (!request.headers.get("content-type")?.toLowerCase().startsWith("application/json")) {
    return response("Expected a JSON request body", 415);
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return response("Invalid JSON request body", 400);
  }
  const suppliedToken =
    body && typeof body === "object" && typeof (body as Record<string, unknown>).token === "string"
      ? (body as Record<string, string>).token
      : "";
  if (!constantTimeEqualText(suppliedToken, reportAccessToken)) {
    return response("Report access is required", 401);
  }

  const granted = response("Report access granted", 200);
  granted.cookies.set(REPORT_ACCESS_COOKIE, issueReportAccessCookie(reportAccessToken), {
    httpOnly: true,
    sameSite: "strict",
    secure: process.env.NODE_ENV === "production",
    path: REPORT_ACCESS_PATH,
    maxAge: REPORT_ACCESS_MAX_AGE_SECONDS,
  });
  return granted;
}
