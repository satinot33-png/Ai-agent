from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging
import os
import uuid

import httpx
import jwt
import bcrypt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("export7ai")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]
JWT_SECRET = os.environ["JWT_SECRET"]
EMERGENT_SESSION_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"

app = FastAPI(title="Export 7 AI Control Center API")
api = APIRouter(prefix="/api")


class SessionRequest(BaseModel):
    session_id: str


class ToggleRequest(BaseModel):
    enabled: bool


class ServerAction(BaseModel):
    action: str = Field(pattern="^(on|off|restart)$")


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    username: str = Field(min_length=3, max_length=40, pattern="^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(pattern="^(Admin|Operator|User)$")
    country: str = Field(min_length=2, max_length=80)
    province: str = Field(min_length=2, max_length=80)
    enabled: bool = True


class UserUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=80)
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)
    role: Optional[str] = Field(default=None, pattern="^(Admin|Operator|User)$")
    country: Optional[str] = Field(default=None, min_length=2, max_length=80)
    province: Optional[str] = Field(default=None, min_length=2, max_length=80)
    enabled: Optional[bool] = None


AI_SEED = [
    ("AI 1", "Pencari Buyer"), ("AI 2", "Analisis Buyer"),
    ("AI 3", "Riset Negara"), ("AI 4", "Analisis Produk"),
    ("AI 5", "Marketing"), ("AI 6", "Follow Up"), ("AI 7", "Laporan"),
]
COUNTRIES = [
    ("ID", "Indonesia", "Asia"), ("MY", "Malaysia", "Asia"),
    ("SG", "Singapura", "Asia"), ("TH", "Thailand", "Asia"),
    ("VN", "Vietnam", "Asia"), ("JP", "Jepang", "Asia"),
    ("KR", "Korea Selatan", "Asia"), ("AU", "Australia", "Oceania"),
    ("US", "Amerika Serikat", "Amerika"), ("CA", "Kanada", "Amerika"),
    ("GB", "Inggris", "Eropa"), ("DE", "Jerman", "Eropa"),
    ("NL", "Belanda", "Eropa"), ("AE", "Uni Emirat Arab", "Timur Tengah"),
]


