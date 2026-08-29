"""Iteration 11 — Role normalization + permission matrix + last-super-admin guard.

Runs against the live preview backend using EXPO_BACKEND_URL.
"""
import os
import time
import uuid
import asyncio

import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient

BASE_URL = os.environ.get("EXPO_BACKEND_URL", "https://ai-management-hub-8.preview.emergentagent.com").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

SUPER = ("superadmin", "SuperAdmin@2026")
ADMIN = ("admin", "Admin@2026")
KARY = ("karyawan", "Karyawan@2026")

CANONICAL = {"SUPER ADMIN", "ADMIN", "KARYAWAN"}


# ---------- shared helpers ----------
def _login(username: str, password: str) -> str:
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": username, "password": password}, timeout=15)
    assert r.status_code == 200, f"login {username} failed: {r.status_code} {r.text}"
    return r.json()["session_token"]


def _auth(tok: str):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def super_token():
    return _login(*SUPER)


@pytest.fixture(scope="module")
def admin_token():
    return _login(*ADMIN)


@pytest.fixture(scope="module")
def kary_token():
    return _login(*KARY)


# ---------- 1. Role normalization on /auth/me + /users ----------
class TestRoleNormalization:
    @pytest.mark.parametrize("legacy_value", ["super_admin", "Super Admin", "SUPER_ADMIN", "super-admin"])
    def test_me_returns_canonical_for_legacy_super_admin(self, legacy_value):
        async def _flow():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            # snapshot original
            orig = await db.users.find_one({"username": "superadmin"}, {"role": 1})
            assert orig, "superadmin seed missing"
            try:
                await db.users.update_one({"username": "superadmin"}, {"$set": {"role": legacy_value}})
                # login (should still work because login doesn't check role text)
                tok = _login(*SUPER)
                r = requests.get(f"{BASE_URL}/api/auth/me", headers=_auth(tok), timeout=15)
                assert r.status_code == 200, r.text
                body = r.json()
                assert body["role"] == "SUPER ADMIN", f"expected canonical, got {body['role']!r}"
                # permissions must still be full super
                assert body["permissions"]["manage_users"] is True
                assert body["permissions"]["assign_super_admin"] is True
            finally:
                await db.users.update_one({"username": "superadmin"}, {"$set": {"role": "SUPER ADMIN"}})
                client.close()

        asyncio.get_event_loop().run_until_complete(_flow()) if False else asyncio.run(_flow())

    @pytest.mark.parametrize("legacy_value,expected", [
        ("operator", "ADMIN"),
        ("staff", "KARYAWAN"),
        ("user", "KARYAWAN"),
    ])
    def test_users_list_normalizes_aliases(self, legacy_value, expected, super_token):
        """Set karyawan seed to a legacy alias, hit GET /users, expect canonical role in list."""
        async def _flow():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            orig = await db.users.find_one({"username": "karyawan"}, {"role": 1})
            try:
                await db.users.update_one({"username": "karyawan"}, {"$set": {"role": legacy_value}})
                r = requests.get(f"{BASE_URL}/api/users", headers=_auth(super_token), timeout=15)
                assert r.status_code == 200, r.text
                rows = r.json()
                kary_row = next((u for u in rows if u.get("name", "").lower().startswith("karyawan")), None)
                assert kary_row, "karyawan not in list"
                assert kary_row["role"] == expected
                assert "permissions" in kary_row and isinstance(kary_row["permissions"], dict)
                # ADMIN → manage_users True; KARYAWAN → False
                assert kary_row["permissions"]["manage_users"] is (expected == "ADMIN")
                assert kary_row["permissions"]["assign_super_admin"] is False
            finally:
                await db.users.update_one({"username": "karyawan"}, {"$set": {"role": orig["role"] if orig else "KARYAWAN"}})
                client.close()

        asyncio.run(_flow())


# ---------- 2. Permission matrix on /auth/me ----------
class TestPermissionMatrix:
    EXPECTED_KEYS = {"manage_users", "manage_ai", "manage_countries", "control_server",
                     "view_activity", "send_reports", "assign_super_admin"}

    def test_super_admin_full_perms(self, super_token):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=_auth(super_token), timeout=15)
        assert r.status_code == 200
        p = r.json()["permissions"]
        assert set(p.keys()) == self.EXPECTED_KEYS
        assert all(p[k] is True for k in self.EXPECTED_KEYS)

    def test_admin_perms(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=_auth(admin_token), timeout=15)
        p = r.json()["permissions"]
        assert p["manage_users"] is True
        assert p["manage_ai"] is True
        assert p["manage_countries"] is True
        assert p["control_server"] is True
        assert p["view_activity"] is True
        assert p["send_reports"] is True
        assert p["assign_super_admin"] is False

    def test_karyawan_perms(self, kary_token):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=_auth(kary_token), timeout=15)
        p = r.json()["permissions"]
        assert p["manage_users"] is False
        assert p["manage_ai"] is False
        assert p["manage_countries"] is False
        assert p["control_server"] is False
        assert p["assign_super_admin"] is False
        assert p["view_activity"] is True
        assert p["send_reports"] is True


