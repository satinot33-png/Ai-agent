from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import asyncio
import logging
import os
import random
import secrets
import uuid

import httpx
import jwt
import bcrypt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
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

from services.wa import send_whatsapp  # noqa: E402
from services.pdf import build_pdf  # noqa: E402
from services.email import send_interrogation_email  # noqa: E402

OTP_TTL_MINUTES = int(os.environ.get("OTP_TTL_MINUTES", "10"))
FEED_MESSAGES = [
    "Scan buyer baru dari LinkedIn direktori",
    "Menganalisis histori transaksi buyer",
    "Menyusun profil demografi negara target",
    "Menghitung margin produk unggulan",
    "Menyusun materi kampanye email",
    "Kirim follow-up ke 3 buyer prospek",
    "Menyusun laporan aktivitas harian",
    "Sinkronisasi data marketplace",
    "Cek kepatuhan regulasi ekspor",
    "Optimasi query database buyer",
]

ROLES = ["SUPER ADMIN", "ADMIN", "KARYAWAN"]
ROLE_PATTERN = "^(SUPER ADMIN|ADMIN|KARYAWAN)$"

app = FastAPI(title="Export 7 AI Control Center API")
api = APIRouter(prefix="/api")


class SessionRequest(BaseModel):
    session_id: str


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=1, max_length=128)


class ToggleRequest(BaseModel):
    enabled: bool


class ServerAction(BaseModel):
    action: str = Field(pattern="^(on|off|restart)$")


class OTPVerifyRequest(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    code: str = Field(min_length=4, max_length=8, pattern="^[0-9]+$")


class OTPResendRequest(BaseModel):
    username: str = Field(min_length=3, max_length=40)


class RecipientCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    note: Optional[str] = Field(default=None, max_length=120)


class EmailInterrogationRequest(BaseModel):
    recipient_id: str = Field(min_length=6, max_length=40)
    mode: str = Field(default="summary", pattern="^(summary|detailed)$")
    note: Optional[str] = Field(default=None, max_length=280)


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    username: str = Field(min_length=3, max_length=40, pattern="^[a-zA-Z0-9_.-]+$")
    email: EmailStr
    whatsapp: str = Field(min_length=6, max_length=25)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(pattern=ROLE_PATTERN)
    allowed_ais: List[str] = Field(default_factory=list)
    allowed_countries: List[str] = Field(default_factory=list)
    allowed_provinces: List[str] = Field(default_factory=list)
    access_start: Optional[str] = None
    access_end: Optional[str] = None
    enabled: bool = True


class UserUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=80)
    email: Optional[EmailStr] = None
    whatsapp: Optional[str] = Field(default=None, min_length=6, max_length=25)
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)
    role: Optional[str] = Field(default=None, pattern=ROLE_PATTERN)
    allowed_ais: Optional[List[str]] = None
    allowed_countries: Optional[List[str]] = None
    allowed_provinces: Optional[List[str]] = None
    access_start: Optional[str] = None
    access_end: Optional[str] = None
    enabled: Optional[bool] = None


