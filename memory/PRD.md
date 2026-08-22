# Export 7 AI — Control Center

## Ringkasan
Aplikasi mobile (Expo + FastAPI + MongoDB) untuk mengendalikan 7 AI bisnis ekspor. Frontend hanya berperan sebagai remote control; semua credential dan keputusan bisnis di backend.

## Fitur
- **Login** — Username/password (JWT + bcrypt) atau Google OAuth via Emergent.
- **Aktivasi WhatsApp OTP** — User baru wajib memverifikasi 6 digit kode yang dikirim ke WA sebelum bisa login. Provider adaptif (mock/fonnte/twilio) lewat env.
- **Dashboard** — Status server, metrik CPU/RAM/Storage/Uptime, ringkasan 7 AI, negara target, aktivitas.
- **7 AI + Live Feed** — Toggle ON/OFF individu & bulk (RBAC), *pulse* Live Feed polling 3 detik menampilkan aktivitas AI real-time dengan pause/resume.
- **Pilih Negara** — 48 negara, search + filter region, toggle per-negara, bulk aktifkan/hapus.
- **Server** — Metrik + ON/OFF/RESTART dengan bottom-sheet konfirmasi.
- **Interogasi Server + PDF Report** — Pemeriksaan OK/WARNING/ERROR. Unduh laporan PDF **Ringkas 1 halaman** atau **Detail 24 jam** dengan header Export 7 AI + tanda tangan digital admin.
- **Akses / User** — Form lengkap (Nama, Username, Email, WhatsApp, Password, Role, tanggal akses, allowed AI/Negara/Provinsi) + status PENDING OTP + kirim ulang.
- **Pengaturan** — Profil, audit log 50 aktivitas terakhir, logout.

## Arsitektur
```
Expo APK ──HTTPS──▶ FastAPI (/api/*) ──▶ MongoDB
                          │
                          ├── JWT session store
                          ├── Audit log (semua tindakan admin)
                          ├── Background feed generator (asyncio)
                          ├── OTP + mock/fonnte/twilio adapter
                          ├── PDF (reportlab) + tanda tangan digital
                          └── 7 AI, Countries, Provinces, Server state, Users
```
Semua secret di `backend/.env`. Frontend hanya membawa `EXPO_PUBLIC_BACKEND_URL`.

## Env (Backend)
| Variable | Default | Deskripsi |
|---|---|---|
| `MONGO_URL` | mongodb://localhost:27017 | koneksi DB |
| `DB_NAME` | test_database | database |
| `JWT_SECRET` | (dev) | secret token |
| `SUPER_ADMIN_EMAILS` | — | daftar email Google → SUPER ADMIN |
| `WA_PROVIDER` | `mock` | `mock` \| `fonnte` \| `twilio` |
| `WA_SENDER_NAME` | `Export 7 AI` | nama pengirim WA |
| `WA_FONNTE_TOKEN` | — | token Fonnte |
| `WA_TWILIO_SID` / `WA_TWILIO_TOKEN` / `WA_TWILIO_FROM` | — | Twilio |
| `OTP_TTL_MINUTES` | 10 | masa berlaku OTP |

## Endpoint utama
- `POST /api/auth/login|session|verify-otp|resend-otp|logout`
- `GET /api/auth/me`
- `GET /api/dashboard`
- `GET/PATCH/POST /api/ai(/bulk)` · `GET /api/ai/feed`
- `GET/PATCH/POST /api/countries(/bulk)` · `GET /api/provinces`
- `GET/POST /api/server(/action)`
- `POST /api/interrogation` · `POST /api/interrogation/pdf?mode=summary|detailed`
- `GET/POST/PATCH/DELETE /api/users` · `POST /api/users/{id}/otp/resend`
- `GET /api/otp/outbox` (admin) · `GET /api/activity`

## Frontend struktur
```
src/
├── ControlCenter.tsx
├── api.ts, types.ts, theme.ts
├── components/
│   ├── Header.tsx, Drawer.tsx, Status.tsx
│   ├── MultiSelect.tsx, Feedback.tsx, OtpSheet.tsx
├── screens/
│   ├── Login.tsx, Dashboard.tsx, AIPage.tsx (+Live Feed),
│   ├── CountryPage.tsx, ServerPage.tsx,
│   ├── InterrogationPage.tsx (+PDF export),
│   ├── AccessPage.tsx (+OTP flow), SettingsPage.tsx
└── utils/download.ts (PDF share)
```

## Testing
- Iteration 6: 29/29 pytest pass
- Iteration 7: 46/46 pytest pass (OTP, feed, PDF, RBAC)
- E2E frontend web preview: semua flow lulus

Test credentials: lihat `/app/memory/test_credentials.md`.
