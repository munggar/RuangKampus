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


def test_alternative_slot_search_excludes_the_exact_requested_time(
    client, auth_headers, student, admin, create_room
):
    room = create_room()
    booking_date = future_weekday(1)
    result = client.post(
        "/api/v1/rooms/alternative-slots",
        json={
            "date": booking_date.isoformat(),
            "duration_minutes": 60,
            "participant_count": 4,
            "room_id": room["id"],
            "preferred_start_time": "10:00:00",
            "search_days": 0,
            "slot_step_minutes": 30,
            "limit": 10,
        },
        headers=auth_headers(),
    )

    assert result.status_code == 200, result.text
    items = result.json()["data"]["items"]
    assert items
    assert all(
        not (item["date"] == booking_date.isoformat() and item["start_time"] == "10:00:00")
        for item in items
    )


def test_alternative_slot_search_preserves_free_text_constraints(
    client, auth_headers, student, admin, create_room
):
    create_room()
    booking_date = future_weekday(1)
    result = client.post(
        "/api/v1/rooms/alternative-slots",
        json={
            "date": booking_date.isoformat(),
            "duration_minutes": 60,
            "participant_count": 4,
            "search_terms": ["criterion-that-does-not-exist"],
            "preferred_start_time": "10:00:00",
            "search_days": 0,
            "slot_step_minutes": 30,
            "limit": 10,
        },
        headers=auth_headers(),
    )

    assert result.status_code == 200, result.text
    assert result.json()["data"]["items"] == []


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
    assert "jam" in data["follow_up_questions"][0].lower()


def test_room_assistant_shows_partial_room_candidates_before_asking_for_schedule(
    client, auth_headers, student, admin, room_payload
):
    room = create_located_room(client, auth_headers, room_payload)
    result = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Carikan ruangan kosong di FTII dengan proyektor"},
        headers=auth_headers(),
    )

    assert result.status_code == 200, result.text
    data = result.json()["data"]
    assert data["assistant_name"] == "RUKKA AI"
    assert data["intent"] == "ROOM_AVAILABILITY"
    assert data["result_type"] == "ROOMS_FOUND"
    assert room["id"] in {item["id"] for item in data["rooms"]}
    assert data["requires_clarification"] is True
    assert len(data["follow_up_questions"]) == 1
    assert "belum bisa dipastikan" in data["message"].lower()
    assert "2403045007" not in result.text


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
    assert data["conversation_id"]
    assert data["confidence"] is not None
    assert data["confidence_basis"] == "RULE_HEURISTIC"
    assert data["slots"]["faculty"] == "FTII"
    assert data["slots"]["min_capacity"] == 20
    assert 0 <= data["confidence"] <= 1
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
    assert result.json()["data"]["conversation_id"] == requested_id
    assert result.json()["data"]["confidence_basis"] == "RULE_HEURISTIC"


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


def test_assistant_parses_indonesian_month_date_and_en_dash_time_range(
    client, auth_headers, student, admin, room_payload
):
    create_located_room(client, auth_headers, room_payload)
    raw_message = (
        "Cek ruangan yang benar-benar kosong tanggal 27 November 2026, "
        "pukul 10.00–12.00, untuk 20 orang di FTII. Wajib ada proyektor."
    )
    result = client.post(
        "/api/v1/assistant/chat",
        json={"message": raw_message},
        headers=auth_headers(),
    )

    assert result.status_code == 200, result.text
    data = result.json()["data"]
    assert data["intent"] == "ROOM_AVAILABILITY"
    assert data["slots"]["date"] == "2026-11-27"
    assert data["slots"]["start_time"] == "10:00:00"
    assert data["slots"]["end_time"] == "12:00:00"
    assert data["slots"]["min_capacity"] == 20
    assert data["slots"]["participant_count"] == 20
    assert data["slots"]["faculty"] == "FTII"
    assert data["slots"]["facilities"] == ["projector"]
    assert data["slots"]["search_terms"] == []
    assert data["requires_clarification"] is False
    assert not {"date", "start_time", "end_time"}.intersection(data["missing_fields"])


def test_assistant_recognizes_casual_lu_siapa_question(
    client, auth_headers, student
):
    result = client.post(
        "/api/v1/assistant/chat",
        json={"message": "lau sokap der"},
        headers=auth_headers(),
    )

    assert result.status_code == 200, result.text
    data = result.json()["data"]
    assert data["intent"] == "SMALLTALK"
    assert data["normalization"]["normalized_text"] == "kamu siapa der"
    assert data["assistant_name"] == "RUKKA AI"


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


