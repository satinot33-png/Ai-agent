"""Iteration 8 backend tests: Job Trend Chart + Email Recipients + Email Report.

Covers:
- GET /api/dashboard now includes job_stats array (7 items).
- GET /api/stats/jobs?days=N validations and ordering.
- Idempotency of job_stats seed (count stays 7).
- POST/GET/DELETE /api/settings/recipients per-user isolation & guardrails.
- POST /api/interrogation/email summary + detailed via Resend sandbox (delivered@resend.dev).
- Audit log entry REPORT_EMAIL exists after send.
- Guardrails: cross-user recipient => 404; invalid mode => 422.
"""
from __future__ import annotations

import os
import uuid

import pytest
import requests

BASE_URL = (
    os.environ.get("EXPO_BACKEND_URL")
    or os.environ.get("EXPO_PUBLIC_BACKEND_URL")
    or ""
).rstrip("/")
if not BASE_URL:
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
    return requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": username, "password": password},
        timeout=30,
    )


@pytest.fixture(scope="module")
def super_token():
    r = _login("superadmin", "SuperAdmin@2026")
    assert r.status_code == 200, r.text
    return r.json()["session_token"]


@pytest.fixture(scope="module")
def karyawan_token():
    r = _login("karyawan", "Karyawan@2026")
    assert r.status_code == 200, r.text
    return r.json()["session_token"]


# Track created recipient IDs per-token for cleanup
_recipients: dict[str, list[str]] = {"super": [], "karyawan": []}


@pytest.fixture(scope="module", autouse=True)
def _cleanup(super_token, karyawan_token):
    yield
    sc = _client(super_token)
    kc = _client(karyawan_token)
    for rid in list(_recipients["super"]):
        try:
            sc.delete(f"{BASE_URL}/api/settings/recipients/{rid}", timeout=15)
        except Exception:
            pass
    for rid in list(_recipients["karyawan"]):
        try:
            kc.delete(f"{BASE_URL}/api/settings/recipients/{rid}", timeout=15)
        except Exception:
            pass


# ---------- Job Trend Chart ----------
class TestJobStats:
    def test_dashboard_returns_job_stats_7_items(self, super_token):
        r = _client(super_token).get(f"{BASE_URL}/api/dashboard", timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert "job_stats" in data
        stats = data["job_stats"]
        assert isinstance(stats, list)
        assert len(stats) == 7, f"expected 7 items, got {len(stats)}"
        keys = {"date", "successful", "failed", "active"}
        for row in stats:
            assert keys.issubset(row.keys()), row
            assert isinstance(row["successful"], int)
            assert isinstance(row["failed"], int)
            assert isinstance(row["active"], int)
        # ascending by date
        dates = [r["date"] for r in stats]
        assert dates == sorted(dates)

    def test_stats_jobs_default_7(self, super_token):
        r = _client(super_token).get(f"{BASE_URL}/api/stats/jobs?days=7", timeout=15)
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) == 7
        dates = [x["date"] for x in rows]
        assert dates == sorted(dates), f"expected ascending, got {dates}"

    def test_stats_jobs_days_3(self, super_token):
        r = _client(super_token).get(f"{BASE_URL}/api/stats/jobs?days=3", timeout=15)
        assert r.status_code == 200
        assert len(r.json()) == 3

    def test_stats_jobs_invalid_days(self, super_token):
        r0 = _client(super_token).get(f"{BASE_URL}/api/stats/jobs?days=0", timeout=15)
        assert r0.status_code == 422
        r31 = _client(super_token).get(f"{BASE_URL}/api/stats/jobs?days=31", timeout=15)
        assert r31.status_code == 422

    def test_stats_jobs_idempotent_count(self, super_token):
        """Reading the endpoint many times must not grow the seed count."""
        first = _client(super_token).get(f"{BASE_URL}/api/stats/jobs?days=30", timeout=15).json()
        for _ in range(3):
            _client(super_token).get(f"{BASE_URL}/api/dashboard", timeout=15)
        second = _client(super_token).get(f"{BASE_URL}/api/stats/jobs?days=30", timeout=15).json()
        assert len(first) == len(second), (
            f"job_stats grew from {len(first)} to {len(second)} (seed not idempotent)"
        )


