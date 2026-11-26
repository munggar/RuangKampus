from datetime import date, timedelta


def test_staff_secretariat_cannot_access_student_assistant_chat(
    client, auth_headers, admin
):
    headers = auth_headers("admin.uhamka")
    response = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Carikan ruangan untuk rapat"},
        headers=headers,
    )

    assert response.status_code == 403


def test_staff_secretariat_cannot_access_student_alternative_slot_api(
    client, auth_headers, admin
):
    headers = auth_headers("admin.uhamka")
    response = client.post(
        "/api/v1/rooms/alternative-slots",
        json={
            "date": (date.today() + timedelta(days=7)).isoformat(),
            "duration_minutes": 60,
            "participant_count": 5,
            "search_days": 0,
            "limit": 5,
        },
        headers=headers,
    )

    assert response.status_code == 403


def test_no_admin_scoped_assistant_endpoint_is_registered(
    client, auth_headers, admin
):
    headers = auth_headers("admin.uhamka")
    response = client.post(
        "/api/v1/admin/assistant/chat",
        json={"message": "Carikan ruangan"},
        headers=headers,
    )

    assert response.status_code == 404


def test_staff_secretariat_auth_response_uses_public_label_without_changing_internal_role(
    client, auth_headers, admin
):
    headers = auth_headers("admin.uhamka")
    current_user = client.get("/api/v1/auth/me", headers=headers)

    assert current_user.status_code == 200, current_user.text
    assert current_user.json()["role"] == "Staff Sekretariat"
    assert admin.role == "TU_ADMIN"
