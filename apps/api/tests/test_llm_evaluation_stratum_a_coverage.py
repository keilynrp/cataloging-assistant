from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).parent / "golden" / "llm-evidence"
CRITICAL = {
    "linguistic-family",
    "linguistic-branch",
    "linguistic-group",
    "linguistic-variant",
    "registered-language",
}
REQUIRED_DIMENSIONS = {
    "compositional_inference",
    "contradiction",
    "binding_distractor",
    "grounding_positive",
    "grounding_negative",
    "multilingual_code_switching",
    "controlled_vocabulary_out_of_vocab",
    "abstention",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_stratum_a_manifest_meets_declared_sample_floor_and_fixtures_validate() -> None:
    manifest = _load(ROOT / "manifest.json")
    manifest_schema = _load(ROOT / "schemas" / "manifest.schema.json")
    source_schema = _load(ROOT / "schemas" / "source.schema.json")
    expected_schema = _load(ROOT / "schemas" / "expected.schema.json")

    Draft202012Validator(manifest_schema).validate(manifest)

    totals = defaultdict(int)
    overall = 0
    dimensions: set[str] = set()
    for case in manifest["cases"]:
        if case["risk_stratum"] != "A":
            continue
        overall += case["opportunity_count"]
        dimensions.update(case.get("methodological_dimensions", []))
        for binding in case["bindings_under_test"]:
            if binding in CRITICAL:
                totals[binding] += case["opportunity_count"]

        case_dir = ROOT / "cases" / case["id"]
        source = _load(case_dir / "source.json")
        expected = _load(case_dir / "expected.json")
        Draft202012Validator(source_schema).validate(source)
        Draft202012Validator(expected_schema).validate(expected)
        assert source["case_id"] == case["id"]
        assert expected["case_id"] == case["id"]

    assert overall >= 20
    assert set(totals) == CRITICAL
    assert all(totals[binding] >= 3 for binding in CRITICAL)
    assert REQUIRED_DIMENSIONS.issubset(dimensions)
    assert any("en" in case.get("languages", []) for case in manifest["cases"])
    group_fields = {
        field
        for case in manifest["cases"]
        if "linguistic-group" in case.get("bindings_under_test", [])
        for field in case.get("metadata_fields_under_test", [])
    }
    assert group_fields == {"dc.subject.linguiscgroup"}
    assert manifest["status"] == "STRATUM_A_SAMPLE_FLOOR_MET_SYNTHETIC_ONLY"
