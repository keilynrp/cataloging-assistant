"""Golden Set runner for VERTICAL-017/VERTICAL-019/VERTICAL-020 evidence ingestion.

Reads tests/golden/evidence/manifest.json and, for each case id, loads
tests/golden/evidence/cases/<id>/case.json. Most cases share one common
extraction-and-assert handler (_run_extraction_case); staleness, vocabulary
revalidation, and remote fetch use small dedicated handlers because they
exercise a multi-step flow (or, for remote fetch, HTTP mocking) rather than
a single extraction.

No case in this suite ever performs a real HTTP call or real DNS lookup.
Non-remote cases run inside a respx guard that fails loudly on any HTTP
traffic at all. Remote-fetch cases (`handler: "remote_fetch"`) register only
the exact URLs their case.json declares with respx (which raises on any
unmocked URL); DNS resolution for hostnames (not IP literals) is satisfied
by a fake resolver fed from the case's own "dns" map, while the *decision*
of whether an IP is public still runs through the real, unmodified
`net_policy.is_public_ip` — the SSRF policy itself is never weakened for
tests, only the network/DNS I/O around it.

Run with: pytest tests/golden -q
"""

from __future__ import annotations

import ipaddress
import json
import uuid
from pathlib import Path

import httpx
import pytest
import respx
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.db.models import DSpaceCollection, DSpaceItem
from cataloging_api.db.session import engine
from cataloging_api.evidence import net_policy
from cataloging_api.evidence import service as evidence_service
from cataloging_api.evidence.models import (
    CatalogEvidenceCandidate,
    CatalogEvidenceSession,
    CatalogEvidenceSource,
)
from cataloging_api.evidence.service import (
    EvidenceValidationError,
    add_pdf_evidence_source,
    add_remote_evidence_source,
    copy_candidates_to_draft,
    create_evidence_session,
    extract_evidence_candidates,
    get_evidence_session,
)
from cataloging_api.vocabularies.service import replace_active_vocabulary
from tests.pdf_fixtures import pdf_with_text, pdf_without_text

GOLDEN_DIR = Path(__file__).parent / "evidence"
MANIFEST = json.loads((GOLDEN_DIR / "manifest.json").read_text(encoding="utf-8"))
CASE_IDS = [case["id"] for case in MANIFEST["cases"]]


def _load_case(case_id: str) -> dict:
    path = GOLDEN_DIR / "cases" / case_id / "case.json"
    return json.loads(path.read_text(encoding="utf-8"))


class _Fixture:
    """Fresh DSpace collection/item plus a clean evidence slate, per case."""

    def __init__(self) -> None:
        self.collection_uuid = uuid.uuid4()
        self.item_uuid = uuid.uuid4()

    async def __aenter__(self) -> tuple[AsyncSession, uuid.UUID]:
        self.connection = await engine.connect()
        self.transaction = await self.connection.begin()
        self.session = AsyncSession(bind=self.connection, expire_on_commit=False)
        await self.session.execute(delete(CatalogEvidenceCandidate))
        await self.session.execute(delete(CatalogEvidenceSource))
        await self.session.execute(delete(CatalogEvidenceSession))
        self.session.add(
            DSpaceCollection(
                uuid=self.collection_uuid,
                handle="test/golden-evidence",
                name="Golden Set evidence",
                raw_json={"uuid": str(self.collection_uuid)},
            )
        )
        self.session.add(
            DSpaceItem(
                uuid=self.item_uuid,
                collection_uuid=self.collection_uuid,
                handle="test/golden-evidence-item",
                name="Golden Set item",
                raw_json={"uuid": str(self.item_uuid)},
                source_hash="9" * 64,
            )
        )
        await self.session.flush()
        return self.session, self.item_uuid

    async def __aexit__(self, *exc: object) -> None:
        await self.session.close()
        await self.transaction.rollback()
        await self.connection.close()


