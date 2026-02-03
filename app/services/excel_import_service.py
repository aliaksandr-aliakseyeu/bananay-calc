"""Excel import service for Producer SKU."""
from typing import Any

from openpyxl import load_workbook
from pydantic import ValidationError

from app.schemas.producer_sku import ProducerSKUCreate


class ExcelImportError(Exception):
    """Custom exception for Excel import errors."""

    pass


class ExcelImportService:
    """Service for importing Producer SKU from Excel files."""

    # Column mapping for Russian template
    RU_COLUMNS = {
        "№": "row_number",
        "наименование товара": "name",
        "наименование товара*": "name",
        "артикул": "sku_code",
        "Штрих код": "barcode",
        "ритейл/хорека": "sales_channel",
        "канал": "sales_channel",
        "категория товара": "product_category",
        "категория": "product_category",
        "категория температурного режима": "temperature_mode",
        "режим": "temperature_mode",
        "длинна см.": "length_cm",
        "ширина см.": "width_cm",
        "высота см.": "height_cm",
        "кол. В упаковке шт.": "items_per_box",
        "вес гр.": "weight_g",
        "Длинна см.": "box_length_cm",
        "Ширина см.": "box_width_cm",
        "Высота см.": "box_height_cm",
        "кол. На евро палете": "items_per_pallet",
        "кол. В одном ряду": "items_per_pallet_row",
        "максимальное число рядов на паллете": "max_pallet_rows",
        "высота, включая паллет": "pallet_height_cm",
        "общий вес полного палета.": "full_pallet_weight_kg",
    }

    EN_COLUMNS = {
        "No.": "row_number",
        "Product Name": "name",
        "SKU Code": "sku_code",
        "Barcode": "barcode",
        "Retail/HoReCa": "sales_channel",
        "Product Category": "product_category",
        "Category": "product_category",
        "Temperature Mode": "temperature_mode",
        "Length (cm)": "length_cm",
        "Width (cm)": "width_cm",
        "Height (cm)": "height_cm",
        "Items per Box": "items_per_box",
        "Weight (g)": "weight_g",
        "Box Length (cm)": "box_length_cm",
        "Box Width (cm)": "box_width_cm",
        "Box Height (cm)": "box_height_cm",
        "Box Weight (g)": "box_weight_g",
        "Items per Pallet": "items_per_pallet",
        "Items per Row": "items_per_pallet_row",
        "Max Rows": "max_pallet_rows",
        "Pallet Height (cm)": "pallet_height_cm",
        "Full Pallet Weight (kg)": "full_pallet_weight_kg",
    }

    @classmethod
    def detect_language(cls, headers: list[str]) -> str:
        """Detect template language based on headers."""
        ru_matches = sum(1 for h in headers if h in cls.RU_COLUMNS)
        en_matches = sum(1 for h in headers if h in cls.EN_COLUMNS)

        if ru_matches > en_matches:
            return "ru"
        elif en_matches > ru_matches:
            return "en"
        else:
            raise ExcelImportError(
                "Cannot detect template language. Please use the official template."
            )

    @classmethod
    def parse_excel(cls, file_content: bytes) -> list[dict[str, Any]]:
        """Parse Excel file and return list of SKU data dictionaries."""
        try:
            from io import BytesIO

            wb = load_workbook(BytesIO(file_content), data_only=True)
            ws = wb.active

            rows = list(ws.rows)
            if len(rows) < 7:
                raise ExcelImportError("Excel file is too short. Expected at least 7 rows.")

            header_row_1 = [cell.value for cell in rows[3]]
            header_row_2 = [cell.value for cell in rows[4]]

            header_row_1_filled: list[Any] = []
            current_group = None
            for v in header_row_1:
                if v is not None and str(v).strip() != "":
                    current_group = v
                header_row_1_filled.append(current_group)

            all_headers = [h for h in header_row_1 + header_row_2 if h]
            language = cls.detect_language(all_headers)
            column_map = cls.RU_COLUMNS if language == "ru" else cls.EN_COLUMNS

            col_indices: dict[str, int] = {}

            for col_idx in range(max(len(header_row_1_filled), len(header_row_2))):
                header1 = header_row_1_filled[col_idx] if col_idx < len(header_row_1_filled) else None
                header2 = header_row_2[col_idx] if col_idx < len(header_row_2) else None

                if header2 == "вес гр.":
                    parent_header = str(header1 or "").lower()
                    if "индивидуальной" in parent_header:
                        field_name = "weight_g"
                    else:
                        field_name = "box_weight_g"
                    col_indices[field_name] = col_idx
                    continue

                header = None
                if header2 and header2 in column_map:
                    header = header2
                elif header1 and header1 in column_map:
                    header = header1

                if header:
                    field_name = column_map[header]
                    if field_name not in col_indices:
                        col_indices[field_name] = col_idx

            skus_data = []
            for row_idx, row in enumerate(rows[6:], start=7):
                row_values = [cell.value for cell in row]
                if all(v is None or str(v).strip() == "" for v in row_values):
                    continue

                name_idx = col_indices.get("name")
                if name_idx is None or row_values[name_idx] is None:
                    continue

                sku_data = {"row_number": row_idx}

                for field_name, col_idx in col_indices.items():
                    if field_name == "row_number":
                        continue

                    if col_idx < len(row_values):
                        value = row_values[col_idx]

                        if value is not None:
                            value = cls._clean_value(field_name, value)

                        if value is not None and value != "":
                            sku_data[field_name] = value

                if sku_data.get("name"):
                    skus_data.append(sku_data)

            if not skus_data:
                raise ExcelImportError("No valid SKU data found in Excel file.")

            return skus_data

        except ExcelImportError:
            raise
        except Exception as e:
            raise ExcelImportError(f"Error parsing Excel file: {str(e)}")

    @classmethod
    def _clean_value(cls, field_name: str, value: Any) -> Any:
        """Clean and convert value based on field type."""
        if value is None or str(value).strip() == "":
            return None

        value_str = str(value).strip()

        if field_name == "sales_channel":
            normalized = value_str.lower().replace("ё", "е")
            if "ритейл" in normalized or "розниц" in normalized or "retail" in normalized:
                return "retail"
            if "хорек" in normalized or "horeca" in normalized:
                return "horeca"
            return normalized

        numeric_fields = {
            "length_cm",
            "width_cm",
            "height_cm",
            "box_length_cm",
            "box_width_cm",
            "box_height_cm",
            "pallet_height_cm",
            "full_pallet_weight_kg",
        }

        integer_fields = {
            "items_per_box",
            "items_per_pallet",
            "items_per_pallet_row",
            "max_pallet_rows",
        }

        if field_name == "weight_g":
            try:
                weight_g = float(value_str)
                return weight_g / 1000
            except (ValueError, TypeError):
                return None

        if field_name == "box_weight_g":
            try:
                return float(value_str)
            except (ValueError, TypeError):
                return None

        if field_name in numeric_fields:
            try:
                return float(value_str)
            except (ValueError, TypeError):
                return None

        if field_name in integer_fields:
            try:
                return int(float(value_str))
            except (ValueError, TypeError):
                return None

        return value_str

    @classmethod
    def validate_skus(cls, skus_data: list[dict[str, Any]]) -> tuple[list[ProducerSKUCreate], list[dict]]:
        """
        Validate SKU data and return valid SKUs and errors.

        Returns:
            Tuple of (valid_skus, errors)
            errors is list of dicts with row_number and error message
        """
        valid_skus = []
        errors = []

        for sku_data in skus_data:
            row_number = sku_data.pop("row_number", "unknown")

            try:
                if "name" not in sku_data:
                    raise ValidationError("Name is required")

                sku_data.setdefault("is_active", True)

                if "weight_g" in sku_data:
                    sku_data["weight_kg"] = sku_data.pop("weight_g")

                sku_data.pop("product_category", None)
                sku_data.pop("temperature_mode", None)

                sku = ProducerSKUCreate(**sku_data)
                valid_skus.append(sku)

            except ValidationError as e:
                error_list = []
                for err in e.errors():
                    loc = " -> ".join(str(x) for x in err.get('loc', []))
                    msg = err.get('msg', 'Unknown error')
                    error_list.append(f"{loc}: {msg}")
                errors.append({
                    "row": row_number,
                    "sku_code": sku_data.get("sku_code"),
                    "name": sku_data.get("name"),
                    "errors": error_list,
                    "details": str(e)
                })
            except Exception as e:
                errors.append({
                    "row": row_number,
                    "sku_code": sku_data.get("sku_code"),
                    "name": sku_data.get("name"),
                    "errors": [str(e)],
                    "details": str(e)
                })

        return valid_skus, errors