def test_assistant_conversation_carries_forward_owned_search_slots(
    client, auth_headers, student, admin, room_payload
):
    room = create_located_room(client, auth_headers, room_payload, faculty="FTII")
    first = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Carikan ruangan untuk 20 orang di FTII"},
        headers=auth_headers(),
    )
    assert first.status_code == 200, first.text
    first_data = first.json()["data"]
    conversation_id = first_data["conversation_id"]
    assert conversation_id
    assert room["id"] in {item["id"] for item in first_data["rooms"]}

    follow_up = client.post(
        "/api/v1/assistant/chat",
        json={
            "message": "yang ada proyektor",
            "conversation_id": conversation_id,
        },
        headers=auth_headers(),
    )
    assert follow_up.status_code == 200, follow_up.text
    data = follow_up.json()["data"]
    assert data["conversation_id"] == conversation_id
    assert data["slots"]["faculty"] == "FTII"
    assert data["slots"]["min_capacity"] == 20
    assert data["slots"]["participant_count"] == 20
    assert data["slots"]["facilities"] == ["projector"]
    assert room["id"] in {item["id"] for item in data["rooms"]}


def test_assistant_conversation_isolated_between_students(
    client, auth_headers, student, admin
):
    first = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Cari ruangan di FTII"},
        headers=auth_headers(),
    )
    assert first.status_code == 200, first.text
    conversation_id = first.json()["data"]["conversation_id"]

    other = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Other Conversation Student",
            "email": "other.conversation.student@example.com",
            "student_identifier": "2403045201",
            "password": "OtherStrongPass123!",
        },
    )
    assert other.status_code == 201, other.text
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    denied = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Carikan ruangan", "conversation_id": conversation_id},
        headers=other_headers,
    )
    assert denied.status_code == 404


def test_assistant_returns_only_authenticated_students_reservations(
    client, auth_headers, student, admin, create_room
):
    room = create_room()
    booking_date = future_weekday(2)
    own = client.post(
        "/api/v1/reservations",
        json={
            "room_id": room["id"],
            "purpose": "My private student meeting",
            "date": booking_date.isoformat(),
            "start_time": "09:00:00",
            "end_time": "10:00:00",
            "participant_count": 5,
            "notes": "My own private notes",
        },
        headers=auth_headers(),
    )
    assert own.status_code == 201, own.text

    other = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Reservation Owner",
            "email": "reservation.owner@example.com",
            "student_identifier": "2403045202",
            "password": "OtherStrongPass123!",
        },
    )
    assert other.status_code == 201, other.text
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    other_reservation = client.post(
        "/api/v1/reservations",
        json={
            "room_id": room["id"],
            "purpose": "Other student's private meeting",
            "date": booking_date.isoformat(),
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "participant_count": 3,
            "notes": "Other private notes",
        },
        headers=other_headers,
    )
    assert other_reservation.status_code == 201, other_reservation.text

    response = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Lihat reservasi saya"},
        headers=auth_headers(),
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["intent"] == "MY_RESERVATIONS"
    assert data["result_type"] == "RESERVATIONS_FOUND"
    assert any(item["id"] == own.json()["data"]["id"] for item in data["data"]["reservations"])
    assert other_reservation.json()["data"]["id"] not in response.text
    assert "Other student's private meeting" not in response.text
    assert "Other private notes" not in response.text


def test_assistant_returns_grounded_room_details_from_catalog(
    client, auth_headers, student, admin, room_payload
):
    room = create_located_room(client, auth_headers, room_payload)
    response = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Apa fasilitas ruang RK-FTII-101?"},
        headers=auth_headers(),
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["intent"] == "ROOM_DETAIL"
    assert data["result_type"] == "ROOM_DETAILS"
    assert data["rooms"][0]["id"] == room["id"]
    assert room["room_name"] in data["message"]


