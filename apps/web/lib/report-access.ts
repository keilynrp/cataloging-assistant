import { createHash, createHmac, randomBytes, timingSafeEqual } from "node:crypto";

export const REPORT_ACCESS_COOKIE = "catalog_report_access";
export const REPORT_ACCESS_PATH = "/api/reports/dspace-weekly";
export const REPORT_ACCESS_MAX_AGE_SECONDS = 10 * 60;

type ReportAccessClaims = {
  version: 1;
  iat: number;
  exp: number;
  nonce: string;
};

function digest(value: string): Buffer {
  return createHash("sha256").update(value, "utf8").digest();
}

export function constantTimeEqualText(left: string, right: string): boolean {
  return timingSafeEqual(digest(left), digest(right));
}

export function hasValidReportAccessConfiguration(
  reportAccessToken: string | undefined,
  reviewToken: string | undefined,
): reportAccessToken is string {
  return Boolean(
    reportAccessToken &&
      reviewToken &&
      Buffer.byteLength(reportAccessToken, "utf8") >= 32 &&
      !constantTimeEqualText(reportAccessToken, reviewToken),
  );
}

export function configuredWebOrigin(value: string | undefined): string | undefined {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    if (
      (url.protocol !== "http:" && url.protocol !== "https:") ||
      url.username ||
      url.password ||
      url.pathname !== "/" ||
      url.search ||
      url.hash
    ) {
      return undefined;
    }
    return url.origin;
  } catch {
    return undefined;
  }
}

function signingKey(reportAccessToken: string): Buffer {
  return createHmac("sha256", reportAccessToken)
    .update("cataloging-assistant/vertical-025/report-access-cookie/v1", "utf8")
    .digest();
}

function sign(encodedClaims: string, reportAccessToken: string): string {
  return createHmac("sha256", signingKey(reportAccessToken))
    .update(encodedClaims, "utf8")
    .digest("base64url");
}

export function issueReportAccessCookie(
  reportAccessToken: string,
  nowSeconds = Math.floor(Date.now() / 1000),
): string {
  const claims: ReportAccessClaims = {
    version: 1,
    iat: nowSeconds,
    exp: nowSeconds + REPORT_ACCESS_MAX_AGE_SECONDS,
    nonce: randomBytes(16).toString("base64url"),
  };
  const encodedClaims = Buffer.from(JSON.stringify(claims), "utf8").toString("base64url");
  return `${encodedClaims}.${sign(encodedClaims, reportAccessToken)}`;
}

function validClaims(value: unknown, nowSeconds: number): value is ReportAccessClaims {
  if (!value || typeof value !== "object") return false;
  const claims = value as Record<string, unknown>;
  return (
    claims.version === 1 &&
    Number.isInteger(claims.iat) &&
    Number.isInteger(claims.exp) &&
    typeof claims.nonce === "string" &&
    claims.nonce.length > 0 &&
    (claims.exp as number) > (claims.iat as number) &&
    (claims.exp as number) - (claims.iat as number) <= REPORT_ACCESS_MAX_AGE_SECONDS &&
    nowSeconds <= (claims.exp as number)
  );
}

export function verifyReportAccessCookie(
  cookieValue: string | undefined,
  reportAccessToken: string,
  nowSeconds = Math.floor(Date.now() / 1000),
): boolean {
  if (!cookieValue) return false;
  const parts = cookieValue.split(".");
  if (parts.length !== 2 || !parts[0] || !parts[1]) return false;

  const [encodedClaims, providedSignature] = parts;
  const expectedSignature = Buffer.from(sign(encodedClaims, reportAccessToken), "base64url");
  const receivedSignature = Buffer.from(providedSignature, "base64url");
  if (
    receivedSignature.length !== expectedSignature.length ||
    !timingSafeEqual(receivedSignature, expectedSignature)
  ) {
    return false;
  }

  try {
    return validClaims(JSON.parse(Buffer.from(encodedClaims, "base64url").toString("utf8")), nowSeconds);
  } catch {
    return false;
  }
}

export function isAccessRequestFromConfiguredOrigin(headers: Headers, webOrigin: string): boolean {
  return headers.get("origin") === webOrigin;
}

export function isTrustedReportDownloadRequest(headers: Headers, webOrigin: string): boolean {
  const origin = headers.get("origin");
  return headers.get("sec-fetch-site") === "same-origin" && (origin === null || origin === webOrigin);
}
