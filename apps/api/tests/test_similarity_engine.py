import uuid

from cataloging_api.similarity.engine import SimilarityItem, rank_similar_items

SOURCE_UUID = uuid.UUID("11111111-1111-4111-8111-111111111111")


def item(item_uuid: str, name: str, metadata: dict[str, list[str]]) -> SimilarityItem:
    return SimilarityItem(uuid=uuid.UUID(item_uuid), name=name, metadata=metadata)


def test_ranking_explains_structured_matches_and_preserves_external_key() -> None:
    source = item(
        str(SOURCE_UUID),
        "Relatos tradicionales de la lengua purépecha",
        {
            "dc.subject.linguisticFamily": ["Tarasca"],
            "dc.subject.linguiscgroup": ["Purépecha"],
        },
    )
    candidate = item(
        "22222222-2222-4222-8222-222222222222",
        "Relatos tradicionales en lengua purépecha",
        {
            "dc.subject.linguisticFamily": ["tarasca"],
            "dc.subject.linguiscgroup": ["Purépecha"],
        },
    )

    matches = rank_similar_items(source, [candidate], limit=5)

    assert len(matches) == 1
    assert matches[0].score > 0.4
    assert [evidence.field for evidence in matches[0].evidence] == [
        "dc.subject.linguisticFamily",
        "dc.subject.linguiscgroup",
        "dc.title",
    ]
    assert matches[0].evidence[1].values == ("Purépecha",)


def test_unrelated_candidate_and_source_itself_are_excluded() -> None:
    source = item(str(SOURCE_UUID), "Título único", {})
    unrelated = item("33333333-3333-4333-8333-333333333333", "Contenido diferente", {})

    assert rank_similar_items(source, [source, unrelated], limit=5) == []


def test_limit_is_applied_after_deterministic_score_ordering() -> None:
    source = item(
        str(SOURCE_UUID),
        "Muestra de lengua",
        {"dc.description.registeredLanguage": ["Purépecha"]},
    )
    strong = item(
        "44444444-4444-4444-8444-444444444444",
        "Muestra de lengua purépecha",
        {"dc.description.registeredLanguage": ["Purépecha"]},
    )
    weak = item(
        "55555555-5555-4555-8555-555555555555",
        "Muestra de lengua distinta",
        {},
    )

    matches = rank_similar_items(source, [weak, strong], limit=1)

    assert [match.item_uuid for match in matches] == [strong.uuid]
