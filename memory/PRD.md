# Export 7 AI — Control Center

## Ringkasan
Aplikasi mobile (Expo + FastAPI + MongoDB) untuk mengendalikan 7 AI bisnis ekspor dari satu tempat. Frontend hanya berperan sebagai remote control; semua credential dan keputusan bisnis berada di backend.

## Fitur Utama
- **Login** — Username/password (JWT session bcrypt) atau Google OAuth via Emergent.
- **Dashboard** — Status server ONLINE/OFFLINE, metrik CPU/RAM/Storage/Uptime, ringkasan 7 AI, negara target, aktivitas terbaru.
- **7 AI** — Toggle ON/OFF individu dan bulk (SUPER ADMIN / ADMIN saja), optimistic UI + revert jika gagal, tersimpan permanen di MongoDB.
- **Pilih Negara** — 48 negara global dengan search + filter region, toggle per-negara, pilih semua / hapus semua.
- **Server** — Metrik server real-time, kontrol SERVER ON/OFF/RESTART dengan bottom-sheet konfirmasi.
- **Interogasi Server** — Pemeriksaan menyeluruh koneksi/API/database/7 AI/job/error → OK/WARNING/ERROR.
- **Akses / User** — Form lengkap (Nama, Username, Email, WhatsApp, Password, Role, tanggal akses, AI/Negara/Provinsi diizinkan) dengan RBAC (SUPER ADMIN / ADMIN / KARYAWAN).
- **Pengaturan** — Profil akun, audit log 50 aktivitas terakhir, logout.

## Arsitektur
```
Expo APK ──HTTPS──▶ FastAPI (/api/*) ──▶ MongoDB
                          │
                          ├── JWT session store
                          ├── Audit log
                          └── AI, Country, Server state, User
```
Semua secret berada di `backend/.env`. Frontend hanya membawa `EXPO_PUBLIC_BACKEND_URL`.

## Endpoint utama
- `POST /api/auth/login` — username+password
- `POST /api/auth/session` — Google OAuth
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /api/dashboard`
- `GET/PATCH/POST /api/ai(/bulk)`
- `GET/PATCH/POST /api/countries(/bulk)`
- `GET /api/provinces`
- `GET/POST /api/server(/action)`
- `POST /api/interrogation`
- `GET/POST/PATCH/DELETE /api/users`
- `GET /api/activity`

## Test Credentials
Lihat `/app/memory/test_credentials.md` untuk 3 akun seed.

## Struktur Frontend (modular)
```
src/
├── ControlCenter.tsx       # root shell + routing
├── api.ts                  # fetch helper
├── types.ts                # tipe TS
├── theme.ts                # warna & konstanta
├── components/
│   ├── Header.tsx
│   ├── Drawer.tsx
│   ├── Status.tsx
│   ├── MultiSelect.tsx
│   └── Feedback.tsx        # Toast + ConfirmSheet
└── screens/
    ├── Login.tsx
    ├── Dashboard.tsx
    ├── AIPage.tsx
    ├── CountryPage.tsx
    ├── ServerPage.tsx
    ├── InterrogationPage.tsx
    ├── AccessPage.tsx
    └── SettingsPage.tsx
```
