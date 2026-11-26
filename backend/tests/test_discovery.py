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
        headers=auth_headers("admin.uhamka"),
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
        headers=auth_headers("admin.uhamka"),
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
        headers=auth_headers("admin.uhamka"),
    )
    assert denied.status_code == 403


def test_old_assistant_contract_remains_and_new_structured_fields_are_present(
    client, auth_headers, student, admin, room_payload
):
    room = create_located_room(client, auth_headers, room_payload)
    result = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Carikan ruangan untuk 20 orang di FTII dengan proyektor"},
        headers=auth_headers(),
    )

    assert result.status_code == 200, result.text
    data = result.json()["data"]
    # Legacy response fields remain available to the existing React page.
    assert data["engine"] == "RULE_BASED"
    assert data["intent"] == "ROOM_SEARCH"
    assert data["message"]
    assert data["filters"]["faculty"] == "FTII"
    assert data["rooms"][0]["id"] == room["id"]
    assert isinstance(data["alternative_slots"], list)
    assert isinstance(data["follow_up_questions"], list)
    assert data["reservation_action"] == "NOT_CREATED"

    # Structured response fields are validated by the Pydantic response model.
    assert data["conversation_id"] is None
    assert data["slots"]["faculty"] == "FTII"
    assert data["slots"]["min_capacity"] == 20
    assert data["confidence"] is None
    assert data["requires_clarification"] is True
    assert data["clarification_message"] == data["follow_up_questions"][0]
    assert data["result_type"] == "ROOMS_FOUND"
    assert data["requires_confirmation"] is False
    assert data["data"]["rooms"][0]["id"] == room["id"]


def test_assistant_accepts_reserved_conversation_id_but_does_not_claim_memory(
    client, auth_headers, student
):
    from uuid import uuid4

    requested_id = str(uuid4())
    result = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Carikan ruangan rapat", "conversation_id": requested_id},
        headers=auth_headers(),
    )

    assert result.status_code == 200, result.text
    assert result.json()["data"]["conversation_id"] is None


def test_assistant_student_response_does_not_expose_admin_schedule_details(
    client, auth_headers, student, admin, create_room
):
    from datetime import date, timedelta

    room = create_room()
    booking_date = date.today() + timedelta(days=30)
    created = client.post(
        "/api/v1/admin/schedules",
        json={
            "room_id": room["id"],
            "course_name": "INTERNAL ADMIN-ONLY COURSE NAME",
            "schedule_date": booking_date.isoformat(),
            "start_time": "09:00:00",
            "end_time": "10:00:00",
            "data_source": "PRIVATE_ADMIN_IMPORT_SOURCE",
        },
        headers=auth_headers("admin.uhamka"),
    )
    assert created.status_code == 201, created.text

    result = client.post(
        "/api/v1/assistant/chat",
        json={
            "message": f"Carikan ruang pada {booking_date.isoformat()} 09:00-10:00",
            "date": booking_date.isoformat(),
            "start_time": "09:00",
            "end_time": "10:00",
        },
        headers=auth_headers(),
    )

    assert result.status_code == 200, result.text
    response_text = result.text
    assert "INTERNAL ADMIN-ONLY COURSE NAME" not in response_text
    assert "PRIVATE_ADMIN_IMPORT_SOURCE" not in response_text
    assert "course_name" not in response_text
    assert "data_source" not in response_text
    assert "reservation_id" not in response_text


def test_assistant_requires_student_authentication(client):
    result = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Carikan ruangan rapat"},
    )
    assert result.status_code == 401


