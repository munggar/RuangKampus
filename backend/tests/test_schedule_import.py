from datetime import date, timedelta


def next_weekday(weekday: int) -> date:
    today = date.today()
    days = (weekday - today.weekday()) % 7
    return today + timedelta(days=days if days >= 2 else days + 7)


def csv_file(rows: str, filename: str = "lecture-schedule.csv"):
    return {"file": (filename, rows.encode("utf-8"), "text/csv")}


def test_admin_can_preview_and_commit_csv_schedule_import(client, auth_headers, admin, create_room, db_session):
    from ruangkampus.models import LectureSchedule

    room = create_room()
    headers = auth_headers("admin@example.com")
    content = (
        "room_code,course_name,schedule_date,start_time,end_time\n"
        f"{room['room_code']},Software Engineering,{next_weekday(4).isoformat()},10:00,11:30\n"
    )
    preview = client.post("/api/v1/admin/schedules/imports/preview", files=csv_file(content), headers=headers)
    assert preview.status_code == 201, preview.text
    batch = preview.json()["data"]
    assert batch["valid_count"] == 1
    assert batch["invalid_count"] == 0
    assert db_session.query(LectureSchedule).count() == 0

    commit = client.post(
        "/api/v1/admin/schedules/imports/commit",
        json={"batch_id": batch["batch_id"]},
        headers=headers,
    )
    assert commit.status_code == 200, commit.text
    assert commit.json()["data"]["status"] == "COMPLETED"
    assert commit.json()["data"]["inserted"] == 1
    assert db_session.query(LectureSchedule).count() == 1

    replay = client.post(
        "/api/v1/admin/schedules/imports/commit",
        json={"batch_id": batch["batch_id"]},
        headers=headers,
    )
    assert replay.status_code == 409
    assert db_session.query(LectureSchedule).count() == 1


def test_schedule_import_preview_reports_invalid_and_overlapping_rows(client, auth_headers, admin, create_room):
    room = create_room()
    headers = auth_headers("admin@example.com")
    content = (
        "room_code,course_name,day_of_week,start_time,end_time\n"
        f"{room['room_code']},Class A,Monday,09:00,11:00\n"
        f"{room['room_code']},Class B,Monday,10:00,12:00\n"
        "UNKNOWN,Class C,Tuesday,09:00,10:00\n"
    )
    response = client.post("/api/v1/admin/schedules/imports/preview", files=csv_file(content), headers=headers)
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["row_count"] == 3
    assert data["valid_count"] == 1
    assert data["invalid_count"] == 2
    assert data["row_results"][1]["status"] == "INVALID"
    assert data["row_results"][2]["status"] == "INVALID"


def test_student_cannot_import_schedules(client, auth_headers, student):
    response = client.post(
        "/api/v1/admin/schedules/imports/preview",
        files=csv_file("room_code,course_name,schedule_date,start_time,end_time\nR-1,Class,2027-01-01,09:00,10:00\n"),
        headers=auth_headers(),
    )
    assert response.status_code == 403


def test_schedule_import_rejects_unsupported_and_malformed_files(client, auth_headers, admin):
    headers = auth_headers("admin@example.com")
    unsupported = client.post(
        "/api/v1/admin/schedules/imports/preview",
        files=csv_file("not important", filename="macro.xlsm"),
        headers=headers,
    )
    assert unsupported.status_code == 415

    malformed = client.post(
        "/api/v1/admin/schedules/imports/preview",
        files=csv_file("course_name,start_time,end_time\nClass,09:00,10:00\n"),
        headers=headers,
    )
    assert malformed.status_code == 422


def test_schedule_import_commit_rechecks_changes_since_preview(client, auth_headers, student, admin, create_room):
    room = create_room()
    headers = auth_headers("admin@example.com")
    booking_date = next_weekday(5)
    content = (
        "room_code,course_name,schedule_date,start_time,end_time\n"
        f"{room['room_code']},Imported Class,{booking_date.isoformat()},14:00,15:00\n"
    )
    preview = client.post("/api/v1/admin/schedules/imports/preview", files=csv_file(content), headers=headers)
    assert preview.status_code == 201
    batch_id = preview.json()["data"]["batch_id"]

    reservation = client.post(
        "/api/v1/reservations",
        json={
            "room_id": room["id"], "purpose": "Study session", "date": booking_date.isoformat(),
            "start_time": "14:00:00", "end_time": "15:00:00", "participant_count": 5,
        },
        headers=auth_headers(),
    )
    assert reservation.status_code == 201

    commit = client.post("/api/v1/admin/schedules/imports/commit", json={"batch_id": batch_id}, headers=headers)
    assert commit.status_code == 409
    assert commit.json()["meta"]["inserted"] == 0


def test_admin_can_preview_xlsx_schedule_import(client, auth_headers, admin, create_room):
    from io import BytesIO
    from openpyxl import Workbook

    room = create_room()
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["room_code", "course_name", "day_of_week", "start_time", "end_time"])
    sheet.append([room["room_code"], "Database Systems", "Thursday", "13:00", "14:30"])
    buffer = BytesIO()
    workbook.save(buffer)
    file = {
        "file": (
            "weekly-schedule.xlsx",
            buffer.getvalue(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }
    response = client.post("/api/v1/admin/schedules/imports/preview", files=file, headers=auth_headers("admin@example.com"))
    assert response.status_code == 201, response.text
    assert response.json()["data"]["valid_count"] == 1
