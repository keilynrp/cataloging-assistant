import json
from pathlib import Path


FIXTURE = Path(__file__).parent / "fixtures" / "dspace_contract_live_traditional_2026-08-26.json"


def test_live_traditional_reconciliation_guardrail() -> None:
    evidence = json.loads(FIXTURE.read_text(encoding="utf-8"))
    counts = evidence["counts"]
    reconciliation = evidence["reconciliation"]

    assert evidence["activeDefinition"] == "traditional"
    assert evidence["activeSectionsObservable"] is False
    assert evidence["activeSectionsWarning"] == "ACTIVE_SUBMISSION_SECTIONS_UNRESOLVED_HTTP_204"
    assert counts["traditionalPageOneBindings"] == 44
    assert counts["traditionalPageTwoBindings"] == 12
    assert counts["traditionalUniqueBindings"] == 56
    assert counts["traditionalUniqueMetadataFields"] == 54
    assert counts["traditionalPageOneBindings"] + counts["traditionalPageTwoBindings"] == 56

    for dimension in (
        "bindingIdentity",
        "metadataField",
        "uiLabel",
        "required",
        "repeatable",
        "inputType",
        "controlledVocabulary",
        "closedVocabulary",
        "formOrder",
        "renderOrder",
    ):
        assert reconciliation[dimension] == "56/56"

    for dimension in ("registryPresence", "registryFieldId", "registryScopeNote"):
        assert reconciliation[dimension] == "54/54"
