from __future__ import annotations

import enum
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.config import get_settings
from cataloging_api.db.session import get_session
from cataloging_api.dspace.authenticated_client import ReadAuthenticatedDSpaceClient
from cataloging_api.dspace.client import DSpaceError
from cataloging_api.reports.exporters import export_csv, export_pdf, export_xlsx
from cataloging_api.reports.weekly_dspace import (
    DatabaseRawEvidenceRecorder,
    WeeklyDSpaceReportService,
)

router = APIRouter()
SessionDep = Annotated[AsyncSession, Depends(get_session)]


class ReportFormat(enum.StrEnum):
    csv = "csv"
    xlsx = "xlsx"
    pdf = "pdf"


@router.get("/api/reports/dspace-weekly.{file_format}")
async def download_weekly_dspace_report(
    file_format: ReportFormat,
    session: SessionDep,
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
) -> Response:
    if from_date > to_date:
        raise HTTPException(status_code=422, detail="invalid_report_range")
    settings = get_settings()
    if not settings.dspace_read_username or not settings.dspace_read_password:
        raise HTTPException(status_code=503, detail="dspace_read_credentials_required")

    try:
        async with ReadAuthenticatedDSpaceClient(
            settings.dspace_base_url,
            timeout_seconds=settings.dspace_timeout_seconds,
            max_retries=settings.dspace_max_retries,
        ) as client:
            await client.authenticate(
                settings.dspace_read_username,
                settings.dspace_read_password,
            )
            service = WeeklyDSpaceReportService(
                client,
                DatabaseRawEvidenceRecorder(session),
                ui_base_url=settings.dspace_ui_base_url,
                page_size=settings.dspace_page_size,
            )
            report = await service.generate(from_date=from_date, to_date=to_date)
    except DSpaceError as exc:
        raise HTTPException(status_code=502, detail=f"dspace_report_unavailable:{exc.code}") from exc

    if file_format is ReportFormat.csv:
        content = export_csv(report)
        media_type = "text/csv; charset=utf-8"
    elif file_format is ReportFormat.xlsx:
        content = export_xlsx(report)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        content = export_pdf(report, font_path=settings.report_pdf_font_path or None)
        media_type = "application/pdf"

    filename = (
        f"dspace-weekly-{from_date.isoformat()}-{to_date.isoformat()}.{file_format.value}"
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )
