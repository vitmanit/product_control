import tempfile

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer


def generate_batch_report_pdf(batch_data: dict, products: list[dict], stats: dict) -> str:
    """Генерирует PDF отчёт по партии. Возвращает путь к временному файлу."""
    tmp = tempfile.NamedTemporaryFile(
        suffix=".pdf",
        prefix=f"batch_{batch_data.get('batch_number', 'unknown')}_report_",
        delete=False,
    )
    doc = SimpleDocTemplate(tmp.name, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Заголовок
    elements.append(Paragraph(
        f"Отчёт по партии #{batch_data.get('batch_number', '')}",
        styles["Title"],
    ))
    elements.append(Spacer(1, 10 * mm))

    # Информация о партии
    elements.append(Paragraph("Информация о партии", styles["Heading2"]))
    info_data = [
        ["Параметр", "Значение"],
        ["Номер партии", str(batch_data.get("batch_number", ""))],
        ["Дата партии", str(batch_data.get("batch_date", ""))],
        ["Статус", "Закрыта" if batch_data.get("is_closed") else "Открыта"],
        ["Смена", str(batch_data.get("shift", ""))],
        ["Бригада", str(batch_data.get("team", ""))],
        ["Номенклатура", str(batch_data.get("nomenclature", ""))],
    ]
    info_table = Table(info_data, colWidths=[60 * mm, 100 * mm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 10 * mm))

    # Статистика
    elements.append(Paragraph("Статистика производства", styles["Heading2"]))
    stats_data = [
        ["Показатель", "Значение"],
        ["Всего продукции", str(stats.get("total_products", 0))],
        ["Аггрегировано", str(stats.get("aggregated", 0))],
        ["Осталось", str(stats.get("remaining", 0))],
        ["Процент выполнения", f"{stats.get('aggregation_rate', 0)}%"],
    ]
    stats_table = Table(stats_data, colWidths=[60 * mm, 100 * mm])
    stats_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(stats_table)

    doc.build(elements)
    tmp.close()
    return tmp.name
