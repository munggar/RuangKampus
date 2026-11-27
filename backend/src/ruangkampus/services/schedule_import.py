import csv
import hashlib
import io
import re
import zipfile
from datetime import date, datetime, time
from pathlib import PurePosixPath
from typing import Any

from fastapi import HTTPException
from openpyxl import load_workbook
from openpyxl.utils.datetime import from_excel

MAX_IMPORT_BYTES = 5 * 1024 * 1024
MAX_IMPORT_ROWS = 5000
MAX_XLSX_UNCOMPRESSED_BYTES = 25 * 1024 * 1024
ALLOWED_EXTENSIONS = {".csv", ".xlsx"}
ALLOWED_MIME_TYPES = {
    "text/csv", "application/csv", "text/plain", "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/octet-stream",
}
REQUIRED_COLUMNS = {"course_name", "start_time", "end_time"}


def safe_source_filename(filename: str | None) -> str:
    raw = (filename or "schedule-import").replace("\\", "/")
    leaf = PurePosixPath(raw).name
    leaf = re.sub(r"[^A-Za-z0-9._ -]", "_", leaf).strip(" .")
    return (leaf or "schedule-import")[:255]


def _normalise_header(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[\s-]+", "_", text)
    return re.sub(r"[^a-z0-9_]", "", text)


def _nonempty_rows(rows: list[list[Any]]) -> list[dict[str, Any]]:
    if not rows:
        raise HTTPException(status_code=422, detail="The import file is empty")
    headers = [_normalise_header(value) for value in rows[0]]
    if len(headers) != len(set(headers)):
        raise HTTPException(status_code=422, detail="The import file contains duplicate column headers")
    missing = REQUIRED_COLUMNS - set(headers)
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing required columns: {', '.join(sorted(missing))}")
    if not ({"room_code", "room_id"} & set(headers)):
        raise HTTPException(status_code=422, detail="Provide either room_code or room_id column")
    if not ({"schedule_date", "day_of_week"} & set(headers)):
        raise HTTPException(status_code=422, detail="Provide schedule_date or day_of_week column")

    parsed = []
    for row_number, values in enumerate(rows[1:], start=2):
        if not any(value is not None and str(value).strip() for value in values):
            continue
        record = {header: values[index] if index < len(values) else None for index, header in enumerate(headers)}
        record["_row_number"] = row_number
        parsed.append(record)
        if len(parsed) > MAX_IMPORT_ROWS:
            raise HTTPException(status_code=413, detail=f"Import files are limited to {MAX_IMPORT_ROWS} non-empty rows")
    return parsed


def parse_schedule_file(filename: str | None, content_type: str | None, content: bytes):
    safe_name = safe_source_filename(filename)
    suffix = PurePosixPath(safe_name).suffix.lower()
    mime = (content_type or "application/octet-stream").split(";", 1)[0].strip().lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Only CSV and XLSX files are supported; XLS and macro-enabled files are rejected")
    if mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported upload content type")
    if not content:
        raise HTTPException(status_code=422, detail="The import file is empty")
    if len(content) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="Import file exceeds the 5 MB limit")

    digest = hashlib.sha256(content).hexdigest()
    if suffix == ".csv":
        if content.startswith(b"PK\x03\x04") or b"\x00" in content:
            raise HTTPException(status_code=415, detail="The uploaded file does not appear to be a valid UTF-8 CSV")
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(status_code=422, detail="CSV must use UTF-8 or UTF-8 with BOM encoding") from None
        try:
            dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;") if text.strip() else csv.excel
            rows = list(csv.reader(io.StringIO(text), dialect))
        except csv.Error:
            rows = list(csv.reader(io.StringIO(text)))
        return safe_name, digest, _nonempty_rows(rows)

    if not content.startswith(b"PK\x03\x04"):
        raise HTTPException(status_code=415, detail="The uploaded XLSX file signature is invalid")
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            total_uncompressed = sum(item.file_size for item in archive.infolist())
            if total_uncompressed > MAX_XLSX_UNCOMPRESSED_BYTES:
                raise HTTPException(status_code=413, detail="XLSX expands beyond the permitted uncompressed size")
            if any(item.filename.lower().endswith("vba_project.bin") for item in archive.infolist()):
                raise HTTPException(status_code=415, detail="Macro-enabled workbooks are not supported")
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True, keep_links=False)
        try:
            worksheet = workbook.active
            if worksheet is None:
                raise HTTPException(status_code=422, detail="The workbook has no active worksheet")
            rows = [list(row) for row in worksheet.iter_rows(values_only=True)]
        finally:
            workbook.close()
    except HTTPException:
        raise
    except (zipfile.BadZipFile, OSError, ValueError, KeyError):
        raise HTTPException(status_code=422, detail="The uploaded XLSX workbook could not be read") from None
    return safe_name, digest, _nonempty_rows(rows)


def parse_date_value(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value or "").strip())
    except ValueError:
        raise ValueError("schedule_date must use ISO format YYYY-MM-DD") from None


def parse_time_value(value: Any) -> time:
    if isinstance(value, datetime):
        return value.time().replace(tzinfo=None)
    if isinstance(value, time):
        return value.replace(tzinfo=None)
    if isinstance(value, (int, float)):
        if not 0 <= float(value) < 1:
            raise ValueError("Excel time values must be between 00:00 and 24:00")
        converted = from_excel(value)
        if isinstance(converted, datetime):
            return converted.time().replace(tzinfo=None)
        if isinstance(converted, time):
            return converted
    text = str(value or "").strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    raise ValueError("Time must use HH:MM or HH:MM:SS format")


def parse_weekday(value: Any) -> int:
    if isinstance(value, int) and 0 <= value <= 6:
        return value
    if isinstance(value, float) and value.is_integer() and 0 <= int(value) <= 6:
        return int(value)
    days = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6,
    }
    text = str(value or "").strip().lower()
    if text.isdigit() and 0 <= int(text) <= 6:
        return int(text)
    if text in days:
        return days[text]
    raise ValueError("day_of_week must be Monday-Sunday or an integer from 0 (Monday) to 6 (Sunday)")
