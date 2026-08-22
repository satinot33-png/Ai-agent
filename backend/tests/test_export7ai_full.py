"""End-to-end backend regression for Export 7 AI Control Center.

Covers auth (username/password + logout), dashboard, AI CRUD/RBAC,
countries + provinces, server actions, interrogation, user CRUD,
activity log, and new-user login lifecycle.
"""
import os
import uuid
import time

import pytest
import requests


BASE_URL = os.environ.get("EXPO_BACKEND_URL") or os.environ.get("EXPO_PUBLIC_BACKEND_URL")
if not BASE_URL:
    pytest.skip("Preview backend URL is not configured", allow_module_level=True)
BASE_URL = BASE_URL.rstrip("/")


# ---------- helpers ----------
def _login(session: requests.Session, username: str, password: str):
    r = session.post(f"{BASE_URL}/api/auth/login", json={"username": username, "password": password}, timeout=30)
    return r


def _client(token: str | None = None) -> requests.Session:
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="module")
def super_token() -> str:
    r = _login(requests.Session(), "superadmin", "SuperAdmin@2026")
    assert r.status_code == 200, r.text
    return r.json()["session_token"]


@pytest.fixture(scope="module")
def admin_token() -> str:
    r = _login(requests.Session(), "admin", "Admin@2026")
    assert r.status_code == 200, r.text
    return r.json()["session_token"]


@pytest.fixture(scope="module")
def karyawan_token() -> str:
    r = _login(requests.Session(), "karyawan", "Karyawan@2026")
    assert r.status_code == 200, r.text
    return r.json()["session_token"]


# ---------- auth ----------
class TestAuth:
    def test_login_wrong_password_401(self):
        r = _login(requests.Session(), "superadmin", "WRONG")
        assert r.status_code == 401

    def test_login_success_returns_token_and_user(self, super_token):
        assert isinstance(super_token, str) and len(super_token) > 10

    def test_me_returns_current_user(self, super_token):
        r = _client(super_token).get(f"{BASE_URL}/api/auth/me", timeout=20)
        assert r.status_code == 200
        body = r.json()
        assert body["username"] == "superadmin"
        assert body["role"] == "SUPER ADMIN"
        assert "allowed_ais" in body and "allowed_countries" in body
        assert "password_hash" not in body

    def test_logout_invalidates_token(self):
        r = _login(requests.Session(), "admin", "Admin@2026")
        token = r.json()["session_token"]
        c = _client(token)
        assert c.post(f"{BASE_URL}/api/auth/logout", timeout=20).status_code == 200
        assert c.get(f"{BASE_URL}/api/auth/me", timeout=20).status_code == 401


# ---------- dashboard + ai ----------
class TestDashboardAndAI:
    def test_dashboard_shape(self, super_token):
        r = _client(super_token).get(f"{BASE_URL}/api/dashboard", timeout=20)
        assert r.status_code == 200
        body = r.json()
        for key in ("server", "ais", "countries", "logs", "user"):
            assert key in body, f"missing {key}"
        # AI seeds expected AI 1..AI 7
        names = sorted(a["name"] for a in body["ais"])
        assert names == [f"AI {i}" for i in range(1, 8)]

    def test_list_ai_seven(self, super_token):
        r = _client(super_token).get(f"{BASE_URL}/api/ai", timeout=20)
        assert r.status_code == 200
        agents = r.json()
        assert len(agents) == 7
        assert {a["agent_id"] for a in agents} == {f"ai-{i}" for i in range(1, 8)}

    def test_toggle_ai_persists(self, super_token):
        c = _client(super_token)
        r = c.patch(f"{BASE_URL}/api/ai/ai-1", json={"enabled": False}, timeout=20)
        assert r.status_code == 200
        assert r.json()["enabled"] is False
        r2 = c.get(f"{BASE_URL}/api/ai", timeout=20)
        assert next(a for a in r2.json() if a["agent_id"] == "ai-1")["enabled"] is False
        # restore
        c.patch(f"{BASE_URL}/api/ai/ai-1", json={"enabled": True}, timeout=20)

    def test_bulk_ai_toggle(self, super_token):
        c = _client(super_token)
        r = c.post(f"{BASE_URL}/api/ai/bulk", json={"enabled": True}, timeout=20)
        assert r.status_code == 200
        assert all(a["enabled"] for a in r.json())

    def test_karyawan_cannot_patch_ai(self, karyawan_token):
        r = _client(karyawan_token).patch(f"{BASE_URL}/api/ai/ai-2", json={"enabled": False}, timeout=20)
        assert r.status_code == 403

    def test_karyawan_cannot_bulk_ai(self, karyawan_token):
        r = _client(karyawan_token).post(f"{BASE_URL}/api/ai/bulk", json={"enabled": False}, timeout=20)
        assert r.status_code == 403


