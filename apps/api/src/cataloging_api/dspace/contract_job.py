from __future__ import annotations

import asyncio
import json

from cataloging_api.config import get_settings
from cataloging_api.db.session import SessionFactory
from cataloging_api.dspace.authenticated_client import ReadAuthenticatedDSpaceClient
from cataloging_api.dspace.contract_governance import get_contract_health, governed_hash
from cataloging_api.dspace.contract_materialize import materialize_snapshot_for_run
from cataloging_api.dspace.contract_sync_core import collect_contract_run


async def run_contract_sync_job() -> dict[str, object]:
    """Run one authenticated, read-only DSpace contract synchronization cycle."""

    settings = get_settings()
    if not settings.dspace_read_username or not settings.dspace_read_password:
        raise RuntimeError("dspace_read_credentials_required")

    async with SessionFactory() as session:
        async with ReadAuthenticatedDSpaceClient(
            settings.dspace_base_url,
            timeout_seconds=settings.dspace_timeout_seconds,
            max_retries=settings.dspace_max_retries,
        ) as client:
            await client.authenticate(
                settings.dspace_read_username,
                settings.dspace_read_password,
            )
            run = await collect_contract_run(
                session,
                client,
                collection_uuid=settings.dspace_pilot_collection_uuid,
                page_size=settings.dspace_page_size,
            )
            snapshot = await materialize_snapshot_for_run(session, run_id=run.run_id)
            health = await get_contract_health(session)

    return {
        "run_id": str(run.run_id),
        "snapshot_id": str(snapshot.snapshot_id),
        "snapshot_status": snapshot.status,
        "observed_hash": snapshot.semantic_hash,
        "effective_hash": snapshot.effective_hash,
        "governed_hash": governed_hash(snapshot),
        "resolution_inherited": snapshot.resolution_inherited_from_snapshot_id is not None,
        "active_snapshot_id": (
            str(health.active_snapshot_id) if health.active_snapshot_id is not None else None
        ),
        "contract_health": health.status,
        "last_verified_at": (
            health.last_verified_at.isoformat() if health.last_verified_at is not None else None
        ),
        "warning_count": health.warning_count,
    }


async def _main() -> None:
    result = await run_contract_sync_job()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(_main())