async def _build_session_from_sources(
    session: AsyncSession, item_uuid: uuid.UUID, sources: list[dict]
) -> CatalogEvidenceSession:
    url = next((s["url"] for s in sources if s["type"] == "url"), None)
    text = next((s["text"] for s in sources if s["type"] == "text"), None)
    pdf_entries = [s for s in sources if s["type"] == "pdf"]

    evidence = await create_evidence_session(
        session,
        item_uuid=item_uuid,
        created_by="Golden Set",
        url=url,
        text=text,
    )
    for pdf_entry in pdf_entries:
        if pdf_entry["fixture"] == "with_text":
            data = pdf_with_text(pdf_entry["lines"])
        elif pdf_entry["fixture"] == "without_text":
            data = pdf_without_text()
        else:  # pragma: no cover - manifest typo guard
            raise ValueError(f"Unknown pdf fixture: {pdf_entry['fixture']}")
        await add_pdf_evidence_source(
            session,
            evidence,
            file_bytes=data,
            original_filename="golden-set.pdf",
            content_type="application/pdf",
            author="Golden Set",
        )
    return evidence


async def _run_extraction_case(
    session: AsyncSession, item_uuid: uuid.UUID, case: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    evidence = await _build_session_from_sources(session, item_uuid, case["sources"])

    _, sources, _, _ = await get_evidence_session(session, evidence.session_id)
    for expected_source in case["expected_sources"]:
        actual = sources[expected_source["position"]]
        assert actual.kind == expected_source["kind"]
        assert actual.position == expected_source["position"]
        if "extraction_status" in expected_source:
            assert actual.extraction_status == expected_source["extraction_status"]

    candidates = await extract_evidence_candidates(session, evidence)

    assert [c.binding_id for c in candidates] == case["expected_binding_ids"]
    assert [c.metadata_field for c in candidates] == case["expected_metadata_fields"]
    assert [c.value for c in candidates] == case["expected_values"]
    assert [c.binding_id for c in candidates] == case["expected_order"]

    expected_state = case.get("expected_evidence_state")
    if expected_state:
        assert all(c.evidence_state == expected_state for c in candidates)

    for expected_candidate, actual_candidate in zip(
        case["expected_candidates"], candidates, strict=True
    ):
        assert actual_candidate.binding_id == expected_candidate["binding_id"]
        assert actual_candidate.metadata_field == expected_candidate["metadata_field"]
        assert actual_candidate.value == expected_candidate["value"]

    validation = case.get("expected_validation_status")
    if validation:
        entry = next(c for c in candidates if c.metadata_field == validation["field"])
        assert entry.validation_json["status"] == validation["status"]


async def _run_stale_session_case(
    session: AsyncSession, item_uuid: uuid.UUID, case: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    evidence = await _build_session_from_sources(session, item_uuid, case["sources"])

    # Freeze a legitimate extraction while the session is still fresh.
    candidates_before = await extract_evidence_candidates(session, evidence)
    assert candidates_before

    await session.execute(
        update(DSpaceItem).where(DSpaceItem.uuid == item_uuid).values(source_hash="stale-hash")
    )
    await session.flush()

    loaded, _, _, stale = await get_evidence_session(session, evidence.session_id)
    assert loaded is not None
    assert stale is True
    # The HTTP layer (routes.extract_session / routes.copy_to_draft /
    # routes.upload_pdf_source / routes.upload_remote_source) refuses to
    # proceed whenever this flag is True, returning 409 before calling into
    # the service layer at all. This case asserts the staleness signal those
    # routes rely on, uniformly for URL/text/PDF/remote sources.


async def _run_vocabulary_revalidation_case(
    session: AsyncSession, item_uuid: uuid.UUID, case: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    evidence = await _build_session_from_sources(session, item_uuid, case["sources"])
    candidates = await extract_evidence_candidates(session, evidence)
    field = case["field"]
    candidate = next(c for c in candidates if c.metadata_field == field)

    await replace_active_vocabulary(
        session,
        request_id=uuid.uuid4(),
        field=field,
        name="Golden Set vocabulary",
        source_uri="https://example.test/golden-vocab",
        version_label="1",
        approved_by="Golden Set",
        approval_note="Fixture.",
        terms=[
            {"value": term, "authority": None, "language": "es"}
            for term in case["outdated_terms"]
        ],
    )
    with pytest.raises(EvidenceValidationError):
        await copy_candidates_to_draft(
            session,
            evidence_session=evidence,
            candidate_ids=[candidate.candidate_id],
            request_id=uuid.uuid4(),
            author="Golden Set",
            note="Debe revalidar contra autoridad vigente.",
            draft_id=None,
            expected_version=None,
        )

    await replace_active_vocabulary(
        session,
        request_id=uuid.uuid4(),
        field=field,
        name="Golden Set vocabulary",
        source_uri="https://example.test/golden-vocab",
        version_label="2",
        approved_by="Golden Set",
        approval_note="Fixture.",
        terms=[
            {"value": term, "authority": None, "language": "es"} for term in case["current_terms"]
        ],
    )
    draft = await copy_candidates_to_draft(
        session,
        evidence_session=evidence,
        candidate_ids=[candidate.candidate_id],
        request_id=uuid.uuid4(),
        author="Golden Set",
        note="Valor revisado contra vocabulario vigente.",
        draft_id=None,
        expected_version=None,
    )
    assert draft is not None
    assert draft.revisions[-1].metadata_patch[field][0]["value"] == candidate.value


def _response_body(entry: dict) -> bytes:
    if "body_text" in entry:
        return entry["body_text"].encode("utf-8")
    if "body_pdf_fixture" in entry:
        fixture = entry["body_pdf_fixture"]
        if fixture["kind"] == "with_text":
            return pdf_with_text(fixture["lines"])
        if fixture["kind"] == "without_text":
            return pdf_without_text()
        raise ValueError(f"Unknown pdf fixture: {fixture['kind']}")  # pragma: no cover
    if "body_repeat" in entry:
        spec = entry["body_repeat"]
        return (spec["char"] * spec["count"]).encode("utf-8")
    return b""


def _register_mock_responses(router: respx.MockRouter, responses: list[dict]) -> None:
    for entry in responses:
        headers = dict(entry.get("headers", {}))
        content = _response_body(entry)
        response = httpx.Response(entry["status"], headers=headers, content=content)
        if entry.get("omit_content_length") and "content-length" in response.headers:
            del response.headers["content-length"]
        router.get(entry["url"]).mock(return_value=response)


def _fake_resolver_for(dns_map: dict[str, list[str]]) -> net_policy.DnsResolver:
    """Test-only DNS seam: canned answers for hostnames listed in `dns_map`,
    falling back to the real resolver (which handles IP literals with no
    network I/O) for anything else. `net_policy.is_public_ip` — the actual
    SSRF decision — is always the real, unmodified function; only the *DNS
    lookup* is faked, never the policy that judges its answer.
    """

    async def resolver(host: str, port: int) -> list[str]:
        if host in dns_map:
            ips = dns_map[host]
            if not ips:
                raise net_policy.DnsResolutionError(host)
            if not all(net_policy.is_public_ip(ipaddress.ip_address(ip)) for ip in ips):
                raise net_policy.TargetNotPublicError(host, ips)
            return ips
        return await net_policy.resolve_public_ips(host, port)

    return resolver


async def _run_remote_fetch_case(
    session: AsyncSession, item_uuid: uuid.UUID, case: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    evidence = await create_evidence_session(
        session, item_uuid=item_uuid, created_by="Golden Set", url=None, text=None
    )

    overrides = dict(case.get("settings_overrides", {}))
    overrides.setdefault("evidence_remote_fetch_enabled", True)
    overridden_settings = evidence_service.get_settings().model_copy(update=overrides)
    monkeypatch.setattr(evidence_service, "get_settings", lambda: overridden_settings)

    resolver = _fake_resolver_for(case.get("dns", {}))
    responses = case.get("responses", [])
    expect_error = case.get("expect_error")

    async def do_fetch() -> CatalogEvidenceSource:
        return await add_remote_evidence_source(
            session,
            evidence,
            url=case["url"],
            author=case.get("author", "Golden Set"),
            resolver=resolver,
        )

    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        _register_mock_responses(router, responses)
        if expect_error:
            error_cls = getattr(evidence_service, expect_error)
            with pytest.raises(error_cls):
                await do_fetch()
            _, sources, candidates, _ = await get_evidence_session(session, evidence.session_id)
            assert sources == [], "a rejected fetch must not persist a source"
            assert candidates == []
            return
        source = await do_fetch()

    expected = case.get("expect_source", {})
    if "kind" in expected:
        assert source.kind == expected["kind"]
    if "media_type" in expected:
        assert source.media_type == expected["media_type"]
    if "extraction_status" in expected:
        assert source.extraction_status == expected["extraction_status"]
    if "final_url" in expected:
        assert source.locator == expected["final_url"]
    if "redirect_hops" in expected:
        redirect_chain = source.extraction_metadata_json["redirect_chain"]
        assert len(redirect_chain) == expected["redirect_hops"]
    if "resolved_hops" in expected:
        actual_hops = source.extraction_metadata_json["resolved_hops"]
        assert len(actual_hops) == len(expected["resolved_hops"])
        for actual_hop, expected_hop in zip(actual_hops, expected["resolved_hops"], strict=True):
            assert actual_hop["url"] == expected_hop["url"]
            assert actual_hop["host"] == expected_hop["host"]
            assert actual_hop["resolved_ips"] == expected_hop["resolved_ips"]
    for needle in expected.get("text_includes", []):
        assert needle in (source.content_text or "")
    for needle in expected.get("text_excludes", []):
        assert needle not in (source.content_text or "")

    if case.get("second_fetch"):
        with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
            _register_mock_responses(router, responses)
            second_source = await do_fetch()
        assert second_source.source_id != source.source_id
        assert second_source.position == source.position + 1
        assert second_source.kind == source.kind

    if "expected_binding_ids" in case:
        candidates = await extract_evidence_candidates(session, evidence)
        assert [c.binding_id for c in candidates] == case["expected_binding_ids"]
        assert [c.metadata_field for c in candidates] == case["expected_metadata_fields"]
        assert [c.value for c in candidates] == case["expected_values"]
        assert [c.binding_id for c in candidates] == case["expected_order"]


_HANDLERS = {
    "stale_session": _run_stale_session_case,
    "vocabulary_revalidation": _run_vocabulary_revalidation_case,
    "remote_fetch": _run_remote_fetch_case,
}


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("case_id", CASE_IDS)
async def test_golden_set_case(case_id: str, monkeypatch: pytest.MonkeyPatch) -> None:
    case = _load_case(case_id)
    handler = _HANDLERS.get(case.get("handler"), _run_extraction_case)
    if case.get("handler") == "remote_fetch":
        # Remote-fetch cases manage their own scoped respx mocking (only the
        # exact URLs their case.json declares); no blanket "no HTTP" guard
        # applies to them, unlike every other case in this suite.
        async with _Fixture() as (session, item_uuid):
            await handler(session, item_uuid, case, monkeypatch)
        return
    # No non-remote evidence-ingestion code path in this vertical performs
    # outbound HTTP; this guard fails the case loudly if that invariant ever
    # breaks.
    with respx.mock(assert_all_called=False) as router:
        router.route().mock(side_effect=AssertionError("golden set must not perform HTTP calls"))
        async with _Fixture() as (session, item_uuid):
            await handler(session, item_uuid, case, monkeypatch)
