from cataloging_api.cataloging_contract import (
    CLIN_RELATIONSHIPS,
    CONTRACT_VERSION,
    CONTROLLED_RUNTIME_FIELDS,
    DRAFTABLE_LINGUISTIC_FIELDS,
    FIELDS,
    LINGUISTIC_BRANCH,
    LINGUISTIC_FAMILY,
    LINGUISTIC_GROUP,
    LINGUISTIC_VARIANT,
    REGISTERED_LANGUAGE,
    contract_payload,
)


def test_master_contract_keeps_56_ui_bindings() -> None:
    assert CONTRACT_VERSION == "dspace-cataloger-v3.6"
    assert len(FIELDS) == 56
    assert sum(field.metadata_field == "dc.format.medium" for field in FIELDS) == 2
    assert sum(field.metadata_field == "dc.subject" for field in FIELDS) == 2


def test_literal_external_metadata_keys_are_preserved() -> None:
    assert LINGUISTIC_GROUP == "dc.subject.linguiscgroup"
    assert LINGUISTIC_GROUP in DRAFTABLE_LINGUISTIC_FIELDS
    assert LINGUISTIC_GROUP in CONTROLLED_RUNTIME_FIELDS


def test_runtime_contract_includes_variant_and_keeps_registered_language_independent() -> None:
    expected = {
        LINGUISTIC_FAMILY,
        LINGUISTIC_BRANCH,
        LINGUISTIC_GROUP,
        LINGUISTIC_VARIANT,
        REGISTERED_LANGUAGE,
    }
    assert set(DRAFTABLE_LINGUISTIC_FIELDS) == expected
    assert set(CONTROLLED_RUNTIME_FIELDS) == expected
    assert (LINGUISTIC_FAMILY, LINGUISTIC_GROUP) in CLIN_RELATIONSHIPS
    assert (LINGUISTIC_GROUP, LINGUISTIC_VARIANT) in CLIN_RELATIONSHIPS
    assert all(REGISTERED_LANGUAGE not in pair for pair in CLIN_RELATIONSHIPS)


def test_contract_payload_is_runtime_serializable() -> None:
    payload = contract_payload()
    assert payload["field_count"] == 56
    runtime = payload["runtime"]
    assert runtime["branch_is_optional_enrichment"] is True
    assert runtime["registered_language_is_independent"] is True
    assert runtime["dspace_write_enabled"] is False
    assert runtime["human_approval_required"] is True
