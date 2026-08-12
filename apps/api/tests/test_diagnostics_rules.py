from cataloging_api.diagnostics.engine import (
    CONTROLLED_LINGUISTIC_FIELDS,
    LINGUISTIC_BRANCH,
    LINGUISTIC_FAMILY,
    VocabularyRule,
    diagnostic_profile_version,
    evaluate_metadata,
)


def test_family_without_branch_produces_reproducible_warning() -> None:
    first = evaluate_metadata({LINGUISTIC_FAMILY: ["Yuto-nahua"]})
    second = evaluate_metadata({LINGUISTIC_FAMILY: ["Yuto-nahua"]})

    assert [(finding.code, finding.severity) for finding in first] == [("CAT-LING-001", "warning")]
    assert first[0].affected_fields == (LINGUISTIC_FAMILY, LINGUISTIC_BRANCH)
    assert first[0].fingerprint == second[0].fingerprint


def test_branch_without_family_produces_completeness_error() -> None:
    findings = evaluate_metadata({LINGUISTIC_BRANCH: ["Tarasca"]})

    assert [(finding.code, finding.severity) for finding in findings] == [("CAT-LING-002", "error")]


def test_empty_values_count_as_absent_for_configured_required_field() -> None:
    findings = evaluate_metadata(
        {LINGUISTIC_FAMILY: ["  "]},
        required_fields=(LINGUISTIC_FAMILY,),
    )

    assert [(finding.code, finding.affected_fields) for finding in findings] == [
        ("CAT-META-001", (LINGUISTIC_FAMILY,))
    ]


def test_required_fields_are_inactive_by_default() -> None:
    assert evaluate_metadata({}) == []
    assert diagnostic_profile_version(()) != diagnostic_profile_version((LINGUISTIC_FAMILY,))


REGISTERED_LANGUAGE = "dc.description.registeredLanguage"


def vocabulary_rule(revision: str = "language:revision-1") -> VocabularyRule:
    return VocabularyRule(
        revision_key=revision,
        name="Lenguas aprobadas",
        source_uri="https://example.test/vocabulary",
        version_label="1",
        approved_by="Referente",
        terms=frozenset({"Purépecha"}),
    )


def test_approved_vocabulary_uses_exact_literal_matching() -> None:
    vocabularies = {REGISTERED_LANGUAGE: vocabulary_rule()}

    assert (
        evaluate_metadata(
            {REGISTERED_LANGUAGE: ["Purépecha"]},
            vocabularies=vocabularies,
        )
        == []
    )

    findings = evaluate_metadata(
        {REGISTERED_LANGUAGE: ["purépecha"]},
        vocabularies=vocabularies,
    )
    assert [(finding.code, finding.severity) for finding in findings] == [
        ("CAT-VOCAB-001", "warning")
    ]
    assert "purépecha" in findings[0].explanation
    assert "https://example.test/vocabulary" in findings[0].explanation


def test_vocabulary_fingerprint_tracks_revision_and_invalid_evidence() -> None:
    first = evaluate_metadata(
        {REGISTERED_LANGUAGE: ["Valor A"]},
        vocabularies={REGISTERED_LANGUAGE: vocabulary_rule()},
    )[0]
    changed_value = evaluate_metadata(
        {REGISTERED_LANGUAGE: ["Valor B"]},
        vocabularies={REGISTERED_LANGUAGE: vocabulary_rule()},
    )[0]
    changed_revision = evaluate_metadata(
        {REGISTERED_LANGUAGE: ["Valor A"]},
        vocabularies={REGISTERED_LANGUAGE: vocabulary_rule("language:revision-2")},
    )[0]

    assert len({first.fingerprint, changed_value.fingerprint, changed_revision.fingerprint}) == 3
    assert first.rule_version != changed_revision.rule_version


def test_diagnostic_profile_tracks_active_vocabulary_revision() -> None:
    base = diagnostic_profile_version(())
    configured = diagnostic_profile_version((), ("language:revision-1",))
    changed = diagnostic_profile_version((), ("language:revision-2",))

    assert len({base, configured, changed}) == 3


def test_duplicate_controlled_values_are_detected_without_inventing_hierarchy() -> None:
    for field in CONTROLLED_LINGUISTIC_FIELDS:
        findings = evaluate_metadata({field: [" Inglés ", "ingle\u0301s"]})

        duplicate_findings = [finding for finding in findings if finding.code == "CAT-LING-003"]
        assert len(duplicate_findings) == 1
        assert duplicate_findings[0].affected_fields == (field,)
        assert duplicate_findings[0].evidence_key is not None


def test_distinct_values_do_not_create_cross_vocabulary_inferences() -> None:
    metadata = {
        field: [value]
        for field, value in zip(
            CONTROLLED_LINGUISTIC_FIELDS,
            ("Familia", "Rama", "Grupo", "Lengua"),
            strict=True,
        )
    }

    assert evaluate_metadata(metadata) == []
