import uuid
from datetime import UTC, datetime

from cataloging_api.agent.tools import _profile_citations
from cataloging_api.profile.schemas import (
    CollectionProfileOut,
    FieldProfileOut,
    RelationshipPairOut,
    RelationshipProfileOut,
    TopValueOut,
)


def _profile() -> CollectionProfileOut:
    return CollectionProfileOut(
        collection_uuid=uuid.uuid4(),
        collection_name="Colección piloto",
        collection_handle="123456789/4",
        generated_at=datetime.now(UTC),
        source="postgresql",
        grain="active_items",
        active_items=42,
        latest_sync_status="succeeded",
        latest_sync_finished_at=datetime.now(UTC),
        fields=[
            FieldProfileOut(
                field="dc.subject.linguisticFamily",
                label="Familia lingüística",
                item_count=30,
                missing_item_count=12,
                value_count=30,
                distinct_value_count=3,
                coverage_rate=30 / 42,
                top_values=[
                    TopValueOut(value="Tarasca", item_count=18, value_count=18, item_rate=18 / 42),
                ],
            ),
            FieldProfileOut(
                field="dc.description.registeredLanguage",
                label="Lengua registrada",
                item_count=0,
                missing_item_count=42,
                value_count=0,
                distinct_value_count=0,
                coverage_rate=0.0,
                top_values=[],
            ),
        ],
        completeness_patterns=[],
        relationships=[
            RelationshipProfileOut(
                from_field="dc.subject.linguisticFamily",
                to_field="dc.subject.linguisticBranch",
                observed_pairs=9,
                pairs=[
                    RelationshipPairOut(
                        from_value="Tarasca", to_value="P'urhepecha", item_count=9, item_rate=9 / 42
                    ),
                ],
            ),
            RelationshipProfileOut(
                from_field="dc.subject.linguisticBranch",
                to_field="dc.subject.linguiscgroup",
                observed_pairs=0,
                pairs=[],
            ),
        ],
        interpretation="",
    )


def test_profile_citations_start_with_the_base_link() -> None:
    citations = _profile_citations(_profile())
    assert citations[0] == {"label": "Evidencia de colección", "target_path": "/catalog-profile"}


def test_profile_citations_enrich_fields_with_a_data_fragment() -> None:
    citations = _profile_citations(_profile())
    field_citation = next(c for c in citations if c["label"] == "Perfil · Familia lingüística")
    assert field_citation["target_path"] == "/catalog-profile"
    assert "Tarasca" in field_citation["detail"]
    assert "18 ítems" in field_citation["detail"]
    assert "71%" in field_citation["detail"] or "%" in field_citation["detail"]


def test_profile_citations_enrich_relationships_with_the_top_pair() -> None:
    citations = _profile_citations(_profile())
    relationship_citation = next(c for c in citations if c["label"].startswith("Relación ·"))
    assert "Tarasca → P'urhepecha" in relationship_citation["detail"]
    assert "9 pares" in relationship_citation["detail"]


def test_profile_citations_skip_fields_and_relationships_without_data() -> None:
    citations = _profile_citations(_profile())
    labels = [c["label"] for c in citations]
    assert "Perfil · Lengua registrada" not in labels
    assert not any(
        label.startswith("Relación · dc.subject.linguisticBranch") for label in labels
    )
