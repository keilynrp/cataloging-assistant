import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.db.models import (
    CatalogSuggestion,
    DSpaceCollection,
    DSpaceItem,
    SuggestionDecisionKind,
)
from cataloging_api.db.session import engine
from cataloging_api.suggestions.decisions import (
    SuggestionDecisionConflictError,
    SuggestionDecisionValidationError,
    record_suggestion_decision,
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_decision_is_idempotent_creates_draft_and_blocks_stale_source() -> None:
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        collection = DSpaceCollection(
            uuid=uuid.uuid4(), handle="test/suggestions", name="Suggestions", raw_json={}
        )
        item = DSpaceItem(
            uuid=uuid.uuid4(),
            collection=collection,
            handle="test/item",
            name="Item",
            raw_json={},
            source_hash="a" * 64,
        )
        suggestion = CatalogSuggestion(
            item=item,
            fingerprint="f" * 64,
            source_hash=item.source_hash,
            field="dc.subject.linguisticFamily",
            proposed_value="Tarasca",
            confidence=0.9,
            method="test",
            method_version="1",
            explanation="Evidence",
            evidence={},
        )
        session.add(suggestion)
        await session.flush()
        deferred = await record_suggestion_decision(
            session,
            suggestion_id=suggestion.suggestion_id,
            request_id=uuid.uuid4(),
            decision=SuggestionDecisionKind.deferred,
            corrected_value=None,
            reviewer="Catalogadora",
            note="Pendiente de verificar.",
        )
        assert deferred is not None
        assert deferred.draft_revision_id is None

        request_id = uuid.uuid4()
        decision = await record_suggestion_decision(
            session,
            suggestion_id=suggestion.suggestion_id,
            request_id=request_id,
            decision=SuggestionDecisionKind.accepted,
            corrected_value=None,
            reviewer="Catalogadora",
            note="Aceptada con evidencia.",
        )
        repeated = await record_suggestion_decision(
            session,
            suggestion_id=suggestion.suggestion_id,
            request_id=request_id,
            decision=SuggestionDecisionKind.accepted,
            corrected_value=None,
            reviewer="Catalogadora",
            note="Aceptada con evidencia.",
        )
        assert decision is not None and repeated is not None
        assert repeated.decision_id == decision.decision_id
        assert decision.draft_revision_id is not None

        item.source_hash = "b" * 64
        stale = CatalogSuggestion(
            item=item,
            fingerprint="g" * 64,
            source_hash="a" * 64,
            field="dc.subject.linguisticBranch",
            proposed_value="Tarasca",
            confidence=0.8,
            method="test",
            method_version="1",
            explanation="Old",
            evidence={},
        )
        session.add(stale)
        await session.flush()
        with pytest.raises(SuggestionDecisionValidationError):
            await record_suggestion_decision(
                session,
                suggestion_id=stale.suggestion_id,
                request_id=uuid.uuid4(),
                decision=SuggestionDecisionKind.accepted,
                corrected_value=None,
                reviewer="Catalogadora",
                note="Debe bloquearse.",
            )
        with pytest.raises(SuggestionDecisionConflictError):
            await record_suggestion_decision(
                session,
                suggestion_id=stale.suggestion_id,
                request_id=request_id,
                decision=SuggestionDecisionKind.rejected,
                corrected_value=None,
                reviewer="Catalogadora",
                note="Conflicto.",
            )
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
