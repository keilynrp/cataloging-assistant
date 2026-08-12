import "server-only";

export function getCatalogReviewToken(): string | undefined {
  const key = ["CATALOG", "REVIEW", "TOKEN"].join("_");
  const value = process.env[key]?.trim();
  return value || undefined;
}