AI_SEED = [
    ("AI 1", "Pencari Buyer"), ("AI 2", "Analisis Buyer"),
    ("AI 3", "Riset Negara"), ("AI 4", "Analisis Produk"),
    ("AI 5", "Marketing"), ("AI 6", "Follow Up"), ("AI 7", "Laporan"),
]
COUNTRIES = [
    ("ID", "Indonesia", "Asia"), ("MY", "Malaysia", "Asia"),
    ("SG", "Singapura", "Asia"), ("TH", "Thailand", "Asia"),
    ("VN", "Vietnam", "Asia"), ("PH", "Filipina", "Asia"),
    ("JP", "Jepang", "Asia"), ("KR", "Korea Selatan", "Asia"),
    ("CN", "Tiongkok", "Asia"), ("IN", "India", "Asia"),
    ("PK", "Pakistan", "Asia"), ("BD", "Bangladesh", "Asia"),
    ("AU", "Australia", "Oseania"), ("NZ", "Selandia Baru", "Oseania"),
    ("US", "Amerika Serikat", "Amerika"), ("CA", "Kanada", "Amerika"),
    ("MX", "Meksiko", "Amerika"), ("BR", "Brasil", "Amerika"),
    ("AR", "Argentina", "Amerika"), ("CL", "Chili", "Amerika"),
    ("GB", "Inggris", "Eropa"), ("DE", "Jerman", "Eropa"),
    ("FR", "Prancis", "Eropa"), ("IT", "Italia", "Eropa"),
    ("ES", "Spanyol", "Eropa"), ("NL", "Belanda", "Eropa"),
    ("BE", "Belgia", "Eropa"), ("PL", "Polandia", "Eropa"),
    ("SE", "Swedia", "Eropa"), ("NO", "Norwegia", "Eropa"),
    ("FI", "Finlandia", "Eropa"), ("DK", "Denmark", "Eropa"),
    ("CH", "Swiss", "Eropa"), ("AT", "Austria", "Eropa"),
    ("RU", "Rusia", "Eropa"), ("TR", "Turki", "Eropa"),
    ("AE", "Uni Emirat Arab", "Timur Tengah"), ("SA", "Arab Saudi", "Timur Tengah"),
    ("QA", "Qatar", "Timur Tengah"), ("KW", "Kuwait", "Timur Tengah"),
    ("BH", "Bahrain", "Timur Tengah"), ("OM", "Oman", "Timur Tengah"),
    ("IL", "Israel", "Timur Tengah"), ("EG", "Mesir", "Afrika"),
    ("ZA", "Afrika Selatan", "Afrika"), ("NG", "Nigeria", "Afrika"),
    ("KE", "Kenya", "Afrika"), ("MA", "Maroko", "Afrika"),
]
PROVINCES_ID = [
    "Aceh", "Sumatera Utara", "Sumatera Barat", "Riau", "Jambi",
    "Sumatera Selatan", "Bengkulu", "Lampung", "Kepulauan Bangka Belitung",
    "Kepulauan Riau", "DKI Jakarta", "Jawa Barat", "Jawa Tengah",
    "DI Yogyakarta", "Jawa Timur", "Banten", "Bali", "Nusa Tenggara Barat",
    "Nusa Tenggara Timur", "Kalimantan Barat", "Kalimantan Tengah",
    "Kalimantan Selatan", "Kalimantan Timur", "Kalimantan Utara",
    "Sulawesi Utara", "Sulawesi Tengah", "Sulawesi Selatan",
    "Sulawesi Tenggara", "Gorontalo", "Sulawesi Barat", "Maluku",
    "Maluku Utara", "Papua", "Papua Barat", "Papua Selatan",
    "Papua Tengah", "Papua Pegunungan", "Papua Barat Daya",
]
SEED_USERS = [
    {"username": "superadmin", "password": "SuperAdmin@2026", "role": "SUPER ADMIN",
     "name": "Super Admin", "email": "superadmin@export7ai.local", "whatsapp": "+628110000001"},
    {"username": "admin", "password": "Admin@2026", "role": "ADMIN",
     "name": "Admin Operasional", "email": "admin@export7ai.local", "whatsapp": "+628110000002"},
    {"username": "karyawan", "password": "Karyawan@2026", "role": "KARYAWAN",
     "name": "Karyawan Demo", "email": "karyawan@export7ai.local", "whatsapp": "+628110000003"},
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
    user = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(401, "Pengguna tidak ditemukan")
    if user.get("enabled") is False:
        raise HTTPException(403, "Akun Anda dinonaktifkan oleh admin")
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
        "log_id": uuid.uuid4().hex,
        "actor": user.get("name", "User"),
        "actor_role": user.get("role", ""),
        "action": action,
        "detail": detail,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode(), hashed.encode())
    except Exception:
        return False


