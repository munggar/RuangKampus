import hashlib
import io
import re
import shutil
import zipfile
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from openpyxl import load_workbook

from ruangkampus.config import get_settings
from ruangkampus.database import get_db
from ruangkampus.dependencies import require_admin
from ruangkampus.models import Room, RoomImportBatch, RoomUpdateLog, User, utcnow
from ruangkampus.responses import success

router = APIRouter(prefix="/admin/rooms/imports", tags=["Room imports"])
MAX_BYTES = 5 * 1024 * 1024
MAX_EXPANDED_BYTES = 25 * 1024 * 1024
PREVIEW_TTL = timedelta(hours=24)

ROOM_IMPORT_HEADERS = {
    "room_name": {"nomor ruangan", "nama ruangan", "room name", "room_name"},
    "capacity": {"kapasitas", "kapasitas estimasi", "kapasitas (estimasi)", "capacity", "capacity estimate"},
    "facilities": {"fasilitas", "facility", "facilities"},
    "documentation": {"dokumentasi", "foto", "photo", "documentation"},
    "location": {"lokasi gedung", "lokasi", "alamat gedung", "alamat", "building location"},
    "faculty": {"fakultas", "faculty"},
}
ROOM_IMPORT_REQUIRED = ("room_name", "capacity", "facilities")


def _normalise_header(value) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\xa0", " ").strip()).casefold()


def _header_columns(sheet) -> dict[str, int]:
    columns: dict[str, int] = {}
    for index, cell in enumerate(sheet[1], start=1):
        header = _normalise_header(cell.value)
        if not header:
            continue
        for field, aliases in ROOM_IMPORT_HEADERS.items():
            if header in aliases:
                if field in columns:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Kolom {field.replace('_', ' ')} ditemukan lebih dari satu kali",
                    )
                columns[field] = index
                break

    missing = [field for field in ROOM_IMPORT_REQUIRED if field not in columns]
    if missing:
        labels = {
            "room_name": "Nomor Ruangan",
            "capacity": "Kapasitas atau Kapasitas (estimasi)",
            "facilities": "Fasilitas",
        }
        required = ", ".join(labels[field] for field in missing)
        raise HTTPException(
            status_code=422,
            detail=(
                f"Kolom wajib belum ditemukan: {required}. "
                "Urutan kolom bebas; kolom Lokasi Gedung, Fakultas, dan Dokumentasi bersifat opsional."
            ),
        )
    return columns


def _facility_tags(value: str) -> list[str]:
    """Extract explicitly named facilities while preserving the full source description."""
    text = value.casefold()
    patterns = (
        ("air conditioner", r"\b(?:ac|air conditioner|pendingin)\b"),
        ("wifi", r"\bwi[\s-]?fi\b|\binternet\b"),
        ("projector", r"\b(?:projector|proyektor|perangkat proyeksi)\b"),
        ("whiteboard", r"\b(?:whiteboard|papan tulis)\b"),
        ("computer", r"\b(?:komputer|computer|workstation|desktop|pc)\b"),
        ("monitor", r"\bmonitor\b"),
        ("display", r"\b(?:layar|display)\b"),
        ("meja komputer", r"\bmeja komputer\b"),
        ("meja praktikum", r"\bmeja praktikum\b"),
        ("meja gambar", r"\bmeja gambar\b"),
        ("meja rapat", r"\bmeja rapat\b"),
        ("instrumen elektronika", r"\b(?:instrumen|perangkat) elektronika\b"),
        ("kabel", r"\bkabel\b"),
        ("kursi", r"\bkursi\b"),
    )
    return [label for label, pattern in patterns if re.search(pattern, text)]


def _safe_filename(value: str | None) -> str:
    leaf = Path((value or "rooms.xlsx").replace("\\", "/")).name
    return re.sub(r"[^A-Za-z0-9._ -]", "_", leaf).strip(" .")[:255] or "rooms.xlsx"


