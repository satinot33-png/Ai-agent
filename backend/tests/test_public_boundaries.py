"""Regression checks for health, auth boundaries, and invalid OAuth exchange."""
import os

import pytest
import requests


BASE_URL = os.environ.get("EXPO_BACKEND_URL") or os.environ.get("EXPO_PUBLIC_BACKEND_URL")
if not BASE_URL:
    pytest.skip("Preview backend URL is not configured", allow_module_level=True)
BASE_URL = BASE_URL.rstrip("/")


@pytest.fixture
def api_client():
    return requests.Session()


def test_health(api_client):
    response = api_client.get(f"{BASE_URL}/api/health", timeout=20)
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "export7ai"}


@pytest.mark.parametrize("method,path", [
    ("get", "/api/dashboard"),
    ("get", "/api/ai"),
    ("get", "/api/countries"),
    ("get", "/api/server"),
    ("post", "/api/interrogation"),
    ("get", "/api/auth/me"),
])
def test_protected_endpoints_reject_missing_token(api_client, method, path):
    response = getattr(api_client, method)(f"{BASE_URL}{path}", timeout=20)
    assert response.status_code == 401
    assert response.json()["detail"]


def test_invalid_oauth_session_rejected(api_client):
    response = api_client.post(
        f"{BASE_URL}/api/auth/session",
        json={"session_id": "TEST_invalid_session"},
        timeout=20,
    )
    assert response.status_code == 401
    assert response.json()["detail"]