def public_user(user: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in user.items() if key not in {"_id", "password_hash"}}


async def issue_session(user_id: str) -> str:
    token = jwt.encode({"sub": user_id, "iat": int(datetime.now(timezone.utc).timestamp())}, JWT_SECRET, algorithm="HS256")
    await db.user_sessions.insert_one({
        "session_token": token, "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
    })
    return token


def generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


async def issue_otp(user: Dict[str, Any], purpose: str = "activation") -> Dict[str, Any]:
    """Store OTP + trigger WhatsApp send. Returns delivery info (safe for admin)."""
    code = generate_otp_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MINUTES)
    await db.otps.update_one(
        {"user_id": user["user_id"], "purpose": purpose},
        {"$set": {
            "otp_id": uuid.uuid4().hex,
            "user_id": user["user_id"],
            "code_hash": hash_password(code),
            "purpose": purpose,
            "attempts": 0,
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc),
            "verified": False,
        }},
        upsert=True,
    )
    message = (
        f"[Export 7 AI] Kode aktivasi akun Anda: {code}. "
        f"Berlaku {OTP_TTL_MINUTES} menit. Jangan bagikan kepada siapa pun."
    )
    delivery = await send_whatsapp(db, user.get("whatsapp", ""), message, purpose="OTP")
    return {
        "delivered_to": delivery.get("to", ""),
        "provider": delivery.get("provider", "mock"),
        "status": delivery.get("status", "queued"),
        "expires_at": expires_at.isoformat(),
        # In mock/dev mode we surface the code so the admin can share it
        # from the app itself without leaving the flow.
        "code": code if delivery.get("provider", "mock") == "mock" else None,
    }


async def _generate_feed_events():
    """Background task: emit synthetic activity for enabled AIs every ~4s."""
    await asyncio.sleep(3)
    while True:
        try:
            enabled = await db.ai_agents.find({"enabled": True}, {"_id": 0}).to_list(20)
            server = await db.server_state.find_one({}, {"_id": 0})
            if enabled and server and server.get("server_online"):
                ai = random.choice(enabled)
                message = random.choice(FEED_MESSAGES)
                level = random.choices(["info", "success", "warning"], weights=[70, 20, 10])[0]
                now = datetime.now(timezone.utc)
                event = {
                    "event_id": uuid.uuid4().hex,
                    "agent_id": ai["agent_id"],
                    "agent_name": ai["name"],
                    "level": level,
                    "message": message,
                    "created_at": now.isoformat(),
                }
                await db.ai_events.insert_one(event.copy())
                await db.ai_agents.update_one(
                    {"agent_id": ai["agent_id"]},
                    {"$set": {"last_activity": f"{message} · {now.strftime('%H:%M:%S')}", "job_status": "Berjalan"}},
                )
                # Trim old events to keep collection small
                total = await db.ai_events.count_documents({})
                if total > 500:
                    oldest = await db.ai_events.find({}, {"event_id": 1}).sort("created_at", 1).to_list(total - 500)
                    if oldest:
                        await db.ai_events.delete_many({"event_id": {"$in": [o["event_id"] for o in oldest]}})
        except Exception as exc:  # noqa: BLE001
            logger.warning("feed generator error: %s", exc)
        await asyncio.sleep(random.uniform(3.5, 5.5))


