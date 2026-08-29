from __future__ import annotations

import copy
import csv
import inspect
import io
import json
import re
import uuid
import zipfile
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api import config as config_module
from cataloging_api.api import routes as api_routes
from cataloging_api.db.session import engine, get_session
from cataloging_api.dspace.client import DSpaceClient, DSpaceError, HalCollectionPage
from cataloging_api.dspace.contract_store import DSpaceContractRawPage, DSpaceContractSyncRun
from cataloging_api.reports import routes as report_routes
from cataloging_api.reports.exporters import export_csv, export_pdf, export_xlsx
from cataloging_api.reports.weekly_dspace import (
    REPORT_TIMEZONE_NAME,
    VISIBLE_HEADERS,
    DatabaseRawEvidenceRecorder,
    WeeklyDSpaceReportService,
    WeeklyReport,
    WeeklyReportRow,
    build_archived_row,
    build_submission_row,
    normalize_report_text,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "weekly_dspace"
XML_NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _page(payload: dict[str, Any], relation: str) -> HalCollectionPage:
    page = payload["page"]
    embedded = payload.get("_embedded", {})
    return HalCollectionPage(
        items=copy.deepcopy(embedded.get(relation, [])),
        page=int(page["number"]),
        total_pages=int(page["totalPages"]),
        total_elements=int(page["totalElements"]),
        raw_payload=copy.deepcopy(payload),
    )


class MemoryEvidence:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []
        self.completed = False
        self.failure: tuple[bool, str, str] | None = None

    async def start(self) -> str:
        return "30000000-0000-4000-8000-000000000001"

    async def record(self, **observation: Any) -> str:
        snapshot = copy.deepcopy(observation)
        self.records.append(snapshot)
        return f"raw:{len(self.records)}"

    async def complete(self) -> None:
        self.completed = True

    async def fail(self, *, interrupted: bool, code: str, message: str) -> None:
        self.failure = (interrupted, code, message)


class FixtureClient:
    def __init__(self) -> None:
        self.archived = _fixture("archived-page.json")
        self.workspace = _fixture("workspace-page.json")
        self.workspace_item = _fixture("workspace-item-55.json")
        self.workflow = _fixture("workflow-empty-page.json")
        self.item_requests: list[tuple[str, str]] = []

    async def get_items_page(self, *, page: int, size: int) -> HalCollectionPage:
        assert (page, size) == (0, 100)
        return _page(self.archived, "items")

    async def get_workspace_items_page(self, *, page: int, size: int) -> HalCollectionPage:
        assert (page, size) == (0, 100)
        return _page(self.workspace, "workspaceitems")

    async def get_workspace_item_item(self, item_id: str | int) -> dict[str, Any]:
        self.item_requests.append(("workspace", str(item_id)))
        if str(item_id) == "55":
            return copy.deepcopy(self.workspace_item)
        raise DSpaceError("not_found", "fixture workspace item unavailable", status_code=404)

    async def get_workflow_items_page(self, *, page: int, size: int) -> HalCollectionPage:
        assert (page, size) == (0, 100)
        return _page(self.workflow, "workflowitems")

    async def get_workflow_item_item(self, item_id: str | int) -> dict[str, Any]:
        self.item_requests.append(("workflow", str(item_id)))
        raise AssertionError("empty workflow must not resolve an item")


class AssociatedItemFailureClient(FixtureClient):
    def __init__(self, error: DSpaceError) -> None:
        super().__init__()
        self.error = error

    async def get_workspace_item_item(self, item_id: str | int) -> dict[str, Any]:
        self.item_requests.append(("workspace", str(item_id)))
        raise self.error


async def _fixture_report(
    *, from_date: date = date(2026, 8, 24), to_date: date = date(2026, 8, 26)
) -> tuple[WeeklyReport, MemoryEvidence, FixtureClient]:
    evidence = MemoryEvidence()
    client = FixtureClient()
    report = await WeeklyDSpaceReportService(
        client,  # type: ignore[arg-type]
        evidence,
        ui_base_url="http://dspace-ui.test",
    ).generate(from_date=from_date, to_date=to_date)
    return report, evidence, client


@pytest.mark.asyncio
async def test_fixture_report_fulfils_filter_mapping_time_and_evidence_contract() -> None:
    report, evidence, client = await _fixture_report()

    assert report.timezone == REPORT_TIMEZONE_NAME
    assert [row.identifier for row in report.rows] == [
        "123456789/100",
        "123456789/101",
        "55",
        "56",
        "123456789/103",
    ]
    assert [row.number for row in report.rows] == [1, 2, 3, 4, 5]
    assert "123456789/102" not in {row.identifier for row in report.rows}
    assert "123456789/104" not in {row.identifier for row in report.rows}

    authored = report.rows[0]
    assert authored.title == "P’urhépecha"
    assert authored.responsibility == "Ávila, Ana; O’Connor, Luis"
    assert authored.responsibility_source == "dc.contributor.author"
    assert authored.internal_url == "http://dspace-ui.test/handle/123456789/100"
    assert authored.catalog_date == date(2026, 8, 24)
    assert authored.catalog_date_source == "dcterms.provenance"

    editor_fallback = report.rows[1]
    assert editor_fallback.responsibility == "+cmd"
    assert editor_fallback.responsibility_source == "dc.contributor.editor"
    assert editor_fallback.catalog_date == date(2026, 8, 24)
    assert editor_fallback.catalog_date_source == "dc.date.accessioned"
    assert editor_fallback.internal_url == "http://dspace-ui.test/handle/123456789/101"

    associated_item = report.rows[2]
    assert associated_item.title == "Título del Item asociado"
    assert associated_item.responsibility == "P’erez, María"
    assert associated_item.catalog_date == date(2026, 8, 25)
    assert associated_item.catalog_date_source == "item.lastModified"
    assert associated_item.internal_url == "http://dspace-ui.test/workspaceitems/55/edit"
    assert len(associated_item.raw_source_refs) == 2

    sections_fallback = report.rows[3]
    assert sections_fallback.title == "Título desde sections"
    assert sections_fallback.responsibility_source == "dc.contributor.editor"
    assert len(sections_fallback.raw_source_refs) == 1

    withdrawn = report.rows[4]
    assert withdrawn.status == "Retirado"
    assert withdrawn.responsibility == ""
    assert withdrawn.responsibility_source == "unavailable"

    assert client.item_requests == [("workspace", "55"), ("workspace", "56")]
    assert evidence.completed is True
    assert evidence.failure is None
    assert len(evidence.records) == 4
    assert evidence.records[-1]["surface"] == "weekly_workflow_workflowitems"
    assert all(row.raw_source_refs for row in report.rows)
    raw_evidence = json.dumps(evidence.records, ensure_ascii=False)
    for secret in ("reader@example.org", "secret-password", "Bearer token", "csrf-cookie"):
        assert secret not in raw_evidence


@pytest.mark.parametrize(
    "error",
    [
        DSpaceError("authentication_failed", "DSpace rejected credentials", status_code=401),
        DSpaceError("timeout", "DSpace associated item timed out"),
        DSpaceError("invalid_hal", "DSpace associated item returned invalid HAL"),
    ],
    ids=["401", "timeout", "invalid-hal"],
)
@pytest.mark.asyncio
async def test_non_404_associated_item_failures_interrupt_without_partial_report(
    error: DSpaceError,
) -> None:
    evidence = MemoryEvidence()
    client = AssociatedItemFailureClient(error)

    with pytest.raises(DSpaceError) as raised:
        await WeeklyDSpaceReportService(
            client,  # type: ignore[arg-type]
            evidence,
            ui_base_url="http://dspace-ui.test",
        ).generate(from_date=date(2026, 8, 24), to_date=date(2026, 8, 26))

    assert raised.value is error
    assert evidence.completed is False
    assert evidence.failure == (True, error.code, str(error))
    assert [record["surface"] for record in evidence.records] == [
        "weekly_core_items",
        "weekly_submission_workspaceitems",
    ]


@pytest.mark.parametrize(
    ("surface", "missing_kind"),
    [("workspace", "missing"), ("workflow", "null")],
)
@pytest.mark.asyncio
async def test_submission_without_id_is_invalid_hal_and_never_returns_partial_report(
    surface: str,
    missing_kind: str,
) -> None:
    evidence = MemoryEvidence()
    client = FixtureClient()
    if surface == "workspace":
        entry = client.workspace["_embedded"]["workspaceitems"][0]
    else:
        client.workflow = {
            "_embedded": {"workflowitems": [{"id": None, "sections": {}}]},
            "page": {"number": 0, "size": 100, "totalElements": 1, "totalPages": 1},
        }
        entry = client.workflow["_embedded"]["workflowitems"][0]
    if missing_kind == "missing":
        entry.pop("id")

    with pytest.raises(DSpaceError) as raised:
        await WeeklyDSpaceReportService(
            client,  # type: ignore[arg-type]
            evidence,
            ui_base_url="http://dspace-ui.test",
        ).generate(from_date=date(2026, 8, 24), to_date=date(2026, 8, 26))

    assert raised.value.code == "invalid_hal"
    assert "Expected submission id" in str(raised.value)
    assert evidence.completed is False
    assert evidence.failure == (True, "invalid_hal", str(raised.value))
    assert all(request_surface != surface for request_surface, _ in client.item_requests)


@pytest.mark.asyncio
async def test_missing_pagination_totals_interrupt_instead_of_truncating_report() -> None:
    payload = _fixture("archived-page.json")
    payload["page"].pop("totalPages")

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    evidence = MemoryEvidence()
    async with DSpaceClient(
        "http://dspace.test/server/api",
        transport=httpx.MockTransport(handler),
        max_retries=0,
    ) as client:
        with pytest.raises(DSpaceError) as raised:
            await WeeklyDSpaceReportService(
                client,
                evidence,
                ui_base_url="http://dspace-ui.test",
            ).generate(from_date=date(2026, 8, 24), to_date=date(2026, 8, 26))

    assert raised.value.code == "invalid_hal"
    assert str(raised.value) == "Expected pagination metadata at /core/items"
    assert evidence.completed is False
    assert evidence.failure == (True, "invalid_hal", str(raised.value))


@pytest.mark.parametrize(
    "malformed_title",
    ["Título no listado", [{"value": "Título"}, "entrada corrupta"]],
    ids=["scalar", "mixed-list"],
)
@pytest.mark.asyncio
async def test_malformed_sections_metadata_interrupts_404_fallback(
    malformed_title: object,
) -> None:
    evidence = MemoryEvidence()
    client = FixtureClient()
    workspace_fallback = client.workspace["_embedded"]["workspaceitems"][1]
    workspace_fallback["sections"]["page"]["dc.title"] = malformed_title

    with pytest.raises(DSpaceError) as raised:
        await WeeklyDSpaceReportService(
            client,  # type: ignore[arg-type]
            evidence,
            ui_base_url="http://dspace-ui.test",
        ).generate(from_date=date(2026, 8, 24), to_date=date(2026, 8, 26))

    assert raised.value.code == "invalid_hal"
    assert "Expected metadata list in sections" in str(raised.value)
    assert evidence.completed is False
    assert evidence.failure == (True, "invalid_hal", str(raised.value))
    assert evidence.records[1]["raw_payload"] == client.workspace


@pytest.mark.parametrize("metadata_kind", ["missing", "null", "list"])
@pytest.mark.asyncio
async def test_invalid_associated_item_metadata_interrupts_after_preserving_raw_payload(
    metadata_kind: str,
) -> None:
    evidence = MemoryEvidence()
    client = FixtureClient()
    if metadata_kind == "missing":
        client.workspace_item.pop("metadata")
    else:
        client.workspace_item["metadata"] = None if metadata_kind == "null" else []

    with pytest.raises(DSpaceError) as raised:
        await WeeklyDSpaceReportService(
            client,  # type: ignore[arg-type]
            evidence,
            ui_base_url="http://dspace-ui.test",
        ).generate(from_date=date(2026, 8, 24), to_date=date(2026, 8, 26))

    assert raised.value.code == "invalid_hal"
    assert "Expected metadata object" in str(raised.value)
    assert evidence.completed is False
    assert evidence.failure == (True, "invalid_hal", str(raised.value))
    assert evidence.records[-1]["surface"] == "weekly_submission_workspaceitems_item:55"
    assert evidence.records[-1]["raw_payload"] == client.workspace_item


@pytest.mark.parametrize("handle_kind", ["missing", "null"])
@pytest.mark.asyncio
async def test_yct_archived_item_without_handle_interrupts_report(handle_kind: str) -> None:
    evidence = MemoryEvidence()
    client = FixtureClient()
    archived_item = client.archived["_embedded"]["items"][0]
    if handle_kind == "missing":
        archived_item.pop("handle")
    else:
        archived_item["handle"] = None

    with pytest.raises(DSpaceError) as raised:
        await WeeklyDSpaceReportService(
            client,  # type: ignore[arg-type]
            evidence,
            ui_base_url="http://dspace-ui.test",
        ).generate(from_date=date(2026, 8, 24), to_date=date(2026, 8, 26))

    assert raised.value.code == "invalid_hal"
    assert str(raised.value) == "Expected handle for archived DSpace item"
    assert evidence.completed is False
    assert evidence.failure == (True, "invalid_hal", str(raised.value))
    assert [record["surface"] for record in evidence.records] == ["weekly_core_items"]


@pytest.mark.asyncio
async def test_bounds_are_inclusive_and_timestamp_uses_mexico_city_before_date() -> None:
    report, _, _ = await _fixture_report(
        from_date=date(2026, 8, 24),
        to_date=date(2026, 8, 24),
    )
    assert [row.identifier for row in report.rows] == ["123456789/100", "123456789/101"]
    assert report.rows[1].catalog_date_source == "dc.date.accessioned"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_evidence_adapter_persists_every_report_reference_immutably() -> None:
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        report = await WeeklyDSpaceReportService(
            FixtureClient(),  # type: ignore[arg-type]
            DatabaseRawEvidenceRecorder(session),
            ui_base_url="http://dspace-ui.test",
        ).generate(from_date=date(2026, 8, 24), to_date=date(2026, 8, 26))

        run_id = uuid.UUID(report.evidence_run_id)
        run = await session.get(DSpaceContractSyncRun, run_id)
        pages = list(
            await session.scalars(
                select(DSpaceContractRawPage).where(
                    DSpaceContractRawPage.run_id == run_id
                )
            )
        )
        expected_refs = {
            f"dspace_contract_raw_pages:{page.page_id}:{page.raw_hash}" for page in pages
        }
        assert run is not None and run.status == "COMPLETE"
        assert len(pages) == 4
        assert all(set(row.raw_source_refs).issubset(expected_refs) for row in report.rows)
        assert all(page.raw_payload for page in pages)
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


def test_workspace_last_modified_is_never_used_as_historical_primary_date() -> None:
    workspace = {
        "id": 9,
        "lastModified": "2026-08-24T12:00:00Z",
        "sections": {
            "page": {
                "dc.title": [{"value": "Sin fecha válida"}],
                "dcterms.provenance": [{"value": "YCT-sin-fecha"}],
            }
        },
    }
    row = build_submission_row(
        workspace,
        item=None,
        source_surface="submission/workspaceitems",
        status="Guardado",
        ui_base_url="http://dspace-ui.test",
        raw_source_refs=("raw:workspace",),
    )
    assert row is None


def test_workflow_uses_configured_general_view_without_claiming_a_direct_item_route() -> None:
    workflow = {"id": 71, "sections": {}}
    item = {
        "uuid": "60000000-0000-4000-8000-000000000071",
        "lastModified": "2026-08-24T12:00:00Z",
        "metadata": {
            "dc.title": [{"value": "En revisión"}],
            "dcterms.provenance": [{"value": "YCT-20260824"}],
        },
    }
    row = build_submission_row(
        workflow,
        item=item,
        source_surface="workflow/workflowitems",
        status="En flujo de trabajo",
        ui_base_url="http://dspace-ui.test",
        workflow_ui_url="http://dspace-ui.test/mydspace/workflow",
        raw_source_refs=("raw:workflow", "raw:item"),
    )
    assert row is not None
    assert row.status == "En flujo de trabajo"
    assert row.internal_url == "http://dspace-ui.test/mydspace/workflow"
    assert "/workflowitems/71" not in row.internal_url


def test_responsibility_fallback_and_blank_are_deterministic() -> None:
    base = {
        "uuid": "40000000-0000-4000-8000-000000000001",
        "handle": "123/1",
        "name": "Name fallback",
        "inArchive": True,
        "withdrawn": False,
        "metadata": {
            "dc.title": [{"value": "Título"}],
            "dcterms.provenance": [{"value": "YCT-20260824"}],
        },
    }
    blank = build_archived_row(
        base,
        ui_base_url="http://dspace-ui.test",
        raw_source_refs=("raw:1",),
    )
    assert blank is not None
    assert (blank.responsibility, blank.responsibility_source) == ("", "unavailable")

    with_both = copy.deepcopy(base)
    with_both["metadata"]["dc.contributor.author"] = [
        {"value": "Autora A"},
        {"value": "Autor B"},
    ]
    with_both["metadata"]["dc.contributor.editor"] = [{"value": "Editora C"}]
    authored = build_archived_row(
        with_both,
        ui_base_url="http://dspace-ui.test",
        raw_source_refs=("raw:2",),
    )
    assert authored is not None
    assert authored.responsibility == "Autora A; Autor B"
    assert authored.responsibility_source == "dc.contributor.author"


def test_text_normalization_is_nfc_conservative_and_canonicalizes_apostrophes() -> None:
    assert normalize_report_text("  Pâ€™urhe\u0301pecha\u00a0\n  ") == "P’urhépecha"
    variants = ["P'urhépecha", "Pʼurhépecha", "P´urhépecha", "P’urhépecha"]
    assert {normalize_report_text(value) for value in variants} == {"P’urhépecha"}
    assert normalize_report_text("No corregir ortografia") == "No corregir ortografia"


@pytest.mark.asyncio
async def test_exports_have_seven_columns_same_rows_and_spreadsheet_formula_safety() -> None:
    report, _, _ = await _fixture_report()
    dangerous = tuple(
        replace(report.rows[0], number=index, identifier=f"SAFE-{index}", title=value)
        for index, value in enumerate(("=SUM(1,2)", "+cmd", "-1+2", "@example"), start=1)
    )
    dangerous_report = replace(report, rows=dangerous)

    csv_bytes = export_csv(dangerous_report)
    assert csv_bytes.startswith(b"\xef\xbb\xbf")
    csv_rows = list(csv.reader(io.StringIO(csv_bytes.decode("utf-8-sig"))))
    assert tuple(csv_rows[0]) == VISIBLE_HEADERS
    assert all(len(row) == 7 for row in csv_rows)
    assert [row[2] for row in csv_rows[1:]] == [
        "'=SUM(1,2)",
        "'+cmd",
        "'-1+2",
        "'@example",
    ]
    assert "raw_source_refs" not in csv_bytes.decode("utf-8-sig")

    xlsx_bytes = export_xlsx(dangerous_report)
    xlsx_rows, sheet_xml = _xlsx_rows(xlsx_bytes)
    assert tuple(xlsx_rows[0]) == VISIBLE_HEADERS
    assert all(len(row) == 7 for row in xlsx_rows)
    assert [row[2] for row in xlsx_rows[1:]] == [
        "=SUM(1,2)",
        "+cmd",
        "-1+2",
        "@example",
    ]
    assert b"<f" not in sheet_xml
    assert b"<hyperlinks" in sheet_xml

    pdf_bytes = export_pdf(dangerous_report)
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert all(identifier in pdf_text for identifier in ["SAFE-1", "SAFE-2", "SAFE-3", "SAFE-4"])
    assert [pdf_text.index(f"SAFE-{index}") for index in range(1, 5)] == sorted(
        pdf_text.index(f"SAFE-{index}") for index in range(1, 5)
    )


@pytest.mark.asyncio
async def test_csv_xlsx_and_pdf_preserve_canonical_dataset_order() -> None:
    report, _, _ = await _fixture_report()
    expected_ids = [row.identifier for row in report.rows]

    csv_rows = list(csv.reader(io.StringIO(export_csv(report).decode("utf-8-sig"))))
    assert [row[1] for row in csv_rows[1:]] == expected_ids

    xlsx_rows, _ = _xlsx_rows(export_xlsx(report))
    assert [row[1] for row in xlsx_rows[1:]] == expected_ids

    pdf = PdfReader(io.BytesIO(export_pdf(report)))
    pdf_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    id_matches = [
        re.search(rf"(?m)^{re.escape(identifier)}$", pdf_text)
        for identifier in expected_ids
    ]
    assert all(match is not None for match in id_matches)
    positions = [match.start() for match in id_matches if match is not None]
    assert positions == sorted(positions)
    assert "P’urhépecha" in pdf_text


def test_pdf_is_landscape_and_repeats_seven_column_header() -> None:
    base = WeeklyReportRow(
        number=1,
        identifier="HANDLE-001",
        title="Título con áéíóú y P’urhépecha",
        internal_url="http://dspace-ui.test/handle/1",
        responsibility="Autora",
        status="Depositado",
        cataloger="YCT-20260824",
        catalog_date=date(2026, 8, 24),
        catalog_date_source="dcterms.provenance",
        source_surface="core/items",
        responsibility_source="dc.contributor.author",
        item_uuid=None,
        raw_source_refs=("raw:1",),
    )
    rows = tuple(
        replace(base, number=index, identifier=f"HANDLE-{index:03d}")
        for index in range(1, 91)
    )
    report = WeeklyReport(
        from_date=date(2026, 8, 24),
        to_date=date(2026, 8, 30),
        timezone=REPORT_TIMEZONE_NAME,
        evidence_run_id="run",
        rows=rows,
    )
    reader = PdfReader(io.BytesIO(export_pdf(report)))
    assert len(reader.pages) > 1
    for page in reader.pages:
        assert float(page.mediabox.width) > float(page.mediabox.height)
        text = page.extract_text() or ""
        for header in ("ID", "Título", "Autor(es)", "Estado", "Catalogador"):
            assert header in text


def test_new_dspace_report_surfaces_issue_only_get_requests() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        path = request.url.path
        if path.endswith("/core/items"):
            return httpx.Response(200, json=_empty_hal("items"))
        if path.endswith("/submission/workspaceitems"):
            return httpx.Response(200, json=_empty_hal("workspaceitems"))
        if path.endswith("/workflow/workflowitems"):
            return httpx.Response(200, json=_empty_hal("workflowitems"))
        return httpx.Response(200, json={"uuid": "50000000-0000-4000-8000-000000000001"})

    async def run() -> None:
        async with DSpaceClient(
            "https://dspace.example/server/api",
            transport=httpx.MockTransport(handler),
            max_retries=0,
        ) as client:
            await client.get_items_page(page=0)
            await client.get_workspace_items_page(page=0)
            await client.get_workspace_item_item(7)
            await client.get_workflow_items_page(page=0)
            await client.get_workflow_item_item(8)

    import asyncio

    asyncio.run(run())
    assert {request.method for request in seen} == {"GET"}
    assert [request.url.path for request in seen] == [
        "/server/api/core/items",
        "/server/api/submission/workspaceitems",
        "/server/api/submission/workspaceitems/7/item",
        "/server/api/workflow/workflowitems",
        "/server/api/workflow/workflowitems/8/item",
    ]
    assert "._client.post" not in inspect.getsource(DSpaceClient)


def test_route_rejects_unauthorized_caller_before_starting_dspace_client(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(report_routes.router)

    async def fake_session():
        yield object()

    app.dependency_overrides[get_session] = fake_session
    settings = config_module.get_settings().model_copy(
        update={
            "catalog_review_token": "review-secret",
            "dspace_read_username": "reader@example.org",
            "dspace_read_password": "secret-password",
        }
    )
    monkeypatch.setattr(report_routes, "get_settings", lambda: settings)
    monkeypatch.setattr(api_routes, "get_settings", lambda: settings)
    started_clients: list[bool] = []

    class UnexpectedDSpaceClient:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            started_clients.append(True)
            raise AssertionError("unauthorized caller must not start DSpace authentication")

    monkeypatch.setattr(report_routes, "ReadAuthenticatedDSpaceClient", UnexpectedDSpaceClient)
    client = TestClient(app)
    report_url = "/api/reports/dspace-weekly.csv?from=2026-08-24&to=2026-08-24"

    unauthorized = client.get(report_url)
    assert unauthorized.status_code == 401
    assert unauthorized.json() == {"detail": "Invalid review token"}

    wrong_token = client.get(
        report_url,
        headers={"X-Catalog-Review-Token": "wrong-secret"},
    )
    assert wrong_token.status_code == 401
    assert wrong_token.json() == {"detail": "Invalid review token"}
    assert started_clients == []


def test_route_rejects_invalid_range_and_missing_read_credentials(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(report_routes.router)

    async def fake_session():
        yield object()

    app.dependency_overrides[get_session] = fake_session
    settings = config_module.get_settings().model_copy(
        update={
            "catalog_review_token": "review-secret",
            "dspace_read_username": "",
            "dspace_read_password": "",
        }
    )
    monkeypatch.setattr(report_routes, "get_settings", lambda: settings)
    monkeypatch.setattr(api_routes, "get_settings", lambda: settings)
    client = TestClient(app)
    report_url = "/api/reports/dspace-weekly.csv?from=2026-08-24&to=2026-08-24"

    headers = {"X-Catalog-Review-Token": "review-secret"}

    invalid = client.get(
        "/api/reports/dspace-weekly.csv?from=2026-08-26&to=2026-08-24",
        headers=headers,
    )
    assert invalid.status_code == 422
    assert invalid.json() == {"detail": "invalid_report_range"}

    unavailable = client.get(report_url, headers=headers)
    assert unavailable.status_code == 503
    assert unavailable.json() == {"detail": "dspace_read_credentials_required"}


def _empty_hal(relation: str) -> dict[str, Any]:
    return {
        "_embedded": {relation: []},
        "page": {"number": 0, "totalPages": 0, "totalElements": 0},
    }


def _xlsx_rows(payload: bytes) -> tuple[list[list[str]], bytes]:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        shared_xml = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
        shared_strings = [
            "".join(node.itertext()) for node in shared_xml.findall("main:si", XML_NS)
        ]
        sheet_bytes = archive.read("xl/worksheets/sheet1.xml")
        sheet_xml = ElementTree.fromstring(sheet_bytes)
    rows: list[list[str]] = []
    for row in sheet_xml.findall(".//main:sheetData/main:row", XML_NS):
        values: list[str] = []
        for cell in row.findall("main:c", XML_NS):
            value = cell.find("main:v", XML_NS)
            raw = value.text if value is not None and value.text is not None else ""
            values.append(shared_strings[int(raw)] if cell.get("t") == "s" else raw)
        rows.append(values)
    return rows, sheet_bytes
