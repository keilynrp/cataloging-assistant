from __future__ import annotations

import hashlib
import re
import uuid
from collections import defaultdict
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.cataloging_contract import (
    CONTRACT_VERSION,
    DRAFTABLE_LINGUISTIC_FIELDS,
    EVIDENCE_STATES,
    FIELDS,
)
from cataloging_api.db.models import DSpaceItem
from cataloging_api.drafts.service import append_draft_revision, create_draft
from cataloging_api.evidence.models import (
    CatalogEvidenceCandidate,
    CatalogEvidenceSession,
    CatalogEvidenceSource,
)
from cataloging_api.vocabularies.service import load_active_vocabulary_rules

MAX_TEXT_CHARS = 250_000
FIELD_NAMES = {field.metadata_field for field in FIELDS}
FIELD_LINE = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*:\s*(.+?)\s*$")
DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
ISSN_RE = re.compile(r"\b\d{4}-\d{3}[\dXx]\b")
ISBN_RE = re.compile(r"\b(?:97[89][- ]?)?(?:\d[- ]?){9}[\dXx]\b")


class EvidenceValidationError(ValueError):
    pass


class EvidenceStaleError(RuntimeError):
    pass


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalized_source_payload(
    *,
    url: str | None,
    text: str | None,
) -> list[dict[str, str | None]]:
    sources: list[dict[str, str | None]] = []
    if url and url.strip():
        locator = url.strip()
        if not locator.startswith(("https://", "http://")):
            raise EvidenceValidationError("External URL must use http or https")
        sources.append(
            {
                "kind": "url",
                "locator": locator,
                "content_text": None,
                "media_type": "text/uri-list",
            }
        )
    if text and text.strip():
        clean = text.strip()
        if len(clean) > MAX_TEXT_CHARS:
            raise EvidenceValidationError(
                f"Evidence text exceeds {MAX_TEXT_CHARS} characters"
            )
        sources.append(
            {
                "kind": "text",
                "locator": None,
                "content_text": clean,
                "media_type": "text/plain",
            }
        )
    if not sources:
        raise EvidenceValidationError("At least one URL or text source is required")
    return sources


async def create_evidence_session(
    session: AsyncSession,
    *,
    item_uuid: uuid.UUID | None,
    created_by: str,
    url: str | None,
    text: str | None,
) -> CatalogEvidenceSession:
    author = created_by.strip()
    if len(author) < 2 or len(author) > 120:
        raise EvidenceValidationError("created_by must contain 2 to 120 characters")

    item: DSpaceItem | None = None
    if item_uuid is not None:
        item = await session.scalar(
            select(DSpaceItem).where(
                DSpaceItem.uuid == item_uuid,
                DSpaceItem.is_active.is_(True),
            )
        )
        if item is None:
            raise EvidenceValidationError("Active DSpace item not found")

    evidence_session = CatalogEvidenceSession(
        item_uuid=item_uuid,
        base_source_hash=item.source_hash if item else None,
        contract_version=CONTRACT_VERSION,
        created_by=author,
    )
    session.add(evidence_session)
    await session.flush()

    for source in _normalized_source_payload(url=url, text=text):
        material = source["content_text"] or source["locator"] or ""
        session.add(
            CatalogEvidenceSource(
                session_id=evidence_session.session_id,
                kind=source["kind"] or "text",
                locator=source["locator"],
                content_text=source["content_text"],
                content_hash=_sha256(material),
                media_type=source["media_type"],
                metadata_json={"captured_by": author, "immutable_snapshot": True},
            )
        )
    await session.flush()
    return evidence_session


def _candidate_rows(
    source: CatalogEvidenceSource,
) -> Iterable[tuple[str, str, dict[str, object]]]:
    if source.kind == "url" and source.locator:
        yield "dc.identifier.url", source.locator, {
            "kind": "source_url",
            "locator": source.locator,
        }
        return
    if source.kind != "text" or not source.content_text:
        return

    text = source.content_text
    seen: set[tuple[str, str]] = set()
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = FIELD_LINE.match(line)
        if match and match.group(1) in FIELD_NAMES:
            key = (match.group(1), match.group(2).strip())
            if key not in seen:
                seen.add(key)
                yield key[0], key[1], {
                    "kind": "explicit_field_line",
                    "line": line_number,
                    "quote": line[:500],
                }

    detectors = (
        ("dc.identifier.doi", DOI_RE),
        ("dc.identifier.issn", ISSN_RE),
        ("dc.identifier.isbn", ISBN_RE),
    )
    for field, pattern in detectors:
        for match in pattern.finditer(text):
            value = match.group(0).rstrip(".,;)")
            key = (field, value)
            if key in seen:
                continue
            seen.add(key)
            yield field, value, {
                "kind": "deterministic_pattern",
                "start": match.start(),
                "end": match.end(),
                "quote": text[
                    max(0, match.start() - 80) : min(len(text), match.end() + 80)
                ],
            }