def test_general_question_uses_conversation_generation_not_room_intent_fallback(
    client, auth_headers, student, admin, monkeypatch
):
    from ruangkampus.config import Settings
    from ruangkampus.routers import discovery

    settings = Settings(
        assistant_ai_enabled=True,
        assistant_ai_endpoint_url="https://ai.example.test/v1/chat/completions",
        assistant_ai_model="test-model",
    )
    generated = []

    def fail_intent_fallback(*args, **kwargs):
        raise AssertionError("general conversation must not use the room-intent classifier fallback")

    def fake_general_response(**kwargs):
        generated.append(kwargs)
        return ("Ada beberapa pilihan yang bisa kamu pertimbangkan. Mulailah dari prioritas dan waktumu.", True)

    monkeypatch.setattr(discovery, "get_settings", lambda: settings)
    monkeypatch.setattr(discovery, "interpret_with_ai_fallback", fail_intent_fallback)
    monkeypatch.setattr(discovery, "_maybe_generate_ai_message", fake_general_response)
    response = client.post(
        "/api/v1/assistant/chat",
        json={"message": "what should I do with my day?"},
        headers=auth_headers(),
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert len(generated) == 1
    assert generated[0]["intent"] == "OUT_OF_SCOPE"
    assert data["intent"] == "OUT_OF_SCOPE"
    assert data["engine"] == "HYBRID"
    assert data["message"].startswith("Ada beberapa pilihan")
    assert data["requires_clarification"] is False
    assert data["follow_up_questions"] == []
    assert data["rooms"] == []
    assert "penyedia AI" in data["privacy"]


def test_ai_fallback_is_not_called_when_rule_engine_recognizes_smalltalk(
    client, auth_headers, student, admin, monkeypatch
):
    from ruangkampus.routers import discovery

    def fail_interpretation(*args, **kwargs):
        raise AssertionError("AI fallback must not run for rule-recognized smalltalk")

    monkeypatch.setattr(discovery, "interpret_with_ai_fallback", fail_interpretation)
    response = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Halo kak"},
        headers=auth_headers(),
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["intent"] == "SMALLTALK"
    assert data["engine"] == "RULE_BASED"
    assert data["confidence_basis"] == "RULE_HEURISTIC"


def test_student_can_submit_explicit_rukka_feedback_and_negative_feedback_requires_reason(
    client, auth_headers, student
):
    feedback = client.post(
        "/api/v1/assistant/feedback",
        json={
            "intent": "SMALLTALK",
            "rating": "NOT_HELPFUL",
            "reason_code": "TOO_FORMAL",
        },
        headers=auth_headers(),
    )
    assert feedback.status_code == 200, feedback.text
    assert feedback.json()["data"]["recorded"] is True

    invalid = client.post(
        "/api/v1/assistant/feedback",
        json={"intent": "SMALLTALK", "rating": "NOT_HELPFUL"},
        headers=auth_headers(),
    )
    assert invalid.status_code == 422



def test_rukka_greeting_is_not_misused_as_a_room_search_keyword(
    client, auth_headers, student
):
    result = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Woy RUKKA, lu bisa bantu gua nyari ruangan kaga?"},
        headers=auth_headers(),
    )

    assert result.status_code == 200, result.text
    data = result.json()["data"]
    assert data["intent"] == "ROOM_SEARCH"
    assert data["rooms"] == []
    assert data["slots"]["search_terms"] == []
    assert data["requires_clarification"] is True
    assert "belum ada ruangan yang cocok" not in data["message"].lower()


def test_room_assistant_parses_forty_org_and_heat_avoidance_as_ac(
    client, auth_headers, student, admin, room_payload
):
    payload = {
        **room_payload,
        "room_name": "Meeting Room AC 101",
        "room_code": "RK-AC-101",
        "capacity": 55,
        "facilities": ["AC", "Projector"],
    }
    room = create_located_room(client, auth_headers, payload)
    result = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Min, cariin ruang yg muat 40 org dong, jgn yg panas ya."},
        headers=auth_headers(),
    )

    assert result.status_code == 200, result.text
    data = result.json()["data"]
    assert data["intent"] == "ROOM_SEARCH"
    assert data["slots"]["min_capacity"] == 40
    assert data["slots"]["facilities"] == ["air conditioner"]
    assert data["slots"]["search_terms"] == []
    assert room["id"] in {item["id"] for item in data["rooms"]}
    assert data["requires_clarification"] is True
    assert "tanggal" in data["follow_up_questions"][0].lower()


def test_room_assistant_only_asks_for_time_when_date_was_already_parsed(
    client, auth_headers, student, admin
):
    result = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Gw mw pinjem rgn buat rapat besok, msh ad yg ksong g?"},
        headers=auth_headers(),
    )

    assert result.status_code == 200, result.text
    data = result.json()["data"]
    assert data["intent"] == "ROOM_AVAILABILITY"
    assert data["slots"]["date"]
    assert data["missing_fields"] == ["start_time", "end_time"]
    assert "tanggalnya udah gue catat" in data["message"].lower()
    assert "jam mulai dan selesai" in data["follow_up_questions"][0].lower()


def test_room_assistant_understands_availability_follow_up_from_same_conversation(
    client, auth_headers, student
):
    first = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Carikan ruangan untuk diskusi."},
        headers=auth_headers(),
    )
    assert first.status_code == 200, first.text
    conversation_id = first.json()["data"]["conversation_id"]

    second = client.post(
        "/api/v1/assistant/chat",
        json={
            "message": "Masih ada yang kosong?",
            "conversation_id": conversation_id,
        },
        headers=auth_headers(),
    )

    assert second.status_code == 200, second.text
    data = second.json()["data"]
    assert data["intent"] == "ROOM_AVAILABILITY"
    assert data["missing_fields"] == ["date", "start_time", "end_time"]
    assert "tanggal dan jam" in data["follow_up_questions"][0].lower()