def _capacity_range(value) -> tuple[int, int, str]:
    text = str(value or "").strip().replace("–", "-").replace("—", "-")
    match = re.search(r"(\d+)\s*(?:-\s*(\d+))?", text)
    if not match:
        raise ValueError("Kapasitas harus berupa angka atau rentang, contoh 20–25")
    minimum = int(match.group(1))
    maximum = int(match.group(2) or minimum)
    if minimum < 1 or maximum < minimum or maximum > 10000:
        raise ValueError("Rentang kapasitas tidak valid")
    return minimum, maximum, f"{minimum}–{maximum}" if maximum != minimum else str(minimum)


def _slug_code(name: str) -> str:
    slug = re.sub(r"[^A-Z0-9]+", "-", name.upper()).strip("-")
    return ("AUTO-" + slug)[:80]


def _room_floor(name: str) -> str | None:
    normalized = name.casefold()
    if re.search(r"\b(lab|laboratorium)\b", normalized):
        return "2"
    first_digit = re.search(r"\d", name)
    return first_digit.group(0) if first_digit else None


def _photo_dir() -> Path:
    path = Path(get_settings().room_media_dir).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _staging_dir(batch_id: UUID) -> Path:
    path = _photo_dir().parent / ".room-import-staging" / str(batch_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _batch_payload(batch: RoomImportBatch) -> dict:
    return {
        "batch_id": str(batch.id), "status": batch.status,
        "source_filename": batch.source_filename, "row_count": batch.row_count,
        "valid_count": batch.valid_count, "invalid_count": batch.invalid_count,
        "row_results": batch.row_results, "preview_rows": batch.parsed_rows,
        "created_at": batch.created_at.isoformat(),
        "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
    }


def _parse_workbook(content: bytes, batch_id: UUID) -> tuple[list[dict], dict[int, tuple[str, bytes]]]:
    if not content or len(content) > MAX_BYTES:
        raise HTTPException(status_code=413 if content else 422, detail="File kosong atau melebihi batas 5 MB")
    if not content.startswith(b"PK\x03\x04"):
        raise HTTPException(status_code=415, detail="File harus berupa workbook .xlsx yang valid")
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            if sum(item.file_size for item in archive.infolist()) > MAX_EXPANDED_BYTES:
                raise HTTPException(status_code=413, detail="Ukuran hasil ekstraksi workbook melebihi batas")
            if any(item.filename.lower().endswith("vba_project.bin") for item in archive.infolist()):
                raise HTTPException(status_code=415, detail="Workbook bermacro tidak didukung")
        workbook = load_workbook(io.BytesIO(content), data_only=True, keep_links=False)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=422, detail="Workbook Excel tidak dapat dibaca") from None

    rows: list[dict] = []
    photos: dict[int, tuple[str, bytes]] = {}
    try:
        sheet = workbook.active
        if sheet is None:
            raise HTTPException(status_code=422, detail="Sheet aktif tidak ditemukan")
        columns = _header_columns(sheet)

        def cell_value(row_number: int, field: str):
            column = columns.get(field)
            return sheet.cell(row_number, column).value if column else None

        for row_number in range(2, sheet.max_row + 1):
            name = str(cell_value(row_number, "room_name") or "").strip()
            capacity_value = cell_value(row_number, "capacity")
            facilities_text = str(cell_value(row_number, "facilities") or "").strip()
            location_value = str(cell_value(row_number, "location") or "").strip()
            faculty_value = str(cell_value(row_number, "faculty") or "").strip()

            if not any((name, capacity_value not in (None, ""), facilities_text, location_value, faculty_value)):
                continue

            errors = []
            if not name:
                errors.append("Nama ruangan wajib diisi")
            try:
                capacity_min, capacity_max, capacity_label = _capacity_range(capacity_value)
            except ValueError as exc:
                errors.append(str(exc))
                capacity_min, capacity_max, capacity_label = 1, 1, ""

            if not facilities_text:
                errors.append("Deskripsi fasilitas kosong")
            if len(location_value) > 500:
                errors.append("Lokasi Gedung maksimal 500 karakter")
            if len(faculty_value) > 160:
                errors.append("Fakultas maksimal 160 karakter")

            code = _slug_code(name) if name else ""
            rows.append({
                "row_number": row_number,
                "room_name": name,
                "room_code": code,
                # The workbook supplies a street address, not a building name.
                # Preserve it as location_description and leave the building label
                # for an admin to complete before activating the room.
                "building": "Belum ditentukan",
                "faculty": faculty_value or None,
                "floor": _room_floor(name),
                "location_description": location_value or None,
                "capacity": capacity_min,
                "capacity_min": capacity_min,
                "capacity_max": capacity_max,
                "capacity_estimate": capacity_label,
                "description": facilities_text,
                "facilities": _facility_tags(facilities_text),
                "operating_hours": {},
                "room_status": "INACTIVE",
                "photo_key": None,
                "errors": errors,
            })

        for image in getattr(sheet, "_images", []):
            row_number = image.anchor._from.row + 1
            try:
                data = image._data()
                if not data or len(data) > 4 * 1024 * 1024:
                    continue
                fmt = (getattr(image, "format", "") or "jpeg").lower()
                ext = "png" if fmt == "png" else "jpg"
                photos[row_number] = (ext, data)
            except Exception:
                continue
    finally:
        workbook.close()

    if not rows:
        raise HTTPException(status_code=422, detail="Tidak ada data ruangan pada workbook")
    if len(rows) > 500:
        raise HTTPException(status_code=413, detail="Maksimal 500 ruangan per impor")
    return rows, photos