@app.on_event("startup")
async def seed_database():
    await db.ai_agents.create_index("agent_id", unique=True)
    await db.countries.create_index("code", unique=True)
    await db.users.create_index("username", unique=True)
    await db.users.create_index("email", unique=True, sparse=True)
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
    else:
        # Sync any new/renamed countries without touching enabled flag
        for code, name, region in COUNTRIES:
            await db.countries.update_one(
                {"code": code},
                {"$set": {"name": name, "region": region},
                 "$setOnInsert": {"enabled": code == "ID"}},
                upsert=True,
            )
    if await db.provinces.count_documents({}) == 0:
        await db.provinces.insert_many([
            {"code": f"ID-{i + 1:02d}", "name": name, "country_code": "ID"}
            for i, name in enumerate(PROVINCES_ID)
        ])
    if await db.server_state.count_documents({}) == 0:
        await db.server_state.insert_one({
            "server_online": True, "domain": "control.export7ai.local",
            "api_online": True, "cpu": 34, "ram": 58, "storage": 41,
            "uptime": "12h 48m", "active_jobs": 3, "successful_jobs": 128,
            "failed_jobs": 4, "last_error": "Tidak ada error baru",
        })
    for seed in SEED_USERS:
        if not await db.users.find_one({"username": seed["username"]}, {"_id": 0}):
            await db.users.insert_one({
                "user_id": f"user_{uuid.uuid4().hex[:12]}",
                "username": seed["username"], "name": seed["name"],
                "email": seed["email"], "whatsapp": seed["whatsapp"],
                "role": seed["role"], "enabled": True,
                "allowed_ais": [f"ai-{i}" for i in range(1, 8)],
                "allowed_countries": [c[0] for c in COUNTRIES],
                "allowed_provinces": [],
                "access_start": None, "access_end": None,
                "password_hash": hash_password(seed["password"]),
                "auth_provider": "password",
                "pending_activation": False,
            })
    # Kick off background feed generator (idempotent — only starts once)
    if not getattr(app.state, "_feed_task", None):
        app.state._feed_task = asyncio.create_task(_generate_feed_events())
    # Seed 7-day job stats history (idempotent)
    today = datetime.now(timezone.utc).date()
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        key = day.isoformat()
        if not await db.job_stats.find_one({"date": key}):
            base = 90 + (offset * 7) + random.randint(-15, 20)
            success = max(20, base + random.randint(-10, 25))
            failed = max(0, random.randint(1, 8))
            await db.job_stats.insert_one({
                "date": key,
                "successful": success,
                "failed": failed,
                "active": random.randint(1, 6),
                "created_at": datetime.now(timezone.utc),
            })


@api.get("/health")
async def health():
    return {"status": "ok", "service": "export7ai"}


@api.post("/auth/login")
async def login(payload: LoginRequest):
    user = await db.users.find_one({"username": payload.username})
    if not user or not user.get("password_hash") or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(401, "Username atau password salah")
    if user.get("enabled") is False:
        raise HTTPException(403, "Akun ini dinonaktifkan")
    if user.get("pending_activation"):
        raise HTTPException(
            403,
            "Akun belum diaktivasi. Masukkan kode OTP yang dikirim ke WhatsApp Anda.",
        )
    token = await issue_session(user["user_id"])
    await audit(user, "LOGIN", f"Login username/password: {user['username']}")
    return {"session_token": token, "user": public_user(user)}


@api.post("/auth/verify-otp")
async def verify_otp(payload: OTPVerifyRequest):
    user = await db.users.find_one({"username": payload.username})
    if not user:
        raise HTTPException(404, "User tidak ditemukan")
    otp = await db.otps.find_one({"user_id": user["user_id"], "purpose": "activation"})
    if not otp:
        raise HTTPException(404, "OTP tidak ditemukan. Minta OTP baru.")
    if otp.get("verified"):
        raise HTTPException(400, "OTP sudah pernah digunakan.")
    expires_at = otp["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(400, "OTP sudah kedaluwarsa. Minta OTP baru.")
    if otp.get("attempts", 0) >= 5:
        raise HTTPException(429, "Percobaan OTP melebihi batas. Minta OTP baru.")
    if not verify_password(payload.code, otp["code_hash"]):
        await db.otps.update_one({"otp_id": otp["otp_id"]}, {"$inc": {"attempts": 1}})
        raise HTTPException(401, "Kode OTP salah")
    await db.otps.update_one({"otp_id": otp["otp_id"]}, {"$set": {"verified": True}})
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"pending_activation": False}})
    user["pending_activation"] = False
    token = await issue_session(user["user_id"])
    await audit(user, "OTP_VERIFIED", f"Aktivasi akun {user['username']} berhasil")
    return {"session_token": token, "user": public_user(user)}


