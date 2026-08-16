import hashlib
import json
import unicodedata
import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cataloging_api.db.models import (
    CatalogControlledTerm,
    CatalogVocabularyRevision,
    DSpaceItem,
    NotificationSeverity,
)
from cataloging_api.diagnostics.engine import VocabularyRule
from cataloging_api.notifications.constants import EventType
from cataloging_api.notifications.producer import record_notification_event

CONTROLLED_FIELDS = (
    "dc.subject.linguisticFamily",
    "dc.subject.linguisticBranch",
    "dc.subject.linguiscgroup",
    "dc.subject.linguisticVariant",
    "dc.description.registeredLanguage",
)


class VocabularyValidationError(ValueError):
    pass


class VocabularyConflictError(RuntimeError):
    pass


def normalize_term(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip().casefold()


def vocabulary_request_fingerprint(
    *,
    field: str,
    name: str,
    source_uri: str,
    version_label: str,
    approved_by: str,
    approval_note: str,
    terms: Sequence[dict[str, str | None]],
) -> str:
    payload = {
        "field": field.strip(),
        "name": name.strip(),
        "source_uri": source_uri.strip(),
        "version_label": version_label.strip(),
        "approved_by": approved_by.strip(),
        "approval_note": approval_note.strip(),
        "terms": [
            {
                "value": term["value"].strip() if term["value"] else "",
                "authority": (term.get("authority") or "").strip() or None,
                "language": (term.get("language") or "").strip() or None,
            }
            for term in terms
        ],
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def prepare_terms(
    terms: Sequence[dict[str, str | None]],
) -> list[dict[str, str | None]]:
    prepared: list[dict[str, str | None]] = []
    seen: set[str] = set()
    for term in terms:
        literal = (term.get("value") or "").strip()
        normalized = normalize_term(literal)
        if not literal:
            raise VocabularyValidationError("Controlled terms cannot be empty")
        if normalized in seen:
            raise VocabularyValidationError(
                f"Duplicate controlled term after normalization: {literal}"
            )
        seen.add(normalized)
        prepared.append(
            {
                "value": literal,
                "normalized_value": normalized,
                "authority": (term.get("authority") or "").strip() or None,
                "language": (term.get("language") or "").strip() or None,
            }
        )
    if not prepared:
        raise VocabularyValidationError("At least one controlled term is required")
    return prepared


async def replace_active_vocabulary(
    session: AsyncSession,
    *,
    request_id: uuid.UUID,
    field: str,
    name: str,
    source_uri: str,
    version_label: str,
    approved_by: str,
    approval_note: str,
    terms: Sequence[dict[str, str | None]],
) -> CatalogVocabularyRevision:
    field = field.strip()
    if field not in CONTROLLED_FIELDS:
        raise VocabularyValidationError("Field is not eligible for controlled vocabulary")
    prepared_terms = prepare_terms(terms)
    fingerprint = vocabulary_request_fingerprint(
        field=field,
        name=name,
        source_uri=source_uri,
        version_label=version_label,
        approved_by=approved_by,
        approval_note=approval_note,
        terms=prepared_terms,
    )
    existing = await session.scalar(
        select(CatalogVocabularyRevision)
        .where(CatalogVocabularyRevision.request_id == request_id)
        .options(selectinload(CatalogVocabularyRevision.terms))
    )
    if existing is not None:
        if existing.request_fingerprint != fingerprint:
            raise VocabularyConflictError("Request identifier was reused with different data")
        return existing

    await session.execute(
        select(CatalogVocabularyRevision)
        .where(
            CatalogVocabularyRevision.field == field,
            CatalogVocabularyRevision.is_active.is_(True),
        )
        .with_for_update()
    )
    await session.execute(
        update(CatalogVocabularyRevision)
        .where(
            CatalogVocabularyRevision.field == field,
            CatalogVocabularyRevision.is_active.is_(True),
        )
        .values(is_active=False)
    )
    revision = CatalogVocabularyRevision(
        request_id=request_id,
        request_fingerprint=fingerprint,
        field=field,
        name=name.strip(),
        source_uri=source_uri.strip(),
        version_label=version_label.strip(),
        approved_by=approved_by.strip(),
        approval_note=approval_note.strip(),
        is_active=True,
    )
    revision.terms = [
        CatalogControlledTerm(
            value=term["value"] or "",
            normalized_value=term["normalized_value"] or "",
            authority=term["authority"],
            language=term["language"],
            position=position,
        )
        for position, term in enumerate(prepared_terms)
    ]
    session.add(revision)
    await session.flush()
    await record_notification_event(
        session,
        event_type=EventType.VOCABULARY_PROMOTED,
        aggregate_type="vocabulary_revision",
        aggregate_id=str(revision.revision_id),
        severity=NotificationSeverity.info,
        title="Vocabulario controlado actualizado",
        summary=f"{revision.name} · {revision.version_label} aprobado por {revision.approved_by}.",
        deduplication_key=f"vocabulary.promoted:{revision.revision_id}",
        target_path="/controlled-terms",
    )
    return revision


async def list_vocabulary_revisions(
    session: AsyncSession,
    *,
    field: str | None = None,
    include_history: bool = False,
) -> list[CatalogVocabularyRevision]:
    query = select(CatalogVocabularyRevision).options(selectinload(CatalogVocabularyRevision.terms))
    if field:
        query = query.where(CatalogVocabularyRevision.field == field)
    if not include_history:
        query = query.where(CatalogVocabularyRevision.is_active.is_(True))
    result = await session.scalars(
        query.order_by(
            CatalogVocabularyRevision.field,
            CatalogVocabularyRevision.created_at.desc(),
        )
    )
    return list(result.unique())


async def load_active_vocabulary_rules(
    session: AsyncSession,
) -> dict[str, VocabularyRule]:
    revisions = await list_vocabulary_revisions(session)
    return {
        revision.field: VocabularyRule(
            revision_key=f"{revision.field}:{revision.revision_id}",
            name=revision.name,
            source_uri=revision.source_uri,
            version_label=revision.version_label,
            approved_by=revision.approved_by,
            terms=frozenset(term.value for term in revision.terms),
        )
        for revision in revisions
    }


def build_metadata_validation_snapshot(
    metadata: Mapping[str, Sequence[str]],
    vocabularies: Mapping[str, VocabularyRule],
) -> dict[str, object]:
    fields: list[dict[str, object]] = []
    any_configured = False
    any_invalid = False
    for field in CONTROLLED_FIELDS:
        if field not in metadata:
            continue
        values = [value.strip() for value in metadata[field] if value.strip()]
        vocabulary = vocabularies.get(field)
        if vocabulary is None:
            fields.append(
                {
                    "field": field,
                    "status": "no_vocabulary",
                    "vocabulary": None,
                    "values": [{"value": value, "approved": None} for value in values],
                }
            )
            continue

        any_configured = True
        value_results = [
            {"value": value, "approved": value in vocabulary.terms} for value in values
        ]
        invalid = any(result["approved"] is False for result in value_results)
        any_invalid = any_invalid or invalid
        fields.append(
            {
                "field": field,
                "status": "no_values" if not values else "invalid" if invalid else "valid",
                "vocabulary": {
                    "revision_key": vocabulary.revision_key,
                    "name": vocabulary.name,
                    "source_uri": vocabulary.source_uri,
                    "version_label": vocabulary.version_label,
                    "approved_by": vocabulary.approved_by,
                },
                "values": value_results,
            }
        )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "invalid" if any_invalid else "valid" if any_configured else "not_configured",
        "vocabulary_profile": sorted(
            vocabulary.profile_key for vocabulary in vocabularies.values()
        ),
        "fields": fields,
    }


async def validate_item_metadata(
    session: AsyncSession,
    item_uuid: uuid.UUID,
) -> dict[str, object] | None:
    item = await session.scalar(
        select(DSpaceItem)
        .where(DSpaceItem.uuid == item_uuid, DSpaceItem.is_active.is_(True))
        .options(selectinload(DSpaceItem.metadata_values))
    )
    if item is None:
        return None
    revisions = await list_vocabulary_revisions(session)
    by_field = {revision.field: revision for revision in revisions}
    metadata: dict[str, list[str]] = {}
    for entry in item.metadata_values:
        if entry.field in CONTROLLED_FIELDS and entry.value.strip():
            metadata.setdefault(entry.field, []).append(entry.value.strip())

    fields: list[dict[str, object]] = []
    any_configured = False
    any_invalid = False
    for field in CONTROLLED_FIELDS:
        revision = by_field.get(field)
        values = metadata.get(field, [])
        if revision is None:
            fields.append(
                {
                    "field": field,
                    "status": "no_vocabulary",
                    "vocabulary": None,
                    "values": [
                        {"value": value, "approved": False, "matched_term": None}
                        for value in values
                    ],
                }
            )
            continue
        any_configured = True
        literal_terms = {term.value: term for term in revision.terms}
        value_results = [
            {
                "value": value,
                "approved": value in literal_terms,
                "matched_term": literal_terms.get(value),
            }
            for value in values
        ]
        invalid = any(not result["approved"] for result in value_results)
        any_invalid = any_invalid or invalid
        fields.append(
            {
                "field": field,
                "status": "no_values" if not values else "invalid" if invalid else "valid",
                "vocabulary": revision,
                "values": value_results,
            }
        )

    return {
        "item_uuid": item.uuid,
        "source_hash": item.source_hash,
        "status": "invalid" if any_invalid else "valid" if any_configured else "not_configured",
        "fields": fields,
    }
