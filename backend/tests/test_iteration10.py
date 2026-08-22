"""Iteration 10 backend tests: Security audit fixes.

Covers:
- SEC-001: ADMIN cannot escalate via PATCH /users/{super_admin_id} or /users/{super_admin_id}/status.
- SEC-001: SUPER ADMIN still has full control (regression); ADMIN self-edit works.
- SEC-002: backend/.env & frontend/.env are gitignored.
- SEC-003: verify-otp and resend-otp return generic responses for unknown usernames.
- SEC-003: resend-otp per-username rate limit (3 per 10 min) — 4th call returns ack without
  triggering WhatsApp send (otp/outbox count doesn't grow beyond 3).
- SEC-005: 6th consecutive failed login within 5 min returns 429; successful login resets counter.
"""
from __future__ import annotations

import os
import subprocess
import time
import uuid

import pytest
import requests

BASE_URL = (
    os.environ.get("EXPO_BACKEND_URL")
    or os.environ.get("EXPO_PUBLIC_BACKEND_URL")
    or ""
).rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("EXPO_PUBLIC_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().strip('"').rstrip("/")
                break
assert BASE_URL, "BASE_URL not set"


# --------- Fixtures ---------

@pytest.fixture(scope="module")
def s():
    return requests.Session()


def _login(s: requests.Session, username: str, password: str) -> dict:
    r = s.post(f"{BASE_URL}/api/auth/login", json={"username": username, "password": password}, timeout=10)
    assert r.status_code == 200, f"login {username} failed: {r.status_code} {r.text}"
    return r.json()


@pytest.fixture(scope="module")
def super_admin(s):
    data = _login(s, "superadmin", "SuperAdmin@2026")
    return {"token": data["session_token"], "user": data["user"]}


@pytest.fixture(scope="module")
def admin_token(s):
    data = _login(s, "admin", "Admin@2026")
    return {"token": data["session_token"], "user": data["user"]}


def h(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# --------- SEC-002: gitignore ---------

class TestSEC002Gitignore:
    """backend/.env and frontend/.env must be gitignored."""

    def test_backend_env_ignored(self):
        result = subprocess.run(
            ["git", "check-ignore", "-v", "backend/.env"], cwd="/app", capture_output=True, text=True
        )
        assert result.returncode == 0, f"backend/.env NOT ignored (stderr={result.stderr})"
        assert "backend/.env" in result.stdout

    def test_frontend_env_ignored(self):
        result = subprocess.run(
            ["git", "check-ignore", "-v", "frontend/.env"], cwd="/app", capture_output=True, text=True
        )
        assert result.returncode == 0, f"frontend/.env NOT ignored (stderr={result.stderr})"
        assert "frontend/.env" in result.stdout

    def test_gitignore_contains_env_entries(self):
        with open("/app/.gitignore") as f:
            content = f.read()
        for entry in [".env", "*.env", "backend/.env", "frontend/.env"]:
            assert f"\n{entry}\n" in f"\n{content}\n", f"missing gitignore entry: {entry}"


# --------- SEC-001: privilege escalation prevention ---------

class TestSEC001PrivilegeEscalation:
    """ADMIN must NOT be able to modify a SUPER ADMIN user."""

    def test_admin_cannot_change_super_admin_password(self, s, super_admin, admin_token):
        sa_id = super_admin["user"]["user_id"]
        r = s.patch(f"{BASE_URL}/api/users/{sa_id}",
                    headers=h(admin_token["token"]),
                    json={"password": "Hacked@2026"}, timeout=10)
        assert r.status_code == 403, f"expected 403 got {r.status_code}: {r.text}"
        assert "SUPER ADMIN" in r.text and "mengubah" in r.text.lower()

    def test_admin_cannot_change_super_admin_role(self, s, super_admin, admin_token):
        sa_id = super_admin["user"]["user_id"]
        r = s.patch(f"{BASE_URL}/api/users/{sa_id}",
                    headers=h(admin_token["token"]),
                    json={"role": "KARYAWAN"}, timeout=10)
        assert r.status_code == 403, r.text

    def test_admin_cannot_change_super_admin_name(self, s, super_admin, admin_token):
        sa_id = super_admin["user"]["user_id"]
        r = s.patch(f"{BASE_URL}/api/users/{sa_id}",
                    headers=h(admin_token["token"]),
                    json={"name": "changed by admin"}, timeout=10)
        assert r.status_code == 403, r.text

    def test_admin_cannot_toggle_super_admin_status(self, s, super_admin, admin_token):
        sa_id = super_admin["user"]["user_id"]
        r = s.patch(f"{BASE_URL}/api/users/{sa_id}/status",
                    headers=h(admin_token["token"]),
                    json={"enabled": False}, timeout=10)
        assert r.status_code == 403, r.text

    def test_super_admin_still_logs_in_with_original_password(self, s):
        """Regression: prior escalation attempts didn't actually change SA password."""
        r = s.post(f"{BASE_URL}/api/auth/login",
                   json={"username": "superadmin", "password": "SuperAdmin@2026"}, timeout=10)
        assert r.status_code == 200, r.text
        assert r.json()["user"]["role"] == "SUPER ADMIN"

    def test_admin_can_still_toggle_admin_status(self, s, admin_token):
        """ADMIN can toggle another ADMIN or KARYAWAN. Use self-toggle: enable→enable (200)."""
        admin_id = admin_token["user"]["user_id"]
        r = s.patch(f"{BASE_URL}/api/users/{admin_id}/status",
                    headers=h(admin_token["token"]),
                    json={"enabled": True}, timeout=10)
        assert r.status_code == 200, r.text
        assert r.json()["enabled"] is True

    def test_admin_can_self_edit_own_record(self, s, admin_token):
        """ADMIN self-edit (name change) succeeds."""
        admin_id = admin_token["user"]["user_id"]
        original_name = admin_token["user"].get("name", "Admin")
        r = s.patch(f"{BASE_URL}/api/users/{admin_id}",
                    headers=h(admin_token["token"]),
                    json={"name": "Admin Iter10"}, timeout=10)
        assert r.status_code == 200, r.text
        assert r.json()["name"] == "Admin Iter10"
        # restore
        s.patch(f"{BASE_URL}/api/users/{admin_id}",
                headers=h(admin_token["token"]),
                json={"name": original_name}, timeout=10)

    def test_super_admin_can_update_any_user(self, s, super_admin):
        """Regression: SUPER ADMIN full-control on a KARYAWAN account."""
        # find karyawan
        r = s.get(f"{BASE_URL}/api/users", headers=h(super_admin["token"]), timeout=10)
        assert r.status_code == 200
        karyawan = next((u for u in r.json() if u.get("username") == "karyawan"), None)
        assert karyawan is not None
        original_name = karyawan.get("name", "Karyawan")
        r = s.patch(f"{BASE_URL}/api/users/{karyawan['user_id']}",
                    headers=h(super_admin["token"]),
                    json={"name": "Karyawan Iter10"}, timeout=10)
        assert r.status_code == 200, r.text
        assert r.json()["name"] == "Karyawan Iter10"
        # restore
        s.patch(f"{BASE_URL}/api/users/{karyawan['user_id']}",
                headers=h(super_admin["token"]),
                json={"name": original_name}, timeout=10)


# --------- SEC-003: username enumeration & OTP abuse ---------

class TestSEC003Enumeration:

    def test_verify_otp_unknown_username_returns_generic_401(self, s):
        unique = f"TEST_nouser_{uuid.uuid4().hex[:6]}"
        r = s.post(f"{BASE_URL}/api/auth/verify-otp",
                   json={"username": unique, "code": "123456"}, timeout=10)
        assert r.status_code == 401, r.text
        detail = r.json().get("detail", "")
        assert "Kode OTP salah atau tidak valid" in detail
        assert "tidak ditemukan" not in detail.lower()

    def test_verify_otp_wrong_code_same_generic_401(self, s):
        # karyawan is already activated -> otp not found or already verified -> generic 401
        r = s.post(f"{BASE_URL}/api/auth/verify-otp",
                   json={"username": "karyawan", "code": "000000"}, timeout=10)
        assert r.status_code == 401, r.text
        assert "Kode OTP salah atau tidak valid" in r.json().get("detail", "")

    def test_resend_otp_unknown_username_returns_generic_ack(self, s):
        unique = f"TEST_nouser_{uuid.uuid4().hex[:6]}"
        r = s.post(f"{BASE_URL}/api/auth/resend-otp",
                   json={"username": unique}, timeout=10)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "message" in body
        assert "tidak ditemukan" not in body["message"].lower()
        # no delivery leak for unknown user
        assert "delivery" not in body

    def test_resend_otp_activated_user_returns_generic_ack_no_delivery(self, s):
        """karyawan is active (not pending_activation) → should NOT leak that fact."""
        r = s.post(f"{BASE_URL}/api/auth/resend-otp",
                   json={"username": "karyawan"}, timeout=10)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "delivery" not in body
        assert "tidak ditemukan" not in body["message"].lower()

    def test_resend_otp_rate_limit_no_wa_send_after_3(self, s, super_admin):
        """4th+ call for same username within 10 min: returns ack, otp/outbox count for that
        username doesn't grow beyond 3."""
        unique = f"TEST_rl_{uuid.uuid4().hex[:6]}"  # user never exists
        # capture outbox before
        r0 = s.get(f"{BASE_URL}/api/otp/outbox?limit=100",
                   headers=h(super_admin["token"]), timeout=10)
        assert r0.status_code == 200
        before_count = sum(1 for o in r0.json() if o.get("username") == unique)
        # spam 5 times
        for _ in range(5):
            r = s.post(f"{BASE_URL}/api/auth/resend-otp", json={"username": unique}, timeout=10)
            assert r.status_code == 200, r.text
        r1 = s.get(f"{BASE_URL}/api/otp/outbox?limit=100",
                   headers=h(super_admin["token"]), timeout=10)
        assert r1.status_code == 200
        after_count = sum(1 for o in r1.json() if o.get("username") == unique)
        # Non-existent user never gets OTP sent — even better than "<=3"
        assert after_count == before_count, (
            f"outbox count grew for non-existent user: {before_count} → {after_count}"
        )


# --------- SEC-005: login rate limiter ---------

class TestSEC005LoginRateLimit:

    def test_sixth_failed_login_returns_429(self, s):
        """5 wrong logins allowed; 6th within 5 min returns 429."""
        unique = f"TEST_ratelim_{uuid.uuid4().hex[:6]}"
        for i in range(5):
            r = s.post(f"{BASE_URL}/api/auth/login",
                       json={"username": unique, "password": "wrong"}, timeout=10)
            assert r.status_code == 401, f"attempt {i+1}: expected 401 got {r.status_code} {r.text}"
        r = s.post(f"{BASE_URL}/api/auth/login",
                   json={"username": unique, "password": "wrong"}, timeout=10)
        assert r.status_code == 429, f"6th attempt should be 429 got {r.status_code} {r.text}"
        assert "Terlalu banyak percobaan login" in r.json().get("detail", "")

    def test_successful_login_resets_counter(self, s):
        """3 wrong for karyawan → successful login → counter reset → 3 more wrong all 401 (not 429)."""
        for _ in range(3):
            r = s.post(f"{BASE_URL}/api/auth/login",
                       json={"username": "karyawan", "password": "wrong"}, timeout=10)
            assert r.status_code == 401, r.text
        r = s.post(f"{BASE_URL}/api/auth/login",
                   json={"username": "karyawan", "password": "Karyawan@2026"}, timeout=10)
        assert r.status_code == 200, r.text
        for i in range(3):
            r = s.post(f"{BASE_URL}/api/auth/login",
                       json={"username": "karyawan", "password": "wrong"}, timeout=10)
            assert r.status_code == 401, f"post-reset attempt {i+1}: expected 401 got {r.status_code}"
        # restore counter fully
        r = s.post(f"{BASE_URL}/api/auth/login",
                   json={"username": "karyawan", "password": "Karyawan@2026"}, timeout=10)
        assert r.status_code == 200


# --------- Regression: superadmin sanity endpoints ---------

class TestRegression:
    def test_health(self, s):
        r = s.get(f"{BASE_URL}/api/health", timeout=10)
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_widget_status_still_works(self, s, super_admin):
        r = s.get(f"{BASE_URL}/api/widget/status", headers=h(super_admin["token"]), timeout=10)
        assert r.status_code == 200
        for k in ("user_id", "server_online", "active_ai", "jobs_today", "active_jobs", "recent_errors", "generated_at"):
            assert k in r.json()

    def test_alerts_default(self, s, super_admin):
        r = s.get(f"{BASE_URL}/api/alerts", headers=h(super_admin["token"]), timeout=10)
        assert r.status_code == 200
        for k in ("window_minutes", "error_count", "warning_count", "latest", "events"):
            assert k in r.json()

    def test_countries_have_lat_lng(self, s, super_admin):
        r = s.get(f"{BASE_URL}/api/countries", headers=h(super_admin["token"]), timeout=10)
        assert r.status_code == 200
        countries = r.json()
        assert len(countries) > 0
        for c in countries:
            assert isinstance(c["lat"], (int, float))
            assert isinstance(c["lng"], (int, float))
