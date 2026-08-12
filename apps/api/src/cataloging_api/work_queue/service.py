import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cataloging_api.db.models import (
    CatalogDraft,
    CatalogDraftRevision,
    CatalogSuggestion,
    CatalogSuggestionDecision,
    DSpaceCollection,
    DSpaceItem,
    SyncRun,
)
from cataloging_api.work_queue.metrics import (
    SEVERITY_RANK,
    QueueItemState,
    classify_queue_item,
    closed_finding_fingerprints,
    derive_draft_state,
    summarize_queue,
)


async def build_work_queue(
    session: AsyncSession,
    collection_uuid: uuid.UUID,
    *,
    q: str | None,
    severity: str | None,
    finding_code: str | None,
    review: str | None,
    suggestion_filter: str | None,
    draft_filter: str | None,
    page: int,
    size: int,
) -> dict[str, Any] | None:
    collection = await session.get(DSpaceCollection, collection_uuid)
    if collection is None:
        return None

    items = list(
        await session.scalars(
            select(DSpaceItem)
            .where(
                DSpaceItem.collection_uuid == collection_uuid,
                DSpaceItem.is_active.is_(True),
            )
            .options(
                selectinload(DSpaceItem.findings),
                selectinload(DSpaceItem.review_decisions),
                selectinload(DSpaceItem.drafts)
                .selectinload(CatalogDraft.revisions)
                .selectinload(CatalogDraftRevision.decisions),
            )
            .order_by(DSpaceItem.uuid)
        )
    )
    item_by_uuid = {item.uuid: item for item in items}
    suggestions = list(
        await session.scalars(
            select(CatalogSuggestion).where(CatalogSuggestion.item_uuid.in_(item_by_uuid))
        )
    )
    decisions = list(
        await session.scalars(
            select(CatalogSuggestionDecision)
            .where(CatalogSuggestionDecision.item_uuid.in_(item_by_uuid))
            .order_by(CatalogSuggestionDecision.created_at)
        )
    )
    latest_decision = {decision.suggestion_id: decision.decision.value for decision in decisions}
    pending_suggestions: dict[uuid.UUID, int] = {}
    for suggestion in suggestions:
        current = item_by_uuid[suggestion.item_uuid]
        if suggestion.source_hash != current.source_hash:
            continue
        if latest_decision.get(suggestion.suggestion_id) not in {
            "accepted",
            "corrected",
            "rejected",
        }:
            pending_suggestions[suggestion.item_uuid] = (
                pending_suggestions.get(suggestion.item_uuid, 0) + 1
            )

    entries: list[tuple[DSpaceItem, QueueItemState]] = []
    all_states: list[QueueItemState] = []
    available_codes: set[str] = set()
    query = q.casefold().strip() if q else None
    for item in items:
        findings = [
            (finding.fingerprint, finding.code, finding.severity) for finding in item.findings
        ]
        review_decisions = [
            (decision.finding_fingerprint, decision.decision.value)
            for decision in item.review_decisions
        ]
        latest_review_by_fingerprint: dict[str, str] = {}
        for fingerprint, decision in review_decisions:
            latest_review_by_fingerprint[fingerprint] = decision
        reviewed_fingerprints = closed_finding_fingerprints(review_decisions)
        local_draft = item.drafts[0] if item.drafts else None
        stale = bool(local_draft and local_draft.base_source_hash != item.source_hash)
        latest_version = (
            local_draft.revisions[-1].version if local_draft and local_draft.revisions else None
        )
        draft_state = derive_draft_state(
            has_draft=local_draft is not None,
            draft_stale=stale,
            latest_decisions=(
                tuple(decision.decision.value for decision in local_draft.revisions[-1].decisions)
                if local_draft and local_draft.revisions
                else ()
            ),
            has_older_decisions=bool(
                local_draft
                and len(local_draft.revisions) > 1
                and any(revision.decisions for revision in local_draft.revisions[:-1])
            ),
        )
        state = classify_queue_item(
            findings,
            reviewed_fingerprints,
            has_draft=local_draft is not None,
            draft_stale=stale,
            pending_suggestion_count=pending_suggestions.get(item.uuid, 0),
            latest_draft_version=latest_version,
            draft_state=draft_state,
            deferred_finding_count=sum(
                latest_review_by_fingerprint.get(fingerprint) == "deferred"
                for fingerprint, _, _ in findings
            ),
        )
        all_states.append(state)
        available_codes.update(state.finding_codes)

        if not (state.finding_count or state.has_draft or state.pending_suggestion_count):
            continue
        if (
            query
            and query not in item.name.casefold()
            and query not in (item.handle or "").casefold()
        ):
            continue
        if severity and severity not in {finding[2] for finding in findings}:
            continue
        if finding_code and finding_code not in state.finding_codes:
            continue
        if review == "pending" and state.pending_finding_count == 0:
            continue
        if review == "reviewed" and not (
            state.finding_count > 0 and state.pending_finding_count == 0
        ):
            continue
        if review == "deferred" and state.deferred_finding_count == 0:
            continue
        if suggestion_filter == "pending" and state.pending_suggestion_count == 0:
            continue
        if suggestion_filter == "none" and state.pending_suggestion_count > 0:
            continue
        if draft_filter == "none" and state.has_draft:
            continue
        if draft_filter and draft_filter != "none" and state.draft_state != draft_filter:
            continue
        entries.append((item, state))

    entries.sort(
        key=lambda entry: (
            -SEVERITY_RANK.get(entry[1].highest_severity or "", 0),
            -entry[1].pending_finding_count,
            -int(entry[1].draft_stale),
            entry[0].name.casefold(),
        )
    )
    total = len(entries)
    page_entries = entries[page * size : (page + 1) * size]
    latest_sync = await session.scalar(
        select(SyncRun)
        .where(SyncRun.collection_uuid == collection_uuid)
        .order_by(SyncRun.started_at.desc())
        .limit(1)
    )

    return {
        "collection_uuid": collection.uuid,
        "collection_name": collection.name,
        "generated_at": datetime.now(UTC),
        "source": "PostgreSQL local derivado de DSpace",
        "grain": "Ítem activo con hallazgo vigente o borrador local",
        "latest_sync_status": latest_sync.status.value if latest_sync else None,
        "latest_sync_finished_at": latest_sync.finished_at if latest_sync else None,
        "available_finding_codes": sorted(available_codes),
        "summary": {"active_items": len(items), **summarize_queue(all_states)},
        "items": [
            {
                "uuid": item.uuid,
                "handle": item.handle,
                "name": item.name,
                "last_modified": item.last_modified,
                "finding_count": state.finding_count,
                "pending_finding_count": state.pending_finding_count,
                "pending_suggestion_count": state.pending_suggestion_count,
                "deferred_finding_count": state.deferred_finding_count,
                "finding_codes": list(state.finding_codes),
                "highest_severity": state.highest_severity,
                "has_draft": state.has_draft,
                "draft_stale": state.draft_stale,
                "latest_draft_version": state.latest_draft_version,
                "draft_state": state.draft_state,
                "priority": state.priority,
            }
            for item, state in page_entries
        ],
        "page": page,
        "size": size,
        "total": total,
    }
