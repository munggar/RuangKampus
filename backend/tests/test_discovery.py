from datetime import date, timedelta


def future_weekday(weekday: int) -> date:
    today = date.today()
    delta = (weekday - today.weekday()) % 7
    return today + timedelta(days=delta if delta >= 2 else delta + 7)


def create_located_room(client, auth_headers, room_payload, faculty="FTII"):
    payload = {
        **room_payload,
        "room_code": "RK-FTII-101",
        "faculty": faculty,
        "location_description": "Lantai 2, dekat lobby utama",
    }
    response = client.post(
        "/api/v1/rooms",
        json=payload,
        headers=auth_headers("admin@example.com"),
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_room_location_metadata_and_faculty_filter(client, auth_headers, admin, room_payload):
    room = create_located_room(client, auth_headers, room_payload)
    assert room["faculty"] == "FTII"
    assert room["location_description"] == "Lantai 2, dekat lobby utama"

    result = client.get("/api/v1/rooms?faculty=FTII&building=Building%20A&facilities=Projector")
    assert result.status_code == 200, result.text
    assert result.json()["meta"]["total"] == 1
    assert result.json()["data"][0]["id"] == room["id"]


def test_time_aware_room_search_excludes_pending_reservation(
    client, auth_headers, student, admin, create_room
):
    room = create_room()
    booking_date = future_weekday(0)
    created = client.post(
        "/api/v1/reservations",
        json={
            "room_id": room["id"],
            "purpose": "Busy time test",
            "date": booking_date.isoformat(),
            "start_time": "09:00:00",
            "end_time": "10:00:00",
            "participant_count": 5,
        },
        headers=auth_headers(),
    )
    assert created.status_code == 201, created.text

    result = client.get(
        f"/api/v1/rooms?date={booking_date.isoformat()}&startTime=09:30&endTime=10:30&participantCount=5"
    )
    assert result.status_code == 200, result.text
    assert result.json()["meta"]["total"] == 0


def test_alternative_slot_endpoint_returns_only_available_slots(
    client, auth_headers, student, admin, create_room
):
    room = create_room()
    booking_date = future_weekday(1)
    schedule = client.post(
        "/api/v1/admin/schedules",
        json={
            "room_id": room["id"],
            "course_name": "Occupied lecture",
            "schedule_date": booking_date.isoformat(),
            "start_time": "09:00:00",
            "end_time": "10:00:00",
        },
        headers=auth_headers("admin@example.com"),
    )
    assert schedule.status_code == 201, schedule.text

    result = client.post(
        "/api/v1/rooms/alternative-slots",
        json={
            "date": booking_date.isoformat(),
            "duration_minutes": 60,
            "participant_count": 4,
            "room_id": room["id"],
            "preferred_start_time": "09:00:00",
            "search_days": 0,
            "slot_step_minutes": 30,
            "limit": 10,
        },
        headers=auth_headers(),
    )
    assert result.status_code == 200, result.text
    items = result.json()["data"]["items"]
    assert items
    assert all(item["room"]["id"] == room["id"] for item in items)
    assert all(
        item["end_time"] <= "09:00:00" or item["start_time"] >= "10:00:00"
        for item in items
    )


def test_student_room_assistant_uses_grounded_room_records(
    client, auth_headers, student, admin, room_payload
):
    room = create_located_room(client, auth_headers, room_payload)
    result = client.post(
        "/api/v1/assistant/chat",
        json={
            "message": "Carikan ruangan untuk 20 orang di FTII dengan proyektor",
            "faculty": "FTII",
            "min_capacity": 20,
            "facilities": ["Projector"],
        },
        headers=auth_headers(),
    )
    assert result.status_code == 200, result.text
    data = result.json()["data"]
    assert data["engine"] == "RULE_BASED"
    assert data["reservation_action"] == "NOT_CREATED"
    assert any(item["id"] == room["id"] for item in data["rooms"])
    assert "ketersediaan" in data["follow_up_questions"][0].lower()


def test_room_assistant_is_student_only(client, auth_headers, student, admin):
    denied = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Carikan ruangan rapat"},
        headers=auth_headers("admin@example.com"),
    )
    assert denied.status_code == 403
