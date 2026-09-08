// Test-only API. Never connects to DSpace or writes production data.
import http from "node:http";

const id = "11111111-1111-4111-8111-111111111111";
const sourceId = "22222222-2222-4222-8222-222222222222";
const candidateIds = [1, 2, 3].map(n => "33333333-3333-4333-8333-" + String(n).padStart(12, "0"));
const candidate = (index, field, binding, value, status) => ({
  candidate_id: candidateIds[index], source_id: sourceId, binding_id: binding,
  metadata_field: field, value, evidence_state: "EXTRAÍDO",
  evidence_json: { kind: "explicit_contract_line", page: 7, line: 42, quote: "Familia: Maya", extractor: "fixture@1" },
  validation_json: { status, vocabulary_revision: "fixture-v1" },
  created_at: "2026-09-08T12:00:00Z",
});
const session = {
  session_id: id, item_uuid: id, base_source_hash: "a".repeat(64),
  contract_version: "fixture-v1", created_by: "Catalogador de prueba",
  created_at: "2026-09-08T12:00:00Z", stale: false,
  sources: [{
    source_id: sourceId, kind: "remote", locator: "https://example.test/" + "fuente".repeat(40),
    content_hash: "b".repeat(64), media_type: "application/pdf",
    metadata_json: {}, extraction_status: "extracted", page_count: 8,
    extracted_text_hash: "c".repeat(64), created_at: "2026-09-08T12:00:00Z",
    extraction_metadata_json: { requested_url: "https://example.test/request", final_url: "https://example.test/final", content_length: 12345, fetched_at: "2026-09-08T12:00:00Z", redirect_chain: ["https://example.test/request"], extractor: "fixture@1" },
  }],
  candidates: [
    candidate(0, "dc.subject.linguisticFamily", "linguistic-family", "Maya", "valid"),
    candidate(1, "dc.subject.linguisticFamily", "linguistic-family", "No válido", "invalid"),
    candidate(2, "dc.title", "title", "Título de referencia", "no_vocabulary"),
  ],
};
let lastCopy = null;
const server = http.createServer(async (request, response) => {
  response.setHeader("Access-Control-Allow-Origin", "*");
  response.setHeader("Content-Type", "application/json");
  const url = new URL(request.url, "http://localhost");
  if (url.pathname === "/__copy") return response.end(JSON.stringify(lastCopy));
  if (url.pathname.endsWith("/copy-to-draft")) {
    let body = ""; for await (const chunk of request) body += chunk;
    lastCopy = JSON.parse(body);
    return response.end(JSON.stringify({ saved: true }));
  }
  if (url.pathname === "/api/cataloging-contract") return response.end(JSON.stringify({
    fields: [{ binding_id: "linguistic-family", assistant_label: "Familia lingüística" }, { binding_id: "title", assistant_label: "Título" }],
    runtime: { draftable_fields: ["dc.subject.linguisticFamily"] },
  }));
  if (url.pathname.startsWith("/api/evidence-sessions/")) {
    const mode = url.pathname.split("/").at(-1);
    return response.end(JSON.stringify({
      ...session, stale: mode === "stale",
      ...(mode === "empty" ? { candidates: [], sources: [] } : {}),
      ...(mode === "unlinked" ? { item_uuid: null } : {}),
    }));
  }
  if (url.pathname.startsWith("/api/items/")) return response.end(JSON.stringify({
    uuid: id, name: "Documentación lingüística y evidencia arqueológica del maya",
    drafts: [{ draft_id: "44444444-4444-4444-8444-444444444444", revisions: [{ version: 7 }] }],
  }));
  if (url.pathname.startsWith("/api/notifications")) return response.end(JSON.stringify({ items: [], unread_count: 0, total: 0 }));
  response.statusCode = 404; response.end(JSON.stringify({ detail: "Test endpoint not found" }));
});
server.listen(Number(process.env.FIXTURE_PORT ?? 18081), "127.0.0.1");
