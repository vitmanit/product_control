from datetime import date, datetime

import pandas as pd


COLUMN_MAPPING = {
    "НомерПартии": "batch_number",
    "ДатаПартии": "batch_date",
    "Номенклатура": "nomenclature",
    "РабочийЦентр": "work_center_name",
    "ИдентификаторРЦ": "work_center_identifier",
    "КодЕКН": "ekn_code",
    "Смена": "shift",
    "Бригада": "team",
    "ПредставлениеЗаданияНаСмену": "task_description",
    "ДатаВремяНачалаСмены": "shift_start",
    "ДатаВремяОкончанияСмены": "shift_end",
    "СтатусЗакрытия": "status_closed",
}

REQUIRED_COLUMNS = ["batch_number", "batch_date", "nomenclature", "shift", "team", "task_description"]


def parse_import_file(file_path: str) -> tuple[list[dict], list[dict]]:
    """Парсит Excel/CSV файл. Возвращает (rows, errors)."""
    if file_path.endswith(".csv"):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)

    # Переименование колонок
    df = df.rename(columns=COLUMN_MAPPING)

    rows = []
    errors = []

    for idx, row in df.iterrows():
        row_num = idx + 2  # Excel rows start at 1, header is row 1
        row_dict = row.to_dict()

        # Проверка обязательных полей
        missing = [col for col in REQUIRED_COLUMNS if pd.isna(row_dict.get(col))]
        if missing:
            errors.append({"row": row_num, "error": f"Missing required fields: {', '.join(missing)}"})
            continue

        # Преобразование типов
        try:
            row_dict["batch_number"] = int(row_dict["batch_number"])
            if isinstance(row_dict.get("batch_date"), str):
                row_dict["batch_date"] = date.fromisoformat(row_dict["batch_date"])
            elif isinstance(row_dict.get("batch_date"), datetime):
                row_dict["batch_date"] = row_dict["batch_date"].date()

            for dt_field in ["shift_start", "shift_end"]:
                if dt_field in row_dict and isinstance(row_dict[dt_field], str):
                    row_dict[dt_field] = datetime.fromisoformat(row_dict[dt_field])

            row_dict["status_closed"] = bool(row_dict.get("status_closed", False))
        except (ValueError, TypeError) as e:
            errors.append({"row": row_num, "error": str(e)})
            continue

        rows.append(row_dict)

    return rows, errors
