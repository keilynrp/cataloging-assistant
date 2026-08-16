import { API_URL, PUBLIC_API_URL } from "@/lib/api";

export type EvidenceSource = {
  source_id: string;
  kind: string;
  locator: string | null;
  content_hash: string;
  media_type: string | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
};

export type EvidenceCandidate = {
  candidate_id: string;
  source_id: string;
  metadata_field: string;
  value: string;
  evidence_state: string;
  evidence_json: Record<string, unknown>;
  validation_json: Record<string, unknown>;
  created_at: string;
};

export type EvidenceSession = {
  session_id: string;
  item_uuid: string | null;
  base_source_hash: string | null;
  contract_version: string;
  created_by: string;
  created_at: string;
  stale: boolean;
  sources: EvidenceSource[];
  candidates: EvidenceCandidate[];
};

async function fetchEvidence(baseUrl: string, sessionId: string): Promise<EvidenceSession> {
  const response = await fetch(
    `${baseUrl}/api/evidence-sessions/${encodeURIComponent(sessionId)}`,
    { cache: "no-store" },
  );
  if (!response.ok) throw new Error(`Evidence API returned ${response.status}`);
  return response.json() as Promise<EvidenceSession>;
}

export function getEvidenceSession(sessionId: string): Promise<EvidenceSession> {
  return fetchEvidence(API_URL, sessionId);
}

export function getPublicEvidenceSession(sessionId: string): Promise<EvidenceSession> {
  return fetchEvidence(PUBLIC_API_URL, sessionId);
}
