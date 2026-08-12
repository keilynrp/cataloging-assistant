import asyncio
import hashlib
import json
import uuid
from datetime import UTC, datetime

import httpx
from sqlalchemy import delete

from cataloging_api.config import get_settings
from cataloging_api.db.models import DSpaceVocabulary, DSpaceVocabularyEntry
from cataloging_api.db.session import SessionFactory


def _hash(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


async def synchronize_dspace_vocabularies() -> tuple[int, int]:
    settings = get_settings()
    if not settings.dspace_read_username or not settings.dspace_read_password:
        raise RuntimeError("DSpace read credentials are not configured")
    async with httpx.AsyncClient(base_url=settings.dspace_base_url, timeout=60) as client:
        status = await client.get("/authn/status")
        status.raise_for_status()
        csrf = status.headers.get("DSPACE-XSRF-TOKEN") or client.cookies.get("DSPACE-XSRF-COOKIE")
        login = await client.post(
            "/authn/login",
            data={"user": settings.dspace_read_username, "password": settings.dspace_read_password},
            headers={"X-XSRF-TOKEN": csrf or ""},
        )
        login.raise_for_status()
        client.headers.update(
            {"Authorization": login.headers["Authorization"], "Accept": "application/hal+json"}
        )
        response = await client.get("/submission/vocabularies", params={"size": 100})
        response.raise_for_status()
        vocabularies = response.json().get("_embedded", {}).get("vocabularies", [])
        entry_total = 0
        async with SessionFactory() as session:
            for vocabulary in vocabularies:
                vocabulary_id = vocabulary["id"]
                entries: list[dict] = []
                page = 0
                while True:
                    result = await client.get(
                        f"/submission/vocabularies/{vocabulary_id}/entries",
                        params={"page": page, "size": 100},
                    )
                    if result.status_code in {404, 422} and vocabulary.get("hierarchical"):
                        result = await client.get(
                            "/submission/vocabularyEntryDetails/search/top",
                            params={"vocabulary": vocabulary_id, "page": page, "size": 100},
                        )
                    result.raise_for_status()
                    payload = result.json()
                    entries.extend(
                        payload.get("_embedded", {}).get(
                            "entries",
                            payload.get("_embedded", {}).get("vocabularyEntryDetails", []),
                        )
                    )
                    info = payload.get("page", {})
                    if page + 1 >= int(info.get("totalPages", 1)):
                        break
                    page += 1
                await session.merge(
                    DSpaceVocabulary(
                        vocabulary_id=vocabulary_id,
                        name=vocabulary.get("name", vocabulary_id),
                        hierarchical=bool(vocabulary.get("hierarchical")),
                        scrollable=bool(vocabulary.get("scrollable")),
                        source_uri=vocabulary.get("_links", {}).get("self", {}).get("href", ""),
                        raw_json=vocabulary,
                        source_hash=_hash(vocabulary),
                        synced_at=datetime.now(UTC),
                    )
                )
                await session.flush()
                await session.execute(
                    delete(DSpaceVocabularyEntry).where(
                        DSpaceVocabularyEntry.vocabulary_id == vocabulary_id
                    )
                )
                for position, entry in enumerate(entries):
                    other = entry.get("otherInformation") or {}
                    session.add(
                        DSpaceVocabularyEntry(
                            row_id=uuid.uuid4(),
                            vocabulary_id=vocabulary_id,
                            entry_id=str(entry.get("id", position)),
                            value=str(entry.get("value", "")),
                            display=entry.get("display"),
                            selectable=bool(entry.get("selectable", True)),
                            parent_id=other.get("parent"),
                            position=position,
                            raw_json=entry,
                            source_hash=_hash(entry),
                            synced_at=datetime.now(UTC),
                        )
                    )
                entry_total += len(entries)
            await session.commit()
    return len(vocabularies), entry_total


def main() -> None:
    vocabularies, entries = asyncio.run(synchronize_dspace_vocabularies())
    print(f"Synchronized {vocabularies} vocabularies and {entries} entries")


if __name__ == "__main__":
    main()
