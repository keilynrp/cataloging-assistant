import asyncio
from types import SimpleNamespace

import cataloging_api.dspace.contract_sync_core as core
from cataloging_api.dspace.client import DSpaceError


class _Session:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class _Client:
    async def get_submission_definition_for_collection(self, collection_uuid: str) -> dict:
        assert collection_uuid == "collection-uuid"
        return {"name": "traditional"}


async def _raise_204(**_: object) -> None:
    raise DSpaceError("invalid_response", "HTTP 204", status_code=204)


def test_active_sections_204_is_persisted_as_unobservable_not_raised(monkeypatch) -> None:
    persisted: list[dict] = []

    async def fake_persist(session, **kwargs):
        persisted.append(kwargs)

    monkeypatch.setattr(core, "persist_page_and_advance_checkpoint", fake_persist)
    monkeypatch.setattr(core, "_collect_surface", _raise_204)

    async def run() -> None:
        session = _Session()
        await core._collect_active_definition(
            session,
            run=SimpleNamespace(),
            client=_Client(),
            collection_uuid="collection-uuid",
            page_size=100,
        )
        assert session.commits == 2

    asyncio.run(run())

    assert len(persisted) == 2
    sections = persisted[1]
    assert sections["surface"] == "active_submission_sections"
    assert sections["raw_payload"]["_observation"] == {
        "observable": False,
        "statusCode": 204,
        "reason": "no_content",
    }
    assert sections["raw_payload"]["page"] == {
        "number": 0,
        "totalPages": 0,
        "totalElements": 0,
    }