@api.post("/auth/resend-otp")
async def resend_otp(payload: OTPResendRequest):
    user = await db.users.find_one({"username": payload.username})
    if not user:
        raise HTTPException(404, "User tidak ditemukan")
    if not user.get("pending_activation"):
        raise HTTPException(400, "Akun sudah aktif. Tidak perlu OTP.")
    delivery = await issue_otp(user, purpose="activation")
    return {"delivery": delivery, "message": "OTP baru telah dikirim ke WhatsApp."}


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
    user = await db.users.find_one({"email": email})
    if not user:
        configured = {item.strip() for item in os.environ.get("SUPER_ADMIN_EMAILS", "").split(",") if item.strip()}
        role = "SUPER ADMIN" if email in configured else "KARYAWAN"
        user = {
            "user_id": f"user_{uuid.uuid4().hex[:12]}",
            "email": email, "name": oauth_user.get("name", email.split("@")[0]),
            "picture": oauth_user.get("picture"), "role": role,
            "username": email.split("@")[0], "whatsapp": "",
            "allowed_ais": [f"ai-{i}" for i in range(1, 8)] if role == "SUPER ADMIN" else [],
            "allowed_countries": [], "allowed_provinces": [],
            "access_start": None, "access_end": None,
            "enabled": True, "auth_provider": "google",
        }
        await db.users.insert_one(user.copy())
    session_token = data.get("session_token") or jwt.encode({"sub": user["user_id"]}, JWT_SECRET, algorithm="HS256")
    await db.user_sessions.insert_one({
        "session_token": session_token, "user_id": user["user_id"],
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
    })
    await audit(user, "LOGIN", f"Login Google: {email}")
    return {"session_token": session_token, "user": public_user(user)}


@api.get("/auth/me")
async def me(user=Depends(current_user)):
    return user


@api.post("/auth/logout")
async def logout(authorization: Optional[str] = Header(default=None)):
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
        await db.user_sessions.delete_one({"session_token": token})
    return {"ok": True}


@api.get("/dashboard")
async def dashboard(user=Depends(current_user)):
    server = await db.server_state.find_one({}, {"_id": 0})
    ais = await db.ai_agents.find({}, {"_id": 0}).to_list(20)
    countries = await db.countries.find({"enabled": True}, {"_id": 0}).to_list(300)
    logs = await db.audit_logs.find({}, {"_id": 0}).sort("created_at", -1).to_list(8)
    stats = await db.job_stats.find({}, {"_id": 0}).sort("date", 1).to_list(30)
    return {
        "server": server, "ais": ais, "countries": countries,
        "logs": logs, "user": user, "job_stats": stats[-7:],
    }


@api.get("/stats/jobs")
async def stats_jobs(user=Depends(current_user), days: int = Query(default=7, ge=1, le=30)):
    rows = await db.job_stats.find({}, {"_id": 0}).sort("date", -1).to_list(days)
    return list(reversed(rows))


@api.get("/ai")
async def list_ai(user=Depends(current_user)):
    return await db.ai_agents.find({}, {"_id": 0}).to_list(20)


