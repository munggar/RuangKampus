import pytest

from ruangkampus.services.assistant_intent import detect_assistant_intent


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Carikan ruangan untuk 20 orang dengan proyektor", "ROOM_SEARCH"),
        ("Cari ruang rapat di FTII", "ROOM_SEARCH"),
        ("Bro, ada ruang kosong nggak?", "ROOM_AVAILABILITY"),
        ("Ada ruangan tersedia besok?", "ROOM_AVAILABILITY"),
        ("Cari ruang besok pukul 10:00 sampai 12:00", "ROOM_AVAILABILITY"),
        ("Tolong cari slot alternatif", "ALTERNATIVE_SLOTS"),
        ("Ada jam lain untuk ruang rapat?", "ALTERNATIVE_SLOTS"),
        ("Apa fasilitas ruang RK-FTII-101?", "ROOM_DETAIL"),
        ("Berapa kapasitas ruangan itu?", "ROOM_DETAIL"),
        ("Bagaimana cara reservasi?", "RESERVATION_HELP"),
        ("Gmn cara booking ruangan?", "RESERVATION_HELP"),
        ("Lihat reservasi saya", "MY_RESERVATIONS"),
        ("Cek riwayat reservasi", "MY_RESERVATIONS"),
        ("Cek status reservasi saya", "RESERVATION_STATUS"),
        ("Apakah reservasi saya sudah disetujui?", "RESERVATION_STATUS"),
        ("Batalkan reservasi saya", "RESERVATION_CANCEL_PREVIEW"),
        ("Saya ingin buat reservasi ruangan", "RESERVATION_CREATE_PREVIEW"),
        ("Apa saja yang bisa kamu bantu?", "FAQ"),
        ("Halo kak", "SMALLTALK"),
        ("Woy", "SMALLTALK"),
        ("Woi bro", "SMALLTALK"),
        ("Wkwk kamu robot ya?", "SMALLTALK"),
        ("Makasih ya", "SMALLTALK"),
        ("Berapa harga laptop?", "OUT_OF_SCOPE"),
    ],
)
def test_detects_supported_intent(message, expected):
    result = detect_assistant_intent(message)
    assert result.intent == expected


def test_negated_cancel_request_does_not_create_cancel_intent():
    result = detect_assistant_intent("Jangan batalkan reservasi saya")
    assert result.intent != "RESERVATION_CANCEL_PREVIEW"


def test_alternative_slots_requires_an_explicit_time_window():
    result = detect_assistant_intent("Cari waktu lain untuk ruangan", has_complete_availability_window=False)
    assert result.intent == "ALTERNATIVE_SLOTS"
    assert result.requires_clarification is True
    assert result.clarification_message


def test_availability_requires_date_and_time():
    result = detect_assistant_intent("Ada ruangan kosong di FTII?")
    assert result.intent == "ROOM_AVAILABILITY"
    assert result.requires_clarification is True
    assert result.clarification_message


def test_structured_availability_filters_are_classified():
    result = detect_assistant_intent(
        "Carikan ruangan",
        has_structured_room_filters=True,
        has_complete_availability_window=True,
    )
    assert result.intent == "ROOM_AVAILABILITY"


def test_room_detail_uses_observed_catalog_room_names_and_codes():
    catalog = {
        "rooms": [
            {
                "room_name": "Laboratorium Komputer Dasar",
                "room_code": "RK-FTII-101",
            }
        ]
    }
    result = detect_assistant_intent("Apa fasilitas RK-FTII-101?", catalog)
    assert result.intent == "ROOM_DETAIL"


def test_empty_message_returns_clarification_without_a_numeric_confidence():
    result = detect_assistant_intent("")
    assert result.intent == "OUT_OF_SCOPE"
    assert result.requires_clarification is True
