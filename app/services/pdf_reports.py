from io import BytesIO
from pathlib import Path

from aiogram.types import BufferedInputFile
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


FONT_NAME = "ReportFont"
FONT_PATHS = [
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]


def ensure_font_registered() -> str:
    if FONT_NAME in pdfmetrics.getRegisteredFontNames():
        return FONT_NAME

    for font_path in FONT_PATHS:
        if Path(font_path).exists():
            pdfmetrics.registerFont(TTFont(FONT_NAME, font_path))
            return FONT_NAME

    raise FileNotFoundError("Не найден шрифт с поддержкой кириллицы для PDF.")


def _build_pdf(
    title: str,
    headers: list[str],
    rows: list[list[str]],
    filename: str,
    col_widths: list[float] | None = None,
) -> BufferedInputFile:
    font_name = ensure_font_registered()
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = styles["Title"].clone("ReportTitle")
    title_style.fontName = font_name
    title_style.fontSize = 16

    cell_style = styles["BodyText"].clone("ReportCell")
    cell_style.fontName = font_name
    cell_style.fontSize = 10
    cell_style.leading = 12

    table_data = []
    if headers:
        table_data.append([Paragraph(f"<b>{header}</b>", cell_style) for header in headers])

    for row_index, row in enumerate(rows):
        is_header_row = not headers and row_index == 0
        formatted_row = []
        for cell in row:
            cell_text = f"<b>{cell}</b>" if is_header_row else str(cell)
            formatted_row.append(Paragraph(cell_text, cell_style))
        table_data.append(formatted_row)

    table = Table(table_data, repeatRows=1, colWidths=col_widths)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9EAF7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FC")]),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    document.build([Paragraph(title, title_style), Spacer(1, 6 * mm), table])
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return BufferedInputFile(pdf_bytes, filename=filename)


def build_student_grades_pdf(student_name: str, rows: list[list[str]]) -> BufferedInputFile:
    return _build_pdf(
        title=f"Таблица оценок ученика: {student_name}",
        headers=["№ ДЗ", "Название задания", "Оценка"],
        rows=rows,
        filename="student_grades.pdf",
    )


def build_teacher_grades_pdf(rows: list[list[str]]) -> BufferedInputFile:
    col_widths = None
    if rows and rows[0]:
        first_column_width = 22 * mm
        other_columns_count = len(rows[0]) - 1
        if other_columns_count > 0:
            page_width, _ = landscape(A4)
            usable_width = page_width - (12 * mm * 2)
            remaining_width = max(usable_width - first_column_width, 40 * mm)
            other_width = remaining_width / other_columns_count
            col_widths = [first_column_width, *([other_width] * other_columns_count)]

    return _build_pdf(
        title="Таблица оценок по всем ученикам",
        headers=[],
        rows=rows,
        filename="all_students_grades.pdf",
        col_widths=col_widths,
    )
