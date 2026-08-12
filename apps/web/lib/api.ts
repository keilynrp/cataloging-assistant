export const API_URL = process.env.CATALOG_API_URL ?? "http://localhost:8000";
// Reachable from the browser: notification reads and the WebSocket connect directly to
// the API (CORS allows GET; mutations are proxied through this app's own /api routes so
// the review token never reaches the client, per VERTICAL-014 principle 8).
export const PUBLIC_API_URL = process.env.NEXT_PUBLIC_CATALOG_API_URL ?? "http://localhost:8000";

export type ItemSummary = {
  uuid: string;
  handle: string | null;
  name: string;
  collection_uuid: string;
  last_modified: string | null;
  is_active: boolean;
};

export type MetadataValue = {
  value: string;
  language: string | null;
  authority: string | null;
  confidence: number | null;
  place: number;
};

export type DraftValidationSnapshot = {
  generated_at: string;
  status: "not_configured" | "valid" | "invalid";
  vocabulary_profile: string[];
  fields: Array<{
    field: string;
    status: "no_vocabulary" | "no_values" | "valid" | "invalid";
    vocabulary: {
      revision_key: string;
      name: string;
      source_uri: string;
      version_label: string;
      approved_by: string;
    } | null;
    values: Array<{
      value: string;
      approved: boolean | null;
    }>;
  }>;
};

export type ItemDetail = ItemSummary & {
  metadata: Record<string, MetadataValue[]>;
  bundles: Array<{
    uuid: string;
    name: string;
    bitstreams: Array<{
      uuid: string;
      name: string;
      mime_type: string | null;
      size_bytes: number | null;
      content_url: string | null;
    }>;
  }>;
  diagnostics: {
    status: "current" | "stale";
    profile_version: string | null;
    evaluated_at: string | null;
    findings: Array<{
      finding_id: string;
      fingerprint: string;
      code: string;
      severity: "error" | "warning" | "suggestion" | "review";
      affected_fields: string[];
      explanation: string;
      rule_version: string;
      detected_at: string;
    }>;
  };
  review_decisions: Array<{
    decision_id: string;
    request_id: string;
    item_uuid: string;
    finding_fingerprint: string;
    finding_code: string;
    finding_severity: string;
    finding_affected_fields: string[];
    finding_explanation: string;
    finding_rule_version: string;
    source_hash: string;
    decision: "confirmed" | "dismissed" | "deferred";
    reviewer: string;
    note: string;
    created_at: string;
  }>;
  drafts: Array<{
    draft_id: string;
    item_uuid: string;
    base_source_hash: string;
    base_metadata: Record<string, MetadataValue[]>;
    status: "open";
    created_by: string;
    created_at: string;
    updated_at: string;
    stale: boolean;
    revisions: Array<{
      revision_id: string;
      request_id: string;
      version: number;
      metadata_patch: Record<string, MetadataValue[]>;
      validation_snapshot: DraftValidationSnapshot;
      author: string;
      note: string;
      created_at: string;
      decisions: Array<{
        decision_id: string;
        request_id: string;
        revision_id: string;
        decision: "approved" | "rejected";
        reviewer: string;
        note: string;
        source_hash: string;
        validation_snapshot: DraftValidationSnapshot;
        validation_override: boolean;
        created_at: string;
      }>;
    }>;
  }>;
};

export type SimilarItems = {
  source_uuid: string;
  method: string;
  candidates_evaluated: number;
  truncated: boolean;
  items: Array<{
    uuid: string;
    handle: string | null;
    name: string;
    score: number;
    evidence: Array<{
      kind: "metadata_value_match" | "title_token_overlap";
      field: string | null;
      values: string[];
      contribution: number;
    }>;
  }>;
};

export type CatalogSuggestions = {
  item_uuid: string;
  method: string;
  suggestions: Array<{
    field: string;
    value: string;
    confidence: number;
    supporting_item_uuids: string[];
    explanation: string;
  }>;
};

