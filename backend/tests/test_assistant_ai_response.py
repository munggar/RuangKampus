from __future__ import annotations

import json

import httpx

from ruangkampus.config import Settings
from ruangkampus.services.assistant_ai_response import generate_grounded_assistant_message


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
        assistant_ai_endpoint_url="https://openrouter.ai/api/v1/chat/completions",
        assistant_ai_model="google/gemma-4-26b-a4b-it:free",
        assistant_ai_api_key="test-only-secret",
        assistant_ai_timeout_seconds=2,
    )


def provider_response(content: str):
    return {"choices": [{"message": {"content": content}}]}


def test_rukka_generates_only_from_grounded_room_facts_and_redacts_identifiers(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["body"] = kwargs["json"]
        captured["headers"] = kwargs["headers"]
        return FakeResponse(provider_response(json.dumps({
            "message": "Aku menemukan satu ruangan yang cocok. Ruang 301 memiliki kapasitas 30 orang dan fasilitas proyektor. Jadwalnya belum diverifikasi; kapan kamu ingin menggunakannya?"
        })))

    monkeypatch.setattr(httpx, "post", fake_post)
    answer = generate_grounded_assistant_message(
        message="Bro cari ruang 20 orang, NIM 2403045007, email test@example.com, telp 081234567890",
        intent="ROOM_SEARCH",
        deterministic_message="Aku menemukan satu ruangan yang sesuai.",
        filters={
            "faculty": "FTII",
            "building": "Building A",
            "min_capacity": 20,
            "facilities": ["Projector"],
            "date": None,
            "start_time": None,
            "end_time": None,
            "participant_count": 20,
        },
        rooms=[{
            "id": "private-internal-room-id",
            "room_name": "Ruang 301",
            "room_code": "RK-301",
            "faculty": "FTII",
            "building": "Building A",
            "floor": 3,
            "capacity": 30,
            "facilities": ["Projector"],
            "location_description": "Dekat lobby",
        }],
        alternative_slots=[],
        follow_up_questions=["Kapan tanggal dan jam pemakaiannya?"],
        availability_checked=False,
        settings=configured_settings(),
        adaptive_preferences=["Use a casual tone and keep answers concise."],
    )

    assert answer is not None
    assert "Ruang 301" in answer
    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-only-secret"
    prompt = captured["body"]["messages"][1]["content"]
    assert "2403045007" not in prompt
    assert "081234567890" not in prompt
    assert "test@example.com" not in prompt
    assert "private-internal-room-id" not in prompt
    assert '"availability_checked":false' in prompt
    payload = json.loads(prompt)
    assert len(payload["language_hints"]) <= 8
    assert payload["response_preferences"] == ["Use a casual tone and keep answers concise."]
    assert captured["body"]["response_format"] == {"type": "json_object"}


def test_rukka_handles_smalltalk_with_short_whatsapp_style_reply(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["body"] = kwargs["json"]
        return FakeResponse(provider_response(json.dumps({
            "message": "Woy juga 😄 Lagi butuh bantuan apa nih?"
        })))

    monkeypatch.setattr(httpx, "post", fake_post)
    answer = generate_grounded_assistant_message(
        message="Woy",
        intent="SMALLTALK",
        deterministic_message="Wkwk, aku asisten virtual RuangKampus.",
        filters={},
        rooms=[],
        alternative_slots=[],
        follow_up_questions=[],
        availability_checked=False,
        settings=configured_settings(),
    )

    assert answer == "Woy juga 😄 Lagi butuh bantuan apa nih?"
    request = captured["body"]
    assert request["max_tokens"] == 120
    assert len(request["messages"][0]["content"]) > 0
    assert "RUKKA AI" in request["messages"][0]["content"]
    assert "WhatsApp" in request["messages"][0]["content"]


def test_rukka_never_sends_private_reservation_intents_to_provider(monkeypatch):
    def fail_post(*args, **kwargs):
        raise AssertionError("private reservation intents must not reach the provider")

    monkeypatch.setattr(httpx, "post", fail_post)
    answer = generate_grounded_assistant_message(
        message="Tampilkan reservasi saya",
        intent="MY_RESERVATIONS",
        deterministic_message="Aku akan menampilkan reservasi milikmu.",
        filters={},
        rooms=[],
        alternative_slots=[],
        follow_up_questions=[],
        availability_checked=False,
        settings=configured_settings(),
    )
    assert answer is None


def test_rukka_falls_back_when_provider_times_out(monkeypatch):
    def timeout(*args, **kwargs):
        raise httpx.TimeoutException("provider timeout")

    monkeypatch.setattr(httpx, "post", timeout)
    answer = generate_grounded_assistant_message(
        message="Carikan ruang di FTII",
        intent="ROOM_SEARCH",
        deterministic_message="Aku menemukan dua ruangan.",
        filters={"faculty": "FTII"},
        rooms=[],
        alternative_slots=[],
        follow_up_questions=[],
        availability_checked=False,
        settings=configured_settings(),
    )
    assert answer is None


def test_rukka_does_not_call_provider_when_disabled(monkeypatch):
    def fail_post(*args, **kwargs):
        raise AssertionError("disabled provider must not be called")

    monkeypatch.setattr(httpx, "post", fail_post)
    answer = generate_grounded_assistant_message(
        message="Carikan ruang di FTII",
        intent="ROOM_SEARCH",
        deterministic_message="Aku menemukan dua ruangan.",
        filters={},
        rooms=[],
        alternative_slots=[],
        follow_up_questions=[],
        availability_checked=False,
        settings=Settings(assistant_ai_enabled=False),
    )
    assert answer is None


def test_openrouter_key_activates_default_model_and_authenticates_real_request_shape(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["body"] = kwargs["json"]
        captured["headers"] = kwargs["headers"]
        return FakeResponse(provider_response(json.dumps({
            "message": "Ada tiga faktor yang perlu dipertimbangkan sebelum menentukan pilihan."
        })))

    monkeypatch.setattr(httpx, "post", fake_post)
    settings = Settings(_env_file=None, openrouter_api_key="sk-or-test-key")

    answer = generate_grounded_assistant_message(
        message="Menurutmu bagaimana cara memilih ruangan yang tepat?",
        intent="OUT_OF_SCOPE",
        deterministic_message="Aku bisa bantu pertimbangkan beberapa hal.",
        filters={},
        rooms=[],
        alternative_slots=[],
        follow_up_questions=[],
        availability_checked=False,
        settings=settings,
    )

    assert answer == "Ada tiga faktor yang perlu dipertimbangkan sebelum menentukan pilihan."
    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer sk-or-test-key"
    assert captured["headers"]["X-OpenRouter-Title"] == "RuangKampus - RUKKA AI"
    assert captured["headers"]["HTTP-Referer"] == settings.public_app_url
    assert captured["body"]["model"] == "google/gemma-4-26b-a4b-it:free"
    assert captured["body"]["response_format"] == {"type": "json_object"}
