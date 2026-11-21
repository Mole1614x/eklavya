"""Resource-bounded parsing and transformations for learner datasets."""

from __future__ import annotations

import csv
import io
import json
import math
import statistics
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any


class DatasetError(ValueError):
    pass


MAX_ROWS = 10_000
MAX_COLUMNS = 200
MAX_CELL_CHARS = 20_000
MAX_XLSX_UNCOMPRESSED_BYTES = 50_000_000
MAX_XLSX_ENTRIES = 5_000


def validate_filename(filename: str) -> tuple[str, str]:
    if filename != Path(filename).name or "\x00" in filename:
        raise DatasetError("Filename must not contain a path")
    extension = Path(filename).suffix.lower()
    formats = {".csv": "CSV", ".xlsx": "XLSX", ".json": "JSON", ".parquet": "PARQUET"}
    if extension not in formats:
        raise DatasetError("Supported dataset formats are CSV, XLSX, JSON, and Parquet")
    return extension, formats[extension]


def validate_xlsx_archive(data: bytes, max_uncompressed_bytes: int = MAX_XLSX_UNCOMPRESSED_BYTES) -> None:
    """Reject malformed or expansion-heavy XLSX ZIP containers before parsing."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            total_size = sum(entry.file_size for entry in entries)
            if not entries or len(entries) > MAX_XLSX_ENTRIES or total_size > max_uncompressed_bytes:
                raise DatasetError("Workbook exceeds the safe decompressed-size limit")
            for entry in entries:
                parts = Path(entry.filename).parts
                if entry.filename.startswith(("/", "\\")) or ".." in parts:
                    raise DatasetError("Workbook contains an invalid internal path")
    except (zipfile.BadZipFile, OSError) as error:
        raise DatasetError("XLSX workbook is malformed") from error


def parse_dataset(data: bytes, dataset_format: str) -> tuple[list[dict[str, Any]], list[str]]:
    if dataset_format == "CSV":
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise DatasetError("CSV files must use UTF-8 encoding") from error
        if "\x00" in text:
            raise DatasetError("CSV contains invalid null bytes")
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or len(reader.fieldnames) > MAX_COLUMNS:
            raise DatasetError("Dataset must contain 1 to 200 named columns")
        rows = []
        for index, row in enumerate(reader):
            if index >= MAX_ROWS:
                raise DatasetError("Dataset exceeds the 10,000-row parsing limit")
            rows.append({key: _bounded(value) for key, value in row.items()})
        return rows, list(reader.fieldnames)
    if dataset_format == "JSON":
        try:
            value = json.loads(data)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise DatasetError("JSON dataset is malformed") from error
        if isinstance(value, dict):
            value = value.get("rows")
        if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
            raise DatasetError("JSON datasets must be an array of objects or an object with a rows array")
        if len(value) > MAX_ROWS:
            raise DatasetError("Dataset exceeds the 10,000-row parsing limit")
        columns = list(dict.fromkeys(key for row in value for key in row))
        if not columns or len(columns) > MAX_COLUMNS:
            raise DatasetError("Dataset must contain 1 to 200 columns")
        return [{key: _bounded(row.get(key)) for key in columns} for row in value], columns
    if dataset_format == "XLSX":
        validate_xlsx_archive(data)
        try:
            from openpyxl import load_workbook
            workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        except ImportError as error:
            raise DatasetError("XLSX support is unavailable on this server") from error
        except Exception as error:
            raise DatasetError("XLSX workbook is malformed or encrypted") from error
        sheet = workbook.active
        iterator = sheet.iter_rows(values_only=True)
        try:
            headers = [str(value or "").strip() for value in next(iterator)]
        except StopIteration as error:
            raise DatasetError("Workbook is empty") from error
        if not headers or any(not header for header in headers) or len(headers) > MAX_COLUMNS or len(set(headers)) != len(headers):
            raise DatasetError("Workbook requires 1 to 200 unique, non-empty column headers")
        rows = []
        for index, values in enumerate(iterator):
            if index >= MAX_ROWS:
                raise DatasetError("Dataset exceeds the 10,000-row parsing limit")
            rows.append({header: _bounded(value) for header, value in zip(headers, values)})
        workbook.close()
        return rows, headers
    if dataset_format == "PARQUET":
        try:
            import duckdb
        except ImportError as error:
            raise DatasetError("Parquet support is unavailable on this server") from error
        try:
            with tempfile.NamedTemporaryFile(suffix=".parquet") as temporary:
                temporary.write(data); temporary.flush()
                connection = duckdb.connect(":memory:")
                try:
                    relation = connection.read_parquet(temporary.name)
                    columns = list(relation.columns)
                    if not columns or len(columns) > MAX_COLUMNS:
                        raise DatasetError("Parquet dataset must contain 1 to 200 columns")
                    values = relation.limit(MAX_ROWS + 1).fetchall()
                finally:
                    connection.close()
        except DatasetError:
            raise
        except Exception as error:
            raise DatasetError("Parquet dataset is malformed") from error
        if len(values) > MAX_ROWS:
            raise DatasetError("Parquet dataset exceeds the 10,000-row parsing limit")
        return [{column: _bounded(value) for column, value in zip(columns, row)} for row in values], columns
    raise DatasetError("Unsupported dataset format")


def _bounded(value: Any) -> Any:
    if isinstance(value, (bytes, bytearray, dict, list, tuple, set)):
        value = json.dumps(value, default=str)
    if isinstance(value, (datetime,)):
        value = value.isoformat()
    if isinstance(value, str) and len(value) > MAX_CELL_CHARS:
        raise DatasetError("A cell exceeds the 20,000-character limit")
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def profile_dataset(rows: list[dict[str, Any]], columns: list[str]) -> tuple[list[dict], dict[str, Any]]:
    typed_rows = [{column: _coerce(row.get(column)) for column in columns} for row in rows]
    info = []
    distributions: dict[str, Any] = {}
    numeric_columns: list[str] = []
    for column in columns:
        values = [row.get(column) for row in typed_rows]
        present = [value for value in values if value not in (None, "")]
        inferred = _infer_type(present)
        entry: dict[str, Any] = {"name": column, "type": inferred, "missing": len(values) - len(present), "unique": len({str(value) for value in present})}
        if inferred in {"integer", "number"} and present:
            numeric = [float(value) for value in present]
            numeric_columns.append(column)
            quartiles = statistics.quantiles(numeric, n=4, method="inclusive") if len(numeric) > 1 else [numeric[0]] * 3
            low, high = quartiles[0] - 1.5 * (quartiles[2] - quartiles[0]), quartiles[2] + 1.5 * (quartiles[2] - quartiles[0])
            entry.update({"min": min(numeric), "max": max(numeric), "mean": statistics.fmean(numeric), "outliers": sum(value < low or value > high for value in numeric)})
            distributions[column] = _histogram(numeric)
        else:
            counts: dict[str, int] = {}
            for value in present[:5000]: counts[str(value)] = counts.get(str(value), 0) + 1
            distributions[column] = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:10]
        info.append(entry)
    duplicates = len(typed_rows) - len({json.dumps(row, sort_keys=True, default=str) for row in typed_rows})
    correlations = []
    for left_index, left in enumerate(numeric_columns):
        for right in numeric_columns[left_index + 1:]:
            pairs = [(float(row[left]), float(row[right])) for row in typed_rows if row.get(left) not in (None, "") and row.get(right) not in (None, "")]
            correlations.append({"left": left, "right": right, "value": _correlation(pairs)})
    profile = {
        "rows": len(rows), "columns": len(columns), "missing_values": sum(item["missing"] for item in info),
        "duplicate_rows": duplicates, "preview": typed_rows[:50], "distributions": distributions,
        "correlations": correlations,
    }
    return info, profile


def _coerce(value: Any) -> Any:
    if not isinstance(value, str): return value
    stripped = value.strip()
    if not stripped: return None
    if stripped.lower() in {"true", "false"}: return stripped.lower() == "true"
    try: return int(stripped)
    except ValueError: pass
    try: return float(stripped)
    except ValueError: return stripped


def _infer_type(values: list[Any]) -> str:
    if not values: return "unknown"
    if all(isinstance(value, bool) for value in values): return "boolean"
    if all(isinstance(value, int) and not isinstance(value, bool) for value in values): return "integer"
    if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values): return "number"
    return "string"


def _histogram(values: list[float]) -> list[dict[str, float | int]]:
    low, high = min(values), max(values)
    if low == high: return [{"start": low, "end": high, "count": len(values)}]
    width = (high - low) / min(10, max(1, int(math.sqrt(len(values)))))
    bins = [{"start": low + index * width, "end": low + (index + 1) * width, "count": 0} for index in range(math.ceil((high - low) / width))]
    for value in values: bins[min(len(bins) - 1, int((value - low) / width))]["count"] += 1
    return bins


def _correlation(pairs: list[tuple[float, float]]) -> float | None:
    if len(pairs) < 2: return None
    left, right = zip(*pairs)
    left_mean, right_mean = statistics.fmean(left), statistics.fmean(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in pairs)
    denominator = math.sqrt(sum((x - left_mean) ** 2 for x in left) * sum((y - right_mean) ** 2 for y in right))
    return round(numerator / denominator, 6) if denominator else None


def transform_rows(rows: list[dict[str, Any]], operation: str, column: str | None = None, value: Any = None, target_type: str | None = None, new_name: str | None = None) -> list[dict[str, Any]]:
    result = [dict(row) for row in rows]
    if operation == "drop_duplicates":
        seen: set[str] = set()
        return [row for row in result if not (json.dumps(row, sort_keys=True, default=str) in seen or seen.add(json.dumps(row, sort_keys=True, default=str)))]
    if operation == "drop_missing":
        return [row for row in result if (row.get(column) not in (None, "") if column else all(item not in (None, "") for item in row.values()))]
    if column is None or any(column not in row for row in result):
        raise DatasetError("The selected column does not exist")
    if operation == "fill_missing":
        for row in result:
            if row.get(column) in (None, ""): row[column] = value
    elif operation == "convert_type":
        converters = {"string": str, "integer": int, "number": float, "boolean": lambda item: str(item).lower() in {"true", "1", "yes"}}
        if target_type not in converters: raise DatasetError("A supported target type is required")
        try:
            for row in result:
                if row.get(column) not in (None, ""): row[column] = converters[target_type](row[column])
        except (TypeError, ValueError) as error: raise DatasetError("A value cannot be converted to the requested type") from error
    elif operation == "normalize":
        values = [float(row[column]) for row in result if row.get(column) not in (None, "")]
        low, high = min(values), max(values)
        for row in result:
            if row.get(column) not in (None, ""): row[column] = 0 if high == low else (float(row[column]) - low) / (high - low)
    elif operation == "standardize_dates":
        try:
            for row in result:
                if row.get(column) not in (None, ""): row[column] = datetime.fromisoformat(str(row[column]).replace("Z", "+00:00")).date().isoformat()
        except ValueError as error: raise DatasetError("Dates must use an ISO-compatible format") from error
    elif operation == "rename_column":
        if not new_name or any(new_name in row for row in result): raise DatasetError("A unique new column name is required")
        for row in result: row[new_name] = row.pop(column)
    else:
        raise DatasetError("Unsupported transformation")
    return result


def rows_to_csv(rows: list[dict[str, Any]]) -> bytes:
    if not rows: return b""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    for row in rows:
        writer.writerow({key: _spreadsheet_safe(value) for key, value in row.items()})
    return output.getvalue().encode("utf-8")


def _spreadsheet_safe(value: Any) -> Any:
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value
