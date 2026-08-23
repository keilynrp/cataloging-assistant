from __future__ import annotations

from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.dspace.client import DSpaceClient, DSpaceError, HalCollectionPage
from cataloging_api.dspace.contract_store import (
    DSpaceContractSyncRun,
    RUN_INTERRUPTED,
    RUN_RUNNING,
    checkpoint_next_page,
    create_sync_run,
    find_resumable_run,
    mark_run_complete,
    mark_run_failed,
    mark_run_interrupted,
    persist_page_and_advance_checkpoint,
)

COLLECTOR_VERSION = "vertical-022/1"

SurfaceLoader = Callable[..., Awaitable[HalCollectionPage]]


async def _collect_surface(
    session: AsyncSession,
    *,
    run: DSpaceContractSyncRun,
    surface: str,
    endpoint: str,
    loader: SurfaceLoader,
    page_size: int,
) -> None:
    page_number = checkpoint_next_page(run, surface)

    while True:
        page = await loader(page=page_number, size=page_size)
        if page.page != page_number:
            raise DSpaceError(
                "invalid_hal",
                f"DSpace returned page {page.page} for requested page {page_number} at {endpoint}",
            )

        await persist_page_and_advance_checkpoint(
            session,
            run=run,
            surface=surface,
            endpoint=endpoint,
            page_number=page.page,
            request_params={"page": page_number, "size": page_size},
            raw_payload=page.raw_payload,
        )
        # Evidence + checkpoint become durable atomically before another page is requested.
        await session.commit()

        if page.total_pages <= page.page + 1:
            return
        page_number = checkpoint_next_page(run, surface)


async def collect_contract_run(
    session: AsyncSession,
    client: DSpaceClient,
    *,
    collector_version: str = COLLECTOR_VERSION,
    page_size: int = 100,
) -> DSpaceContractSyncRun:
    """Collect all required contract surfaces with resumable page checkpoints.

    This slice creates no comparable snapshot and performs no baseline promotion.
    A complete run is only an immutable acquisition unit for later canonicalization.
    """

    run = await find_resumable_run(session, collector_version=collector_version)
    if run is None:
        run = await create_sync_run(session, collector_version=collector_version)
        await session.commit()
    elif run.status == RUN_INTERRUPTED:
        run.status = RUN_RUNNING
        run.error_code = None
        run.error_message = None
        run.failed_at = None
        await session.commit()

    surfaces: tuple[tuple[str, str, SurfaceLoader], ...] = (
        ("metadata_schemas", "/core/metadataschemas", client.get_metadata_schemas_page),
        ("metadata_fields", "/core/metadatafields", client.get_metadata_fields_page),
        (
            "submission_definitions",
            "/config/submissiondefinitions",
            client.get_submission_definitions_page,
        ),
        (
            "submission_sections",
            "/config/submissionsections",
            client.get_submission_sections_page,
        ),
    )

    try:
        for surface, endpoint, loader in surfaces:
            await _collect_surface(
                session,
                run=run,
                surface=surface,
                endpoint=endpoint,
                loader=loader,
                page_size=page_size,
            )
    except DSpaceError as exc:
        await mark_run_interrupted(
            session,
            run=run,
            error_code=exc.code,
            error_message=str(exc),
        )
        await session.commit()
        raise
    except Exception as exc:
        await mark_run_failed(
            session,
            run=run,
            error_code="collector_error",
            error_message=str(exc),
        )
        await session.commit()
        raise

    await mark_run_complete(session, run=run)
    await session.commit()
    return run
