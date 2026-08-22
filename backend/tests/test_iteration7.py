"""Iteration 7 backend tests: OTP + AI feed + PDF export.

Covers new endpoints:
- POST /api/users returns otp block; user pending_activation=true
- POST /api/auth/login blocked (403) for pending user
- POST /api/auth/verify-otp: happy, wrong code, expired, attempts>=5
- POST /api/auth/resend-otp + POST /api/users/{id}/otp/resend
- GET /api/otp/outbox (admin-only)
- GET /api/ai/feed with limit/since/agent_id and background emitter
- POST /api/interrogation/pdf summary/detailed; invalid mode -> 422
- Audit log has USER_CREATE (OTP dikirim), OTP_VERIFIED, OTP_RESEND, REPORT_EXPORT
"""
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

BASE_URL = (os.environ.get("EXPO_BACKEND_URL") or os.environ.get("EXPO_PUBLIC_BACKEND_URL") or "").rstrip("/")
if not BASE_URL:
    # fallback to frontend/.env
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("EXPO_PUBLIC_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().strip('"').rstrip("/")
                    break
    except Exception:
        pass
if not BASE_URL:
    pytest.skip("Preview backend URL is not configured", allow_module_level=True)


# ---------- helpers ----------
def _client(token=None):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


def _login(username, password):
    return requests.post(f"{BASE_URL}/api/auth/login", json={"username": username, "password": password}, timeout=30)


@pytest.fixture(scope="module")
def super_token():
    r = _login("superadmin", "SuperAdmin@2026")
    assert r.status_code == 200, r.text
    return r.json()["session_token"]


@pytest.fixture(scope="module")
def admin_token():
    r = _login("admin", "Admin@2026")
    assert r.status_code == 200, r.text
    return r.json()["session_token"]


@pytest.fixture(scope="module")
def karyawan_token():
    r = _login("karyawan", "Karyawan@2026")
    assert r.status_code == 200, r.text
    return r.json()["session_token"]


def _make_user_payload():
    sfx = uuid.uuid4().hex[:6]
    return {
        "name": "TEST OTP user",
        "username": f"otp_{sfx}",
        "email": f"otp_{sfx}@example.com",
        "whatsapp": "+628110000999",
        "password": "TestPass@2026",
        "role": "KARYAWAN",
    }


# Track created users for cleanup (module scope)
_created_users = []


@pytest.fixture(scope="module")
def pending_user(super_token):
    """Create one pending user shared across the OTP lifecycle tests."""
    payload = _make_user_payload()
    r = _client(super_token).post(f"{BASE_URL}/api/users", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    _created_users.append(body["user"]["user_id"])
    yield {
        "username": payload["username"],
        "password": payload["password"],
        "user_id": body["user"]["user_id"],
        "code": body["otp"]["code"],
        "otp": body["otp"],
        "user": body["user"],
    }


@pytest.fixture(scope="module", autouse=True)
def _cleanup(super_token):
    yield
    c = _client(super_token)
    for uid in _created_users:
        try:
            c.delete(f"{BASE_URL}/api/users/{uid}", timeout=15)
        except Exception:
            pass


# ---------- OTP creation + login blocked ----------
class TestOtpCreationAndBlockedLogin:
    def test_create_returns_otp_code_and_pending(self, pending_user):
        assert pending_user["user"]["pending_activation"] is True
        assert pending_user["otp"].get("provider") == "mock"
        assert pending_user["code"] and pending_user["code"].isdigit()
        assert len(pending_user["code"]) == 6

    def test_outbox_has_new_message(self, super_token, pending_user):
        r = _client(super_token).get(f"{BASE_URL}/api/otp/outbox", timeout=15)
        assert r.status_code == 200
        outbox = r.json()
        assert isinstance(outbox, list) and len(outbox) >= 1
        assert "message" in outbox[0] and "created_at" in outbox[0]
        if len(outbox) > 1:
            assert outbox[0]["created_at"] >= outbox[1]["created_at"]

    def test_karyawan_blocked_on_outbox(self, karyawan_token):
        r = _client(karyawan_token).get(f"{BASE_URL}/api/otp/outbox", timeout=15)
        assert r.status_code == 403

    def test_pending_user_cannot_login(self, pending_user):
        r = _login(pending_user["username"], pending_user["password"])
        assert r.status_code == 403
        detail = (r.json() or {}).get("detail", "")
        assert "aktivasi" in detail.lower() or "otp" in detail.lower()


# ---------- OTP verify: wrong code + attempts + happy ----------
class TestOtpVerify:
    def test_wrong_code_and_lockout_and_resend_and_verify(self, super_token, pending_user):
        username = pending_user["username"]
        # 5 wrong attempts (attempts increments from 0 -> 5; each returns 401)
        for i in range(5):
            r = requests.post(f"{BASE_URL}/api/auth/verify-otp",
                              json={"username": username, "code": "000000"}, timeout=15)
            assert r.status_code == 401, f"attempt {i}: {r.status_code} {r.text}"
        # 6th call: attempts now = 5, next check hits >=5 => 429
        r6 = requests.post(f"{BASE_URL}/api/auth/verify-otp",
                           json={"username": username, "code": "000000"}, timeout=15)
        assert r6.status_code == 429

        # Admin-side resend (resets attempts by re-issuing OTP)
        rr = _client(super_token).post(
            f"{BASE_URL}/api/users/{pending_user['user_id']}/otp/resend", timeout=15)
        assert rr.status_code == 200, rr.text
        code = rr.json()["delivery"]["code"]
        assert code and code.isdigit()

        # Verify with the correct code
        v = requests.post(f"{BASE_URL}/api/auth/verify-otp",
                          json={"username": username, "code": code}, timeout=15)
        assert v.status_code == 200, v.text
        assert "session_token" in v.json()
        assert v.json()["user"]["pending_activation"] is False

    def test_login_works_after_activation(self, pending_user):
        r = _login(pending_user["username"], pending_user["password"])
        assert r.status_code == 200

    def test_admin_resend_after_active_returns_400(self, super_token, pending_user):
        r = _client(super_token).post(
            f"{BASE_URL}/api/users/{pending_user['user_id']}/otp/resend", timeout=15)
        assert r.status_code == 400


# ---------- public resend endpoint ----------
class TestPublicResendOtp:
    def test_resend_for_active_returns_generic_ack(self, pending_user):
        """SEC-003: resend-otp for any username (even active) returns 200 with generic ack to
        avoid username enumeration. Previously returned 400 — updated for iteration 10 fix."""
        r = requests.post(f"{BASE_URL}/api/auth/resend-otp",
                          json={"username": pending_user["username"]}, timeout=15)
        assert r.status_code == 200
        assert "message" in r.json()

    def test_resend_for_pending_generates_new_otp(self, super_token):
        # Create a new pending user
        payload = _make_user_payload()
        r = _client(super_token).post(f"{BASE_URL}/api/users", json=payload, timeout=15)
        assert r.status_code == 200
        uid = r.json()["user"]["user_id"]
        _created_users.append(uid)
        first = r.json()["otp"]["code"]
        # Public resend
        r2 = requests.post(f"{BASE_URL}/api/auth/resend-otp",
                           json={"username": payload["username"]}, timeout=15)
        assert r2.status_code == 200, r2.text
        second = r2.json()["delivery"]["code"]
        assert second and second != first  # cryptographically very unlikely to match


# ---------- karyawan RBAC on admin resend ----------
class TestKaryawanRbac:
    def test_karyawan_cannot_admin_resend(self, karyawan_token, super_token):
        payload = _make_user_payload()
        r = _client(super_token).post(f"{BASE_URL}/api/users", json=payload, timeout=15)
        uid = r.json()["user"]["user_id"]
        _created_users.append(uid)
        r2 = _client(karyawan_token).post(f"{BASE_URL}/api/users/{uid}/otp/resend", timeout=15)
        assert r2.status_code == 403


# ---------- Expired OTP ----------
class TestExpiredOtp:
    def test_expired_otp_returns_400(self, super_token):
        # Create user, then update expires_at to past via Mongo
        payload = _make_user_payload()
        r = _client(super_token).post(f"{BASE_URL}/api/users", json=payload, timeout=15)
        assert r.status_code == 200
        uid = r.json()["user"]["user_id"]
        code = r.json()["otp"]["code"]
        _created_users.append(uid)

        # Manipulate DB directly to expire OTP
        mongo_url = os.environ.get("MONGO_URL")
        db_name = os.environ.get("DB_NAME")
        if not mongo_url or not db_name:
            # Read from backend/.env
            with open("/app/backend/.env") as f:
                for line in f:
                    if line.startswith("MONGO_URL="):
                        mongo_url = line.split("=", 1)[1].strip().strip('"')
                    elif line.startswith("DB_NAME="):
                        db_name = line.split("=", 1)[1].strip().strip('"')

        async def _expire():
            cli = AsyncIOMotorClient(mongo_url)
            d = cli[db_name]
            await d.otps.update_one(
                {"user_id": uid, "purpose": "activation"},
                {"$set": {"expires_at": datetime.now(timezone.utc) - timedelta(minutes=5)}}
            )
            cli.close()

        asyncio.get_event_loop().run_until_complete(_expire())

        v = requests.post(f"{BASE_URL}/api/auth/verify-otp",
                          json={"username": payload["username"], "code": code}, timeout=15)
        assert v.status_code == 400
        assert "kedaluwarsa" in v.json().get("detail", "").lower()


# ---------- AI feed ----------
class TestAiFeed:
    def test_feed_returns_events_with_query_params(self, super_token):
        c = _client(super_token)
        # Ensure server on & at least one AI enabled
        c.post(f"{BASE_URL}/api/server/action", json={"action": "on"}, timeout=15)
        c.post(f"{BASE_URL}/api/ai/bulk", json={"enabled": True}, timeout=15)
        # Wait for generator to emit at least a few events
        time.sleep(8)
        r = c.get(f"{BASE_URL}/api/ai/feed?limit=20", timeout=15)
        assert r.status_code == 200
        events = r.json()
        assert isinstance(events, list)
        assert len(events) >= 1, "expected at least 1 feed event within 8s"
        # shape
        e = events[-1]
        for key in ("event_id", "agent_id", "agent_name", "level", "message", "created_at"):
            assert key in e
        # since filter: use most recent ts; api uses $gt on strings.
        # Use the latest returned event; nothing should come at or before it.
        cutoff = events[-1]["created_at"]
        r2 = c.get(f"{BASE_URL}/api/ai/feed?since={cutoff}", timeout=15)
        assert r2.status_code == 200
        for ev in r2.json():
            assert ev["created_at"] >= cutoff
        # agent_id filter
        aid = events[-1]["agent_id"]
        r3 = c.get(f"{BASE_URL}/api/ai/feed?agent_id={aid}", timeout=15)
        assert r3.status_code == 200
        assert all(ev["agent_id"] == aid for ev in r3.json())

    def test_feed_stops_when_all_ai_off(self, super_token):
        c = _client(super_token)
        c.post(f"{BASE_URL}/api/ai/bulk", json={"enabled": False}, timeout=15)
        time.sleep(2)  # let any inflight event flush
        before = len(c.get(f"{BASE_URL}/api/ai/feed?limit=200", timeout=15).json())
        time.sleep(8)
        after = len(c.get(f"{BASE_URL}/api/ai/feed?limit=200", timeout=15).json())
        # Should not have grown (or at most by 1 due to timing race)
        assert after - before <= 1, f"feed still emitting after AI off: before={before}, after={after}"
        # Restore
        c.post(f"{BASE_URL}/api/ai/bulk", json={"enabled": True}, timeout=15)


# ---------- Interrogation PDF ----------
class TestInterrogationPdf:
    def test_summary_pdf_returned(self, super_token):
        r = _client(super_token).post(f"{BASE_URL}/api/interrogation/pdf?mode=summary", timeout=30)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd.lower() and ".pdf" in cd.lower()
        assert r.content[:5] == b"%PDF-"
        assert len(r.content) > 1000
        TestInterrogationPdf.summary_size = len(r.content)

    def test_detailed_pdf_larger(self, super_token):
        r = _client(super_token).post(f"{BASE_URL}/api/interrogation/pdf?mode=detailed", timeout=30)
        assert r.status_code == 200
        assert r.content[:5] == b"%PDF-"
        assert len(r.content) > 1000
        # detailed should generally be >= summary (extra audit page); allow equality just in case
        assert len(r.content) >= TestInterrogationPdf.summary_size

    def test_invalid_mode_422(self, super_token):
        r = _client(super_token).post(f"{BASE_URL}/api/interrogation/pdf?mode=bogus", timeout=15)
        assert r.status_code == 422


# ---------- Audit log ----------
class TestAuditLog:
    def test_audit_contains_new_actions(self, super_token):
        r = _client(super_token).get(f"{BASE_URL}/api/activity", timeout=15)
        assert r.status_code == 200
        logs = r.json()
        actions = {l["action"] for l in logs}
        assert "USER_CREATE" in actions
        assert "OTP_VERIFIED" in actions
        assert "OTP_RESEND" in actions
        assert "REPORT_EXPORT" in actions
        # USER_CREATE detail should mention OTP dikirim
        uc = next((l for l in logs if l["action"] == "USER_CREATE"), None)
        assert uc and "otp" in uc["detail"].lower()
