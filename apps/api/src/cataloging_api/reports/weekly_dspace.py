from __future__ import annotations

import re
import unicodedata
import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime
from typing import Any, Protocol
from urllib.parse import quote, urlsplit
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.dspace.client import DSpaceClient, DSpaceError, HalCollectionPage
from cataloging_api.dspace.contract_store import (
    DSpaceContractSyncRun,
    create_sync_run,
    mark_run_complete,
    mark_run_failed,
    mark_run_interrupted,
    persist_page_and_advance_checkpoint,
)

REPORT_TIMEZONE_NAME = "America/Mexico_City"
REPORT_TIMEZONE = ZoneInfo(REPORT_TIMEZONE_NAME)
REPORT_COLLECTOR_VERSION = "vertical-025/1"
VISIBLE_HEADERS = (
    "#",
    "ID",
    "Título",
    "URL interna DSpace",
    "Autor(es)",
    "Estado",
    "Catalogador",
)

_TERMINAL_DATE = re.compile(r"(\d{8})$")
_APOSTROPHES = str.maketrans(
    {
        "'": "’",
        "`": "’",
        "´": "’",
        "ʻ": "’",
        "ʼ": "’",
        "‘": "’",
        "′": "’",
    }
)
_MOJIBAKE_REPLACEMENTS = (
    ("â€™", "’"),
    ("â€˜", "‘"),
    ("Ã¡", "á"),
    ("Ã©", "é"),
    ("Ã­", "í"),
    ("Ã³", "ó"),
    ("Ãº", "ú"),
    ("Ã±", "ñ"),
    ("Ã", "Á"),
    ("Ã‰", "É"),
    ("Ã", "Í"),
    ("Ã“", "Ó"),
    ("Ãš", "Ú"),
    ("Ã‘", "Ñ"),
)


@dataclass(frozen=True)
class WeeklyReportRow:
    number: int
    identifier: str
    title: str
    internal_url: str
    responsibility: str
    status: str
    cataloger: str
    catalog_date: date
    catalog_date_source: str
    source_surface: str
    responsibility_source: str
    item_uuid: str | None
    raw_source_refs: tuple[str, ...]

    def visible_values(self) -> tuple[int | str, ...]:
        return (
            self.number,
            self.identifier,
            self.title,
            self.internal_url,
            self.responsibility,
            self.status,
            self.cataloger,
        )


@dataclass(frozen=True)
class WeeklyReport:
    from_date: date
    to_date: date
    timezone: str
    evidence_run_id: str
    rows: tuple[WeeklyReportRow, ...]


class RawEvidenceRecorder(Protocol):
    async def start(self) -> str: ...

    async def record(
        self,
        *,
        surface: str,
        endpoint: str,
        page_number: int,
        request_params: dict[str, Any],
        raw_payload: dict[str, Any],
    ) -> str: ...

    async def complete(self) -> None: ...

    async def fail(self, *, interrupted: bool, code: str, message: str) -> None: ...