export type SuggestionHistory = {
  item_uuid: string;
  entries: Array<{
    suggestion_id: string;
    fingerprint: string;
    source_hash: string;
    source_stale: boolean;
    field: string;
    proposed_value: string;
    confidence: number;
    method: string;
    method_version: string;
    explanation: string;
    evidence: Record<string, unknown>;
    created_at: string;
    decisions: Array<{
      decision_id: string;
      decision: "accepted" | "corrected" | "rejected" | "deferred";
      corrected_value: string | null;
      reviewer: string;
      note: string;
      source_stale: boolean;
      draft_revision_id: string | null;
      created_at: string;
    }>;
  }>;
};

export type WorkQueue = {
  collection_uuid: string;
  collection_name: string;
  generated_at: string;
  source: string;
  grain: string;
  latest_sync_status: string | null;
  latest_sync_finished_at: string | null;
  available_finding_codes: string[];
  summary: {
    active_items: number;
    attention_items: number;
    items_with_findings: number;
    pending_review_items: number;
    items_with_pending_suggestions: number;
    pending_suggestions: number;
    reviewed_items: number;
    items_with_draft: number;
    stale_draft_items: number;
    open_draft_items: number;
    approved_draft_items: number;
    rejected_draft_items: number;
    superseded_draft_items: number;
  };
  items: Array<{
    uuid: string;
    handle: string | null;
    name: string;
    last_modified: string | null;
    finding_count: number;
    pending_finding_count: number;
    pending_suggestion_count: number;
    deferred_finding_count: number;
    finding_codes: string[];
    highest_severity: string | null;
    has_draft: boolean;
    draft_stale: boolean;
    latest_draft_version: number | null;
    priority: "critical" | "high" | "suggestion" | "rebase" | "draft" | "approved" | "rejected" | "reviewed";
    draft_state: "open" | "approved" | "rejected" | "superseded" | "stale" | null;
  }>;
  page: number;
  size: number;
  total: number;
};


export type ControlledTerm = {
  term_id: string;
  value: string;
  authority: string | null;
  language: string | null;
  position: number;
};

export type DSpaceVocabularyList = {
  total: number;
  entry_total: number;
  vocabularies: Array<{
    vocabulary_id: string;
    name: string;
    hierarchical: boolean;
    scrollable: boolean;
    source_uri: string;
    synced_at: string;
    entry_count: number;
  }>;
};
export type DSpaceVocabularyComparison = {
  vocabulary_id: string; field: string; term_count: number; distinct_term_count: number; duplicate_term_count: number; observed_value_count: number;
  exact_count: number; normalized_count: number; outside_count: number; unused_term_count: number;
  values: Array<{ value: string; item_count: number; status: "exact" | "normalized" | "outside"; candidates: string[] }>;
  unused_terms: string[];
  duplicate_terms: string[];
  normalized_duplicate_count: number;
  normalized_duplicate_terms: string[][];
};

export type VocabularyRevision = {
  revision_id: string;
  request_id: string;
  field: string;
  name: string;
  source_uri: string;
  version_label: string;
  approved_by: string;
  approval_note: string;
  is_active: boolean;
  created_at: string;
  terms: ControlledTerm[];
};

export type ItemMetadataValidation = {
  item_uuid: string;
  source_hash: string;
  status: "not_configured" | "valid" | "invalid";
  fields: Array<{
    field: string;
    status: "no_vocabulary" | "no_values" | "valid" | "invalid";
    vocabulary: VocabularyRevision | null;
    values: Array<{
      value: string;
      approved: boolean;
      matched_term: ControlledTerm | null;
    }>;
  }>;
};

export type CatalogProfile = {
  collection_uuid: string;
  collection_name: string;
  collection_handle: string | null;
  generated_at: string;
  source: string;
  grain: string;
  active_items: number;
  latest_sync_status: string | null;
  latest_sync_finished_at: string | null;
  interpretation: string;
  fields: Array<{
    field: string;
    label: string;
    item_count: number;
    missing_item_count: number;
    value_count: number;
    distinct_value_count: number;
    coverage_rate: number;
    top_values: Array<{
      value: string;
      item_count: number;
      value_count: number;
      item_rate: number;
    }>;
  }>;
  completeness_patterns: Array<{
    fields_present: string[];
    item_count: number;
    rate: number;
  }>;
  relationships: Array<{
    from_field: string;
    to_field: string;
    observed_pairs: number;
    pairs: Array<{
      from_value: string;
      to_value: string;
      item_count: number;
      item_rate: number;
    }>;
  }>;
};

