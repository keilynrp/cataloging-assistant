import asyncio
import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from cataloging_api.config import Settings
from cataloging_api.db.models import NotificationSeverity, SyncRun, SyncStatus
from cataloging_api.dspace.client import DSpaceClient, DSpaceError
from cataloging_api.dspace.normalizer import ItemData, normalize_item
from cataloging_api.notifications.constants import EventType
from cataloging_api.notifications.producer import record_notification_event
from cataloging_api.sync.repository import mark_missing_inactive, upsert_collection, upsert_item
from cataloging_api.vocabularies.service import load_active_vocabulary_rules

logger = structlog.get_logger()


class SyncService:
    def __init__(
        self,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        client: DSpaceClient | None = None,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self._provided_client = client

    async def run(self, *, resume_page: int = 0) -> uuid.UUID:
        collection_uuid = uuid.UUID(self.settings.dspace_pilot_collection_uuid)
        run = SyncRun(
            collection_uuid=collection_uuid,
            status=SyncStatus.running,
            started_at=datetime.now(UTC),
            checkpoint_page=resume_page,
        )
        async with self.session_factory() as session:
            session.add(run)
            await session.commit()
            await session.refresh(run)
            vocabularies = await load_active_vocabulary_rules(session)

        client = self._provided_client or DSpaceClient(
            self.settings.dspace_base_url,
            timeout_seconds=self.settings.dspace_timeout_seconds,
            max_retries=self.settings.dspace_max_retries,
        )
        owns_client = self._provided_client is None
        seen: set[uuid.UUID] = set()
        errors: list[str] = []
        items_with_new_findings = 0
        try:
            collection = await client.get_collection(str(collection_uuid))
            async with self.session_factory() as session:
                await upsert_collection(session, collection)
                await session.commit()

            page_number = resume_page
            while True:
                page = await client.discover_items(
                    str(collection_uuid),
                    page=page_number,
                    size=self.settings.dspace_page_size,
                )
                snapshots = await self._fetch_page(client, page.items, str(collection_uuid))
                async with self.session_factory() as session:
                    for snapshot in snapshots:
                        if isinstance(snapshot, Exception):
                            errors.append(str(snapshot))
                            continue
                        seen.add(snapshot.uuid)
                        run.items_seen += 1
                        upsert_result = await upsert_item(
                            session,
                            snapshot,
                            required_fields=self.settings.required_fields,
                            vocabularies=vocabularies,
                        )
                        if upsert_result.changed:
                            run.items_changed += 1
                        if upsert_result.has_new_findings:
                            items_with_new_findings += 1
                    run.pages_processed += 1
                    run.checkpoint_page = page_number + 1
                    await session.merge(run)
                    await session.commit()

                logger.info(
                    "sync_page_completed",
                    run_id=str(run.run_id),
                    page=page_number,
                    items=len(page.items),
                    total=page.total_elements,
                )
                page_number += 1
                if page_number >= page.total_pages:
                    break

            async with self.session_factory() as session:
                if not errors and resume_page == 0:
                    await mark_missing_inactive(session, collection_uuid, seen)
                run.status = SyncStatus.partial if errors else SyncStatus.succeeded
                run.finished_at = datetime.now(UTC)
                run.error_code = "item_errors" if errors else None
                run.error_detail = "\n".join(errors[:20]) if errors else None
                run.metrics = {
                    "errors": len(errors),
                    "seen_this_process": len(seen),
                    "items_with_new_findings": items_with_new_findings,
                }
                merged_run = await session.merge(run)
                await self._emit_sync_events(session, merged_run, items_with_new_findings)
                await session.commit()
        except Exception as exc:
            async with self.session_factory() as session:
                run.status = SyncStatus.failed
                run.finished_at = datetime.now(UTC)
                run.error_code = exc.code if isinstance(exc, DSpaceError) else "unexpected_error"
                run.error_detail = str(exc)[:2000]
                merged_run = await session.merge(run)
                await self._emit_sync_events(session, merged_run, items_with_new_findings)
                await session.commit()
            raise
        finally:
            if owns_client:
                await client.aclose()
        return run.run_id

    async def _emit_sync_events(
        self, session: AsyncSession, run: SyncRun, items_with_new_findings: int
    ) -> None:
        if run.status == SyncStatus.failed:
            await record_notification_event(
                session,
                event_type=EventType.SYNC_FAILED,
                aggregate_type="sync_run",
                aggregate_id=str(run.run_id),
                collection_uuid=run.collection_uuid,
                severity=NotificationSeverity.error,
                title="Sincronización fallida",
                summary=(run.error_detail or "La sincronización no pudo completarse.")[:500],
                deduplication_key=f"sync.failed:{run.run_id}",
                target_path="/work-queue",
            )
            return
        await record_notification_event(
            session,
            event_type=EventType.SYNC_COMPLETED,
            aggregate_type="sync_run",
            aggregate_id=str(run.run_id),
            collection_uuid=run.collection_uuid,
            severity=NotificationSeverity.info,
            title="Sincronización completada",
            summary=f"{run.items_seen} ítems vistos, {run.items_changed} nuevos o modificados.",
            deduplication_key=f"sync.completed:{run.run_id}",
            target_path="/work-queue",
        )
        if run.items_changed > 0:
            await record_notification_event(
                session,
                event_type=EventType.ITEMS_CHANGED,
                aggregate_type="sync_run",
                aggregate_id=str(run.run_id),
                collection_uuid=run.collection_uuid,
                severity=NotificationSeverity.info,
                title="Ítems nuevos o modificados",
                summary=f"{run.items_changed} ítems cambiaron en la colección piloto.",
                deduplication_key=f"items.changed:{run.run_id}",
                target_path="/work-queue",
            )
        if items_with_new_findings > 0:
            await record_notification_event(
                session,
                event_type=EventType.DIAGNOSTICS_CHANGED,
                aggregate_type="sync_run",
                aggregate_id=str(run.run_id),
                collection_uuid=run.collection_uuid,
                severity=NotificationSeverity.warning,
                title="Nuevos hallazgos de diagnóstico",
                summary=(
                    f"{items_with_new_findings} ítem(s) con hallazgos nuevos tras esta "
                    "sincronización."
                ),
                deduplication_key=f"diagnostics.changed:sync:{run.run_id}",
                target_path="/work-queue",
            )

    async def _fetch_page(
        self,
        client: DSpaceClient,
        discover_items: list[dict[str, object]],
        collection_uuid: str,
    ) -> list[ItemData | Exception]:
        semaphore = asyncio.Semaphore(self.settings.dspace_max_concurrency)

        async def fetch(discover_item: dict[str, object]) -> ItemData:
            async with semaphore:
                item_uuid = str(discover_item["uuid"])
                raw_item = await client.get_item(item_uuid)
                raw_bundles = await client.get_item_bundles(item_uuid)
                bitstream_lists = await asyncio.gather(
                    *(client.get_bundle_bitstreams(str(bundle["uuid"])) for bundle in raw_bundles)
                )
                return normalize_item(
                    raw_item,
                    collection_uuid=collection_uuid,
                    bundles=list(zip(raw_bundles, bitstream_lists, strict=True)),
                )

        return await asyncio.gather(
            *(fetch(item) for item in discover_items), return_exceptions=True
        )
