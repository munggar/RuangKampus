from __future__ import annotations

import json

import httpx

from ruangkampus.config import Settings
from ruangkampus.services.assistant_ai_fallback import interpret_with_ai_fallback


CATALOG = {
    "faculties": [{"value": "FTII", "source_values": ["FTII"]}],
    "buildings": [{"value": "Building A", "source_values": ["Building A"]}],
    "facilities": [
        {
            "canonical_name": "projector",
            "display_name": "Projector",
            "source_values": ["Projector"],
            "aliases": ["projector", "proyektor"],
        }
    ],
}


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
        assistant_ai_model="small-instruct-model",
        assistant_ai_api_key="test-only-secret",
        assistant_ai_timeout_seconds=2,
    )


def provider_response(content: str):
    return {"choices": [{"message": {"content": content}}]}


def test_ai_fallback_disabled_never_calls_provider(monkeypatch):
    def fail_post(*args, **kwargs):
        raise AssertionError("provider must not be called when disabled")

    monkeypatch.setattr(httpx, "post", fail_post)
    assert interpret_with_ai_fallback(
        "cari ruang rapat", CATALOG, Settings(assistant_ai_enabled=False)
    ) is None


def test_ai_fallback_accepts_schema_and_resolves_only_catalog_values(monkeypatch):
    response = provider_response(json.dumps({
        "intent": "ROOM_SEARCH",
        "faculty": "FTII",
        "building": "Building A",
        "min_capacity": 20,
        "facilities": ["proyektor"],
        "date": None,
        "start_time": None,
        "end_time": None,
        "participant_count": 20,
    }))
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["body"] = kwargs["json"]
        captured["headers"] = kwargs["headers"]
        return FakeResponse(response)

    monkeypatch.setattr(httpx, "post", fake_post)
    result = interpret_with_ai_fallback(
        "gue butuh ruang buat rapat 20 orang di FTII pake proyektor",
        CATALOG,
        configured_settings(),
    )

    assert result is not None
    assert result.intent == "ROOM_SEARCH"
    assert result.faculty == "FTII"
    assert result.building == "Building A"
    assert result.min_capacity == 20
    assert result.facilities == ["projector"]
    assert captured["url"] == "https://ai.example.test/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-only-secret"
    user_message = captured["body"]["messages"][1]["content"]
    assert "conversation_id" not in user_message
    assert "user_id" not in user_message
    assert "reservation" not in user_message.lower()


def test_ai_fallback_rejects_unobserved_faculty_and_facility(monkeypatch):
    response = provider_response(json.dumps({
        "intent": "ROOM_SEARCH",
        "faculty": "Fakultas Rekayasa Fiktif",
        "building": None,
        "min_capacity": None,
        "facilities": ["projector"],
        "date": None,
        "start_time": None,
        "end_time": None,
        "participant_count": 1,
    }))
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: FakeResponse(response))
    assert interpret_with_ai_fallback(
        "carikan ruang fakultas fiktif", CATALOG, configured_settings()
    ) is None


def test_ai_fallback_rejects_unsupported_intent_or_extra_fields(monkeypatch):
    response = provider_response(json.dumps({
        "intent": "RESERVATION_CREATE",
        "faculty": None,
        "building": None,
        "min_capacity": None,
        "facilities": [],
        "date": None,
        "start_time": None,
        "end_time": None,
        "participant_count": 1,
        "execute_transaction": True,
    }))
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: FakeResponse(response))
    assert interpret_with_ai_fallback("bookingkan ruangan", CATALOG, configured_settings()) is None


def test_ai_fallback_fails_closed_on_timeout(monkeypatch):
    def timeout(*args, **kwargs):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(httpx, "post", timeout)
    assert interpret_with_ai_fallback("cari tempat rapat", CATALOG, configured_settings()) is None
