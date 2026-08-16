import { API_URL, PUBLIC_API_URL } from "@/lib/api";

export type CatalogingContractField = {
  binding_id: string;
  metadata_field: string;
  ui_label: string;
  assistant_label: string;
  repeatable: boolean;
  required: boolean;
  controlled: boolean;
  vocabulary_id: string | null;
  runtime_draftable: boolean;
  runtime_profiled: boolean;
  runtime_vocabularied: boolean;
};

export type CatalogingContract = {
  contract_version: string;
  dspace_version: string;
  field_count: number;
  fields: CatalogingContractField[];
  runtime: {
    draftable_fields: string[];
    controlled_fields: string[];
    profile_fields: string[];
    profile_relationships: [string, string][];
    clin_relationships: [string, string][];
    branch_is_optional_enrichment: boolean;
    registered_language_is_independent: boolean;
    dspace_write_enabled: boolean;
    human_approval_required: boolean;
  };
  evidence_states: string[];
  qa_rules: string[];
};

async function fetchContract(baseUrl: string): Promise<CatalogingContract> {
  const response = await fetch(`${baseUrl}/api/cataloging-contract`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Catalog contract API returned ${response.status}`);
  return response.json() as Promise<CatalogingContract>;
}

export function getCatalogingContract(): Promise<CatalogingContract> {
  return fetchContract(API_URL);
}

export function getPublicCatalogingContract(): Promise<CatalogingContract> {
  return fetchContract(PUBLIC_API_URL);
}

export function contractLabel(contract: CatalogingContract, metadataField: string): string {
  return contract.fields.find((field) => field.metadata_field === metadataField)?.assistant_label ?? metadataField;
}
