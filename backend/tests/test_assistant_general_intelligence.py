from __future__ import annotations

import json
from datetime import timedelta

import httpx

from ruangkampus.config import Settings
from ruangkampus.services.assistant_intent import detect_assistant_intent
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
        "Bayangkan kampus memiliki 100 ruangan, tetapi setiap hari masih banyak mahasiswa "
        "kesulitan mendapatkan tempat belajar. Menurutmu, apa kemungkinan penyebabnya? "
        "Jangan langsung menyimpulkan bahwa jumlah ruangan kurang."
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
        "mendapatkan ruangan dan AI asisten kampus yang berusaha menyelesaikan masalahnya."
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
        "kamu akan tetap mencoba memberikan jawaban atau mengakui keterbatasanmu?"
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
        assert result.matched_rule in {
            "GENERAL_REASONING_REQUEST",
            "HYPOTHETICAL_REASONING_REQUEST",
            "NO_SUPPORTED_INTENT",
        }


def test_explicit_room_tasks_keep_their_domain_intents():
    cases = [
        ("Cari ruang 20 orang dengan proyektor", "ROOM_SEARCH"),
        ("Apakah ada ruangan kosong besok?", "ROOM_AVAILABILITY"),
        ("Cari slot alternatif untuk ruangan", "ALTERNATIVE_SLOTS"),
        ("Bagaimana cara booking ruangan?", "RESERVATION_HELP"),
        ("Apa fasilitas ruang RK-FTII-101?", "ROOM_DETAIL"),
        ("Woy RUKKA, lu bisa bantu gua nyari ruangan kaga?", "ROOM_SEARCH"),
    ]
    for message, expected in cases:
        assert detect_assistant_intent(message).intent == expected


def test_ai_mode_question_is_routed_to_faq():
    assert detect_assistant_intent("Aktifkan mode AI").intent == "FAQ"


def test_general_reasoning_response_uses_recent_context_and_variable_length(monkeypatch):
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
    monkeypatch.setattr(
        "ruangkampus.routers.discovery.get_settings",
        configured_settings,
    )

    from fastapi.testclient import TestClient
    from ruangkampus.main import app

    client = TestClient(app)
    # This test invokes the same endpoint used by the student chat page.
    # Authentication is provided by the shared test fixtures in the API-level test below.
    # A direct unit call keeps this test independent from database seed and auth configuration.
