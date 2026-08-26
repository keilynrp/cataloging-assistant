import pytest

from cataloging_api.dspace.baseline_payload import (
    RECONCILIATION_HASH,
    SOURCE_EXPORT_HASH,
    _resolved_sections,
)


def _section(form_id: str, *, header: str, section_id: str | None = None) -> dict:
    return {
        "id": section_id or form_id,
        "sectionType": "submission-form",
        "header": header,
        "mandatory": True,
        "scope": None,
        "_links": {
            "config": {
                "href": f"http://dspace.example/api/config/submissionforms/{form_id}"
            }
        },
    }


def test_resolved_sections_use_authoritative_global_evidence_in_expected_order() -> None:
    pages = {
        "submission_sections": [
            {
                "_embedded": {
                    "submissionsections": [
                        _section("traditionalpagetwo", header="step-two"),
                        _section("traditionalpageone", header="step-one"),
                    ]
                }
            }
        ]
    }

    sections = _resolved_sections(pages)

    assert [section["configForm"] for section in sections] == [
        "traditionalpageone",
        "traditionalpagetwo",
    ]
    assert [section["order"] for section in sections] == [0, 1]
    assert [section["header"] for section in sections] == ["step-one", "step-two"]


def test_resolved_sections_deduplicate_identical_global_evidence() -> None:
    duplicate = _section("traditionalpagetwo", header="step-two")
    pages = {
        "submission_sections": [
            {
                "_embedded": {
                    "submissionsections": [
                        _section("traditionalpageone", header="step-one"),
                        duplicate,
                        dict(duplicate),
                    ]
                }
            }
        ]
    }

    sections = _resolved_sections(pages)

    assert [section["configForm"] for section in sections] == [
        "traditionalpageone",
        "traditionalpagetwo",
    ]


def test_resolved_sections_prefer_exact_section_id_for_reused_form() -> None:
    pages = {
        "submission_sections": [
            {
                "_embedded": {
                    "submissionsections": [
                        _section("traditionalpageone", header="step-one"),
                        _section(
                            "traditionalpagetwo",
                            header="other-use",
                            section_id="other-section",
                        ),
                        _section("traditionalpagetwo", header="step-two"),
                    ]
                }
            }
        ]
    }

    sections = _resolved_sections(pages)

    assert sections[1]["id"] == "traditionalpagetwo"
    assert sections[1]["header"] == "step-two"


def test_resolved_sections_reject_ambiguous_reused_form_without_exact_identity() -> None:
    pages = {
        "submission_sections": [
            {
                "_embedded": {
                    "submissionsections": [
                        _section("traditionalpageone", header="step-one"),
                        _section(
                            "traditionalpagetwo",
                            header="use-a",
                            section_id="section-a",
                        ),
                        _section(
                            "traditionalpagetwo",
                            header="use-b",
                            section_id="section-b",
                        ),
                    ]
                }
            }
        ]
    }

    with pytest.raises(ValueError, match="ambiguous_authoritative_section:traditionalpagetwo"):
        _resolved_sections(pages)


def test_baseline_payload_pins_authenticated_reconciliation_hashes() -> None:
    assert SOURCE_EXPORT_HASH == (
        "8260b2023b7b417f3056d3724664869f96cb613371c673517d6b7400af2a0b1c"
    )
    assert RECONCILIATION_HASH == (
        "5b549a16307354b84b9327325532755877a622e323573616e92c8a0dee93ea92"
    )