def test_assistant_does_not_expose_another_students_reservation_details(
    client, auth_headers, student, admin, create_room
):
    room = create_room()
    booking_date = future_weekday(2)
    other = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Other Student",
            "email": "other.assistant.student@example.com",
            "student_identifier": "2403045098",
            "password": "OtherStrongPass123!",
        },
    )
    assert other.status_code == 201, other.text
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    reservation = client.post(
        "/api/v1/reservations",
        json={
            "room_id": room["id"],
            "purpose": "PRIVATE PURPOSE OF ANOTHER STUDENT",
            "date": booking_date.isoformat(),
            "start_time": "09:00:00",
            "end_time": "10:00:00",
            "participant_count": 5,
            "notes": "PRIVATE RESERVATION NOTES",
        },
        headers=other_headers,
    )
    assert reservation.status_code == 201, reservation.text

    response = client.post(
        "/api/v1/assistant/chat",
        json={
            "message": f"Carikan ruangan untuk 5 orang pada {booking_date.isoformat()} 09:00-10:00",
            "date": booking_date.isoformat(),
            "start_time": "09:00",
            "end_time": "10:00",
            "participant_count": 5,
        },
        headers=auth_headers(),
    )

    assert response.status_code == 200, response.text
    assert reservation.json()["data"]["id"] not in response.text
    assert "PRIVATE PURPOSE OF ANOTHER STUDENT" not in response.text
    assert "PRIVATE RESERVATION NOTES" not in response.text
    assert other.json()["user"]["email"] not in response.text
    assert "applicant" not in response.json()["data"]


def test_structured_slots_serialize_explicit_date_and_time(
    client, auth_headers, student, admin, create_room
):
    room = create_room()
    booking_date = future_weekday(1)
    result = client.post(
        "/api/v1/assistant/chat",
        json={
            "message": "Carikan ruangan",
            "date": booking_date.isoformat(),
            "start_time": "09:00",
            "end_time": "10:00",
        },
        headers=auth_headers(),
    )

    assert result.status_code == 200, result.text
    data = result.json()["data"]
    assert data["slots"]["date"] == booking_date.isoformat()
    assert data["slots"]["start_time"] == "09:00:00"
    assert data["slots"]["end_time"] == "10:00:00"
    assert data["data"]["filters"]["date"] == booking_date.isoformat()
    assert "date" not in data["missing_fields"]
    assert room["id"] in {item["id"] for item in data["rooms"]}



def test_assistant_normalizes_student_slang_before_existing_room_search(
    client, auth_headers, student, admin, room_payload
):
    room = create_located_room(client, auth_headers, room_payload)
    raw_message = "Bro, cariin ruangn di FTII yg kosong besok pukul 10:00 sampai 12:00 dengan proyektor dong"
    result = client.post(
        "/api/v1/assistant/chat",
        json={"message": raw_message},
        headers=auth_headers(),
    )

    assert result.status_code == 200, result.text
    data = result.json()["data"]
    assert data["intent"] == "ROOM_AVAILABILITY"
    assert data["normalization"]["raw_text"] == raw_message
    assert data["normalization"]["normalized_text"] == (
        "bro cari ruangan di ftii yang kosong besok pukul 10:00 sampai 12:00 dengan proyektor dong"
    )
    assert data["normalization"]["parser_text"] == (
        "cari ruangan di ftii yang kosong besok pukul 10:00 sampai 12:00 dengan proyektor"
    )
    assert {"bro", "dong"}.issubset(set(data["normalization"]["filler_tokens"]))
    assert data["slots"]["faculty"] == "FTII"
    assert data["slots"]["facilities"] == ["projector"]
    assert room["id"] in {item["id"] for item in data["rooms"]}


def test_negated_facility_is_not_interpreted_as_a_positive_room_filter(
    client, auth_headers, student, admin, room_payload
):
    create_located_room(client, auth_headers, room_payload)
    result = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Jangan cari ruangan dengan proyektor."},
        headers=auth_headers(),
    )

    assert result.status_code == 200, result.text
    data = result.json()["data"]
    assert data["normalization"]["normalized_tokens"] == [
        "jangan", "cari", "ruangan", "dengan", "proyektor"
    ]
    assert data["slots"]["facilities"] == []
    # Stage 2.2 does not yet implement negative-filter semantics. It must
    # clarify rather than returning the entire room catalogue unfiltered.
    assert data["rooms"] == []
    assert data["requires_clarification"] is True