# ---------- Recipients ----------
class TestRecipients:
    def test_create_recipient_shape(self, super_token):
        sfx = uuid.uuid4().hex[:6]
        payload = {"name": "TEST Ops", "email": f"test_ops_{sfx}@example.com", "note": "TEST"}
        r = _client(super_token).post(
            f"{BASE_URL}/api/settings/recipients", json=payload, timeout=15
        )
        assert r.status_code == 200, r.text  # endpoint returns 200 with body
        body = r.json()
        for key in ("recipient_id", "name", "email", "created_at"):
            assert key in body, body
        assert body["email"] == payload["email"]
        assert body["name"] == "TEST Ops"
        _recipients["super"].append(body["recipient_id"])

    def test_name_too_short_422(self, super_token):
        r = _client(super_token).post(
            f"{BASE_URL}/api/settings/recipients",
            json={"name": "A", "email": "a@b.com"},
            timeout=15,
        )
        assert r.status_code == 422

    def test_invalid_email_422(self, super_token):
        r = _client(super_token).post(
            f"{BASE_URL}/api/settings/recipients",
            json={"name": "OK Name", "email": "not-an-email"},
            timeout=15,
        )
        assert r.status_code == 422

    def test_duplicate_email_409(self, super_token):
        sfx = uuid.uuid4().hex[:6]
        payload = {"name": "TEST Dup", "email": f"test_dup_{sfx}@example.com"}
        r1 = _client(super_token).post(
            f"{BASE_URL}/api/settings/recipients", json=payload, timeout=15
        )
        assert r1.status_code == 200
        _recipients["super"].append(r1.json()["recipient_id"])
        r2 = _client(super_token).post(
            f"{BASE_URL}/api/settings/recipients", json=payload, timeout=15
        )
        assert r2.status_code == 409

    def test_list_only_own(self, super_token, karyawan_token):
        # Create as super
        sfx = uuid.uuid4().hex[:6]
        r = _client(super_token).post(
            f"{BASE_URL}/api/settings/recipients",
            json={"name": "TEST Owner", "email": f"test_owner_{sfx}@example.com"},
            timeout=15,
        )
        assert r.status_code == 200
        super_rid = r.json()["recipient_id"]
        _recipients["super"].append(super_rid)

        # Karyawan should not see it
        r2 = _client(karyawan_token).get(f"{BASE_URL}/api/settings/recipients", timeout=15)
        assert r2.status_code == 200
        emails = [x["email"] for x in r2.json()]
        assert f"test_owner_{sfx}@example.com" not in emails

    def test_delete_wrong_owner_404(self, super_token, karyawan_token):
        # Karyawan creates own recipient
        sfx = uuid.uuid4().hex[:6]
        rk = _client(karyawan_token).post(
            f"{BASE_URL}/api/settings/recipients",
            json={"name": "TEST Kary", "email": f"test_kary_{sfx}@example.com"},
            timeout=15,
        )
        assert rk.status_code == 200
        kary_rid = rk.json()["recipient_id"]
        _recipients["karyawan"].append(kary_rid)

        # Super tries to delete karyawan's recipient
        rdel = _client(super_token).delete(
            f"{BASE_URL}/api/settings/recipients/{kary_rid}", timeout=15
        )
        assert rdel.status_code == 404


# ---------- Email interrogation via Resend sandbox ----------
class TestEmailInterrogation:
    @pytest.fixture(scope="class")
    def super_recipient_id(self, super_token):
        sfx = uuid.uuid4().hex[:6]
        r = _client(super_token).post(
            f"{BASE_URL}/api/settings/recipients",
            json={
                "name": "TEST Resend Sandbox",
                "email": "delivered@resend.dev",
                "note": "TEST",
            },
            timeout=15,
        )
        # Might 409 if a prior test used the same email in this super_token session — accept both.
        if r.status_code == 409:
            listed = _client(super_token).get(
                f"{BASE_URL}/api/settings/recipients", timeout=15
            ).json()
            rid = next(x["recipient_id"] for x in listed if x["email"] == "delivered@resend.dev")
        else:
            assert r.status_code == 200, r.text
            rid = r.json()["recipient_id"]
        _recipients["super"].append(rid)
        return rid

    def test_email_summary_delivered(self, super_token, super_recipient_id):
        r = _client(super_token).post(
            f"{BASE_URL}/api/interrogation/email",
            json={"recipient_id": super_recipient_id, "mode": "summary", "note": "TEST"},
            timeout=45,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "sent"
        assert body["recipient"] == "delivered@resend.dev"
        assert body["recipient_name"]
        assert "subject" in body
        # message_id may be None if proxy doesn't return one — allow both.

    def test_email_detailed_and_audit(self, super_token, super_recipient_id):
        r = _client(super_token).post(
            f"{BASE_URL}/api/interrogation/email",
            json={"recipient_id": super_recipient_id, "mode": "detailed"},
            timeout=45,
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "sent"
        # Audit log has REPORT_EMAIL mentioning the recipient email
        ract = _client(super_token).get(f"{BASE_URL}/api/activity", timeout=15)
        assert ract.status_code == 200
        rows = ract.json()
        report_email_rows = [row for row in rows if row.get("action") == "REPORT_EMAIL"]
        assert report_email_rows, "no REPORT_EMAIL audit log entry"
        assert any(
            "delivered@resend.dev" in row.get("detail", "") for row in report_email_rows
        )

    def test_invalid_mode_422(self, super_token, super_recipient_id):
        r = _client(super_token).post(
            f"{BASE_URL}/api/interrogation/email",
            json={"recipient_id": super_recipient_id, "mode": "bogus"},
            timeout=15,
        )
        assert r.status_code == 422

    def test_cross_user_recipient_404(self, super_token, karyawan_token):
        # Karyawan creates own recipient
        sfx = uuid.uuid4().hex[:6]
        rk = _client(karyawan_token).post(
            f"{BASE_URL}/api/settings/recipients",
            json={"name": "TEST Cross", "email": f"test_cross_{sfx}@example.com"},
            timeout=15,
        )
        assert rk.status_code == 200
        kary_rid = rk.json()["recipient_id"]
        _recipients["karyawan"].append(kary_rid)

        # Super tries to send using karyawan's recipient
        rmail = _client(super_token).post(
            f"{BASE_URL}/api/interrogation/email",
            json={"recipient_id": kary_rid, "mode": "summary"},
            timeout=15,
        )
        assert rmail.status_code == 404