# ---------- 3. GET /permissions ----------
class TestPermissionsEndpoint:
    def test_open_to_all_authed_users(self, kary_token, admin_token, super_token):
        for tok in [kary_token, admin_token, super_token]:
            r = requests.get(f"{BASE_URL}/api/permissions", headers=_auth(tok), timeout=15)
            assert r.status_code == 200, r.text
            body = r.json()
            assert "roles" in body and "permissions" in body and "current" in body
            assert set(body["roles"]) == CANONICAL
            assert set(body["permissions"].keys()) == CANONICAL

    def test_unauthed_rejected(self):
        r = requests.get(f"{BASE_URL}/api/permissions", timeout=15)
        assert r.status_code in (401, 403)


# ---------- 4. GET /users authorization ----------
class TestUsersListAuth:
    def test_karyawan_forbidden(self, kary_token):
        r = requests.get(f"{BASE_URL}/api/users", headers=_auth(kary_token), timeout=15)
        assert r.status_code == 403

    def test_admin_can_read(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/users", headers=_auth(admin_token), timeout=15)
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list) and rows
        for u in rows:
            assert u["role"] in CANONICAL
            assert "permissions" in u


# ---------- 5. POST /users role normalisation + assign_super_admin gating ----------
class TestUserCreateRoleNormalisation:
    def _cleanup(self, user_id, token):
        try:
            requests.delete(f"{BASE_URL}/api/users/{user_id}", headers=_auth(token), timeout=15)
        except Exception:
            pass

    def test_super_can_create_super_admin_with_lowercase_role(self, super_token):
        uname = f"iter11a_{uuid.uuid4().hex[:6]}"
        payload = {
            "name": "TEST role-norm super",
            "username": uname,
            "email": f"{uname}@example.com",
            "whatsapp": "+6281111111111",
            "password": "Passw0rd!X",
            "role": "super_admin",
        }
        r = requests.post(f"{BASE_URL}/api/users", headers=_auth(super_token), json=payload, timeout=20)
        assert r.status_code in (200, 201), r.text
        body = r.json()
        user = body.get("user", body)
        assert user["role"] == "SUPER ADMIN"
        self._cleanup(user["user_id"], super_token)

    def test_admin_cannot_create_super_admin(self, admin_token):
        uname = f"iter11b_{uuid.uuid4().hex[:6]}"
        payload = {
            "name": "TEST admin creating super",
            "username": uname,
            "email": f"{uname}@example.com",
            "whatsapp": "+6281111111112",
            "password": "Passw0rd!X",
            "role": "SUPER_ADMIN",
        }
        r = requests.post(f"{BASE_URL}/api/users", headers=_auth(admin_token), json=payload, timeout=15)
        assert r.status_code == 403, r.text

    def test_karyawan_cannot_create(self, kary_token):
        uname = f"iter11c_{uuid.uuid4().hex[:6]}"
        r = requests.post(f"{BASE_URL}/api/users", headers=_auth(kary_token), json={
            "name": "n", "username": uname, "email": f"{uname}@example.com",
            "whatsapp": "+6281111111113", "password": "Passw0rd!X", "role": "karyawan",
        }, timeout=15)
        assert r.status_code == 403


# ---------- 6. PATCH /users/{id} role lowercase normalisation ----------
class TestUserUpdateRoleNormalisation:
    def test_patch_role_lowercase_saved_as_canonical(self, super_token):
        uname = f"iter11d_{uuid.uuid4().hex[:6]}"
        create = requests.post(f"{BASE_URL}/api/users", headers=_auth(super_token), json={
            "name": "TEST patch role", "username": uname, "email": f"{uname}@example.com",
            "whatsapp": "+6281111111114", "password": "Passw0rd!X", "role": "admin",
        }, timeout=20)
        assert create.status_code in (200, 201), create.text
        target = create.json().get("user", create.json())
        uid = target["user_id"]
        try:
            r = requests.patch(f"{BASE_URL}/api/users/{uid}", headers=_auth(super_token),
                               json={"role": "karyawan"}, timeout=15)
            assert r.status_code == 200, r.text
            assert r.json()["role"] == "KARYAWAN"
            # verify via GET /users
            g = requests.get(f"{BASE_URL}/api/users", headers=_auth(super_token), timeout=15)
            row = next(u for u in g.json() if u["user_id"] == uid)
            assert row["role"] == "KARYAWAN"
        finally:
            requests.delete(f"{BASE_URL}/api/users/{uid}", headers=_auth(super_token), timeout=15)