def test_assistant_uses_only_positive_faculty_from_a_contrast_clause(
    client, auth_headers, student, admin, room_payload
):
    ftii_room = create_located_room(client, auth_headers, room_payload, faculty="FTII")
    fkip_payload = {
        **room_payload,
        "room_name": "Room FKIP 101",
        "room_code": "RK-FKIP-101",
        "faculty": "FKIP",
        "location_description": "Lantai 1, dekat lobby",
    }
    created = client.post(
        "/api/v1/rooms",
        json=fkip_payload,
        headers=auth_headers("admin.uhamka"),
    )
    assert created.status_code == 201, created.text
    fkip_room = created.json()["data"]

    result = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Cari ruangan bukan FTII, tetapi FKIP"},
        headers=auth_headers(),
    )
    assert result.status_code == 200, result.text
    data = result.json()["data"]
    assert data["slots"]["faculty"] == "FKIP"
    room_ids = {item["id"] for item in data["rooms"]}
    assert fkip_room["id"] in room_ids
    assert ftii_room["id"] not in room_ids


def test_ambiguous_positive_faculties_are_not_arbitrarily_selected(
    client, auth_headers, student, admin, room_payload
):
    create_located_room(client, auth_headers, room_payload, faculty="FTII")
    second_payload = {
        **room_payload,
        "room_name": "Room FKIP 101",
        "room_code": "RK-FKIP-201",
        "faculty": "FKIP",
    }
    second = client.post(
        "/api/v1/rooms",
        json=second_payload,
        headers=auth_headers("admin.uhamka"),
    )
    assert second.status_code == 201, second.text

    result = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Cari ruangan FTII atau FKIP"},
        headers=auth_headers(),
    )
    assert result.status_code == 200, result.text
    data = result.json()["data"]
    assert data["slots"]["faculty"] is None
    # Multiple positive faculties are ambiguous. Do not choose either one
    # and do not fall back to an unfiltered room catalogue.
    assert data["rooms"] == []
    assert data["requires_clarification"] is True



def test_empty_or_symbol_only_assistant_message_does_not_return_unfiltered_rooms(
    client, auth_headers, student, admin, room_payload
):
    create_located_room(client, auth_headers, room_payload)
    result = client.post(
        "/api/v1/assistant/chat",
        json={"message": "!!! ???"},
        headers=auth_headers(),
    )

    assert result.status_code == 200, result.text
    data = result.json()["data"]
    assert data["normalization"]["normalized_text"] == ""
    assert data["normalization"]["parser_text"] == ""
    assert data["rooms"] == []
    assert data["result_type"] == "NO_RESULTS"
    assert data["requires_clarification"] is True


def test_assistant_does_not_return_unfiltered_rooms_for_conversational_messages(
    client, auth_headers, student, admin, room_payload
):
    create_located_room(client, auth_headers, room_payload)
    messages = (
        "Bro, ada ruang kosong nggak?",
        "Gmn cara reservasi?",
        "Wkwkwk kamu robot ya?",
        "Halo kak.",
        "Cari ruangan",
        "!!! ???",
    )

    headers = auth_headers()
    for message in messages:
        result = client.post(
            "/api/v1/assistant/chat",
            json={"message": message},
            headers=headers,
        )

        assert result.status_code == 200, (message, result.text)
        data = result.json()["data"]
        assert data["rooms"] == [], message
        assert data["result_type"] == "NO_RESULTS", message
        if message == "Gmn cara reservasi?":
            assert data["intent"] == "RESERVATION_HELP"
            assert data["requires_clarification"] is False
            assert "reservasi" in data["message"].lower()
        elif message in {"Wkwkwk kamu robot ya?", "Halo kak."}:
            assert data["intent"] == "SMALLTALK"
            assert data["requires_clarification"] is False
        else:
            assert data["requires_clarification"] is True, message
            assert data["clarification_message"], message
        assert data["slots"]["search_terms"] == [], message



def test_room_assistant_endpoint_is_student_only(client, auth_headers, admin):
    response = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Cari ruangan untuk rapat"},
        headers=auth_headers("admin.uhamka"),
    )
    assert response.status_code == 403
