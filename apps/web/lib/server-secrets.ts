import "server-only";

export function getCatalogReviewToken(): string | undefined {
  const key = ["CATALOG", "REVIEW", "TOKEN"].join("_");
  const value = process.env[key]?.trim();
  return value || undefined;
}

export function getCatalogReportAccessToken(): string | undefined {
  const key = ["CATALOG", "REPORT", "ACCESS", "TOKEN"].join("_");
  const value = process.env[key]?.trim();
  return value || undefined;
}

export function getCatalogWebOrigin(): string | undefined {
  const key = ["CATALOG", "WEB", "ORIGIN"].join("_");
  const value = process.env[key]?.trim();
  return value || undefined;
}
