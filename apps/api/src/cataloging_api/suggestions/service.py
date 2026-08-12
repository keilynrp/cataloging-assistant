import hashlib
import json
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.db.models import CatalogSuggestion, DSpaceItem, NotificationSeverity
from cataloging_api.notifications.constants import EventType
from cataloging_api.notifications.producer import record_notification_event
from cataloging_api.similarity.service import find_similar_items

METHOD = "similarity-consensus"
METHOD_VERSION = "1"


LINGUISTIC_FIELDS = (
    "dc.subject.linguisticFamily",
    "dc.subject.linguisticBranch",
    "dc.subject.linguiscgroup",
    "dc.description.registeredLanguage",
)


@dataclass(frozen=True)
class Suggestion:
    field: str
    value: str
    confidence: float
    supporting_item_uuids: list[uuid.UUID]
    explanation: str


async def suggest_missing_metadata(
    session: AsyncSession, item_uuid: uuid.UUID
) -> list[Suggestion] | None:
    result = await find_similar_items(session, item_uuid=item_uuid, limit=12)
    if result.source is None:
        return None
    present = {value.field for value in result.source.metadata_values if value.value.strip()}
    votes: dict[str, dict[str, list[uuid.UUID]]] = {field: {} for field in LINGUISTIC_FIELDS}
    for neighbor, match in result.matches:
        if match.score < 0.25:
            continue
        for value in neighbor.metadata_values:
            if value.field in votes and value.value.strip():
                votes[value.field].setdefault(value.value, []).append(neighbor.uuid)
    proposals: list[Suggestion] = []
    for field, choices in votes.items():
        if field in present or not choices:
            continue
        value, support = max(choices.items(), key=lambda entry: (len(entry[1]), entry[0]))
        total = sum(len(rows) for rows in choices.values())
        if len(support) < 2 or len(support) / total < 0.75:
            continue
        proposals.append(
            Suggestion(
                field,
                value,
                round(min(0.95, 0.45 + 0.15 * len(support)), 2),
                support,
                "Consenso entre vecinos estructuralmente similares; requiere revisión humana.",
            )
        )
    return proposals


def suggestion_fingerprint(
    *, item_uuid: uuid.UUID, source_hash: str, suggestion: Suggestion
) -> str:
    payload = {
        "item_uuid": str(item_uuid),
        "source_hash": source_hash,
        "field": suggestion.field,
        "value": suggestion.value,
        "method": METHOD,
        "method_version": METHOD_VERSION,
        "supporting_item_uuids": sorted(map(str, suggestion.supporting_item_uuids)),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


async def persist_current_suggestions(
    session: AsyncSession, item_uuid: uuid.UUID
) -> list[CatalogSuggestion] | None:
    proposals = await suggest_missing_metadata(session, item_uuid)
    if proposals is None:
        return None
    item = await session.scalar(
        select(DSpaceItem).where(DSpaceItem.uuid == item_uuid, DSpaceItem.is_active.is_(True))
    )
    if item is None:
        return None
    rows: list[CatalogSuggestion] = []
    for proposal in proposals:
        fingerprint = suggestion_fingerprint(
            item_uuid=item_uuid, source_hash=item.source_hash, suggestion=proposal
        )
        existing = await session.scalar(
            select(CatalogSuggestion).where(CatalogSuggestion.fingerprint == fingerprint)
        )
        if existing is not None:
            rows.append(existing)
            continue
        row = CatalogSuggestion(
            item_uuid=item_uuid,
            fingerprint=fingerprint,
            source_hash=item.source_hash,
            field=proposal.field,
            proposed_value=proposal.value,
            confidence=proposal.confidence,
            method=METHOD,
            method_version=METHOD_VERSION,
            explanation=proposal.explanation,
            evidence={
                "supporting_item_uuids": [str(value) for value in proposal.supporting_item_uuids]
            },
        )
        session.add(row)
        await session.flush()
        await record_notification_event(
            session,
            event_type=EventType.SUGGESTION_PENDING,
            aggregate_type="suggestion",
            aggregate_id=str(row.suggestion_id),
            collection_uuid=item.collection_uuid,
            severity=NotificationSeverity.info,
            title="Sugerencia pendiente de decisión",
            summary=f"Propuesta para {row.field}: {row.proposed_value}",
            deduplication_key=f"suggestion.pending:{row.suggestion_id}",
            target_path=f"/items/{item_uuid}",
        )
        rows.append(row)
    return rows
