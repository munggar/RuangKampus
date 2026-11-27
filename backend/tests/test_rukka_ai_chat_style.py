from ruangkampus.config import Settings
from ruangkampus.routers import discovery


def test_rukka_ai_answers_woy_through_the_student_assistant(
    client, auth_headers, student, monkeypatch
):
    settings = Settings(
        assistant_ai_enabled=True,
        assistant_ai_endpoint_url="https://openrouter.ai/api/v1/chat/completions",
        assistant_ai_model="google/gemma-4-26b-a4b-it:free",
    )
    generated = []

    def fake_generate(**kwargs):
        generated.append(kwargs)
        return "Woy juga 😄 Lagi butuh bantuan apa nih?"

    monkeypatch.setattr(discovery, "get_settings", lambda: settings)
    monkeypatch.setattr(discovery, "generate_grounded_assistant_message", fake_generate)

    response = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Woy"},
        headers=auth_headers(),
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["assistant_name"] == "RUKKA AI"
    assert data["intent"] == "SMALLTALK"
    assert data["engine"] == "HYBRID"
    assert data["message"] == "Woy juga 😄 Lagi butuh bantuan apa nih?"
    assert len(generated) == 1
    assert generated[0]["intent"] == "SMALLTALK"
    assert generated[0]["rooms"] == []
