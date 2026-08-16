from __future__ import annotations

import asyncio
import hashlib
import os
import re
import uuid
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import urlsplit

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cataloging_api.cataloging_contract import (
    CONTRACT_VERSION,
    DRAFTABLE_LINGUISTIC_FIELDS,
    EVIDENCE_STATES,
    FIELDS,
    CatalogField,
)
from cataloging_api.config import get_settings
from cataloging_api.db.models import CatalogDraft, DSpaceItem
from cataloging_api.drafts.service import append_draft_revision, create_draft
from cataloging_api.evidence.html_extraction import extract_html_text
from cataloging_api.evidence.models import (
    CatalogEvidenceCandidate,
    CatalogEvidenceSession,
    CatalogEvidenceSource,
)
from cataloging_api.evidence.net_policy import (
    DnsResolutionError,
    DnsResolver,
    TargetNotPublicError,
    UrlShapeError,
    resolve_public_ips,
)
from cataloging_api.evidence.pdf_extraction import (
    EXTRACTOR_NAME,
    MAX_PDF_BYTES,
    PdfRejectedError,
    extract_pdf_text,
    page_for_offset,
)
from cataloging_api.evidence.remote_fetch import (
    ContentTooLargeError,
    ContentTypeNotAllowedError,
    FetchTimeoutError,
    RedirectLimitError,
    RedirectLoopError,
    RemoteFetchOutcome,
    UpstreamError,
    fetch_remote_resource,
)
from cataloging_api.vocabularies.service import load_active_vocabulary_rules

logger = structlog.get_logger()

REMOTE_FETCH_POLICY_VERSION = "2026-08-16"

MAX_TEXT_CHARS = 250_000
FIELD_LINE = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*:\s*(.+?)\s*$")
DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
ISSN_RE = re.compile(r"\b\d{4}-\d{3}[\dXx]\b")
ISBN_RE = re.compile(r"\b(?:97[89][- ]?)?(?:\d[- ]?){9}[\dXx]\b")
BINDINGS_BY_ID = {field.binding_id: field for field in FIELDS}
BINDINGS_BY_METADATA: dict[str, list[CatalogField]] = defaultdict(list)
for contract_field in FIELDS:
    BINDINGS_BY_METADATA[contract_field.metadata_field].append(contract_field)


class EvidenceValidationError(ValueError):
    pass


class EvidencePdfTooLargeError(EvidenceValidationError):
    pass


class EvidencePdfInvalidTypeError(EvidenceValidationError):
    pass


class EvidencePdfTimeoutError(EvidenceValidationError):
    pass


class EvidenceRemoteFetchDisabledError(EvidenceValidationError):
    pass


class EvidenceRemoteUrlInvalidError(EvidenceValidationError):
    pass


class EvidenceRemoteTargetNotPublicError(EvidenceValidationError):
    pass


class EvidenceRemoteDnsResolutionError(EvidenceValidationError):
    pass


class EvidenceRemoteRedirectBlockedError(EvidenceValidationError):
    pass


class EvidenceRemoteRedirectLimitError(EvidenceValidationError):
    pass


class EvidenceRemoteContentTypeNotAllowedError(EvidenceValidationError):
    pass


class EvidenceRemoteContentTooLargeError(EvidenceValidationError):
    pass


class EvidenceRemoteContentInvalidError(EvidenceValidationError):
    pass


class EvidenceRemotePdfInvalidError(EvidenceValidationError):
    pass


class EvidenceRemotePdfTimeoutError(EvidenceValidationError):
    pass


class EvidenceRemoteFetchTimeoutError(EvidenceValidationError):
    pass


class EvidenceRemoteUpstreamError(EvidenceValidationError):
    pass


class EvidenceStaleError(RuntimeError):
    pass


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sanitize_filename(name: str) -> str:
    # Never trusted as a path: only ever used for display/audit. Strip any
    # directory components and control characters, cap length.
    base = os.path.basename((name or "").replace("\x00", "")).strip()
    return base[:255] if base else "documento.pdf"


