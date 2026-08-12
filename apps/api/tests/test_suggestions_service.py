import uuid
from types import SimpleNamespace

import pytest

from cataloging_api.suggestions import service


def item(field: str | None, value: str = "Tarasca") -> SimpleNamespace:
    metadata = [] if field is None else [SimpleNamespace(field=field, value=value)]
    return SimpleNamespace(uuid=uuid.uuid4(), metadata_values=metadata)


@pytest.mark.asyncio
async def test_suggests_only_with_two_neighbors_and_75_percent_consensus(monkeypatch) -> None:
    field = "dc.subject.linguisticFamily"
    source = item(None)
    neighbors = [item(field), item(field), item(field), item(field, "Otra")]
    result = SimpleNamespace(
        source=source,
        matches=[(neighbor, SimpleNamespace(score=0.4)) for neighbor in neighbors],
    )

    async def fake_find(*args, **kwargs):
        return result

    monkeypatch.setattr(service, "find_similar_items", fake_find)
    proposals = await service.suggest_missing_metadata(SimpleNamespace(), source.uuid)

    assert proposals is not None
    assert [(proposal.field, proposal.value) for proposal in proposals] == [(field, "Tarasca")]
    assert len(proposals[0].supporting_item_uuids) == 3


@pytest.mark.asyncio
async def test_does_not_suggest_without_sufficient_evidence(monkeypatch) -> None:
    field = "dc.subject.linguisticFamily"
    source = item(None)
    result = SimpleNamespace(
        source=source,
        matches=[
            (item(field), SimpleNamespace(score=0.4)),
            (item(field, "Otra"), SimpleNamespace(score=0.4)),
        ],
    )

    async def fake_find(*args, **kwargs):
        return result

    monkeypatch.setattr(service, "find_similar_items", fake_find)
    assert await service.suggest_missing_metadata(SimpleNamespace(), source.uuid) == []