class DatabaseRawEvidenceRecorder:
    """Adapter over the existing immutable VERTICAL-022 raw HAL store."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._run: DSpaceContractSyncRun | None = None

    async def start(self) -> str:
        self._run = await create_sync_run(
            self._session,
            collector_version=REPORT_COLLECTOR_VERSION,
        )
        await self._session.commit()
        return str(self._run.run_id)

    async def record(
        self,
        *,
        surface: str,
        endpoint: str,
        page_number: int,
        request_params: dict[str, Any],
        raw_payload: dict[str, Any],
    ) -> str:
        run = self._require_run()
        page = await persist_page_and_advance_checkpoint(
            self._session,
            run=run,
            surface=surface,
            endpoint=endpoint,
            page_number=page_number,
            request_params=request_params,
            raw_payload=raw_payload,
        )
        await self._session.commit()
        return f"dspace_contract_raw_pages:{page.page_id}:{page.raw_hash}"

    async def complete(self) -> None:
        await mark_run_complete(self._session, run=self._require_run())
        await self._session.commit()

    async def fail(self, *, interrupted: bool, code: str, message: str) -> None:
        run = self._require_run()
        marker = mark_run_interrupted if interrupted else mark_run_failed
        await marker(
            self._session,
            run=run,
            error_code=code,
            error_message=message,
        )
        await self._session.commit()

    def _require_run(self) -> DSpaceContractSyncRun:
        if self._run is None:
            raise RuntimeError("report_evidence_run_not_started")
        return self._run


PageLoader = Callable[..., Awaitable[HalCollectionPage]]


class WeeklyDSpaceReportService:
    def __init__(
        self,
        client: DSpaceClient,
        evidence: RawEvidenceRecorder,
        *,
        ui_base_url: str,
        workflow_ui_url: str | None = None,
        page_size: int = 100,
    ) -> None:
        self._client = client
        self._evidence = evidence
        self._ui_base_url = ui_base_url.rstrip("/")
        self._workflow_ui_url = (workflow_ui_url or self._ui_base_url).rstrip("/")
        self._page_size = page_size

    async def generate(self, *, from_date: date, to_date: date) -> WeeklyReport:
        if from_date > to_date:
            raise ValueError("invalid_report_range")

        evidence_run_id = await self._evidence.start()
        rows: list[WeeklyReportRow] = []
        try:
            await self._collect_archived(rows, from_date=from_date, to_date=to_date)
            await self._collect_submissions(
                rows,
                source_surface="submission/workspaceitems",
                endpoint="/submission/workspaceitems",
                loader=self._client.get_workspace_items_page,
                item_loader=self._client.get_workspace_item_item,
                status="Guardado",
                from_date=from_date,
                to_date=to_date,
            )
            await self._collect_submissions(
                rows,
                source_surface="workflow/workflowitems",
                endpoint="/workflow/workflowitems",
                loader=self._client.get_workflow_items_page,
                item_loader=self._client.get_workflow_item_item,
                status="En flujo de trabajo",
                from_date=from_date,
                to_date=to_date,
            )
        except DSpaceError as exc:
            await self._evidence.fail(interrupted=True, code=exc.code, message=str(exc))
            raise
        except Exception as exc:
            await self._evidence.fail(
                interrupted=False,
                code="report_collection_error",
                message=str(exc),
            )
            raise

        ordered = sorted(rows, key=lambda row: (row.catalog_date, row.status, row.identifier))
        numbered = tuple(replace(row, number=index) for index, row in enumerate(ordered, start=1))
        await self._evidence.complete()
        return WeeklyReport(
            from_date=from_date,
            to_date=to_date,
            timezone=REPORT_TIMEZONE_NAME,
            evidence_run_id=evidence_run_id,
            rows=numbered,
        )

    async def _collect_archived(
        self,
        rows: list[WeeklyReportRow],
        *,
        from_date: date,
        to_date: date,
    ) -> None:
        page_number = 0
        while True:
            page = await self._client.get_items_page(page=page_number, size=self._page_size)
            _require_requested_page(page, requested_page=page_number, endpoint="/core/items")
            source_ref = await self._record_page(
                page,
                surface="weekly_core_items",
                endpoint="/core/items",
            )
            for raw_item in page.items:
                row = build_archived_row(
                    raw_item,
                    ui_base_url=self._ui_base_url,
                    raw_source_refs=(source_ref,),
                )
                if row is not None and from_date <= row.catalog_date <= to_date:
                    rows.append(row)
            if page.total_pages <= page.page + 1:
                return
            page_number = page.page + 1

    async def _collect_submissions(
        self,
        rows: list[WeeklyReportRow],
        *,
        source_surface: str,
        endpoint: str,
        loader: PageLoader,
        item_loader: Callable[[str | int], Awaitable[dict[str, Any]]],
        status: str,
        from_date: date,
        to_date: date,
    ) -> None:
        page_number = 0
        while True:
            page = await loader(page=page_number, size=self._page_size)
            _require_requested_page(page, requested_page=page_number, endpoint=endpoint)
            page_ref = await self._record_page(
                page,
                surface=f"weekly_{source_surface.replace('/', '_')}",
                endpoint=endpoint,
            )
            for submission in page.items:
                submission_id = submission.get("id")
                if submission_id is None:
                    raise DSpaceError(
                        "invalid_hal",
                        f"Expected submission id in DSpace response at {endpoint}",
                    )
                item: dict[str, Any] | None = None
                item_ref: str | None = None
                try:
                    item = await item_loader(str(submission_id))
                except DSpaceError as exc:
                    if exc.status_code != 404:
                        raise
                    item = None
                if item is not None:
                    item_ref = await self._evidence.record(
                        surface=(
                            f"weekly_{source_surface.replace('/', '_')}_item:{submission_id}"
                        ),
                        endpoint=f"/{source_surface}/{submission_id}/item",
                        page_number=0,
                        request_params={},
                        raw_payload=item,
                    )
                refs = (page_ref,) if item_ref is None else (page_ref, item_ref)
                row = build_submission_row(
                    submission,
                    item=item,
                    source_surface=source_surface,
                    status=status,
                    ui_base_url=self._ui_base_url,
                    workflow_ui_url=self._workflow_ui_url,
                    raw_source_refs=refs,
                )
                if row is not None and from_date <= row.catalog_date <= to_date:
                    rows.append(row)
            if page.total_pages <= page.page + 1:
                return
            page_number = page.page + 1

    async def _record_page(
        self,
        page: HalCollectionPage,
        *,
        surface: str,
        endpoint: str,
    ) -> str:
        if page.page < 0:
            raise DSpaceError("invalid_hal", f"DSpace returned invalid page at {endpoint}")
        return await self._evidence.record(
            surface=surface,
            endpoint=endpoint,
            page_number=page.page,
            request_params={"page": page.page, "size": self._page_size},
            raw_payload=page.raw_payload,
        )


def normalize_report_text(value: object) -> str:
    text = "" if value is None else str(value)
    for broken, repaired in _MOJIBAKE_REPLACEMENTS:
        text = text.replace(broken, repaired)
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\u00a0", " ").replace("\r", " ").replace("\n", " ")
    text = text.translate(_APOSTROPHES)
    return " ".join(text.split())


def build_archived_row(
    raw_item: dict[str, Any],
    *,
    ui_base_url: str,
    raw_source_refs: Sequence[str],
) -> WeeklyReportRow | None:
    if raw_item.get("inArchive") is not True and raw_item.get("withdrawn") is not True:
        return None
    metadata = _coerce_metadata(raw_item.get("metadata"))
    provenance = _yct_provenance(metadata)
    if provenance is None:
        return None
    catalog_date, date_source = _catalog_date(
        provenance,
        accessioned=_first_value(metadata, "dc.date.accessioned"),
        item_last_modified=raw_item.get("lastModified"),
    )
    if catalog_date is None or date_source is None:
        return None

    handle = normalize_report_text(raw_item.get("handle"))
    return _make_row(
        identifier=handle,
        title=_first_value(metadata, "dc.title") or normalize_report_text(raw_item.get("name")),
        internal_url=_archived_url(metadata, handle=handle, ui_base_url=ui_base_url),
        metadata=metadata,
        provenance=provenance,
        status="Retirado" if raw_item.get("withdrawn") is True else "Depositado",
        catalog_date=catalog_date,
        catalog_date_source=date_source,
        source_surface="core/items",
        item_uuid=_item_uuid(raw_item),
        raw_source_refs=raw_source_refs,
    )


def build_submission_row(
    submission: dict[str, Any],
    *,
    item: dict[str, Any] | None,
    source_surface: str,
    status: str,
    ui_base_url: str,
    raw_source_refs: Sequence[str],
    workflow_ui_url: str | None = None,
) -> WeeklyReportRow | None:
    submission_id = submission.get("id")
    if submission_id is None:
        return None
    metadata = (
        _coerce_metadata(item.get("metadata"))
        if item is not None
        else _metadata_from_sections(submission.get("sections"))
    )
    provenance = _yct_provenance(metadata)
    if provenance is None:
        return None
    catalog_date, date_source = _catalog_date(
        provenance,
        item_last_modified=item.get("lastModified") if item is not None else None,
    )
    if catalog_date is None or date_source is None:
        return None

    if source_surface == "submission/workspaceitems":
        internal_url = f"{ui_base_url.rstrip('/')}/workspaceitems/{quote(str(submission_id))}/edit"
    else:
        internal_url = (workflow_ui_url or ui_base_url).rstrip("/")
    return _make_row(
        identifier=normalize_report_text(submission_id),
        title=_first_value(metadata, "dc.title"),
        internal_url=internal_url,
        metadata=metadata,
        provenance=provenance,
        status=status,
        catalog_date=catalog_date,
        catalog_date_source=date_source,
        source_surface=source_surface,
        item_uuid=_item_uuid(item),
        raw_source_refs=raw_source_refs,
    )


def _make_row(
    *,
    identifier: str,
    title: str,
    internal_url: str,
    metadata: dict[str, list[dict[str, Any]]],
    provenance: str,
    status: str,
    catalog_date: date,
    catalog_date_source: str,
    source_surface: str,
    item_uuid: str | None,
    raw_source_refs: Sequence[str],
) -> WeeklyReportRow:
    if not raw_source_refs:
        raise ValueError("report_row_requires_raw_evidence")
    authors = _values(metadata, "dc.contributor.author")
    editors = _values(metadata, "dc.contributor.editor")
    if authors:
        responsibility = "; ".join(authors)
        responsibility_source = "dc.contributor.author"
    elif editors:
        responsibility = "; ".join(editors)
        responsibility_source = "dc.contributor.editor"
    else:
        responsibility = ""
        responsibility_source = "unavailable"
    return WeeklyReportRow(
        number=0,
        identifier=normalize_report_text(identifier),
        title=normalize_report_text(title),
        internal_url=normalize_report_text(internal_url),
        responsibility=normalize_report_text(responsibility),
        status=status,
        cataloger=provenance,
        catalog_date=catalog_date,
        catalog_date_source=catalog_date_source,
        source_surface=source_surface,
        responsibility_source=responsibility_source,
        item_uuid=item_uuid,
        raw_source_refs=tuple(dict.fromkeys(raw_source_refs)),
    )


def _coerce_metadata(value: object) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, list[dict[str, Any]]] = {}
    for field, entries in value.items():
        if not isinstance(field, str) or not isinstance(entries, list):
            continue
        result[field] = [entry for entry in entries if isinstance(entry, dict)]
    return result


def _metadata_from_sections(value: object) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}

    def visit(node: object) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                if (
                    isinstance(key, str)
                    and (key.startswith("dc.") or key.startswith("dcterms."))
                    and isinstance(child, list)
                ):
                    result.setdefault(key, []).extend(
                        entry for entry in child if isinstance(entry, dict)
                    )
                else:
                    visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(value)
    return result


def _values(metadata: dict[str, list[dict[str, Any]]], field: str) -> list[str]:
    values: list[str] = []
    for entry in metadata.get(field, []):
        normalized = normalize_report_text(entry.get("value"))
        if normalized:
            values.append(normalized)
    return values


def _first_value(metadata: dict[str, list[dict[str, Any]]], field: str) -> str:
    values = _values(metadata, field)
    return values[0] if values else ""


def _yct_provenance(metadata: dict[str, list[dict[str, Any]]]) -> str | None:
    for value in _values(metadata, "dcterms.provenance"):
        if value.casefold().startswith("yct"):
            return value
    return None


def _catalog_date(
    provenance: str,
    *,
    accessioned: object = None,
    item_last_modified: object = None,
) -> tuple[date | None, str | None]:
    match = _TERMINAL_DATE.search(provenance)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y%m%d").date(), "dcterms.provenance"
        except ValueError:
            pass
    for value, source in (
        (accessioned, "dc.date.accessioned"),
        (item_last_modified, "item.lastModified"),
    ):
        converted = _timestamp_to_report_date(value)
        if converted is not None:
            return converted, source
    return None, None


def _timestamp_to_report_date(value: object) -> date | None:
    if value is None or value == "":
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(REPORT_TIMEZONE).date()


def _archived_url(
    metadata: dict[str, list[dict[str, Any]]],
    *,
    handle: str,
    ui_base_url: str,
) -> str:
    for candidate in _values(metadata, "dc.identifier.uri"):
        if _same_origin(candidate, ui_base_url):
            return candidate
    return f"{ui_base_url.rstrip('/')}/handle/{quote(handle, safe='/')}"


def _same_origin(candidate: str, configured_base: str) -> bool:
    try:
        left = urlsplit(candidate)
        right = urlsplit(configured_base)
        return (
            left.scheme.casefold(),
            left.hostname.casefold() if left.hostname else None,
            _effective_port(left.scheme, left.port),
        ) == (
            right.scheme.casefold(),
            right.hostname.casefold() if right.hostname else None,
            _effective_port(right.scheme, right.port),
        )
    except ValueError:
        return False


def _effective_port(scheme: str, port: int | None) -> int | None:
    if port is not None:
        return port
    return {"http": 80, "https": 443}.get(scheme.casefold())


def _require_requested_page(
    page: HalCollectionPage,
    *,
    requested_page: int,
    endpoint: str,
) -> None:
    if page.page != requested_page:
        raise DSpaceError(
            "invalid_hal",
            f"DSpace returned page {page.page} for requested page {requested_page} at {endpoint}",
        )


def _item_uuid(item: dict[str, Any] | None) -> str | None:
    if item is None:
        return None
    value = item.get("uuid") or item.get("id")
    if value is None:
        return None
    try:
        return str(uuid.UUID(str(value)))
    except ValueError:
        return normalize_report_text(value) or None
