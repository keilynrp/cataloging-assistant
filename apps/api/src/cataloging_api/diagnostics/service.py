from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from cataloging_api.db.models import DSpaceItem
from cataloging_api.diagnostics.engine import evaluate_metadata, group_metadata_values
from cataloging_api.diagnostics.repository import replace_item_findings
from cataloging_api.vocabularies.service import load_active_vocabulary_rules


class DiagnosticsService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        required_fields: tuple[str, ...] = (),
        batch_size: int = 100,
    ) -> None:
        self.session_factory = session_factory
        self.required_fields = required_fields
        self.batch_size = batch_size

    async def rebuild(self) -> dict[str, object]:
        async with self.session_factory() as session:
            vocabularies = await load_active_vocabulary_rules(session)

        items_evaluated = 0
        findings_total = 0
        codes: Counter[str] = Counter()
        offset = 0

        while True:
            async with self.session_factory() as session:
                result = await session.scalars(
                    select(DSpaceItem)
                    .where(DSpaceItem.is_active.is_(True))
                    .options(selectinload(DSpaceItem.metadata_values))
                    .order_by(DSpaceItem.uuid)
                    .offset(offset)
                    .limit(self.batch_size)
                )
                items = list(result)
                if not items:
                    break

                for item in items:
                    metadata_values = [(value.field, value.value) for value in item.metadata_values]
                    findings = evaluate_metadata(
                        group_metadata_values(metadata_values),
                        required_fields=self.required_fields,
                        vocabularies=vocabularies,
                    )
                    codes.update(finding.code for finding in findings)
                    findings_total += await replace_item_findings(
                        session,
                        item_uuid=item.uuid,
                        source_hash=item.source_hash,
                        metadata_values=metadata_values,
                        required_fields=self.required_fields,
                        vocabularies=vocabularies,
                        collection_uuid=item.collection_uuid,
                    )
                    items_evaluated += 1
                await session.commit()
                offset += len(items)

        return {
            "items_evaluated": items_evaluated,
            "findings_total": findings_total,
            "by_code": dict(sorted(codes.items())),
        }
