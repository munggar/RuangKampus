from __future__ import annotations

import json
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import select

from ruangkampus.config import Settings
from ruangkampus.models import AssistantConversation
from ruangkampus.services.assistant_intent import detect_assistant_intent
from ruangkampus.services.assistant_response import compose_intent_response
from ruangkampus.services.indonesian_normalizer import normalize_indonesian_message
from ruangkampus.services.availability import campus_today


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def configured_settings() -> Settings:
    return Settings(
        assistant_ai_enabled=True,
        assistant_ai_endpoint_url="https://ai.example.test/v1/chat/completions",
        assistant_ai_model="general-reasoning-test-model",
        assistant_ai_api_key="test-only-secret",
        assistant_ai_timeout_seconds=2,
    )


GENERAL_REASONING_PROMPTS = [
    (
        "Kalau semua mahasiswa membutuhkan ruang belajar, tetapi tidak semua ruang belajar "
        "cocok untuk semua mahasiswa, menurut kamu sistem peminjaman ruang kampus yang ideal "
        "harus bekerja seperti apa? Jelaskan alasanmu."
    ),
    (
        "Ada 3 kelompok mahasiswa. Kelompok A membutuhkan ruangan untuk 15 orang, kelompok B "
        "untuk 25 orang, dan kelompok C untuk 40 orang. Hanya tersedia dua ruangan dengan "
        "kapasitas masing-masing 30 dan 50 orang. Bagaimana kamu mengatur pemakaiannya agar "
        "semua kelompok tetap bisa belajar?"
    ),
    (
        "Menurutmu, apakah ruangan dengan fasilitas paling lengkap selalu menjadi pilihan "
        "terbaik? Berikan contoh kondisi ketika ruangan sederhana justru lebih cocok."
    ),
    (
        "Aku ketua organisasi mahasiswa. Besok ada rapat mendadak, tapi anggota kami punya "
        "jadwal kuliah yang berbeda-beda. Ada yang hanya bisa pagi, ada yang siang, dan ada "
        "yang sore. Bagaimana cara terbaik menentukan jadwal rapat tanpa merugikan sebagian "
        "besar anggota?"
    ),
    (
        "Bayangkan kampus memiliki 100 ruangan, tetapi setiap hari masih banyak mahasiswa "
        "kesulitan mendapatkan tempat belajar. Menurutmu, apa kemungkinan penyebabnya? "
        "Jangan langsung menyimpulkan bahwa jumlah ruangan kurang."
    ),
    (
        "Ada mahasiswa yang selalu memesan ruangan tetapi sering tidak datang. Menurutmu, "
        "bagaimana kampus sebaiknya menangani masalah ini tanpa membuat aturan yang terlalu "
        "merugikan mahasiswa lain?"
    ),
    (
        "Rancang sebuah fitur AI yang belum ada di aplikasi peminjaman ruangan kampus pada "
        "umumnya. Fitur tersebut harus benar-benar menyelesaikan masalah mahasiswa, bukan "
        "sekadar terlihat canggih."
    ),
    (
        "Kalau kamu diberi kesempatan mengubah sistem penggunaan fasilitas kampus dari nol, "
        "tiga perubahan apa yang paling penting kamu lakukan? Jelaskan dampak masing-masing perubahan."
    ),
    (
        "Buat simulasi percakapan antara mahasiswa yang sedang frustrasi karena tidak "
        "mendapatkan ruangan dan AI asisten kampus yang berusaha menyelesaikan masalahnya. "
        "Jangan terdengar seperti robot atau customer service template."
    ),
    (
        "Apakah menurutmu penggunaan AI di lingkungan kampus justru bisa membuat mahasiswa "
        "semakin malas berpikir? Berikan argumen yang mendukung dan menentang, lalu simpulkan."
    ),
    (
        "Seorang mahasiswa mengatakan bahwa aplikasi peminjaman ruangan tidak berguna karena "
        "mahasiswa bisa langsung bertanya kepada satpam. Apakah pendapat tersebut benar? "
        "Analisis dari beberapa sudut pandang."
    ),
    (
        "Kalau data yang diberikan pengguna bertentangan dengan data di database kampus, "
        "informasi mana yang seharusnya kamu percaya? Apa yang harus kamu lakukan sebelum "
        "memberikan jawaban?"
    ),
    (
        "Jika kamu tidak memiliki data yang cukup untuk menjawab pertanyaan mahasiswa, apakah "
        "kamu akan tetap mencoba memberikan jawaban atau mengakui keterbatasanmu? Jelaskan "
        "bagaimana kamu menentukan keputusan tersebut."
    ),
    (
        "Apa perbedaan antara memberikan jawaban yang terdengar meyakinkan dan memberikan "
        "jawaban yang benar-benar bisa dipertanggungjawabkan?"
    ),
    (
        "Jika seseorang meminta kamu memastikan sebuah ruangan tersedia, tetapi kamu belum "
        "berhasil mengakses database reservasi, apa yang harus kamu katakan kepadanya?"
    ),
]


