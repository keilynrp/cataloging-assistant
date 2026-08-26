from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

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

COLLECTOR_VERSION = "vertical-022/3"
SurfaceLoader = Callable[..., Awaitable[HalCollectionPage]]


async def _collect_surface(
    session: AsyncSession,
    *,
    run: DSpaceContractSyncRun,
    surface: str,
    endpoint: str,
    loader: SurfaceLoader,
    page_size: int,
    request_params_extra: dict[str, Any] | None = None,
) -> None:
    page_number = checkpoint_next_page(run, surface)
    while True:
        page = await loader(page=page_number, size=page_size)
        if page.page != page_number:
            raise DSpaceError(
                "invalid_hal",
                f"DSpace returned page {page.page} for requested page {page_number} at {endpoint}",
            )
        request_params = {
            "page": page_number,
            "size": page_size,
            **(request_params_extra or {}),
        }
        await persist_page_and_advance_checkpoint(
            session,
            run=run,
            surface=surface,
            endpoint=endpoint,
            page_number=page.page,
            request_params=request_params,
            raw_payload=page.raw_payload,
        )
        await session.commit()
        if page.total_pages <= page.page + 1:
            return
        page_number = checkpoint_next_page(run, surface)


async def _collect_metadata_registry(
    session: AsyncSession,
    *,
    run: DSpaceContractSyncRun,
    client: DSpaceClient,
    page_size: int,
) -> None:
    """Collect schemas and every metadata field with explicit schema identity."""

    schema_prefixes: list[str] = []
    page_number = 0
    endpoint = "/core/metadataschemas"
    while True:
        page = await client.get_metadata_schemas_page(page=page_number, size=page_size)
        if page.page != page_number:
            raise DSpaceError(
                "invalid_hal",
                f"DSpace returned schema page {page.page} for requested page {page_number}",
            )
        for schema in page.items:
            prefix = schema.get("prefix")
            if not isinstance(prefix, str) or not prefix:
                raise DSpaceError("invalid_hal", "Metadata schema lacks a prefix")
            schema_prefixes.append(prefix)
        await persist_page_and_advance_checkpoint(
            session,
            run=run,
            surface="metadata_schemas",
            endpoint=endpoint,
            page_number=page.page,
            request_params={"page": page_number, "size": page_size},
            raw_payload=page.raw_payload,
        )
        await session.commit()
        if page.total_pages <= page.page + 1:
            break
        page_number += 1

    await _collect_surface(
        session,
        run=run,
        surface="metadata_fields",
        endpoint="/core/metadatafields",
        loader=client.get_metadata_fields_page,
        page_size=page_size,
    )

    by_schema_endpoint = "/core/metadatafields/search/bySchema"
    for prefix in sorted(set(schema_prefixes)):

        async def schema_loader(
            *, page: int, size: int, schema_prefix: str = prefix
        ) -> HalCollectionPage:
            return await client.get_metadata_fields_by_schema_page(
                schema_prefix,
                page=page,
                size=size,
            )

        await _collect_surface(
            session,
            run=run,
            surface=f"metadata_fields_by_schema:{prefix}",
            endpoint=by_schema_endpoint,
            loader=schema_loader,
            page_size=page_size,
            request_params_extra={"schema": prefix},
        )


async def _collect_active_definition(
    session: AsyncSession,
    *,
    run: DSpaceContractSyncRun,
    client: DSpaceClient,
    collection_uuid: str,
    page_size: int,
) -> None:
    surface = "active_submission_definition"
    endpoint = "/config/submissiondefinitions/search/findByCollection"

    payload = await client.get_submission_definition_for_collection(collection_uuid)
    definition_name = payload.get("name")
    if not isinstance(definition_name, str) or not definition_name:
        raise DSpaceError("invalid_hal", "Active submission definition lacks a name")
    await persist_page_and_advance_checkpoint(
        session,
        run=run,
        surface=surface,
        endpoint=endpoint,
        page_number=0,
        request_params={"uuid": collection_uuid},
        raw_payload=payload,
    )
    await session.commit()

    sections_endpoint = f"/config/submissiondefinitions/{definition_name}/sections"

    async def sections_loader(*, page: int, size: int) -> HalCollectionPage:
        return await client.get_submission_definition_sections_page(
            definition_name,
            page=page,
            size=size,
        )

    try:
        await _collect_surface(
            session,
            run=run,
            surface="active_submission_sections",
            endpoint=sections_endpoint,
            loader=sections_loader,
            page_size=page_size,
        )
    except DSpaceError as exc:
        if exc.status_code != 204:
            raise
        # The target DSpace 7.6.6 instance returns 204 No Content for this
        # documented linked resource. Preserve that HTTP observation explicitly
        # instead of treating it as an empty collection or aborting the entire run.
        await persist_page_and_advance_checkpoint(
            session,
            run=run,
            surface="active_submission_sections",
            endpoint=sections_endpoint,
            page_number=0,
            request_params={"page": 0, "size": page_size},
            raw_payload={
                "_observation": {
                    "observable": False,
                    "statusCode": 204,
                    "reason": "no_content",
                },
                "page": {
                    "number": 0,
                    "totalPages": 0,
                    "totalElements": 0,
                },
            },
        )
        await session.commit()


async def collect_contract_run(
    session: AsyncSession,
    client: DSpaceClient,
    *,
    collection_uuid: str,
    collector_version: str = COLLECTOR_VERSION,
    page_size: int = 100,
) -> DSpaceContractSyncRun:
    """Collect a complete collection-scoped contract observation."""

    if not collection_uuid:
        raise ValueError("collection_uuid_required")

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
        (
            "submission_forms",
            "/config/submissionforms",
            client.get_submission_forms_page,
        ),
    )

    try:
        await _collect_metadata_registry(
            session,
            run=run,
            client=client,
            page_size=page_size,
        )
        for surface_name, endpoint_path, loader in surfaces:
            await _collect_surface(
                session,
                run=run,
                surface=surface_name,
                endpoint=endpoint_path,
                loader=loader,
                page_size=page_size,
            )
        await _collect_active_definition(
            session,
            run=run,
            client=client,
            collection_uuid=collection_uuid,
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