export type NotificationSeverity = "info" | "warning" | "error";
export type NotificationState = "unread" | "read" | "archived";

export type Notification = {
  notification_id: string;
  event_type: string;
  severity: NotificationSeverity;
  title: string;
  summary: string;
  target_path: string | null;
  state: NotificationState;
  occurred_at: string;
};

export type NotificationList = {
  items: Notification[];
  next_cursor: string | null;
  unread_count: number;
};

export type NotificationPreference = { event_type: string; muted: boolean };
export type NotificationPreferenceList = { preferences: NotificationPreference[] };

async function apiFetch<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Catalog API returned ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function getItems(query: string): Promise<{ items: ItemSummary[]; total: number }> {
  const params = new URLSearchParams({ size: "50" });
  if (query) params.set("q", query);
  return apiFetch(`/api/items?${params.toString()}`);
}

export function getItem(uuid: string): Promise<ItemDetail> {
  return apiFetch(`/api/items/${encodeURIComponent(uuid)}`);
}
export function getSimilarItems(uuid: string): Promise<SimilarItems> {
  return apiFetch(`/api/items/${encodeURIComponent(uuid)}/similar?limit=5`);
}
export function getItemSuggestions(uuid: string): Promise<CatalogSuggestions> {
  return apiFetch("/api/items/" + encodeURIComponent(uuid) + "/suggestions");
}
export function getSuggestionHistory(uuid: string): Promise<SuggestionHistory> {
  return apiFetch("/api/items/" + encodeURIComponent(uuid) + "/suggestion-history");
}

export function getCatalogProfile(): Promise<CatalogProfile> {
  return apiFetch("/api/catalog-profile");
}

export function getWorkQueue(filters: Record<string, string | undefined>): Promise<WorkQueue> {
  const params = new URLSearchParams({ size: "25" });
  for (const [key, value] of Object.entries(filters)) {
    if (value) params.set(key, value);
  }
  return apiFetch(`/api/work-queue?${params.toString()}`);
}

export function getControlledVocabularies(
  includeHistory = false,
): Promise<{ revisions: VocabularyRevision[]; total: number }> {
  const query = includeHistory ? "?include_history=true" : "";
  return apiFetch(`/api/controlled-vocabularies${query}`);
}

export function getDSpaceVocabularies(): Promise<DSpaceVocabularyList> {
  return apiFetch("/api/dspace-vocabularies");
}
export function getDSpaceVocabularyComparison(id: string): Promise<DSpaceVocabularyComparison> {
  return apiFetch(`/api/dspace-vocabularies/${encodeURIComponent(id)}/comparison`);
}

export function getItemMetadataValidation(uuid: string): Promise<ItemMetadataValidation> {
  return apiFetch(`/api/items/${encodeURIComponent(uuid)}/metadata-validation`);
}

export type AgentCitation = { label: string; target_path: string };

export type AgentMessage = {
  message_id: string;
  role: "user" | "assistant";
  content: string;
  citations: AgentCitation[];
  created_at: string;
};

export type AgentConversation = {
  conversation_id: string;
  started_by: string;
  started_at: string;
  status: "open" | "archived";
};

export type AgentConversationDetail = AgentConversation & { messages: AgentMessage[] };

export function getAgentConversation(id: string): Promise<AgentConversationDetail> {
  return apiFetch(`/api/agent/conversations/${encodeURIComponent(id)}`);
}

export function getNotifications(filters: {
  state?: string;
  event_type?: string;
  cursor?: string;
  limit?: number;
}): Promise<NotificationList> {
  const params = new URLSearchParams({ limit: String(filters.limit ?? 25) });
  if (filters.state) params.set("state", filters.state);
  if (filters.event_type) params.set("event_type", filters.event_type);
  if (filters.cursor) params.set("cursor", filters.cursor);
  return apiFetch(`/api/notifications?${params.toString()}`);
}