@api.patch("/ai/{agent_id}")
async def toggle_ai(agent_id: str, payload: ToggleRequest, user=Depends(require_roles("SUPER ADMIN", "ADMIN"))):
    result = await db.ai_agents.update_one(
        {"agent_id": agent_id},
        {"$set": {
            "enabled": payload.enabled,
            "job_status": "Idle" if not payload.enabled else "Siap",
            "last_activity": f"{'Diaktifkan' if payload.enabled else 'Dinonaktifkan'} oleh {user.get('name', 'admin')} · {datetime.now(timezone.utc).isoformat()}",
        }},
    )
    if not result.matched_count:
        raise HTTPException(404, "AI tidak ditemukan")
    await audit(user, "AI_TOGGLE", f"{agent_id} → {'ON' if payload.enabled else 'OFF'}")
    return await db.ai_agents.find_one({"agent_id": agent_id}, {"_id": 0})


@api.post("/ai/bulk")
async def bulk_ai(payload: ToggleRequest, user=Depends(require_roles("SUPER ADMIN", "ADMIN"))):
    await db.ai_agents.update_many({}, {"$set": {
        "enabled": payload.enabled,
        "job_status": "Idle" if not payload.enabled else "Siap",
    }})
    await audit(user, "AI_BULK_TOGGLE", f"Semua AI → {'ON' if payload.enabled else 'OFF'}")
    return await db.ai_agents.find({}, {"_id": 0}).to_list(20)


@api.get("/ai/feed")
async def ai_feed(
    user=Depends(current_user),
    since: Optional[str] = Query(default=None),
    agent_id: Optional[str] = Query(default=None),
    limit: int = Query(default=40, ge=1, le=200),
):
    query: Dict[str, Any] = {}
    if since:
        query["created_at"] = {"$gt": since}
    if agent_id:
        query["agent_id"] = agent_id
    events = await db.ai_events.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return list(reversed(events))


@api.get("/countries")
async def list_countries(user=Depends(current_user)):
    return await db.countries.find({}, {"_id": 0}).sort("name", 1).to_list(500)


@api.patch("/countries/{code}")
async def toggle_country(code: str, payload: ToggleRequest, user=Depends(require_roles("SUPER ADMIN", "ADMIN"))):
    result = await db.countries.update_one({"code": code}, {"$set": {"enabled": payload.enabled}})
    if not result.matched_count:
        raise HTTPException(404, "Negara tidak ditemukan")
    await audit(user, "COUNTRY_TOGGLE", f"{code} → {'ON' if payload.enabled else 'OFF'}")
    return await db.countries.find_one({"code": code}, {"_id": 0})


@api.post("/countries/bulk")
async def bulk_countries(payload: ToggleRequest, user=Depends(require_roles("SUPER ADMIN", "ADMIN"))):
    await db.countries.update_many({}, {"$set": {"enabled": payload.enabled}})
    await audit(user, "COUNTRY_BULK", f"Semua negara {'aktif' if payload.enabled else 'nonaktif'}")
    return await db.countries.find({}, {"_id": 0}).sort("name", 1).to_list(500)


@api.get("/provinces")
async def list_provinces(user=Depends(current_user)):
    return await db.provinces.find({}, {"_id": 0}).sort("name", 1).to_list(500)


@api.get("/server")
async def server_status(user=Depends(current_user)):
    return await db.server_state.find_one({}, {"_id": 0})


@api.post("/server/action")
async def server_action(payload: ServerAction, user=Depends(require_roles("SUPER ADMIN", "ADMIN"))):
    if payload.action == "restart":
        updates = {"server_online": True, "api_online": True, "uptime": "0m (baru restart)"}
    else:
        updates = {"server_online": payload.action != "off", "api_online": payload.action != "off"}
    await db.server_state.update_one({}, {"$set": updates})
    await audit(user, "SERVER_ACTION", payload.action.upper())
    return await server_status(user)