def _pdf_storage_path(source_id: uuid.UUID) -> Path:
    # The on-disk name is derived solely from a server-generated UUID, never
    # from the uploaded filename, so path traversal via filename is not possible.
    directory = Path(get_settings().evidence_pdf_storage_dir)
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{source_id}.pdf"


def _write_pdf_bytes(source_id: uuid.UUID, data: bytes) -> None:
    _pdf_storage_path(source_id).write_bytes(data)


def delete_pdf_artifact(source_id: uuid.UUID) -> None:
    """Remove a PDF evidence artifact from disk, if present.

    Safe to call whether or not the corresponding row was ever persisted
    (e.g. flush succeeded but the caller's later commit failed) or the file
    is already gone.
    """
    _pdf_storage_path(source_id).unlink(missing_ok=True)


def _resolve_binding(key: str) -> tuple[CatalogField | None, str | None]:
    by_id = BINDINGS_BY_ID.get(key)
    if by_id is not None:
        return by_id, "binding_id"
    by_metadata = BINDINGS_BY_METADATA.get(key, [])
    if len(by_metadata) == 1:
        return by_metadata[0], "metadata_field"
    return None, None


def _binding_for_unique_metadata(metadata_field: str) -> CatalogField:
    bindings = BINDINGS_BY_METADATA.get(metadata_field, [])
    if len(bindings) != 1:
        raise EvidenceValidationError(
            f"Expected one binding for deterministic field: {metadata_field}"
        )
    return bindings[0]


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
    # A session may be created with neither: PDF (added afterward via
    # add_pdf_evidence_source) is an equally valid first source, so an
    # empty list here is a legitimate "not yet populated" session, not
    # an error.
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

    for position, source in enumerate(_normalized_source_payload(url=url, text=text)):
        material = source["content_text"] or source["locator"] or ""
        session.add(
            CatalogEvidenceSource(
                session_id=evidence_session.session_id,
                position=position,
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


async def _next_source_position(session: AsyncSession, session_id: uuid.UUID) -> int:
    current_max = await session.scalar(
        select(func.max(CatalogEvidenceSource.position)).where(
            CatalogEvidenceSource.session_id == session_id
        )
    )
    return 0 if current_max is None else current_max + 1


async def _extract_pdf_text_off_loop(data: bytes, *, timeout_seconds: float):
    """Run the pure-sync `extract_pdf_text` off the event loop, timeout-enforced.

    Shared by local PDF upload and remote PDF fetch so both get the exact
    same off-loop dispatch and the exact same configurable timeout
    (`EVIDENCE_PDF_EXTRACTION_TIMEOUT_SECONDS`) — neither path may call
    `extract_pdf_text` directly. Raises the stdlib `TimeoutError` or
    `PdfRejectedError` as-is; callers map both to their own domain-specific
    error types, since local and remote ingestion have distinct stable API
    codes for the same underlying failure.
    """
    return await asyncio.wait_for(
        asyncio.to_thread(extract_pdf_text, data), timeout=timeout_seconds
    )


async def add_pdf_evidence_source(
    session: AsyncSession,
    evidence_session: CatalogEvidenceSession,
    *,
    file_bytes: bytes,
    original_filename: str,
    content_type: str,
    author: str,
) -> CatalogEvidenceSource:
    """Ingest an uploaded PDF as a new evidence source.

    Only ever reads structure/text via pypdf (no JS, launch actions,
    embedded-file extraction, or link-following) and never performs network
    I/O. A rejected PDF (encrypted, corrupt, too many pages, not actually a
    PDF, or one that times out) raises before anything is written to disk
    or the database, so no partial state is left behind. If persistence
    fails *after* the file was written (e.g. a concurrent position
    collision), the file is unlinked before the error propagates.

    This only covers failure up to and including `flush()`. The row is not
    committed here, so a caller that commits separately and has that commit
    fail is responsible for calling `delete_pdf_artifact(source.source_id)`
    itself once it rolls back.
    """
    normalized_type = (content_type or "").split(";")[0].strip().lower()
    if normalized_type != "application/pdf" or not (original_filename or "").lower().endswith(
        ".pdf"
    ):
        raise EvidencePdfInvalidTypeError(
            "Only application/pdf uploads with a .pdf filename are accepted"
        )
    if len(file_bytes) > MAX_PDF_BYTES:
        raise EvidencePdfTooLargeError("PDF exceeds the maximum allowed size")

    try:
        result = await _extract_pdf_text_off_loop(
            file_bytes, timeout_seconds=get_settings().evidence_pdf_extraction_timeout_seconds
        )
    except TimeoutError as error:
        # Fails closed: nothing has been written to disk or the database yet.
        raise EvidencePdfTimeoutError(
            "PDF extraction exceeded the configured timeout"
        ) from error
    except PdfRejectedError as error:
        raise EvidenceValidationError(f"PDF rejected: {error.reason}") from error

    # Serialize position assignment for this session: without this lock, two
    # concurrent uploads could both read the same MAX(position) and race on
    # UNIQUE(session_id, position). The second transaction blocks here until
    # the first commits or rolls back, then reads an up-to-date MAX.
    await session.execute(
        select(CatalogEvidenceSession.session_id)
        .where(CatalogEvidenceSession.session_id == evidence_session.session_id)
        .with_for_update()
    )
    position = await _next_source_position(session, evidence_session.session_id)

    source_id = uuid.uuid4()
    _write_pdf_bytes(source_id, file_bytes)

    source = CatalogEvidenceSource(
        source_id=source_id,
        session_id=evidence_session.session_id,
        position=position,
        kind="pdf",
        locator=None,
        content_text=result.text or None,
        content_hash=_sha256_bytes(file_bytes),
        media_type="application/pdf",
        metadata_json={
            "captured_by": author,
            "immutable_snapshot": True,
            "original_filename": _sanitize_filename(original_filename),
        },
        extraction_status=result.status,
        extraction_metadata_json={
            "extractor": EXTRACTOR_NAME,
            "page_char_offsets": result.page_char_offsets,
        },
        extracted_text_hash=result.extracted_text_hash,
        page_count=result.page_count,
    )
    session.add(source)
    try:
        await session.flush()
    except Exception:
        delete_pdf_artifact(source_id)
        raise
    return source


async def add_remote_evidence_source(
    session: AsyncSession,
    evidence_session: CatalogEvidenceSession,
    *,
    url: str,
    author: str,
    resolver: DnsResolver = resolve_public_ips,
) -> CatalogEvidenceSource:
    """Fetch `url` under the SSRF/size/MIME policy and persist it as a source.

    Explicit, one-shot, backend-only fetch (ADR-016): no crawling, no
    following of links found in the downloaded content, no LLM, no DSpace
    write. `resolver` is a test seam only (default is the real DNS
    resolver); production callers never override it, so the SSRF policy in
    `net_policy` is exercised unmodified on every real request. The raw
    body is never written to disk, so there is no filesystem artifact to
    clean up if persistence fails after a successful fetch — only the SHA-256
    and, when applicable, the derived text are retained.
    """
    settings = get_settings()
    if not settings.evidence_remote_fetch_enabled:
        raise EvidenceRemoteFetchDisabledError("Remote evidence fetch is disabled")

    try:
        outcome = await fetch_remote_resource(url, settings=settings, resolver=resolver)
    except UrlShapeError as error:
        raise EvidenceRemoteUrlInvalidError(str(error)) from error
    except TargetNotPublicError as error:
        raise EvidenceRemoteTargetNotPublicError(str(error)) from error
    except DnsResolutionError as error:
        raise EvidenceRemoteDnsResolutionError(str(error)) from error
    except RedirectLoopError as error:
        raise EvidenceRemoteRedirectBlockedError(str(error)) from error
    except RedirectLimitError as error:
        raise EvidenceRemoteRedirectLimitError(str(error)) from error
    except ContentTypeNotAllowedError as error:
        raise EvidenceRemoteContentTypeNotAllowedError(str(error)) from error
    except ContentTooLargeError as error:
        raise EvidenceRemoteContentTooLargeError(str(error)) from error
    except FetchTimeoutError as error:
        raise EvidenceRemoteFetchTimeoutError(str(error)) from error
    except UpstreamError as error:
        raise EvidenceRemoteUpstreamError(str(error)) from error

    logger.info(
        "remote_evidence_fetch",
        session_id=str(evidence_session.session_id),
        requested_host=_host_of(outcome.requested_url),
        final_host=_host_of(outcome.final_url),
        status=outcome.status_code,
        bytes=outcome.content_length,
        media_type=outcome.media_type,
        redirects=len(outcome.redirect_chain),
        result="fetched",
    )

    source = await _persist_remote_source(
        session, evidence_session, outcome=outcome, author=author
    )

    logger.info(
        "remote_evidence_fetch",
        session_id=str(evidence_session.session_id),
        source_id=str(source.source_id),
        requested_host=_host_of(outcome.requested_url),
        final_host=_host_of(outcome.final_url),
        status=outcome.status_code,
        bytes=outcome.content_length,
        media_type=outcome.media_type,
        extraction_status=source.extraction_status,
        result="persisted",
    )
    return source


def _host_of(url: str) -> str:
    return urlsplit(url).hostname or ""


async def _persist_remote_source(
    session: AsyncSession,
    evidence_session: CatalogEvidenceSession,
    *,
    outcome: RemoteFetchOutcome,
    author: str,
) -> CatalogEvidenceSource:
    media_type = outcome.media_type
    is_pdf = media_type == "application/pdf"
    is_markup = media_type in ("text/html", "application/xhtml+xml", "application/xml", "text/xml")
    is_plain_text = media_type == "text/plain"

    extracted_text: str | None = None
    extracted_text_hash: str | None = None
    extraction_status = "extracted"
    extraction_metadata: dict[str, object] = {}
    page_count: int | None = None

    if is_pdf:
        try:
            result = await _extract_pdf_text_off_loop(
                outcome.body,
                timeout_seconds=get_settings().evidence_pdf_extraction_timeout_seconds,
            )
        except TimeoutError as error:
            # Fails closed, same as local upload: nothing is persisted.
            raise EvidenceRemotePdfTimeoutError(
                "Remote PDF extraction exceeded the configured timeout"
            ) from error
        except PdfRejectedError as error:
            raise EvidenceRemotePdfInvalidError(f"PDF rejected: {error.reason}") from error
        extraction_status = result.status
        extracted_text = result.text or None
        extracted_text_hash = result.extracted_text_hash
        page_count = result.page_count
        extraction_metadata["page_char_offsets"] = result.page_char_offsets
        extraction_metadata["extractor"] = EXTRACTOR_NAME
    elif is_markup:
        text = extract_html_text(outcome.body)
        if len(text) > MAX_TEXT_CHARS:
            # Reject rather than silently truncate: identical policy to
            # text/plain below, so a source is never persisted as
            # "extracted" while quietly discarding part of the document.
            raise EvidenceRemoteContentInvalidError(
                f"Remote HTML/XML derived text exceeds {MAX_TEXT_CHARS} characters"
            )
        extracted_text = text or None
        extraction_status = "extracted" if text.strip() else "no_extractable_text"
        extraction_metadata["extractor"] = "html_stdlib_parser"
    elif is_plain_text:
        try:
            text = outcome.body.decode("utf-8")
        except UnicodeDecodeError as error:
            raise EvidenceRemoteContentInvalidError(
                "Remote text/plain body is not valid UTF-8"
            ) from error
        if len(text) > MAX_TEXT_CHARS:
            raise EvidenceRemoteContentInvalidError(
                f"Remote text exceeds {MAX_TEXT_CHARS} characters"
            )
        extracted_text = text or None
        extraction_status = "extracted" if text.strip() else "no_extractable_text"
        extraction_metadata["extractor"] = "utf8_decode"
    else:  # pragma: no cover - fetch_remote_resource already enforces the allowlist
        raise EvidenceRemoteContentTypeNotAllowedError(f"Unsupported media type: {media_type}")

    if extracted_text:
        extracted_text_hash = _sha256(extracted_text)

    extraction_metadata.update(
        {
            "requested_url": outcome.requested_url,
            "final_url": outcome.final_url,
            "redirect_chain": outcome.redirect_chain,
            "resolved_ips": outcome.resolved_ips,
            "resolved_hops": outcome.resolved_hops,
            "status_code": outcome.status_code,
            "content_length": outcome.content_length,
            "fetched_at": outcome.fetched_at.isoformat(),
            "response_body_sha256": outcome.body_sha256,
            "derived_text_sha256": extracted_text_hash,
            "remote_fetch_policy_version": REMOTE_FETCH_POLICY_VERSION,
        }
    )

    await session.execute(
        select(CatalogEvidenceSession.session_id)
        .where(CatalogEvidenceSession.session_id == evidence_session.session_id)
        .with_for_update()
    )
    position = await _next_source_position(session, evidence_session.session_id)

    source = CatalogEvidenceSource(
        session_id=evidence_session.session_id,
        position=position,
        kind="remote",
        locator=outcome.final_url,
        content_text=extracted_text,
        content_hash=outcome.body_sha256,
        media_type=media_type,
        metadata_json={
            "captured_by": author,
            "immutable_snapshot": True,
            "requested_url": outcome.requested_url,
        },
        extraction_status=extraction_status,
        extraction_metadata_json=extraction_metadata,
        extracted_text_hash=extracted_text_hash,
        page_count=page_count,
    )
    session.add(source)
    await session.flush()
    return source


def _candidate_rows(
    source: CatalogEvidenceSource,
) -> Iterable[tuple[str, str, str, dict[str, object]]]:
    if source.kind == "url" and source.locator:
        binding = _binding_for_unique_metadata("dc.identifier.url")
        yield binding.binding_id, binding.metadata_field, source.locator, {
            "kind": "source_url",
            "locator": source.locator,
        }
        return
    if source.kind not in ("text", "pdf", "remote") or not source.content_text:
        return

    text = source.content_text
    is_pdf = source.kind == "pdf" or (
        source.kind == "remote" and source.media_type == "application/pdf"
    )
    page_offsets: list[int] = (
        source.extraction_metadata_json.get("page_char_offsets", []) if is_pdf else []
    )

    def pdf_extra(start: int) -> dict[str, object]:
        extra: dict[str, object] = {
            "source_id": str(source.source_id),
            "extractor": source.extraction_metadata_json.get("extractor", EXTRACTOR_NAME),
            "extracted_text_hash": source.extracted_text_hash,
        }
        if page_offsets:
            extra["page"] = page_for_offset(page_offsets, start)
        return extra

    seen: set[tuple[str, str]] = set()
    offset = 0
    for line_number, (line, raw_line) in enumerate(
        zip(text.splitlines(), text.splitlines(keepends=True), strict=True), start=1
    ):
        match = FIELD_LINE.match(line)
        if match:
            binding, matched_by = _resolve_binding(match.group(1))
            if binding is not None:
                value = match.group(2).strip()
                key = (binding.binding_id, value)
                if key not in seen:
                    seen.add(key)
                    evidence: dict[str, object] = {
                        "kind": "explicit_contract_line",
                        "matched_by": matched_by,
                        "line": line_number,
                        "quote": line[:500],
                    }
                    if is_pdf:
                        evidence["start"] = offset
                        evidence["end"] = offset + len(line)
                        evidence.update(pdf_extra(offset))
                    yield binding.binding_id, binding.metadata_field, value, evidence
        offset += len(raw_line)

    detectors = (
        ("dc.identifier.doi", DOI_RE),
        ("dc.identifier.issn", ISSN_RE),
        ("dc.identifier.isbn", ISBN_RE),
    )
    for metadata_field, pattern in detectors:
        binding = _binding_for_unique_metadata(metadata_field)
        for match in pattern.finditer(text):
            value = match.group(0).rstrip(".,;)")
            key = (binding.binding_id, value)
            if key in seen:
                continue
            seen.add(key)
            evidence = {
                "kind": "deterministic_pattern",
                "start": match.start(),
                "end": match.end(),
                "quote": text[
                    max(0, match.start() - 80) : min(len(text), match.end() + 80)
                ],
            }
            if is_pdf:
                evidence.update(pdf_extra(match.start()))
            yield binding.binding_id, binding.metadata_field, value, evidence


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
            .order_by(CatalogEvidenceCandidate.position)
        )
    )
    if existing:
        return existing

    sources = list(
        await session.scalars(
            select(CatalogEvidenceSource)
            .where(CatalogEvidenceSource.session_id == evidence_session.session_id)
            .order_by(CatalogEvidenceSource.position)
        )
    )
    vocabularies = await load_active_vocabulary_rules(session)
    candidates: list[CatalogEvidenceCandidate] = []
    position = 0
    for source in sources:
        for binding_id, metadata_field, value, evidence in _candidate_rows(source):
            vocabulary = vocabularies.get(metadata_field)
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
                position=position,
                binding_id=binding_id,
                metadata_field=metadata_field,
                value=value,
                evidence_state="EXTRAÍDO",
                evidence_json=evidence,
                validation_json=validation,
            )
            session.add(candidate)
            candidates.append(candidate)
            position += 1
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
            .order_by(CatalogEvidenceSource.position)
        )
    )
    candidates = list(
        await session.scalars(
            select(CatalogEvidenceCandidate)
            .where(CatalogEvidenceCandidate.session_id == session_id)
            .order_by(CatalogEvidenceCandidate.position)
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


def _revision_values(draft: CatalogDraft) -> dict[str, list[str]]:
    latest_patch = draft.revisions[-1].metadata_patch if draft.revisions else {}
    values: dict[str, list[str]] = {}
    for field in DRAFTABLE_LINGUISTIC_FIELDS:
        entries = latest_patch.get(field)
        if entries is None:
            entries = draft.base_metadata.get(field, [])
        values[field] = [str(entry["value"]) for entry in entries]
    return values


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
            select(CatalogEvidenceCandidate)
            .where(
                CatalogEvidenceCandidate.session_id == evidence_session.session_id,
                CatalogEvidenceCandidate.candidate_id.in_(candidate_ids),
            )
            .order_by(CatalogEvidenceCandidate.position)
        )
    )
    if len(selected) != len(set(candidate_ids)):
        raise EvidenceValidationError(
            "One or more candidates do not belong to this session"
        )

    current_vocabularies = await load_active_vocabulary_rules(session)
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
        current_vocabulary = current_vocabularies.get(candidate.metadata_field)
        if (
            current_vocabulary is not None
            and candidate.value not in current_vocabulary.terms
        ):
            raise EvidenceValidationError(
                "Candidate is outside the current active controlled vocabulary: "
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

    current_draft = await session.scalar(
        select(CatalogDraft)
        .where(
            CatalogDraft.draft_id == draft_id,
            CatalogDraft.item_uuid == evidence_session.item_uuid,
        )
        .options(selectinload(CatalogDraft.revisions))
    )
    if current_draft is None:
        return None
    merged_changes = _revision_values(current_draft)
    for field, candidate_values in grouped.items():
        for candidate_value in candidate_values:
            if candidate_value not in merged_changes[field]:
                merged_changes[field].append(candidate_value)

    return await append_draft_revision(
        session,
        item_uuid=evidence_session.item_uuid,
        draft_id=draft_id,
        request_id=request_id,
        expected_version=expected_version,
        author=author,
        note=provenance_note,
        changes=merged_changes,
    )