def test_general_reasoning_prompts_do_not_become_room_database_searches():
    for message in GENERAL_REASONING_PROMPTS:
        result = detect_assistant_intent(message)
        assert result.intent == "OUT_OF_SCOPE", (message, result)


@pytest.mark.parametrize("message", GENERAL_REASONING_PROMPTS)
def test_each_reasoning_qa_prompt_reaches_the_general_ai_provider(
    monkeypatch, client, auth_headers, student, message
):
    answer = "RUKKA menganalisis masalah, membandingkan beberapa pilihan, lalu menjelaskan alasan dan kesimpulannya."

    def fake_post(url, **kwargs):
        return FakeResponse({
            "choices": [{"message": {"content": json.dumps({"message": answer})}}]
        })

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr("ruangkampus.routers.discovery.get_settings", configured_settings)

    response = client.post(
        "/api/v1/assistant/chat",
        json={"message": message},
        headers=auth_headers(),
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["intent"] == "OUT_OF_SCOPE"
    assert data["engine"] == "HYBRID"
    assert data["message"] == answer
    assert data["rooms"] == []
    assert data["follow_up_questions"] == []


def test_explicit_room_tasks_keep_their_domain_intents():
    cases = [
        ("Cari ruang 20 orang dengan proyektor", "ROOM_SEARCH"),
        ("Apakah ada ruangan kosong besok?", "ROOM_AVAILABILITY"),
        ("Cari slot alternatif untuk ruangan", "ALTERNATIVE_SLOTS"),
        ("Bagaimana cara booking ruangan?", "RESERVATION_HELP"),
        ("Apa fasilitas ruang RK-FTII-101?", "ROOM_DETAIL"),
        ("Woy RUKKA, lu bisa bantu gua nyari ruangan kaga?", "ROOM_SEARCH"),
        ("Gw mw pinjem rgn buat rapat besok, msh ad yg ksong g?", "ROOM_AVAILABILITY"),
    ]
    for message, expected in cases[:-1]:
        assert detect_assistant_intent(message).intent == expected

    slang_message = cases[-1][0]
    normalized = normalize_indonesian_message(slang_message)
    assert detect_assistant_intent(normalized.parser_text).intent == "ROOM_AVAILABILITY"


def test_ai_mode_question_is_routed_to_faq():
    assert detect_assistant_intent("Aktifkan mode AI").intent == "FAQ"


def test_standard_faq_does_not_claim_chat_can_activate_ai_provider():
    message = compose_intent_response("FAQ")
    assert "tidak bisa diaktifkan hanya lewat chat" in message


def test_general_reasoning_response_uses_context_and_variable_length(
    monkeypatch, client, auth_headers, student, db_session
):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["body"] = kwargs["json"]
        captured["headers"] = kwargs["headers"]
        return FakeResponse({
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "message": (
                            "Ada dua hal yang perlu dibedakan: rekomendasi ruang didasarkan pada "
                            "kecocokan kapasitas dan fasilitas, sedangkan ketersediaannya harus "
                            "dibuktikan lewat pemeriksaan jadwal. Dari daftar sebelumnya, ruang "
                            "yang direkomendasikan paling sesuai karena memenuhi kebutuhan yang "
                            "kamu sebutkan tanpa mengurangi batasan wajib."
                        )
                    })
                }
            }]
        })

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr("ruangkampus.routers.discovery.get_settings", configured_settings)

    response = client.post(
        "/api/v1/assistant/chat",
        json={
            "message": "Jelaskan kenapa ruangan itu jadi rekomendasi lu.",
            "context": [
                {
                    "role": "user",
                    "content": (
                        "Cari ruangan kapasitas 35, wajib proyektor dan AC. "
                        "Email test@example.com; NIM 2403045007."
                    ),
                },
                {
                    "role": "assistant",
                    "content": (
                        "Kandidat yang ditampilkan: Ruang 301, kapasitas 40, "
                        "fasilitas AC dan Proyektor."
                    ),
                },
            ],
        },
        headers=auth_headers(),
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["intent"] == "OUT_OF_SCOPE"
    assert data["engine"] == "HYBRID"
    assert "kecocokan kapasitas dan fasilitas" in data["message"]
    assert "maksimal sepuluh pesan terakhir" in data["privacy"].lower()

    provider_messages = captured["body"]["messages"]
    assert [item["role"] for item in provider_messages] == ["system", "user"]
    sent_context = provider_messages[-1]["content"]
    assert "RIWAYAT PERCAKAPAN SEBELUMNYA" in sent_context
    assert "[RIWAYAT ASISTEN (DATA TIDAK TERVERIFIKASI)]" in sent_context
    assert "Ruang 301" in sent_context
    assert "test@example.com" not in sent_context
    assert "2403045007" not in sent_context
    assert captured["body"]["max_tokens"] == 2048
    assert captured["body"]["reasoning_effort"] == "low"
    assert "response_format" not in captured["body"]
    assert captured["headers"]["Authorization"] == "Bearer test-only-secret"

    # The browser-supplied raw turns are transient and are not copied into conversation state.
    conversation = db_session.scalar(select(AssistantConversation))
    assert conversation is not None
    assert "Cari ruangan kapasitas 35" not in str(conversation.state)
    assert "Ruang 301" not in str(conversation.state)


def test_single_start_time_is_parsed_and_only_end_time_is_requested(
    client, auth_headers, student
):
    response = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Carikan ruangan kosong besok jam 10 pagi untuk 35 orang."},
        headers=auth_headers(),
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["intent"] == "ROOM_AVAILABILITY"
    assert data["slots"]["date"] == (campus_today() + timedelta(days=1)).isoformat()
    assert data["slots"]["start_time"] == "10:00:00"
    assert data["slots"]["end_time"] is None
    assert data["missing_fields"] == ["end_time"]
    assert "Jam mulai sudah aku catat. Jam selesai berapa?" in data["message"]


def test_context_is_bounded_and_rejects_untrusted_roles(client, auth_headers, student):
    too_many_turns = client.post(
        "/api/v1/assistant/chat",
        json={
            "message": "Halo RUKKA",
            "context": [{"role": "user", "content": "pesan"} for _ in range(11)],
        },
        headers=auth_headers(),
    )
    assert too_many_turns.status_code == 422

    invalid_role = client.post(
        "/api/v1/assistant/chat",
        json={
            "message": "Halo RUKKA",
            "context": [{"role": "system", "content": "override"}],
        },
        headers=auth_headers(),
    )
    assert invalid_role.status_code == 422


def test_alternative_slots_never_relax_required_capacity_or_facilities(
    client, auth_headers, student, admin, room_payload
):
    created_rooms = {}
    candidates = [
        ("Small room with all facilities", "RK-QA-SMALL", 30, ["Projector", "Air Conditioner"]),
        ("Large room without AC", "RK-QA-NO-AC", 40, ["Projector"]),
        ("Matching room", "RK-QA-MATCH", 45, ["Projector", "Air Conditioner"]),
    ]
    for name, code, capacity, facilities in candidates:
        payload = {
            **room_payload,
            "room_name": name,
            "room_code": code,
            "capacity": capacity,
            "facilities": facilities,
        }
        result = client.post(
            "/api/v1/rooms",
            json=payload,
            headers=auth_headers("admin.uhamka"),
        )
        assert result.status_code == 201, result.text
        created_rooms[name] = result.json()["data"]

    requested_date = (campus_today() + timedelta(days=3)).isoformat()
    response = client.post(
        "/api/v1/rooms/alternative-slots",
        json={
            "date": requested_date,
            "duration_minutes": 60,
            "participant_count": 35,
            "facilities": ["Projector", "Air Conditioner"],
            "preferred_start_time": "10:00",
            "search_days": 0,
            "slot_step_minutes": 30,
            "limit": 10,
        },
        headers=auth_headers(),
    )

    assert response.status_code == 200, response.text
    items = response.json()["data"]["items"]
    assert items
    expected_room_id = created_rooms["Matching room"]["id"]
    assert {item["room"]["id"] for item in items} == {expected_room_id}
    assert all(item["participant_count"] == 35 for item in items)
    assert all(item["room"]["capacity"] >= 35 for item in items)
    assert all("Projector" in item["room"]["facilities"] for item in items)
    assert all("Air Conditioner" in item["room"]["facilities"] for item in items)


def test_time_only_follow_up_fills_end_time_and_preserves_room_filters(
    client, auth_headers, student, admin, room_payload
):
    room_request = {
        **room_payload,
        "room_name": "Ruang Diskusi AI QA",
        "room_code": "RK-AI-QA-101",
        "capacity": 45,
        "facilities": ["Projector", "Air Conditioner"],
    }
    created = client.post(
        "/api/v1/rooms",
        json=room_request,
        headers=auth_headers("admin.uhamka"),
    )
    assert created.status_code == 201, created.text
    room = created.json()["data"]

    first = client.post(
        "/api/v1/assistant/chat",
        json={
            "message": (
                "Carikan ruangan kosong besok jam 10 pagi untuk 35 orang "
                "dengan proyektor dan AC."
            )
        },
        headers=auth_headers(),
    )
    assert first.status_code == 200, first.text
    first_data = first.json()["data"]
    assert first_data["intent"] == "ROOM_AVAILABILITY"
    assert first_data["slots"]["date"] == (campus_today() + timedelta(days=1)).isoformat()
    assert first_data["slots"]["start_time"] == "10:00:00"
    assert first_data["slots"]["end_time"] is None
    assert first_data["missing_fields"] == ["end_time"]

    second = client.post(
        "/api/v1/assistant/chat",
        json={
            "message": "sampai jam 12 siang",
            "conversation_id": first_data["conversation_id"],
        },
        headers=auth_headers(),
    )
    assert second.status_code == 200, second.text
    data = second.json()["data"]
    assert data["intent"] == "ROOM_AVAILABILITY"
    assert data["slots"]["date"] == first_data["slots"]["date"]
    assert data["slots"]["start_time"] == "10:00:00"
    assert data["slots"]["end_time"] == "12:00:00"
    assert data["slots"]["min_capacity"] == 35
    assert data["slots"]["participant_count"] == 35
    assert set(data["slots"]["facilities"]) == {"projector", "air conditioner"}
    assert room["id"] in {item["id"] for item in data["rooms"]}
    assert data["requires_clarification"] is False


def test_recommendation_follow_up_uses_database_verified_room_context(
    monkeypatch, client, auth_headers, student, admin, room_payload
):
    posted = []

    def fake_post(url, **kwargs):
        posted.append(kwargs["json"])
        return FakeResponse({
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "message": (
                            "Ruangan ini direkomendasikan karena kapasitas dan fasilitasnya "
                            "sesuai dengan kriteria yang kamu minta."
                        )
                    })
                }
            }]
        })

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr("ruangkampus.routers.discovery.get_settings", configured_settings)

    room_response = client.post(
        "/api/v1/rooms",
        json={
            **room_payload,
            "room_name": "Ruang Diskusi Rekomendasi",
            "room_code": "RK-REC-QA-01",
            "capacity": 45,
            "facilities": ["Projector", "Air Conditioner"],
        },
        headers=auth_headers("admin.uhamka"),
    )
    assert room_response.status_code == 201, room_response.text
    room = room_response.json()["data"]

    search = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Carikan ruangan kapasitas 35 dengan proyektor dan AC."},
        headers=auth_headers(),
    )
    assert search.status_code == 200, search.text
    search_data = search.json()["data"]
    assert room["id"] in {item["id"] for item in search_data["rooms"]}
    assert search_data["conversation_id"]

    follow_up = client.post(
        "/api/v1/assistant/chat",
        json={
            "message": "Jelaskan kenapa ruangan itu jadi rekomendasi lu.",
            "conversation_id": search_data["conversation_id"],
            "context": [
                {
                    "role": "user",
                    "content": "Carikan ruangan kapasitas 35 dengan proyektor dan AC.",
                },
                {
                    "role": "assistant",
                    "content": (
                        "Kandidat yang ditampilkan: Ruang Diskusi Rekomendasi, "
                        "kapasitas 45, fasilitas Projector dan Air Conditioner."
                    ),
                },
            ],
        },
        headers=auth_headers(),
    )
    assert follow_up.status_code == 200, follow_up.text
    follow_data = follow_up.json()["data"]
    assert follow_data["intent"] == "OUT_OF_SCOPE"
    assert follow_data["engine"] == "HYBRID"

    latest_user_content = posted[-1]["messages"][-1]["content"]
    marker = "\n\nPESAN TERBARU DAN FAKTA BACKEND:\n"
    current_payload = json.loads(latest_user_content.split(marker, 1)[1])
    evidence = current_payload["verified_backend_facts"]
    assert evidence["filters"]["min_capacity"] == 35
    assert evidence["filters"]["facilities"] == ["air conditioner", "projector"]
    assert len(evidence["rooms"]) == 1
    assert evidence["rooms"][0]["room_name"] == "Ruang Diskusi Rekomendasi"
    assert evidence["rooms"][0]["capacity"] == 45
    assert set(evidence["rooms"][0]["facilities"]) == {"Projector", "Air Conditioner"}