@api.post("/interrogation")
async def interrogation(user=Depends(current_user)):
    server = await server_status(user)
    ais = await list_ai(user)
    report = {
        "connection": "OK" if server["server_online"] else "ERROR",
        "api": "OK" if server["api_online"] else "ERROR",
        "database": "OK",
        "ai": [{"agent_id": ai["agent_id"], "name": ai["name"], "status": "OK" if ai["enabled"] else "WARNING"} for ai in ais],
        "active_jobs": server["active_jobs"],
        "successful_jobs": server["successful_jobs"],
        "failed_jobs": server["failed_jobs"],
        "last_error": server["last_error"],
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    await audit(user, "SERVER_CHECK", "Pemeriksaan server dijalankan")
    return report


@api.post("/interrogation/pdf")
async def interrogation_pdf(
    user=Depends(current_user),
    mode: str = Query(default="summary", pattern="^(summary|detailed)$"),
):
    report = await interrogation(user)
    logs: List[Dict[str, Any]] = []
    if mode == "detailed":
        since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        logs = await db.audit_logs.find(
            {"created_at": {"$gte": since}},
            {"_id": 0},
        ).sort("created_at", -1).to_list(200)
    pdf_bytes = build_pdf(mode, report, user, logs)
    await audit(user, "REPORT_EXPORT", f"PDF {mode} ({len(pdf_bytes)} bytes)")
    filename = f"export7ai-{mode}-{datetime.now().strftime('%Y%m%d-%H%M')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Report-Mode": mode,
        },
    )


@api.get("/settings/recipients")
async def list_recipients(user=Depends(current_user)):
    rows = await db.report_recipients.find(
        {"user_id": user["user_id"]}, {"_id": 0}
    ).sort("created_at", 1).to_list(50)
    return rows


@api.post("/settings/recipients")
async def add_recipient(payload: RecipientCreate, user=Depends(current_user)):
    if await db.report_recipients.count_documents({"user_id": user["user_id"]}) >= 20:
        raise HTTPException(400, "Maksimal 20 penerima per akun.")
    if await db.report_recipients.find_one({"user_id": user["user_id"], "email": payload.email}):
        raise HTTPException(409, "Email penerima sudah terdaftar.")
    record = {
        "recipient_id": f"rcp_{uuid.uuid4().hex[:12]}",
        "user_id": user["user_id"],
        "name": payload.name.strip(),
        "email": payload.email,
        "note": (payload.note or "").strip(),
        "created_at": datetime.now(timezone.utc),
    }
    await db.report_recipients.insert_one(record.copy())
    record["created_at"] = record["created_at"].isoformat()
    await audit(user, "RECIPIENT_ADD", f"{payload.name} <{payload.email}>")
    record.pop("_id", None)
    return record


@api.delete("/settings/recipients/{recipient_id}")
async def delete_recipient(recipient_id: str, user=Depends(current_user)):
    result = await db.report_recipients.delete_one(
        {"user_id": user["user_id"], "recipient_id": recipient_id}
    )
    if not result.deleted_count:
        raise HTTPException(404, "Penerima tidak ditemukan")
    await audit(user, "RECIPIENT_DELETE", recipient_id)
    return {"deleted": True}


@api.post("/interrogation/email")
async def email_interrogation(
    payload: EmailInterrogationRequest,
    user=Depends(current_user),
):
    recipient = await db.report_recipients.find_one(
        {"user_id": user["user_id"], "recipient_id": payload.recipient_id},
        {"_id": 0},
    )
    if not recipient:
        raise HTTPException(404, "Penerima tidak ditemukan di daftar Anda")
    report = await interrogation(user)
    logs: List[Dict[str, Any]] = []
    if payload.mode == "detailed":
        since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        logs = await db.audit_logs.find(
            {"created_at": {"$gte": since}},
            {"_id": 0},
        ).sort("created_at", -1).to_list(200)
    pdf_bytes = build_pdf(payload.mode, report, user, logs)
    filename = f"export7ai-{payload.mode}-{datetime.now().strftime('%Y%m%d-%H%M')}.pdf"
    try:
        result = await send_interrogation_email(
            to=recipient["email"],
            recipient_name=recipient["name"],
            report=report,
            actor=user,
            note=payload.note or "",
            mode=payload.mode,
            pdf_bytes=pdf_bytes,
            pdf_filename=filename,
        )
    except ValueError as exc:
        raise HTTPException(400, f"Konten email ditolak guardrail: {exc}")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Email delivery failed")
        raise HTTPException(502, f"Gagal mengirim email: {exc}")
    await audit(
        user, "REPORT_EMAIL",
        f"{payload.mode} → {recipient['name']} <{recipient['email']}> (id={result.get('message_id')})",
    )
    return result