async def current_user(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Token diperlukan")
    token = authorization.split(" ", 1)[1]
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session:
        raise HTTPException(401, "Sesi tidak valid atau sudah berakhir")
    expires_at = session["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(401, "Sesi tidak valid atau sudah berakhir")
    user = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(401, "Pengguna tidak ditemukan")
    return user


def require_roles(*roles: str):
    async def dependency(user: Dict[str, Any] = Depends(current_user)):
        allowed = {role.upper() for role in roles}
        if str(user.get("role", "")).upper() not in allowed:
            raise HTTPException(403, "Anda tidak memiliki izin untuk tindakan ini")
        return user
    return dependency


async def audit(user: Dict[str, Any], action: str, detail: str):
    await db.audit_logs.insert_one({
        "log_id": uuid.uuid4().hex, "actor": user.get("name", "User"),
        "action": action, "detail": detail,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


@app.on_event("startup")
async def seed_database():
    await db.ai_agents.create_index("agent_id", unique=True)
    await db.countries.create_index("code", unique=True)
    if await db.ai_agents.count_documents({}) == 0:
        await db.ai_agents.insert_many([
            {"agent_id": f"ai-{i + 1}", "name": name, "function": function,
             "enabled": True, "job_status": "Idle", "last_activity": "Belum ada aktivitas"}
            for i, (name, function) in enumerate(AI_SEED)
        ])
    if await db.countries.count_documents({}) == 0:
        await db.countries.insert_many([
            {"code": code, "name": name, "region": region, "enabled": code == "ID"}
            for code, name, region in COUNTRIES
        ])
    if await db.server_state.count_documents({}) == 0:
        await db.server_state.insert_one({
            "server_online": True, "domain": "control.export7ai.local",
            "api_online": True, "cpu": 34, "ram": 58, "storage": 41,
            "uptime": "12h 48m", "active_jobs": 3, "successful_jobs": 128,
            "failed_jobs": 4, "last_error": "Tidak ada error baru",
        })


@api.get("/health")
async def health():
    return {"status": "ok", "service": "export7ai"}


@api.post("/auth/session")
async def exchange_session(payload: SessionRequest):
    async with httpx.AsyncClient(timeout=10) as http:
        response = await http.get(EMERGENT_SESSION_URL, headers={"X-Session-ID": payload.session_id})
    if response.status_code != 200:
        raise HTTPException(401, "Sesi Google tidak valid")
    data = response.json()
    oauth_user = data.get("user_data", data)
    email = oauth_user.get("email")
    if not email:
        raise HTTPException(401, "Data akun Google tidak lengkap")
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user:
        configured = {item.strip() for item in os.environ.get("SUPER_ADMIN_EMAILS", "").split(",") if item.strip()}
        role = "SUPER ADMIN" if email in configured else "KARYAWAN"
        user = {"user_id": f"user_{uuid.uuid4().hex[:12]}", "email": email,
                "name": oauth_user.get("name", email.split("@")[0]), "picture": oauth_user.get("picture"),
                "role": role, "permissions": ["dashboard", "interrogation"] if role == "KARYAWAN" else ["*"]}
        await db.users.insert_one(user.copy())
    session_token = data.get("session_token") or jwt.encode({"sub": user["user_id"]}, JWT_SECRET, algorithm="HS256")
    await db.user_sessions.insert_one({"session_token": session_token, "user_id": user["user_id"],
                                       "created_at": datetime.now(timezone.utc),
                                       "expires_at": datetime.now(timezone.utc) + timedelta(days=7)})
    return {"session_token": session_token, "user": user}


@api.get("/auth/me")
async def me(user=Depends(current_user)):
    return user


@api.get("/dashboard")
async def dashboard(user=Depends(current_user)):
    server = await db.server_state.find_one({}, {"_id": 0})
    ais = await db.ai_agents.find({}, {"_id": 0}).to_list(20)
    countries = await db.countries.find({"enabled": True}, {"_id": 0}).to_list(100)
    logs = await db.audit_logs.find({}, {"_id": 0}).sort("created_at", -1).to_list(8)
    return {"server": server, "ais": ais, "countries": countries, "logs": logs, "user": user}


@api.get("/ai")
async def list_ai(user=Depends(current_user)):
    return await db.ai_agents.find({}, {"_id": 0}).to_list(20)


@api.patch("/ai/{agent_id}")
async def toggle_ai(agent_id: str, payload: ToggleRequest, user=Depends(require_roles("SUPER ADMIN", "ADMIN"))):
    result = await db.ai_agents.update_one({"agent_id": agent_id}, {"$set": {"enabled": payload.enabled, "job_status": "Idle"}})
    if not result.matched_count:
        raise HTTPException(404, "AI tidak ditemukan")
    await audit(user, "AI_TOGGLE", f"{agent_id} → {'ON' if payload.enabled else 'OFF'}")
    return await db.ai_agents.find_one({"agent_id": agent_id}, {"_id": 0})


@api.post("/ai/bulk")
async def bulk_ai(payload: ToggleRequest, user=Depends(require_roles("SUPER ADMIN", "ADMIN"))):
    await db.ai_agents.update_many({}, {"$set": {"enabled": payload.enabled, "job_status": "Idle"}})
    await audit(user, "AI_BULK_TOGGLE", f"Semua AI → {'ON' if payload.enabled else 'OFF'}")
    return await db.ai_agents.find({}, {"_id": 0}).to_list(20)


@api.get("/countries")
async def list_countries(user=Depends(current_user)):
    return await db.countries.find({}, {"_id": 0}).to_list(300)


@api.post("/countries/bulk")
async def bulk_countries(payload: ToggleRequest, user=Depends(require_roles("SUPER ADMIN", "ADMIN"))):
    await db.countries.update_many({}, {"$set": {"enabled": payload.enabled}})
    await audit(user, "COUNTRY_BULK", f"Semua negara {'aktif' if payload.enabled else 'nonaktif'}")
    return {"updated": True}


@api.get("/server")
async def server_status(user=Depends(current_user)):
    return await db.server_state.find_one({}, {"_id": 0})


@api.post("/server/action")
async def server_action(payload: ServerAction, user=Depends(require_roles("SUPER ADMIN", "ADMIN"))):
    updates = {"server_online": payload.action != "off", "api_online": payload.action != "off"}
    if payload.action == "restart":
        updates = {"server_online": True, "api_online": True, "uptime": "0m (baru restart)"}
    await db.server_state.update_one({}, {"$set": updates})
    await audit(user, "SERVER_ACTION", payload.action.upper())
    return await server_status(user)


@api.post("/interrogation")
async def interrogation(user=Depends(current_user)):
    server = await server_status(user)
    ais = await list_ai(user)
    report = {"connection": "OK" if server["server_online"] else "ERROR",
              "api": "OK" if server["api_online"] else "ERROR", "database": "OK",
              "ai": [{"name": ai["name"], "status": "OK" if ai["enabled"] else "WARNING"} for ai in ais],
              "active_jobs": server["active_jobs"], "successful_jobs": server["successful_jobs"],
              "failed_jobs": server["failed_jobs"], "last_error": server["last_error"],
              "checked_at": datetime.now(timezone.utc).isoformat()}
    await audit(user, "SERVER_CHECK", "Pemeriksaan server dijalankan")
    return report


@api.get("/activity")
async def activity(user=Depends(current_user)):
    return await db.audit_logs.find({}, {"_id": 0}).sort("created_at", -1).to_list(50)


def public_user(user: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in user.items() if key not in {"_id", "password_hash"}}


@api.get("/users")
async def users(user=Depends(require_roles("SUPER ADMIN", "ADMIN"))):
    records = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(100)
    return records


@api.post("/users")
async def create_user(payload: UserCreate, user=Depends(require_roles("SUPER ADMIN", "ADMIN"))):
    if await db.users.find_one({"username": payload.username}, {"_id": 0}):
        raise HTTPException(409, "Username sudah digunakan")
    record = payload.model_dump(exclude={"password"})
    record.update({"user_id": f"user_{uuid.uuid4().hex[:12]}", "password_hash": bcrypt.hashpw(payload.password.encode(), bcrypt.gensalt()).decode()})
    await db.users.insert_one(record.copy())
    await audit(user, "USER_CREATE", payload.username)
    return public_user(record)


@api.patch("/users/{user_id}")
async def update_user(user_id: str, payload: UserUpdate, user=Depends(require_roles("SUPER ADMIN", "ADMIN"))):
    updates = payload.model_dump(exclude_none=True)
    password = updates.pop("password", None)
    if password:
        updates["password_hash"] = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    if updates.get("role") == "Admin" and user.get("role") != "SUPER ADMIN":
        raise HTTPException(403, "Hanya SUPER ADMIN yang dapat memberikan role Admin")
    result = await db.users.update_one({"user_id": user_id}, {"$set": updates})
    if not result.matched_count:
        raise HTTPException(404, "User tidak ditemukan")
    record = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    await audit(user, "USER_UPDATE", user_id)
    return record


@api.patch("/users/{user_id}/status")
async def toggle_user_status(user_id: str, payload: ToggleRequest, user=Depends(require_roles("SUPER ADMIN", "ADMIN"))):
    result = await db.users.update_one({"user_id": user_id}, {"$set": {"enabled": payload.enabled}})
    if not result.matched_count:
        raise HTTPException(404, "User tidak ditemukan")
    await audit(user, "USER_STATUS", f"{user_id} → {'ON' if payload.enabled else 'OFF'}")
    return await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})


@api.delete("/users/{user_id}")
async def delete_user(user_id: str, user=Depends(require_roles("SUPER ADMIN", "ADMIN"))):
    if user_id == user.get("user_id"):
        raise HTTPException(400, "Akun yang sedang digunakan tidak dapat dihapus")
    result = await db.users.delete_one({"user_id": user_id})
    if not result.deleted_count:
        raise HTTPException(404, "User tidak ditemukan")
    await audit(user, "USER_DELETE", user_id)
    return {"deleted": True}


app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()