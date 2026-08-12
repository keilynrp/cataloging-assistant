import asyncio
import hashlib
import json
import uuid

import httpx
from sqlalchemy import select, text

from cataloging_api.config import get_settings
from cataloging_api.db.models import DSpaceItem
from cataloging_api.db.session import SessionFactory
from cataloging_api.provenance.parser import extract_actor

FIELDS = ("dc.description.provenance", "dcterms.provenance")


async def synchronize_provenance() -> tuple[int, int]:
    settings = get_settings()
    if not settings.catalog_review_token:
        raise RuntimeError("CATALOG_REVIEW_TOKEN is required as the local HMAC secret")
    async with SessionFactory() as session:
        item_ids = list(
            await session.scalars(select(DSpaceItem.uuid).where(DSpaceItem.is_active.is_(True)))
        )
    async with httpx.AsyncClient(base_url=settings.dspace_base_url, timeout=60) as client:
        status = await client.get("/authn/status")
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
        associations = 0
        async with SessionFactory() as session:
            for item_uuid in item_ids:
                response = await client.get(f"/core/items/{item_uuid}")
                response.raise_for_status()
                metadata = response.json().get("metadata", {})
                await session.execute(
                    text("DELETE FROM dspace_item_provenance_actors WHERE item_uuid=:item_uuid"),
                    {"item_uuid": item_uuid},
                )
                for field in FIELDS:
                    for position, evidence in enumerate(metadata.get(field, [])):
                        value = str(evidence.get("value", ""))
                        actor = extract_actor(value, secret=settings.catalog_review_token)
                        if actor is None:
                            continue
                        await session.execute(
                            text(
                                "INSERT INTO dspace_item_provenance_actors "
                                "(association_id,item_uuid,actor_key,actor_type,source_field,"
                                "source_position,source_text_hash,confidence,"
                                "explanation,raw_evidence) "
                                "VALUES (:association_id,:item_uuid,:actor_key,:actor_type,"
                                ":source_field,:source_position,:source_text_hash,:confidence,"
                                ":explanation,CAST(:raw_evidence AS jsonb))"
                            ),
                            {
                                "association_id": uuid.uuid4(),
                                "item_uuid": item_uuid,
                                "actor_key": actor["actor_key"],
                                "actor_type": actor["actor_type"],
                                "source_field": field,
                                "source_position": position,
                                "source_text_hash": hashlib.sha256(value.encode()).hexdigest(),
                                "confidence": actor["confidence"],
                                "explanation": actor["explanation"],
                                "raw_evidence": json.dumps(evidence, ensure_ascii=False),
                            },
                        )
                        associations += 1
            await session.commit()
    return len(item_ids), associations


def main() -> None:
    items, associations = asyncio.run(synchronize_provenance())
    print(f"Inspected {items} items; stored {associations} pseudonymous associations")


if __name__ == "__main__":
    main()
