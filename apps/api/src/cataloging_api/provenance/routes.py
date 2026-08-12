from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.config import get_settings
from cataloging_api.db.session import get_session
from cataloging_api.reviews.security import review_token_is_valid

router = APIRouter(prefix="/api/audit/provenance-actors", tags=["Restricted audit"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("")
async def list_provenance_actors(
    session: SessionDep,
    x_catalog_review_token: Annotated[str | None, Header()] = None,
) -> dict:
    configured = get_settings().catalog_review_token
    if not configured:
        raise HTTPException(503, "Restricted audit is not configured")
    if not review_token_is_valid(configured, x_catalog_review_token):
        raise HTTPException(401, "Invalid review token")
    rows = (
        await session.execute(
            text(
                "SELECT actor_key, actor_type, source_field, confidence, "
                "count(DISTINCT item_uuid) item_count, max(synced_at) synced_at "
                "FROM dspace_item_provenance_actors "
                "GROUP BY actor_key, actor_type, source_field, confidence "
                "ORDER BY item_count DESC, actor_key"
            )
        )
    ).mappings()
    actors = [
        {
            "actor_alias": f"actor-{row['actor_key'][:12]}",
            "actor_type": row["actor_type"],
            "source_field": row["source_field"],
            "confidence": row["confidence"],
            "item_count": row["item_count"],
            "synced_at": row["synced_at"],
        }
        for row in rows
    ]
    return {
        "actors": actors,
        "actor_count": len(actors),
        "item_count": sum(actor["item_count"] for actor in actors),
        "identity_disclosure": "pseudonymous_only",
    }