@router.post("/preview", status_code=201)
async def preview_room_import(
    file: UploadFile = File(...),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    filename = _safe_filename(file.filename)
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=415, detail="Gunakan file .xlsx; format .xls dan macro tidak didukung")
    content = await file.read(MAX_BYTES + 1)
    batch_id = uuid4()
    rows, photos = _parse_workbook(content, batch_id)
    staging = _staging_dir(batch_id)
    seen_names: dict[str, int] = {}
    seen_codes: dict[str, int] = {}
    for row in rows:
        row_number = row["row_number"]
        if row_number in photos:
            ext, data = photos[row_number]
            key = f"row-{row_number}.{ext}"
            (staging / key).write_bytes(data)
            row["photo_key"] = key

        name_key = row["room_name"].strip().casefold()
        code_key = row["room_code"].strip().casefold()
        previous_name_row = seen_names.get(name_key)
        previous_code_row = seen_codes.get(code_key)
        if previous_name_row is not None:
            row["errors"].append(f"Nama ruangan duplikat dengan baris Excel {previous_name_row}")
        if previous_code_row is not None and previous_code_row != previous_name_row:
            row["errors"].append(f"Kode ruangan duplikat dengan baris Excel {previous_code_row}")
        seen_names.setdefault(name_key, row_number)
        seen_codes.setdefault(code_key, row_number)

        active_match = db.scalar(select(Room.id).where(
            Room.deleted_at.is_(None),
            or_(
                func.lower(Room.room_name) == name_key,
                Room.room_code == row["room_code"],
            ),
        ))
        if active_match:
            row["errors"].append("Ruangan dengan nama atau kode ini masih terdaftar aktif")
            row["import_action"] = "BLOCKED"
            continue

        deleted_match = db.scalar(select(Room.id).where(
            Room.deleted_at.is_not(None),
            or_(
                func.lower(Room.room_name) == name_key,
                Room.room_code == row["room_code"],
            ),
        ))
        row["import_action"] = "RESTORE" if deleted_match else "CREATE"
    results = [{
        "row_number": row["row_number"],
        "room_name": row["room_name"],
        "status": "INVALID" if row["errors"] else "VALID",
        "errors": row["errors"],
        "has_photo": bool(row["photo_key"]),
        "capacity_estimate": row["capacity_estimate"],
        "floor": row["floor"],
        "faculty": row["faculty"],
        "location_description": row["location_description"],
        "facilities": row["facilities"],
        "import_action": row.get("import_action", "CREATE"),
    } for row in rows]
    valid = sum(1 for item in results if item["status"] == "VALID")
    batch = RoomImportBatch(
        id=batch_id, created_by_id=admin.id, status="PREVIEWED",
        source_filename=filename, file_sha256=hashlib.sha256(content).hexdigest(),
        row_count=len(rows), valid_count=valid, invalid_count=len(rows) - valid,
        parsed_rows=rows, row_results=results,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return success(_batch_payload(batch), "Pratinjau impor ruangan berhasil dibuat")


@router.post("/commit")
def commit_room_import(
    payload: dict,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        batch_id = UUID(str(payload.get("batch_id", "")))
    except ValueError:
        raise HTTPException(status_code=422, detail="batch_id tidak valid") from None
    batch = db.scalar(select(RoomImportBatch).where(
        RoomImportBatch.id == batch_id, RoomImportBatch.created_by_id == admin.id
    ).with_for_update())
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch impor tidak ditemukan")
    if batch.status != "PREVIEWED":
        raise HTTPException(status_code=409, detail="Batch ini sudah diproses")
    created = batch.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=utcnow().tzinfo)
    if created + PREVIEW_TTL <= utcnow():
        batch.status = "FAILED"
        db.commit()
        raise HTTPException(status_code=409, detail="Pratinjau kedaluwarsa, silakan unggah ulang")
    valid_rows = [row for row in batch.parsed_rows if not row["errors"]]
    if not valid_rows:
        raise HTTPException(status_code=422, detail="Tidak ada baris valid untuk diimpor")

    created_rooms = []
    try:
        for row in valid_rows:
            duplicate = db.scalar(select(Room.id).where(
                Room.deleted_at.is_(None),
                (func.lower(Room.room_name) == row["room_name"].lower()) | (Room.room_code == row["room_code"]),
            ))
            if duplicate:
                raise HTTPException(status_code=409, detail=f"Ruangan {row['room_name']} sudah terdaftar; tidak ada data yang disimpan")
            photo_url = None
            photo_key = row.get("photo_key")
            if photo_key:
                staged = _staging_dir(batch.id) / Path(photo_key).name
                if staged.exists():
                    final_name = f"{uuid4().hex}{staged.suffix.lower()}"
                    destination = _photo_dir() / final_name
                    shutil.move(str(staged), str(destination))
                    photo_url = f"/media/rooms/{final_name}"
            room = Room(
                room_name=row["room_name"], room_code=row["room_code"],
                building=row["building"], faculty=row["faculty"], floor=row["floor"],
                location_description=row["location_description"], capacity=row["capacity"],
                capacity_estimate=row["capacity_estimate"], description=row["description"],
                facilities=row["facilities"], operating_hours=row["operating_hours"],
                room_status=row["room_status"], photo_url=photo_url,
            )
            db.add(room)
            db.flush()
            db.add(RoomUpdateLog(
                admin_id=admin.id, entity_type="ROOM", entity_id=room.id,
                action="IMPORT_CREATE", previous_value=None,
                new_value={"room_name": room.room_name, "room_code": room.room_code,
                           "capacity": room.capacity, "capacity_estimate": room.capacity_estimate,
                           "photo_url": room.photo_url, "import_batch_id": str(batch.id)},
            ))
            created_rooms.append(room)
        batch.status = "COMPLETED"
        batch.completed_at = utcnow()
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Terjadi duplikasi data; tidak ada perubahan yang disimpan") from None
    finally:
        shutil.rmtree(_photo_dir().parent / ".room-import-staging" / str(batch.id), ignore_errors=True)
    return success({
        "batch_id": str(batch.id), "status": batch.status,
        "inserted": len(created_rooms), "row_count": batch.row_count,
        "invalid_count": batch.invalid_count,
    }, "Data ruangan berhasil diimpor")


@router.get("")
def list_room_imports(
    limit: int = 20,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="limit harus antara 1 dan 100")
    batches = db.scalars(select(RoomImportBatch).where(
        RoomImportBatch.created_by_id == admin.id
    ).order_by(RoomImportBatch.created_at.desc()).limit(limit)).all()
    return success([_batch_payload(batch) for batch in batches], "Riwayat impor ruangan berhasil diambil")
