def test_admin_provisions_student_with_hashed_password(client, db_session, admin, auth_headers):
    response = client.post("/api/v1/users", headers=auth_headers("admin.uhamka"), json={
        "name": "New Student", "email": "new@example.com",
        "student_identifier": "2403049999", "password": "VeryStrongPass123!",
    })
    assert response.status_code == 201, response.text
    user = db_session.query(__import__("ruangkampus.models", fromlist=["User"]).User).filter_by(email="new@example.com").one()
    assert user.password_hash != "VeryStrongPass123!"
    login = client.post("/api/v1/auth/login", json={"identifier": "2403049999", "password": "VeryStrongPass123!"})
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "Student"
    assert "ruangkampus_refresh" in login.cookies


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


def test_logout_revokes_cookie_session_after_access_token_expiry(client, student):
    login = client.post("/api/v1/auth/login", json={
        "identifier": "2403045007", "password": "StrongPass123!",
    })
    assert login.status_code == 200
    refresh_cookie = login.cookies.get("ruangkampus_refresh")
    assert refresh_cookie
    logout = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": "Bearer expired.or.invalid.token"},
        cookies={"ruangkampus_refresh": refresh_cookie},
    )
    assert logout.status_code == 200
    refresh = client.post("/api/v1/auth/refresh", cookies={"ruangkampus_refresh": refresh_cookie})
    assert refresh.status_code == 401


def test_forgot_password_response_does_not_disclose_account(client, student):
    existing = client.post("/api/v1/auth/forgot-password", json={"email": "student@example.com"})
    missing = client.post("/api/v1/auth/forgot-password", json={"email": "missing@example.com"})
    assert existing.status_code == missing.status_code == 202
    assert existing.json() == missing.json()


def test_admin_login_returns_frontend_role_label(client, admin):
    response = client.post("/api/v1/auth/login", json={"identifier": "admin.uhamka", "password": "StrongPass123!"})
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "TU/Admin"


def test_public_student_registration_is_disabled_until_nim_verification(client):
    response = client.post("/api/v1/auth/register", json={
        "name": "Unverified Student", "email": "unverified@example.com",
        "student_identifier": "2403041234", "password": "VeryStrongPass123!",
    })
    assert response.status_code == 403


def test_admin_student_creation_rejects_duplicate_nim(client, admin, auth_headers):
    headers = auth_headers("admin.uhamka")
    payload = {
        "name": "First Student", "email": "first@example.com",
        "student_identifier": "2403041234", "password": "VeryStrongPass123!",
    }
    first = client.post("/api/v1/users", headers=headers, json=payload)
    duplicate = client.post("/api/v1/users", headers=headers, json={
        **payload, "name": "Second Student", "email": "second@example.com",
    })
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