@api.get("/activity")
async def activity(user=Depends(current_user)):
    return await db.audit_logs.find({}, {"_id": 0}).sort("created_at", -1).to_list(50)


@api.get("/otp/outbox")
async def otp_outbox(user=Depends(require_roles("SUPER ADMIN", "ADMIN")), limit: int = Query(default=20, ge=1, le=100)):
    """Return the last WA messages (mock or real) with their status."""
    return await db.mock_wa_outbox.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)


@api.get("/users")
async def users(user=Depends(require_roles("SUPER ADMIN", "ADMIN"))):
    return await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(200)


@api.post("/users")
async def create_user(payload: UserCreate, user=Depends(require_roles("SUPER ADMIN", "ADMIN"))):
    if payload.role == "SUPER ADMIN" and user.get("role") != "SUPER ADMIN":
        raise HTTPException(403, "Hanya SUPER ADMIN yang dapat membuat SUPER ADMIN")
    if await db.users.find_one({"username": payload.username}):
        raise HTTPException(409, "Username sudah digunakan")
    if await db.users.find_one({"email": payload.email}):
        raise HTTPException(409, "Email sudah digunakan")
    record = payload.model_dump(exclude={"password"})
    record.update({
        "user_id": f"user_{uuid.uuid4().hex[:12]}",
        "password_hash": hash_password(payload.password),
        "auth_provider": "password",
        "pending_activation": True,
    })
    await db.users.insert_one(record.copy())
    delivery = await issue_otp(record, purpose="activation")
    await audit(user, "USER_CREATE", f"{payload.username} ({payload.role}) — OTP dikirim ke WA")
    return {"user": public_user(record), "otp": delivery}


@api.post("/users/{user_id}/otp/resend")
async def resend_user_otp(user_id: str, user=Depends(require_roles("SUPER ADMIN", "ADMIN"))):
    target = await db.users.find_one({"user_id": user_id})
    if not target:
        raise HTTPException(404, "User tidak ditemukan")
    if not target.get("pending_activation"):
        raise HTTPException(400, "User sudah aktif — OTP tidak perlu dikirim ulang.")
    delivery = await issue_otp(target, purpose="activation")
    await audit(user, "OTP_RESEND", f"OTP dikirim ulang untuk {target.get('username')}")
    return {"delivery": delivery}


@api.patch("/users/{user_id}")
async def update_user(user_id: str, payload: UserUpdate, user=Depends(require_roles("SUPER ADMIN", "ADMIN"))):
    updates = payload.model_dump(exclude_none=True)
    password = updates.pop("password", None)
    if password:
        updates["password_hash"] = hash_password(password)
    if updates.get("role") == "SUPER ADMIN" and user.get("role") != "SUPER ADMIN":
        raise HTTPException(403, "Hanya SUPER ADMIN yang dapat memberikan role SUPER ADMIN")
    if not updates:
        raise HTTPException(400, "Tidak ada perubahan")
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
    target = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    if not target:
        raise HTTPException(404, "User tidak ditemukan")
    if target.get("role") == "SUPER ADMIN" and user.get("role") != "SUPER ADMIN":
        raise HTTPException(403, "Hanya SUPER ADMIN yang dapat menghapus SUPER ADMIN")
    await db.users.delete_one({"user_id": user_id})
    await audit(user, "USER_DELETE", user_id)
    return {"deleted": True}


app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