# ---------- countries / provinces ----------
class TestGeography:
    def test_countries_have_region(self, super_token):
        r = _client(super_token).get(f"{BASE_URL}/api/countries", timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 46
        assert all("region" in c and "code" in c for c in data)

    def test_country_toggle_persists(self, super_token):
        c = _client(super_token)
        r = c.patch(f"{BASE_URL}/api/countries/US", json={"enabled": True}, timeout=20)
        assert r.status_code == 200 and r.json()["enabled"] is True
        got = next(x for x in c.get(f"{BASE_URL}/api/countries", timeout=20).json() if x["code"] == "US")
        assert got["enabled"] is True

    def test_country_bulk(self, super_token):
        c = _client(super_token)
        r = c.post(f"{BASE_URL}/api/countries/bulk", json={"enabled": False}, timeout=30)
        assert r.status_code == 200
        assert all(not x["enabled"] for x in r.json())
        # restore ID
        c.patch(f"{BASE_URL}/api/countries/ID", json={"enabled": True}, timeout=20)

    def test_provinces_indonesia(self, super_token):
        r = _client(super_token).get(f"{BASE_URL}/api/provinces", timeout=20)
        assert r.status_code == 200
        assert len(r.json()) == 38


# ---------- server + interrogation ----------
class TestServer:
    def test_server_state(self, super_token):
        r = _client(super_token).get(f"{BASE_URL}/api/server", timeout=20)
        assert r.status_code == 200
        assert "server_online" in r.json()

    def test_server_off_on_restart(self, super_token):
        c = _client(super_token)
        r = c.post(f"{BASE_URL}/api/server/action", json={"action": "off"}, timeout=20)
        assert r.status_code == 200 and r.json()["server_online"] is False and r.json()["api_online"] is False
        r = c.post(f"{BASE_URL}/api/server/action", json={"action": "on"}, timeout=20)
        assert r.json()["server_online"] is True
        r = c.post(f"{BASE_URL}/api/server/action", json={"action": "restart"}, timeout=20)
        assert "restart" in r.json()["uptime"].lower() or r.json()["uptime"].startswith("0m")

    def test_karyawan_cannot_server_action(self, karyawan_token):
        r = _client(karyawan_token).post(f"{BASE_URL}/api/server/action", json={"action": "off"}, timeout=20)
        assert r.status_code == 403

    def test_interrogation_shape(self, super_token):
        r = _client(super_token).post(f"{BASE_URL}/api/interrogation", timeout=20)
        assert r.status_code == 200
        body = r.json()
        for key in ("connection", "api", "database", "ai", "active_jobs", "successful_jobs", "failed_jobs", "last_error", "checked_at"):
            assert key in body
        assert len(body["ai"]) == 7
        assert all({"agent_id", "name", "status"} <= set(item) for item in body["ai"])


# ---------- user CRUD ----------
@pytest.fixture(scope="module")
def created_user(super_token):
    suffix = uuid.uuid4().hex[:6]
    payload = {
        "name": "TEST User",
        "username": f"test_{suffix}",
        "email": f"test_{suffix}@example.com",
        "whatsapp": "+628110000999",
        "password": "TestPass@2026",
        "role": "KARYAWAN",
        "allowed_ais": ["ai-1", "ai-2"],
        "allowed_countries": ["ID", "US"],
        "allowed_provinces": ["Jawa Barat"],
        "access_start": "2026-01-01",
        "access_end": "2026-12-31",
        "enabled": True,
    }
    c = _client(super_token)
    r = c.post(f"{BASE_URL}/api/users", json=payload, timeout=20)
    assert r.status_code == 200, r.text
    body = r.json()
    yield {"user": body, "payload": payload}
    c.delete(f"{BASE_URL}/api/users/{body['user_id']}", timeout=20)


class TestUsers:
    def test_create_persists(self, super_token, created_user):
        u = created_user["user"]
        r = _client(super_token).get(f"{BASE_URL}/api/users", timeout=20)
        assert r.status_code == 200
        assert any(x["user_id"] == u["user_id"] for x in r.json())

    def test_duplicate_username_409(self, super_token, created_user):
        payload = created_user["payload"].copy()
        payload["email"] = f"other_{uuid.uuid4().hex[:5]}@example.com"
        r = _client(super_token).post(f"{BASE_URL}/api/users", json=payload, timeout=20)
        assert r.status_code == 409

    def test_invalid_email_422(self, super_token):
        payload = {"name": "TEST bad", "username": f"bad_{uuid.uuid4().hex[:5]}",
                   "email": "not-an-email", "whatsapp": "+628110000999",
                   "password": "TestPass@2026", "role": "KARYAWAN"}
        r = _client(super_token).post(f"{BASE_URL}/api/users", json=payload, timeout=20)
        assert r.status_code == 422

    def test_short_password_422(self, super_token):
        payload = {"name": "TEST short", "username": f"sp_{uuid.uuid4().hex[:5]}",
                   "email": f"sp_{uuid.uuid4().hex[:5]}@example.com",
                   "whatsapp": "+628110000999", "password": "abc", "role": "KARYAWAN"}
        r = _client(super_token).post(f"{BASE_URL}/api/users", json=payload, timeout=20)
        assert r.status_code == 422

    def test_admin_cannot_create_superadmin(self, admin_token):
        payload = {"name": "TEST elevate", "username": f"el_{uuid.uuid4().hex[:5]}",
                   "email": f"el_{uuid.uuid4().hex[:5]}@example.com",
                   "whatsapp": "+628110000999", "password": "TestPass@2026",
                   "role": "SUPER ADMIN"}
        r = _client(admin_token).post(f"{BASE_URL}/api/users", json=payload, timeout=20)
        assert r.status_code == 403

    def test_update_user_password_and_role(self, super_token, created_user):
        u = created_user["user"]
        r = _client(super_token).patch(f"{BASE_URL}/api/users/{u['user_id']}",
                                       json={"password": "NewPass@2026", "name": "TEST Updated"},
                                       timeout=20)
        assert r.status_code == 200 and r.json()["name"] == "TEST Updated"
        # login with new password
        lr = _login(requests.Session(), u["username"], "NewPass@2026")
        assert lr.status_code == 200

    def test_admin_cannot_elevate_to_superadmin(self, admin_token, created_user):
        r = _client(admin_token).patch(f"{BASE_URL}/api/users/{created_user['user']['user_id']}",
                                       json={"role": "SUPER ADMIN"}, timeout=20)
        assert r.status_code == 403

    def test_toggle_status_and_login_blocked(self, super_token, created_user):
        u = created_user["user"]
        c = _client(super_token)
        r = c.patch(f"{BASE_URL}/api/users/{u['user_id']}/status", json={"enabled": False}, timeout=20)
        assert r.status_code == 200 and r.json()["enabled"] is False
        # disabled user login should be blocked (403)
        lr = _login(requests.Session(), u["username"], "NewPass@2026")
        assert lr.status_code in (401, 403)
        # re-enable
        c.patch(f"{BASE_URL}/api/users/{u['user_id']}/status", json={"enabled": True}, timeout=20)

    def test_cannot_delete_self(self, super_token):
        me = _client(super_token).get(f"{BASE_URL}/api/auth/me", timeout=20).json()
        r = _client(super_token).delete(f"{BASE_URL}/api/users/{me['user_id']}", timeout=20)
        assert r.status_code == 400


# ---------- activity + new user flow ----------
class TestActivityAndNewLogin:
    def test_activity_has_entries(self, super_token):
        r = _client(super_token).get(f"{BASE_URL}/api/activity", timeout=20)
        assert r.status_code == 200
        actions = {log["action"] for log in r.json()}
        # After running previous tests, expect these to have accumulated
        assert "LOGIN" in actions
        assert any(a in actions for a in ("AI_TOGGLE", "AI_BULK_TOGGLE", "SERVER_ACTION", "USER_CREATE"))

    def test_new_user_can_login_and_rbac(self, super_token):
        suffix = uuid.uuid4().hex[:5]
        payload = {"name": "TEST New Login", "username": f"nl_{suffix}",
                   "email": f"nl_{suffix}@example.com", "whatsapp": "+628110000999",
                   "password": "NewLogin@2026", "role": "KARYAWAN"}
        c = _client(super_token)
        r = c.post(f"{BASE_URL}/api/users", json=payload, timeout=20)
        assert r.status_code == 200
        uid = r.json()["user_id"]
        try:
            lr = _login(requests.Session(), payload["username"], payload["password"])
            assert lr.status_code == 200
            new_token = lr.json()["session_token"]
            # RBAC check: cannot toggle AI
            rr = _client(new_token).patch(f"{BASE_URL}/api/ai/ai-3", json={"enabled": False}, timeout=20)
            assert rr.status_code == 403
        finally:
            c.delete(f"{BASE_URL}/api/users/{uid}", timeout=20)
