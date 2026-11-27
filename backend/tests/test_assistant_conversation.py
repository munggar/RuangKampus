from datetime import date, datetime, time, timedelta, timezone
from uuid import uuid4

from ruangkampus.models import AssistantConversation
from ruangkampus.services.assistant_conversation import (
    is_new_room_search_request,
    load_or_create_conversation,
    merge_room_slots,
    save_conversation_state,
)


def test_conversation_state_persists_only_structured_slots(db_session, student):
    conversation = load_or_create_conversation(
        db_session, user_id=student.id, requested_id=uuid4()
    )
    slots = {
        "faculty": "FTII",
        "building": "Building A",
        "min_capacity": 20,
        "facilities": ["projector"],
        "date": date(2026, 12, 1),
        "start_time": time(9, 0),
        "end_time": time(10, 0),
        "participant_count": 20,
        "search_terms": ["rapat"],
        "raw_text": "this must never be persisted",
    }
    save_conversation_state(db_session, conversation, intent="ROOM_SEARCH", slots=slots)
    db_session.commit()
    db_session.refresh(conversation)

    assert conversation.state["slots"]["faculty"] == "FTII"
    assert conversation.state["slots"]["date"] == "2026-12-01"
    assert conversation.state["slots"]["start_time"] == "09:00:00"
    assert "raw_text" not in conversation.state
    assert "this must never be persisted" not in str(conversation.state)
    assert conversation.last_intent == "ROOM_SEARCH"


def test_follow_up_merges_previous_slots_and_new_criteria_wins():
    previous = {
        "version": 1,
        "slots": {
            "faculty": "FTII",
            "building": "Building A",
            "min_capacity": 20,
            "facilities": ["projector"],
            "date": "2026-12-01",
            "start_time": "09:00:00",
            "end_time": "10:00:00",
            "participant_count": 20,
            "search_terms": ["rapat"],
        },
    }
    current = {
        "faculty": None,
        "building": "Building B",
        "min_capacity": None,
        "facilities": ["wifi"],
        "date": None,
        "start_time": None,
        "end_time": None,
        "participant_count": 1,
        "search_terms": [],
    }
    merged = merge_room_slots(current, previous, message="di gedung B pakai wifi")
    assert merged["faculty"] == "FTII"
    assert merged["building"] == "Building B"
    assert merged["min_capacity"] == 20
    assert merged["facilities"] == ["wifi"]
    assert merged["date"] == date(2026, 12, 1)
    assert merged["start_time"] == time(9, 0)
    assert merged["participant_count"] == 20
    assert merged["search_terms"] == ["rapat"]


def test_negation_does_not_readd_previous_faculty_building_or_facilities():
    previous = {
        "slots": {
            "faculty": "FTII",
            "building": "Building A",
            "facilities": ["projector"],
            "date": None,
            "start_time": None,
            "end_time": None,
            "participant_count": 1,
            "min_capacity": None,
            "search_terms": ["rapat"],
        }
    }
    current = {
        "faculty": None, "building": None, "min_capacity": None,
        "facilities": [], "date": None, "start_time": None, "end_time": None,
        "participant_count": 1, "search_terms": [],
    }
    merged = merge_room_slots(current, previous, message="tanpa proyektor, bukan FTII")
    assert merged["faculty"] is None
    assert merged["building"] is None
    assert merged["facilities"] == []
    assert merged["search_terms"] == ["rapat"]


def test_reset_phrase_does_not_carry_previous_slots():
    previous = {"slots": {"faculty": "FTII", "search_terms": ["rapat"]}}
    current = {"faculty": None, "search_terms": []}
    merged = merge_room_slots(current, previous, message="mulai dari awal, cari ruang untuk kelas")
    assert merged == current


def test_expired_conversation_rotates_identifier(db_session, student):
    old = AssistantConversation(
        user_id=student.id,
        state={"version": 1, "slots": {"faculty": "FTII"}},
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    db_session.add(old)
    db_session.commit()
    old_id = old.id

    fresh = load_or_create_conversation(
        db_session, user_id=student.id, requested_id=old_id
    )
    assert fresh.id != old_id
    assert fresh.state == {"version": 1, "slots": {}}



def test_new_search_phrase_is_distinguished_from_incremental_filter_reply():
    assert is_new_room_search_request("aku mau mencari ruang buat rapat organisasi minggu depan")
    assert not is_new_room_search_request("pesertanya sekitar 18 sampai 25 orang")
    assert not is_new_room_search_request("kalau bisa hari Rabu setelah kelas")


def test_changed_date_does_not_inherit_previous_days_time_window():
    previous = {
        "slots": {
            "date": "2026-11-30",
            "start_time": "10:00:00",
            "end_time": "12:00:00",
            "min_capacity": 20,
            "participant_count": 20,
        }
    }
    current = {
        "faculty": None,
        "building": None,
        "min_capacity": None,
        "facilities": [],
        "date": date(2026, 12, 2),
        "start_time": None,
        "end_time": None,
        "participant_count": 1,
        "search_terms": [],
    }

    merged = merge_room_slots(current, previous, message="hari Rabu setelah kelas")

    assert merged["date"] == date(2026, 12, 2)
    assert merged["start_time"] is None
    assert merged["end_time"] is None
    assert merged["min_capacity"] == 20
    assert merged["participant_count"] == 20
