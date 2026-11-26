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