async def extract_evidence_candidates(
    session: AsyncSession,
    evidence_session: CatalogEvidenceSession,
) -> list[CatalogEvidenceCandidate]:
    existing = list(
        await session.scalars(
            select(CatalogEvidenceCandidate)
            .where(
                CatalogEvidenceCandidate.session_id == evidence_session.session_id
            )
            .order_by(
                CatalogEvidenceCandidate.created_at,
                CatalogEvidenceCandidate.candidate_id,
            )
        )
    )
    if existing:
        return existing

    sources = list(
        await session.scalars(
            select(CatalogEvidenceSource)
            .where(CatalogEvidenceSource.session_id == evidence_session.session_id)
            .order_by(
                CatalogEvidenceSource.created_at,
                CatalogEvidenceSource.source_id,
            )
        )
    )
    vocabularies = await load_active_vocabulary_rules(session)
    candidates: list[CatalogEvidenceCandidate] = []
    for source in sources:
        for field, value, evidence in _candidate_rows(source):
            vocabulary = vocabularies.get(field)
            validation = {
                "status": (
                    "no_vocabulary"
                    if vocabulary is None
                    else "valid"
                    if value in vocabulary.terms
                    else "invalid"
                ),
                "vocabulary_revision": (
                    vocabulary.revision_key if vocabulary else None
                ),
            }
            candidate = CatalogEvidenceCandidate(
                session_id=evidence_session.session_id,
                source_id=source.source_id,
                metadata_field=field,
                value=value,
                evidence_state="EXTRAÍDO",
                evidence_json=evidence,
                validation_json=validation,
            )
            session.add(candidate)
            candidates.append(candidate)
    await session.flush()
    return candidates


async def get_evidence_session(
    session: AsyncSession,
    session_id: uuid.UUID,
) -> tuple[
    CatalogEvidenceSession | None,
    list[CatalogEvidenceSource],
    list[CatalogEvidenceCandidate],
    bool,
]:
    evidence_session = await session.get(CatalogEvidenceSession, session_id)
    if evidence_session is None:
        return None, [], [], False
    sources = list(
        await session.scalars(
            select(CatalogEvidenceSource)
            .where(CatalogEvidenceSource.session_id == session_id)
            .order_by(
                CatalogEvidenceSource.created_at,
                CatalogEvidenceSource.source_id,
            )
        )
    )
    candidates = list(
        await session.scalars(
            select(CatalogEvidenceCandidate)
            .where(CatalogEvidenceCandidate.session_id == session_id)
            .order_by(
                CatalogEvidenceCandidate.created_at,
                CatalogEvidenceCandidate.candidate_id,
            )
        )
    )
    stale = False
    if evidence_session.item_uuid and evidence_session.base_source_hash:
        current_hash = await session.scalar(
            select(DSpaceItem.source_hash).where(
                DSpaceItem.uuid == evidence_session.item_uuid,
                DSpaceItem.is_active.is_(True),
            )
        )
        stale = current_hash is None or current_hash != evidence_session.base_source_hash
    return evidence_session, sources, candidates, stale


async def copy_candidates_to_draft(
    session: AsyncSession,
    *,
    evidence_session: CatalogEvidenceSession,
    candidate_ids: list[uuid.UUID],
    request_id: uuid.UUID,
    author: str,
    note: str,
    draft_id: uuid.UUID | None,
    expected_version: int | None,
):
    if evidence_session.item_uuid is None:
        raise EvidenceValidationError(
            "Evidence session is not attached to a DSpace item"
        )

    current_hash = await session.scalar(
        select(DSpaceItem.source_hash).where(
            DSpaceItem.uuid == evidence_session.item_uuid,
            DSpaceItem.is_active.is_(True),
        )
    )
    if current_hash is None or current_hash != evidence_session.base_source_hash:
        raise EvidenceStaleError("DSpace item changed after evidence capture")

    selected = list(
        await session.scalars(
            select(CatalogEvidenceCandidate).where(
                CatalogEvidenceCandidate.session_id == evidence_session.session_id,
                CatalogEvidenceCandidate.candidate_id.in_(candidate_ids),
            )
        )
    )
    if len(selected) != len(set(candidate_ids)):
        raise EvidenceValidationError(
            "One or more candidates do not belong to this session"
        )

    grouped: dict[str, list[str]] = defaultdict(list)
    for candidate in selected:
        if candidate.evidence_state not in EVIDENCE_STATES:
            raise EvidenceValidationError(
                "Candidate contains an unsupported evidence state"
            )
        if candidate.metadata_field not in DRAFTABLE_LINGUISTIC_FIELDS:
            raise EvidenceValidationError(
                "Field is evidence-only and cannot be copied to a linguistic draft: "
                f"{candidate.metadata_field}"
            )
        if candidate.validation_json.get("status") == "invalid":
            raise EvidenceValidationError(
                "Candidate is outside the active controlled vocabulary: "
                f"{candidate.metadata_field}"
            )
        grouped[candidate.metadata_field].append(candidate.value)

    if not grouped:
        raise EvidenceValidationError("At least one draftable candidate is required")
    provenance_note = (
        f"{note.strip()} [evidence-session:{evidence_session.session_id}]"
    )
    if draft_id is None:
        return await create_draft(
            session,
            item_uuid=evidence_session.item_uuid,
            request_id=request_id,
            author=author,
            note=provenance_note,
            changes=dict(grouped),
        )
    if expected_version is None:
        raise EvidenceValidationError(
            "expected_version is required when revising a draft"
        )
    return await append_draft_revision(
        session,
        item_uuid=evidence_session.item_uuid,
        draft_id=draft_id,
        request_id=request_id,
        expected_version=expected_version,
        author=author,
        note=provenance_note,
        changes=dict(grouped),
    )
