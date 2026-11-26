import hashlib
import io
import re
import shutil
import zipfile
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, select
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
        headers = [str(cell.value or "").strip().lower() for cell in sheet[1]]
        expected = ["nomor ruangan", "kapasitas (estimasi)", "fasilitas"]
        if headers[:3] != expected:
            raise HTTPException(status_code=422, detail="Kolom wajib harus: nomor ruangan, Kapasitas (estimasi), Fasilitas")
        for row_number in range(2, sheet.max_row + 1):
            name = str(sheet.cell(row_number, 1).value or "").strip()
            capacity_value = sheet.cell(row_number, 2).value
            facilities_text = str(sheet.cell(row_number, 3).value or "").strip()
            if not name and not capacity_value and not facilities_text:
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
            code = _slug_code(name) if name else ""
            rows.append({
                "row_number": row_number, "room_name": name, "room_code": code,
                "building": "Belum ditentukan", "faculty": None, "floor": None,
                "location_description": None, "capacity": capacity_min,
                "capacity_min": capacity_min, "capacity_max": capacity_max,
                "capacity_estimate": capacity_label, "description": facilities_text,
                "facilities": [part.strip() for part in re.split(r"[;,]", facilities_text) if part.strip()],
                "operating_hours": {}, "room_status": "INACTIVE", "photo_key": None,
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
    for row in rows:
        row_number = row["row_number"]
        if row_number in photos:
            ext, data = photos[row_number]
            key = f"row-{row_number}.{ext}"
            (staging / key).write_bytes(data)
            row["photo_key"] = key
        existing = db.scalar(select(Room.id).where(
            Room.deleted_at.is_(None),
            (func.lower(Room.room_name) == row["room_name"].lower()) | (Room.room_code == row["room_code"]),
        ))
        if existing:
            row["errors"].append("Ruangan dengan nama atau kode otomatis ini sudah terdaftar")
    results = [{
        "row_number": row["row_number"],
        "room_name": row["room_name"],
        "status": "INVALID" if row["errors"] else "VALID",
        "errors": row["errors"],
        "has_photo": bool(row["photo_key"]),
        "capacity_estimate": row["capacity_estimate"],
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
