"""Iteration 9 backend tests: WorldMap (countries lat/lng), Alerts, WidgetStatus.

Covers:
- GET /api/countries now includes lat/lng floats; sync idempotency preserves enabled flag.
- GET /api/alerts default minutes=5, minutes=60 ok, minutes=0 or >60 -> 422.
- Alerts response shape and only error/warning levels.
- Background feed generator emits error/warning events (given ~30s).
- GET /api/widget/status returns required keys with correct types.
- Auth: /api/alerts and /api/widget/status require bearer token (401).
"""
from __future__ import annotations

import os
import time

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


# ---------- Countries: lat/lng + idempotency ----------
class TestCountriesLatLng:
    def test_countries_include_lat_lng_floats(self, super_token):
        r = _client(super_token).get(f"{BASE_URL}/api/countries", timeout=15)
        assert r.status_code == 200, r.text
        rows = r.json()
        assert isinstance(rows, list) and len(rows) >= 5
        for row in rows:
            assert "lat" in row and "lng" in row, row
            assert isinstance(row["lat"], (int, float)), row
            assert isinstance(row["lng"], (int, float)), row
            assert -90.0 <= float(row["lat"]) <= 90.0
            assert -180.0 <= float(row["lng"]) <= 180.0

    def test_countries_idempotent_enabled_flag(self, super_token):
        # Toggle a specific country, then re-GET; enabled flag must persist
        # (indirect check: seed sync should NOT reset toggled state on subsequent GETs).
        c = _client(super_token)
        first = c.get(f"{BASE_URL}/api/countries", timeout=15).json()
        target = next((x for x in first if x["code"] not in {"ID"}), None)
        assert target is not None
        code = target["code"]
        original = bool(target["enabled"])
        try:
            r = c.patch(
                f"{BASE_URL}/api/countries/{code}",
                json={"enabled": not original},
                timeout=15,
            )
            assert r.status_code == 200, r.text
            # Re-fetch and confirm
            after = c.get(f"{BASE_URL}/api/countries", timeout=15).json()
            toggled = next(x for x in after if x["code"] == code)
            assert toggled["enabled"] is (not original)
        finally:
            # restore
            c.patch(
                f"{BASE_URL}/api/countries/{code}",
                json={"enabled": original},
                timeout=15,
            )


# ---------- Alerts ----------
class TestAlerts:
    def test_alerts_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/alerts", timeout=15)
        assert r.status_code == 401

    def test_alerts_default_shape(self, super_token):
        r = _client(super_token).get(f"{BASE_URL}/api/alerts", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["window_minutes"] == 5
        for key in ("window_minutes", "error_count", "warning_count", "latest", "events"):
            assert key in body, body
        assert isinstance(body["error_count"], int)
        assert isinstance(body["warning_count"], int)
        assert isinstance(body["events"], list)
        assert len(body["events"]) <= 10
        for ev in body["events"]:
            assert ev["level"] in {"error", "warning"}, ev

    def test_alerts_minutes_60(self, super_token):
        r = _client(super_token).get(f"{BASE_URL}/api/alerts?minutes=60", timeout=15)
        assert r.status_code == 200
        assert r.json()["window_minutes"] == 60

    def test_alerts_minutes_0_invalid(self, super_token):
        r = _client(super_token).get(f"{BASE_URL}/api/alerts?minutes=0", timeout=15)
        assert r.status_code == 422

    def test_alerts_minutes_too_large_invalid(self, super_token):
        r = _client(super_token).get(f"{BASE_URL}/api/alerts?minutes=61", timeout=15)
        assert r.status_code == 422

    def test_feed_generator_emits_error_or_warning(self, super_token):
        """Wait up to ~35s for background feed generator to emit at least one error/warning."""
        c = _client(super_token)
        deadline = time.time() + 40
        seen = 0
        while time.time() < deadline:
            body = c.get(f"{BASE_URL}/api/alerts?minutes=5", timeout=15).json()
            seen = body["error_count"] + body["warning_count"]
            if seen > 0:
                break
            time.sleep(4)
        assert seen > 0, "Expected at least one error/warning event within 40s"


# ---------- Widget Status ----------
class TestWidgetStatus:
    def test_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/widget/status", timeout=15)
        assert r.status_code == 401

    def test_widget_status_shape(self, super_token):
        r = _client(super_token).get(f"{BASE_URL}/api/widget/status", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        for key in (
            "user_id",
            "server_online",
            "active_ai",
            "jobs_today",
            "active_jobs",
            "recent_errors",
            "generated_at",
        ):
            assert key in body, body
        assert isinstance(body["server_online"], bool)
        assert isinstance(body["active_ai"], str)
        # active_ai format like 'N/7'
        assert body["active_ai"].endswith("/7")
        assert isinstance(body["jobs_today"], dict)
        assert "successful" in body["jobs_today"]
        assert "failed" in body["jobs_today"]
        assert isinstance(body["jobs_today"]["successful"], int)
        assert isinstance(body["jobs_today"]["failed"], int)
        assert isinstance(body["active_jobs"], int)
        assert isinstance(body["recent_errors"], int)
        assert isinstance(body["generated_at"], str) and len(body["generated_at"]) > 10
