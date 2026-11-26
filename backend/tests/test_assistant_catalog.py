from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError

from ruangkampus.models import Room
from ruangkampus.services.assistant_catalog import (
    assess_assistant_data_quality,
    build_assistant_data_catalog,
    find_facility_matches,
)


VALID_HOURS = {
    day: [{"start": "07:00:00", "end": "21:00:00"}]
    for day in (
        "monday", "tuesday", "wednesday", "thursday",
        "friday", "saturday", "sunday",
    )
}


def add_room(db_session, **overrides):
    payload = {
        "room_name": "Room Catalog Test",
        "room_code": f"CAT-{db_session.query(Room).count() + 1}",
        "faculty": "FTII",
        "building": "Building A",
        "floor": "2",
        "location_description": "Lantai 2, dekat lobby",
        "capacity": 30,
        "facilities": ["Projector", "Whiteboard"],
        "operating_hours": VALID_HOURS,
        "room_status": "ACTIVE",
    }
    payload.update(overrides)
    room = Room(**payload)
    db_session.add(room)
    db_session.flush()
    return room


def test_faculty_catalog_uses_distinct_values_from_active_room_records(db_session):
    add_room(db_session, faculty="FTII")
    add_room(db_session, faculty=" FTII ")
    add_room(db_session, faculty="Belum ditentukan")
    add_room(db_session, faculty=None)
    add_room(db_session, faculty="FKIP", room_status="INACTIVE")
    add_room(db_session, faculty="FKIP", deleted_at=datetime.now())

    catalog = build_assistant_data_catalog(db_session)

    assert [entry["value"] for entry in catalog["faculties"]] == ["FTII"]
    assert catalog["faculties"][0]["room_count"] == 2
    assert set(catalog["faculties"][0]["source_values"]) == {"FTII", " FTII "}
    assert "FKIP" not in [entry["value"] for entry in catalog["faculties"]]
    assert catalog["verification_status"] == "VERIFIED"


def test_facility_catalog_preserves_source_values_and_maps_only_known_aliases(db_session):
    projector_room = add_room(db_session, facilities=["Projector", "CCTV"])
    add_room(db_session, facilities=["Proyektor", "CCTV"])
    add_room(db_session, facilities=["Belum ditentukan", ""])

    catalog = build_assistant_data_catalog(db_session)
    projector = next(item for item in catalog["facilities"] if item["canonical_name"] == "projector")
    cctv = next(item for item in catalog["facilities"] if item["display_name"] == "CCTV")

    assert set(projector["source_values"]) == {"Projector", "Proyektor"}
    assert projector["mapping_status"] == "KNOWN_ALIAS_GROUP"
    assert cctv["canonical_name"] is None
    assert cctv["mapping_status"] == "UNMAPPED_SOURCE_VALUE"
    assert find_facility_matches(catalog, "proyektor")[0]["canonical_name"] == "projector"
    assert find_facility_matches(catalog, "CCTV")[0]["canonical_name"] is None
    assert projector_room.facilities == ["Projector", "CCTV"]


def test_unknown_facility_is_searchable_but_never_canonicalized(db_session):
    add_room(db_session, facilities=["CCTV"])
    catalog = build_assistant_data_catalog(db_session)

    matches = find_facility_matches(catalog, "CCTV")

    assert len(matches) == 1
    assert matches[0]["canonical_name"] is None
    assert matches[0]["source_values"] == ["CCTV"]
    assert find_facility_matches(catalog, "projector") == []


def test_placeholder_building_faculty_and_location_are_not_catalogued_as_valid(db_session):
    add_room(
        db_session,
        faculty="Belum ditentukan",
        building="Belum ditentukan",
        location_description="Belum ditentukan",
    )

    catalog = build_assistant_data_catalog(db_session)

    assert catalog["faculties"] == []
    assert catalog["buildings"] == []
    quality = catalog["data_quality"]
    assert quality["fields"]["faculty"]["placeholder_rooms"] == 1
    assert quality["fields"]["building"]["placeholder_rooms"] == 1
    assert quality["room_quality_counts"]["INCOMPLETE"] == 1


def test_data_quality_assessment_distinguishes_valid_incomplete_and_inconsistent_rooms(db_session):
    add_room(db_session)
    add_room(
        db_session,
        room_code="CAT-INCOMPLETE",
        faculty=None,
        building="Belum ditentukan",
        location_description=None,
        facilities=[],
        operating_hours={},
    )
    add_room(
        db_session,
        room_code="CAT-INCONSISTENT",
        facilities=["Projector", "projector"],
        operating_hours={"monday": [{"start": "10:00", "end": "09:00"}]},
    )

    report = assess_assistant_data_quality(db_session)

    assert report["verification_status"] == "VERIFIED"
    assert report["active_room_count"] == 3
    assert report["room_quality_counts"] == {
        "VALID": 1,
        "INCOMPLETE": 1,
        "INCONSISTENT": 1,
        "UNVERIFIABLE": 0,
    }
    assert report["fields"]["operating_hours"] == {
        "valid": 1,
        "missing": 1,
        "inconsistent": 1,
    }
    inconsistent = next(
        item for item in report["room_assessments"]
        if item["room_name"] == "Room Catalog Test"
        and item["status"] == "INCONSISTENT"
    )
    assert "DUPLICATE_FACILITY_LABELS" in inconsistent["issues"]
    assert "INVALID_OPERATING_WINDOW_RANGE" in inconsistent["issues"]


def test_data_quality_reports_database_unavailable_without_exposing_exception_details():
    class BrokenSession:
        def scalars(self, statement):
            raise SQLAlchemyError("private database connection detail")

    report = assess_assistant_data_quality(BrokenSession())

    assert report["verification_status"] == "UNABLE_TO_VERIFY"
    assert report["reason_code"] == "DATABASE_QUERY_FAILED"
    assert report["active_room_count"] is None
    assert "private database connection detail" not in str(report)
