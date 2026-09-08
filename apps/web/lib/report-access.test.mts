import assert from "node:assert/strict";
import test from "node:test";

import {
  configuredWebOrigin,
  hasValidReportAccessConfiguration,
  isAccessRequestFromConfiguredOrigin,
  isTrustedReportDownloadRequest,
  issueReportAccessCookie,
  verifyReportAccessCookie,
} from "./report-access.ts";

const REPORT_TOKEN = "r".repeat(32);
const REVIEW_TOKEN = "v".repeat(32);

test("the report access secret must be distinct and at least 32 UTF-8 bytes", () => {
  assert.equal(hasValidReportAccessConfiguration(REPORT_TOKEN, REVIEW_TOKEN), true);
  assert.equal(hasValidReportAccessConfiguration("short", REVIEW_TOKEN), false);
  assert.equal(hasValidReportAccessConfiguration(REPORT_TOKEN, REPORT_TOKEN), false);
});

test("a signed report cookie expires and rejects tampering", () => {
  const cookie = issueReportAccessCookie(REPORT_TOKEN, 1_000);
  assert.equal(verifyReportAccessCookie(cookie, REPORT_TOKEN, 1_600), true);
  assert.equal(verifyReportAccessCookie(cookie, REPORT_TOKEN, 1_601), false);
  assert.equal(verifyReportAccessCookie(`${cookie}x`, REPORT_TOKEN, 1_000), false);
  assert.equal(verifyReportAccessCookie(cookie, REVIEW_TOKEN, 1_000), false);
});

test("only the configured origin can issue access and download requests are same-origin", () => {
  const origin = configuredWebOrigin("http://localhost:3000");
  assert.equal(origin, "http://localhost:3000");
  assert.equal(configuredWebOrigin("http://localhost:3000/path"), undefined);
  assert.equal(isAccessRequestFromConfiguredOrigin(new Headers({ Origin: origin }), origin!), true);
  assert.equal(isAccessRequestFromConfiguredOrigin(new Headers({ Origin: "https://evil.example" }), origin!), false);
  assert.equal(
    isTrustedReportDownloadRequest(new Headers({ "Sec-Fetch-Site": "same-origin", Origin: origin }), origin!),
    true,
  );
  assert.equal(
    isTrustedReportDownloadRequest(new Headers({ "Sec-Fetch-Site": "same-site" }), origin!),
    false,
  );
  assert.equal(
    isTrustedReportDownloadRequest(new Headers({ "Sec-Fetch-Site": "same-origin", Origin: "https://evil.example" }), origin!),
    false,
  );
});
