import io

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from PIL import Image


def make_room_workbook(with_photo: bool = True) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["nomor ruangan", "Kapasitas (estimasi)", "Fasilitas", "Dokumentasi"])
    sheet.append(["Laboratorium Komputer Dasar", "20–25", "Workstation, monitor, meja komputer", None])
    sheet.append(["Ruang 301", "40–45 mahasiswa", "AC dan akses Wi-Fi; meja/kursi mahasiswa", None])
    if with_photo:
        photo = io.BytesIO()
        Image.new("RGB", (12, 12), "blue").save(photo, format="PNG")
        photo.seek(0)
        sheet.add_image(XLImage(photo), "D2")
    output = io.BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def make_six_column_inventory_workbook() -> bytes:
    from openpyxl import Workbook
    from openpyxl.drawing.image import Image as XLImage
    from PIL import Image

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Table 1"
    sheet.append([
        "Nomor Ruangan", "Kapasitas", "Fasilitas", "Dokumentasi",
        "Lokasi Gedung", "Fakultas",
    ])
    sheet.append([
        "Laboratorium Komputer Dasar", "20–25",
        "Workstation, monitor, meja komputer, kursi; beberapa foto menampilkan proyektor/layar.",
        None,
        "Jl. Tanah Merdeka No.6, Rambutan, Jakarta Timur 13830",
        "Fakultas Teknologi Industri dan Informatika (FTII)",
    ])
    sheet.append([
        "Ruang 301", "40–45 mahasiswa",
        "AC dan akses Wi-Fi; meja/kursi mahasiswa; papan tulis serta layar dan perangkat proyeksi.",
        None,
        "Jl. Tanah Merdeka No.6, Rambutan, Jakarta Timur 13830",
        "Fakultas Teknologi Industri dan Informatika (FTII)",
    ])

    for row in (2, 3):
        photo = io.BytesIO()
        Image.new("RGB", (12, 12), "blue").save(photo, format="JPEG")
        photo.seek(0)
        sheet.add_image(XLImage(photo), f"D{row}")

    output = io.BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def upload(client, headers, content=None):
    return client.post(
        "/api/v1/admin/rooms/imports/preview",
        headers=headers,
        files={"file": ("rooms.xlsx", content or make_room_workbook(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )


def test_room_import_preview_requires_admin(client, auth_headers, student):
    response = upload(client, auth_headers(), make_room_workbook())
    assert response.status_code == 403


def test_room_import_preview_maps_capacity_range_and_embedded_photo(client, auth_headers, admin):
    response = upload(client, auth_headers("admin.uhamka"), make_room_workbook())
    assert response.status_code == 201, response.text
    payload = response.json()["data"]
    assert payload["row_count"] == 2
    assert payload["valid_count"] == 2
    assert payload["preview_rows"][0]["capacity"] == 20
    assert payload["preview_rows"][0]["capacity_estimate"] == "20–25"
    assert payload["preview_rows"][0]["floor"] == "2"  # All labs are on floor 2.
    assert payload["preview_rows"][1]["floor"] == "3"  # First digit in "Ruang 301" is the floor.
    assert payload["row_results"][0]["has_photo"] is True


def test_room_import_commit_persists_photo_for_student_directory(client, auth_headers, admin, student):
    headers = auth_headers("admin.uhamka")
    preview = upload(client, headers, make_room_workbook())
    assert preview.status_code == 201, preview.text
    batch_id = preview.json()["data"]["batch_id"]
    committed = client.post("/api/v1/admin/rooms/imports/commit", headers=headers, json={"batch_id": batch_id})
    assert committed.status_code == 200, committed.text
    assert committed.json()["data"]["inserted"] == 2
    rooms = client.get("/api/v1/rooms?search=Laboratorium%20Komputer%20Dasar", headers=headers)
    assert rooms.status_code == 200
    room = rooms.json()["data"][0]
    assert room["capacity"] == 20
    assert room["capacity_estimate"] == "20–25"
    assert room["photo_url"].startswith("/media/rooms/")
    photo = client.get(room["photo_url"])
    assert photo.status_code == 200

    activated = client.patch(
        f"/api/v1/rooms/{room['id']}",
        headers=headers,
        json={"room_status": "ACTIVE"},
    )
    assert activated.status_code == 200, activated.text
    student_rooms = client.get(
        "/api/v1/rooms?search=Laboratorium%20Komputer%20Dasar",
        headers=auth_headers(),
    )
    assert student_rooms.status_code == 200, student_rooms.text
    student_room = student_rooms.json()["data"][0]
    assert student_room["photo_url"] == room["photo_url"]
    student_photo = client.get(student_room["photo_url"])
    assert student_photo.status_code == 200
    assert student_photo.headers["content-type"].startswith("image/")

    history = client.get("/api/v1/admin/rooms/imports", headers=headers)
    assert history.status_code == 200
    assert history.json()["data"][0]["status"] == "COMPLETED"


def test_room_import_rejects_non_xlsx(client, auth_headers, admin):
    response = client.post(
        "/api/v1/admin/rooms/imports/preview",
        headers=auth_headers("admin.uhamka"),
        files={"file": ("rooms.xls", b"not an xlsx", "application/vnd.ms-excel")},
    )
    assert response.status_code == 415



def test_room_import_accepts_six_column_inventory_workbook_and_maps_optional_fields(
    client, auth_headers, admin
):
    headers = auth_headers("admin.uhamka")
    response = upload(client, headers, make_six_column_inventory_workbook())
    assert response.status_code == 201, response.text

    batch = response.json()["data"]
    assert batch["row_count"] == 2
    assert batch["valid_count"] == 2
    assert batch["invalid_count"] == 0

    lab, classroom = batch["preview_rows"]
    assert lab["room_name"] == "Laboratorium Komputer Dasar"
    assert lab["capacity"] == 20
    assert lab["capacity_estimate"] == "20–25"
    assert lab["faculty"] == "Fakultas Teknologi Industri dan Informatika (FTII)"
    assert lab["location_description"].startswith("Jl. Tanah Merdeka")
    assert {"computer", "monitor", "projector", "display"}.issubset(set(lab["facilities"]))
    assert lab["floor"] == "2"
    assert lab["room_status"] == "INACTIVE"

    assert classroom["capacity"] == 40
    assert classroom["capacity_estimate"] == "40–45"
    assert {"air conditioner", "wifi", "whiteboard", "projector"}.issubset(
        set(classroom["facilities"])
    )

    assert batch["row_results"][0]["faculty"] == lab["faculty"]
    assert batch["row_results"][0]["location_description"] == lab["location_description"]
    assert batch["row_results"][0]["has_photo"] is True
    assert batch["row_results"][1]["has_photo"] is True

    committed = client.post(
        "/api/v1/admin/rooms/imports/commit",
        headers=headers,
        json={"batch_id": batch["batch_id"]},
    )
    assert committed.status_code == 200, committed.text
    assert committed.json()["data"]["inserted"] == 2

    rooms = client.get(
        "/api/v1/rooms?search=Laboratorium%20Komputer%20Dasar",
        headers=headers,
    )
    assert rooms.status_code == 200, rooms.text
    room = rooms.json()["data"][0]
    assert room["faculty"] == lab["faculty"]
    assert room["location_description"] == lab["location_description"]
    assert room["building"] == "Belum ditentukan"
    assert room["capacity"] == 20
    assert room["room_status"] == "INACTIVE"
    assert room["photo_url"].startswith("/media/rooms/")



def test_room_import_restores_soft_deleted_room_instead_of_violating_unique_room_code(
    client, auth_headers, admin, db_session
):
    from datetime import date, time
    from sqlalchemy import select
    from ruangkampus.models import Reservation, Room

    headers = auth_headers("admin.uhamka")
    historical = Room(
        room_name="Laboratorium Komputer Dasar",
        room_code="AUTO-LABORATORIUM-KOMPUTER-DASAR",
        building="Gedung lama",
        faculty=None,
        floor="1",
        capacity=18,
        capacity_estimate="18–20",
        description="Data sebelum dihapus",
        facilities=["computer"],
        operating_hours={},
        room_status="INACTIVE",
        deleted_at=admin.created_at,
    )
    db_session.add(historical)
    db_session.flush()
    booking = Reservation(
        user_id=admin.id,
        room_id=historical.id,
        purpose="Riwayat sebelum impor ulang",
        reservation_date=date(2026, 11, 20),
        start_time=time(9, 0),
        end_time=time(10, 0),
        participant_count=4,
        status="CANCELLED",
    )
    db_session.add(booking)
    db_session.commit()
    historical_id = historical.id

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Nomor Ruangan", "Kapasitas", "Fasilitas"])
    sheet.append(["Laboratorium Komputer Dasar", "20–25", "Workstation, monitor, meja komputer"])
    output = io.BytesIO()
    workbook.save(output)
    workbook.close()

    preview = upload(client, headers, output.getvalue())
    assert preview.status_code == 201, preview.text
    batch = preview.json()["data"]
    assert batch["valid_count"] == 1
    assert batch["row_results"][0]["import_action"] == "RESTORE"

    committed = client.post(
        "/api/v1/admin/rooms/imports/commit",
        headers=headers,
        json={"batch_id": batch["batch_id"]},
    )
    assert committed.status_code == 200, committed.text
    assert committed.json()["data"]["inserted"] == 0
    assert committed.json()["data"]["restored"] == 1
    assert committed.json()["data"]["imported"] == 1

    restored = db_session.scalar(select(Room).where(Room.id == historical_id))
    assert restored is not None
    assert restored.deleted_at is None
    assert restored.room_name == "Laboratorium Komputer Dasar"
    assert restored.capacity == 20
    assert restored.capacity_estimate == "20–25"
    assert restored.room_status == "INACTIVE"
    assert db_session.scalar(select(Reservation).where(Reservation.room_id == historical_id)) is not None


def test_room_import_preview_marks_duplicate_rows_inside_workbook_invalid(
    client, auth_headers, admin
):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Nomor Ruangan", "Kapasitas", "Fasilitas"])
    sheet.append(["Ruang 701", "20", "AC"])
    sheet.append(["Ruang 701  ", "25", "Projector"])
    output = io.BytesIO()
    workbook.save(output)
    workbook.close()

    response = upload(client, auth_headers("admin.uhamka"), output.getvalue())
    assert response.status_code == 201, response.text
    batch = response.json()["data"]
    assert batch["valid_count"] == 1
    assert batch["invalid_count"] == 1
    assert batch["row_results"][1]["status"] == "INVALID"
    assert any("duplikat dengan baris Excel 2" in error for error in batch["row_results"][1]["errors"])