# ---------- 7. iter-10 regression: ADMIN cannot patch SUPER ADMIN ----------
class TestIter10Regression:
    def test_admin_cannot_patch_super(self, admin_token, super_token):
        me = requests.get(f"{BASE_URL}/api/auth/me", headers=_auth(super_token), timeout=15).json()
        r = requests.patch(f"{BASE_URL}/api/users/{me['user_id']}", headers=_auth(admin_token),
                           json={"name": "hacked"}, timeout=15)
        assert r.status_code == 403


# ---------- 8. Last-super-admin guard ----------
class TestLastSuperAdminGuard:
    def test_cannot_disable_or_demote_last_super_admin_then_second_super_lifts_guard(self, super_token):
        me = requests.get(f"{BASE_URL}/api/auth/me", headers=_auth(super_token), timeout=15).json()
        uid = me["user_id"]

        # Confirm only one active super admin currently exists.
        rows = requests.get(f"{BASE_URL}/api/users", headers=_auth(super_token), timeout=15).json()
        active_supers = [u for u in rows if u["role"] == "SUPER ADMIN" and u.get("enabled", True)]
        assert len(active_supers) == 1, f"precondition: expected 1 active super, got {len(active_supers)}"

        # 8a. try to disable self
        r = requests.patch(f"{BASE_URL}/api/users/{uid}/status", headers=_auth(super_token),
                           json={"enabled": False}, timeout=15)
        assert r.status_code == 400, r.text
        assert "SUPER ADMIN terakhir" in r.json().get("detail", ""), r.text

        # 8b. try to demote self to ADMIN
        r = requests.patch(f"{BASE_URL}/api/users/{uid}", headers=_auth(super_token),
                          json={"role": "ADMIN"}, timeout=15)
        assert r.status_code == 400, r.text
        assert "SUPER ADMIN terakhir" in r.json().get("detail", ""), r.text

        # 8c. create second SUPER ADMIN, guard should lift
        uname = f"iter11e_{uuid.uuid4().hex[:6]}"
        create = requests.post(f"{BASE_URL}/api/users", headers=_auth(super_token), json={
            "name": "TEST second super", "username": uname, "email": f"{uname}@example.com",
            "whatsapp": "+6281111111115", "password": "Passw0rd!X", "role": "SUPER ADMIN",
        }, timeout=20)
        assert create.status_code in (200, 201), create.text
        second = create.json().get("user", create.json())
        second_id = second["user_id"]

        # Second super is pending_activation? Force-activate directly via DB so it counts as "active".
        async def _activate():
            client = AsyncIOMotorClient(MONGO_URL)
            try:
                await client[DB_NAME].users.update_one(
                    {"user_id": second_id},
                    {"$set": {"pending_activation": False, "enabled": True, "role": "SUPER ADMIN"}},
                )
            finally:
                client.close()
        asyncio.run(_activate())

        try:
            # Now guard should NOT block a self-demote attempt (there are 2 active supers).
            # But we don't want to actually demote the seed superadmin (it would break future tests).
            # Instead, verify by disabling the *second* super — should succeed (200).
            r = requests.patch(f"{BASE_URL}/api/users/{second_id}/status", headers=_auth(super_token),
                               json={"enabled": False}, timeout=15)
            assert r.status_code == 200, r.text
            # Re-enable then delete to clean up
            requests.patch(f"{BASE_URL}/api/users/{second_id}/status", headers=_auth(super_token),
                           json={"enabled": True}, timeout=15)
        finally:
            requests.delete(f"{BASE_URL}/api/users/{second_id}", headers=_auth(super_token), timeout=15)

        # sanity: seed super still there & canonical
        me2 = requests.get(f"{BASE_URL}/api/auth/me", headers=_auth(super_token), timeout=15).json()
        assert me2["role"] == "SUPER ADMIN"
        assert me2.get("enabled") is not False
