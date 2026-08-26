from cataloging_api.cataloging_contract import (
    FIELDS,
    live_dspace_label,
    live_dspace_selector_label,
)
from cataloging_api.dspace.baseline_diagnose import diagnose_bindings


def _binding(index: int, *, repeatable: bool | None = None) -> dict:
    expected = FIELDS[index]
    form = "traditionalpageone" if index < 44 else "traditionalpagetwo"
    return {
        "bindingKey": f"{form}:{expected.metadata_field}:{index}",
        "form": form,
        "metadata": expected.metadata_field,
        "position": [0 if index < 44 else 1, index if index < 44 else index - 44, 0, 0],
        "label": live_dspace_label(expected),
        "selectorLabel": live_dspace_selector_label(expected),
        "required": expected.required,
        "repeatable": expected.repeatable if repeatable is None else repeatable,
        "controlledVocabulary": expected.vocabulary_id,
    }


def test_diagnose_bindings_accepts_runtime_contract_aligned_with_live_shape() -> None:
    bindings = [_binding(index) for index in range(len(FIELDS))]

    report = diagnose_bindings(bindings)

    assert report["binding_count"] == 56
    assert report["expected_binding_count"] == 56
    assert report["mismatch_count"] == 0
    assert report["mismatch_dimensions"] == {}
    assert report["mismatches"] == []


def test_diagnose_bindings_reports_all_mismatches_not_only_first() -> None:
    bindings = [_binding(index) for index in range(len(FIELDS))]
    bindings[2] = {**bindings[2], "repeatable": not FIELDS[2].repeatable}
    bindings[15] = {**bindings[15], "label": "Identificador incorrecto"}

    report = diagnose_bindings(bindings)

    assert report["binding_count"] == 56
    assert report["mismatch_count"] == 2
    assert report["mismatch_dimensions"] == {"label": 1, "repeatable": 1}
    assert {(item["index"], item["dimension"]) for item in report["mismatches"]} == {
        (2, "repeatable"),
        (15, "label"),
    }


def test_diagnose_bindings_validates_selector_label_independently() -> None:
    bindings = [_binding(index) for index in range(len(FIELDS))]
    bindings[15] = {
        **bindings[15],
        "selectorLabel": "WRONG",
    }

    report = diagnose_bindings(bindings)

    mismatch = report["mismatches"][0]
    assert mismatch["dimension"] == "selectorLabel"
    assert mismatch["live"] == "WRONG"
    assert mismatch["expected"] == "ISSN"
