from cataloging_api.cataloging_contract import FIELDS
from cataloging_api.dspace.baseline_diagnose import diagnose_bindings


def _binding(index: int, *, repeatable: bool | None = None) -> dict:
    expected = FIELDS[index]
    form = "traditionalpageone" if index < 44 else "traditionalpagetwo"
    return {
        "bindingKey": f"{form}:{expected.metadata_field}:{index}",
        "form": form,
        "metadata": expected.metadata_field,
        "position": [0 if index < 44 else 1, index if index < 44 else index - 44, 0, 0],
        "label": expected.ui_label,
        "selectorLabel": None,
        "required": expected.required,
        "repeatable": expected.repeatable if repeatable is None else repeatable,
        "controlledVocabulary": expected.vocabulary_id,
    }


def test_diagnose_bindings_reports_all_mismatches_not_only_first() -> None:
    bindings = [_binding(index) for index in range(len(FIELDS))]
    bindings[2] = {**bindings[2], "repeatable": not FIELDS[2].repeatable}
    bindings[15] = {**bindings[15], "label": "Identificador"}

    report = diagnose_bindings(bindings)

    assert report["binding_count"] == 56
    assert report["mismatch_count"] == 2
    assert report["mismatch_dimensions"] == {"label": 1, "repeatable": 1}
    assert {(item["index"], item["dimension"]) for item in report["mismatches"]} == {
        (2, "repeatable"),
        (15, "label"),
    }


def test_diagnose_bindings_reports_selector_label_for_context() -> None:
    bindings = [_binding(index) for index in range(len(FIELDS))]
    bindings[15] = {
        **bindings[15],
        "label": "Identificador",
        "selectorLabel": "ISSN",
    }

    report = diagnose_bindings(bindings)

    mismatch = report["mismatches"][0]
    assert mismatch["dimension"] == "label"
    assert mismatch["selectorLabel"] == "ISSN"
