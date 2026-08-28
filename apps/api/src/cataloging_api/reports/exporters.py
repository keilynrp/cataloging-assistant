from __future__ import annotations

import csv
import html
import io
from pathlib import Path

import xlsxwriter
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from cataloging_api.reports.weekly_dspace import VISIBLE_HEADERS, WeeklyReport

_FORMULA_PREFIXES = ("=", "+", "-", "@")
_PDF_FONT_NAME = "WeeklyReportUnicode"
_SYSTEM_FONT_PATHS = (
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
    Path("C:/Windows/Fonts/arial.ttf"),
)


def export_csv(report: WeeklyReport) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(VISIBLE_HEADERS)
    for row in report.rows:
        writer.writerow(
            [row.number, *(_csv_safe(value) for value in row.visible_values()[1:])]
        )
    return output.getvalue().encode("utf-8-sig")


def export_xlsx(report: WeeklyReport) -> bytes:
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(
        output,
        {
            "in_memory": True,
            "strings_to_formulas": False,
            "strings_to_urls": False,
        },
    )
    worksheet = workbook.add_worksheet("Reporte semanal")
    header_format = workbook.add_format(
        {
            "bold": True,
            "bg_color": "#DCECE6",
            "font_color": "#0E4736",
            "border": 1,
            "text_wrap": True,
            "valign": "top",
        }
    )
    text_format = workbook.add_format(
        {"num_format": "@", "text_wrap": True, "valign": "top"}
    )
    hyperlink_format = workbook.add_format(
        {
            "font_color": "blue",
            "underline": True,
            "text_wrap": True,
            "valign": "top",
        }
    )

    for column, header in enumerate(VISIBLE_HEADERS):
        worksheet.write_string(0, column, header, header_format)
    for row_number, row in enumerate(report.rows, start=1):
        values = row.visible_values()
        worksheet.write_number(row_number, 0, row.number)
        for column, value in enumerate(values[1:], start=1):
            if column == 3:
                worksheet.write_url(
                    row_number,
                    column,
                    str(value),
                    hyperlink_format,
                    string=str(value),
                )
            else:
                worksheet.write_string(row_number, column, str(value), text_format)

    worksheet.freeze_panes(1, 0)
    worksheet.autofilter(0, 0, len(report.rows), len(VISIBLE_HEADERS) - 1)
    worksheet.set_column(0, 0, 6)
    worksheet.set_column(1, 1, 20)
    worksheet.set_column(2, 2, 34)
    worksheet.set_column(3, 3, 48)
    worksheet.set_column(4, 4, 34)
    worksheet.set_column(5, 5, 22)
    worksheet.set_column(6, 6, 24)
    workbook.close()
    return output.getvalue()


def export_pdf(report: WeeklyReport, *, font_path: str | None = None) -> bytes:
    registered_font = _register_system_font(font_path)
    output = io.BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=landscape(letter),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title="Reporte semanal DSpace",
    )
    title_style = ParagraphStyle(
        "WeeklyReportTitle",
        fontName=registered_font,
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#0E4736"),
        spaceAfter=4 * mm,
    )
    cell_style = ParagraphStyle(
        "WeeklyReportCell",
        fontName=registered_font,
        fontSize=6.3,
        leading=7.8,
        alignment=TA_LEFT,
        wordWrap="CJK",
    )
    header_style = ParagraphStyle(
        "WeeklyReportHeader",
        parent=cell_style,
        fontSize=6.5,
        leading=8,
        textColor=colors.HexColor("#0E4736"),
    )

    table_data = [
        [Paragraph(html.escape(header), header_style) for header in VISIBLE_HEADERS]
    ]
    for row in report.rows:
        table_data.append(
            [
                Paragraph(html.escape(str(value)), cell_style)
                for value in row.visible_values()
            ]
        )
    table = Table(
        table_data,
        colWidths=[9 * mm, 25 * mm, 46 * mm, 59 * mm, 45 * mm, 29 * mm, 36 * mm],
        repeatRows=1,
        splitByRow=True,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCECE6")),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#AEB8B2")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2.5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2.5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    period = f"{report.from_date.isoformat()} – {report.to_date.isoformat()}"
    story = [
        Paragraph(f"Reporte semanal DSpace · {html.escape(period)}", title_style),
        Spacer(1, 1 * mm),
        table,
    ]
    document.build(story)
    return output.getvalue()


def _csv_safe(value: object) -> str:
    text = str(value)
    if text.lstrip().startswith(_FORMULA_PREFIXES):
        return f"'{text}"
    return text


def _register_system_font(preferred_path: str | None) -> str:
    candidates = ([Path(preferred_path)] if preferred_path else []) + list(_SYSTEM_FONT_PATHS)
    path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if path is None:
        raise RuntimeError("unicode_pdf_font_unavailable")
    if _PDF_FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(_PDF_FONT_NAME, str(path)))
    return _PDF_FONT_NAME
