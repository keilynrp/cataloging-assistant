import uuid
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.db.models import CatalogFinding, DSpaceItem, NotificationSeverity
from cataloging_api.diagnostics.engine import (
    VocabularyRule,
    diagnostic_profile_version,
    evaluate_metadata,
    group_metadata_values,
)
from cataloging_api.notifications.constants import EventType
from cataloging_api.notifications.producer import record_notification_event


async def replace_item_findings(
    session: AsyncSession,
    *,
    item_uuid: uuid.UUID,
    source_hash: str,
    metadata_values: Iterable[tuple[str, str]],
    required_fields: Iterable[str] = (),
    vocabularies: Mapping[str, VocabularyRule] | None = None,
    collection_uuid: uuid.UUID | None = None,
) -> int:
    required = tuple(required_fields)
    rules = dict(vocabularies or {})
    profile_version = diagnostic_profile_version(
        required,
        (rule.profile_key for rule in rules.values()),
    )
    findings = evaluate_metadata(
        group_metadata_values(metadata_values),
        required_fields=required,
        vocabularies=rules,
    )

    existing_fingerprints = set(
        (
            await session.execute(
                select(CatalogFinding.fingerprint).where(CatalogFinding.item_uuid == item_uuid)
            )
        ).scalars()
    )
    await session.execute(delete(CatalogFinding).where(CatalogFinding.item_uuid == item_uuid))
    session.add_all(
        [
            CatalogFinding(
                item_uuid=item_uuid,
                code=finding.code,
                severity=finding.severity,
                affected_fields=list(finding.affected_fields),
                explanation=finding.explanation,
                fingerprint=finding.fingerprint,
                rule_version=finding.rule_version,
                source_hash=source_hash,
            )
            for finding in findings
        ]
    )
    await session.execute(
        update(DSpaceItem)
        .where(DSpaceItem.uuid == item_uuid)
        .values(
            diagnostic_source_hash=source_hash,
            diagnostic_profile_version=profile_version,
            diagnosed_at=datetime.now(UTC),
        )
    )

    new_fingerprints = {finding.fingerprint for finding in findings} - existing_fingerprints
    if new_fingerprints:
        await record_notification_event(
            session,
            event_type=EventType.DIAGNOSTICS_CHANGED,
            aggregate_type="item",
            aggregate_id=str(item_uuid),
            collection_uuid=collection_uuid,
            severity=NotificationSeverity.warning,
            title="Nuevos hallazgos de diagnóstico",
            summary=f"{len(new_fingerprints)} hallazgo(s) nuevo(s) detectado(s).",
            deduplication_key=f"diagnostics.changed:{item_uuid}:{source_hash}:{profile_version}",
            target_path="/work-queue",
        )
    return len(findings)
