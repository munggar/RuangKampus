def test_register_and_login_uses_hashed_password(client, db_session):
    response = client.post("/api/v1/auth/register", json={"name": "New Student", "email": "new@example.com", "student_identifier": "2403049999", "password": "VeryStrongPass123!"})
    assert response.status_code == 201, response.text
    assert set(response.json()) == {"access_token", "token_type", "expires_in", "user"}
    user = db_session.query(__import__("ruangkampus.models", fromlist=["User"]).User).filter_by(email="new@example.com").one()
    assert user.password_hash != "VeryStrongPass123!"
    login = client.post("/api/v1/auth/login", json={"identifier": "2403049999", "password": "VeryStrongPass123!"})
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "Student"
    assert "ruangkampus_refresh" in login.cookies
    assert set(login.json()) == {"access_token", "token_type", "expires_in", "user"}


def test_register_does_not_accept_role_from_client(client):
    response = client.post("/api/v1/auth/register", json={"name": "Fake Admin", "email": "fake@example.com", "student_identifier": "2403049998", "password": "VeryStrongPass123!", "role": "TU_ADMIN"})
    assert response.status_code == 422


def test_bad_password_rejected(client, student):
    response = client.post("/api/v1/auth/login", json={"identifier": "2403045007", "password": "wrong-password"})
    assert response.status_code == 401


def test_protected_route_rejects_anonymous_user(client):
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


def test_profile_and_logout_revoke_access_token(client, auth_headers, student):
    headers = auth_headers()
    profile = client.get("/api/v1/auth/me", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["role"] == "Student"
    logout = client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 200
    denied = client.get("/api/v1/auth/me", headers=headers)
    assert denied.status_code == 401


def test_forgot_password_response_does_not_disclose_account(client, student):
    existing = client.post("/api/v1/auth/forgot-password", json={"email": "student@example.com"})
    missing = client.post("/api/v1/auth/forgot-password", json={"email": "missing@example.com"})
    assert existing.status_code == missing.status_code == 202
    assert existing.json() == missing.json()


def test_admin_login_returns_frontend_role_label(client, admin):
    response = client.post("/api/v1/auth/login", json={"identifier": "admin.uhamka", "password": "StrongPass123!"})
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "TU/Admin"


def test_register_requires_unique_nim(client):
    missing = client.post("/api/v1/auth/register", json={"name": "No NIM", "email": "nonim@example.com", "password": "VeryStrongPass123!"})
    assert missing.status_code == 422
    first = client.post("/api/v1/auth/register", json={"name": "First Student", "email": "first@example.com", "student_identifier": "2403041234", "password": "VeryStrongPass123!"})
    duplicate = client.post("/api/v1/auth/register", json={"name": "Second Student", "email": "second@example.com", "student_identifier": "2403041234", "password": "VeryStrongPass123!"})
    assert first.status_code == 201
    assert duplicate.status_code == 409


def test_admin_username_login_is_case_insensitive(client, admin):
    response = client.post("/api/v1/auth/login", json={"identifier": "ADMIN.UHAMKA", "password": "StrongPass123!"})
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "TU/Admin"


def test_health_and_readiness_endpoints(client):
    health = client.get("/health")
    ready = client.get("/ready")
    assert health.status_code == 200
    assert health.json()["data"]["status"] == "ok"
    assert ready.status_code == 200
    assert ready.json()["data"]["database"] == "reachable"


def test_chunked_body_size_limit_is_enforced(client):
    response = client.post(
        "/api/v1/auth/register",
        content=b"x" * (6 * 1024 * 1024 + 1),
        headers={"Content-Type": "application/json", "Transfer-Encoding": "chunked"},
    )
    assert response.status_code == 413
    assert response.json()["success"] is False

def test_register_accepts_eight_character_password(client):
    accepted = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Eight Char Student",
            "email": "eight-char@example.com",
            "student_identifier": "2403048888",
            "password": "Pass123!",
        },
    )
    assert accepted.status_code == 201, accepted.text


def test_register_rejects_password_shorter_than_eight_characters(client):
    rejected = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Seven Char Student",
            "email": "seven-char@example.com",
            "student_identifier": "2403047777",
            "password": "Pass12!",
        },
    )
    assert rejected.status_code == 422



def test_admin_can_update_profile_email_and_username_remains_unchanged(client, admin, auth_headers):
    headers = auth_headers("admin.uhamka")
    response = client.patch(
        "/api/v1/users/me",
        json={"email": "Admin.Updated@Example.com"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["email"] == "admin.updated@example.com"
    assert response.json()["data"]["student_identifier"] == "admin.uhamka"


def test_profile_email_cannot_duplicate_another_account_case_insensitively(client, admin, student, auth_headers):
    headers = auth_headers("admin.uhamka")
    response = client.patch(
        "/api/v1/users/me",
        json={"email": "STUDENT@EXAMPLE.COM"},
        headers=headers,
    )
    assert response.status_code == 409


def test_change_password_accepts_eight_characters(client, admin, auth_headers):
    headers = auth_headers("admin.uhamka")
    changed = client.patch(
        "/api/v1/users/me/password",
        json={"current_password": "StrongPass123!", "new_password": "Pass123!"},
        headers=headers,
    )
    assert changed.status_code == 200, changed.text
    login = client.post(
        "/api/v1/auth/login",
        json={"identifier": "admin.uhamka", "password": "Pass123!"},
    )
    assert login.status_code == 200


def test_change_password_rejects_fewer_than_eight_characters(client, admin, auth_headers):
    headers = auth_headers("admin.uhamka")
    response = client.patch(
        "/api/v1/users/me/password",
        json={"current_password": "StrongPass123!", "new_password": "Pass12!"},
        headers=headers,
    )
    assert response.status_code == 422



def test_forgot_password_sends_branded_email_with_reset_link(client, student, monkeypatch):
    captured = {}

    def fake_send_email(to_email, subject, body, html_body=None):
        captured.update(to=to_email, subject=subject, body=body, html=html_body)
        return True

    monkeypatch.setattr("ruangkampus.routers.auth.send_email", fake_send_email)
    response = client.post("/api/v1/auth/forgot-password", json={"email": student.email})
    assert response.status_code == 202
    assert captured["to"] == student.email
    assert "Atur ulang password" in captured["subject"]
    assert "reset-password#token=" in captured["body"]
    assert "reset-password#token=" in captured["html"]
    assert "KEAMANAN AKUN" in captured["html"]
    assert "Masa berlaku" in captured["html"]
    assert "Atur ulang password" in captured["html"]
