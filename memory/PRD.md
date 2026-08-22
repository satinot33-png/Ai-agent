# Export 7 AI — Control Center

Mobile control panel (Expo + FastAPI + MongoDB) untuk mengendalikan 7 AI ekspor + server dari satu tempat. Frontend hanya remote-control; semua kredensial di backend.

## Fitur
- **Auth**: Username/password JWT bcrypt, Google OAuth via Emergent, OTP WhatsApp aktivasi.
- **Dashboard**: Status server, metrik, ringkasan 7 AI, negara target, **Chart tren job 7 hari (sukses vs gagal)**, aktivitas.
- **7 AI + Live Feed**: Toggle ON/OFF (RBAC), Live Feed polling 3 detik dengan pulse pause/resume.
- **Pilih Negara**: 48 negara, search + region filter, toggle per-negara + bulk.
- **Server**: Metrik + ON/OFF/RESTART dengan konfirmasi bottom-sheet.
- **Interogasi Server**: OK/WARNING/ERROR + **Unduh PDF** (ringkas/detail) + **Kirim ke Email** (penerima terdaftar, PDF attachment).
- **Akses / User**: Form lengkap + OTP WhatsApp aktivasi + kirim ulang.
- **Pengaturan**: Profil, audit log 50 aktivitas terakhir.

## Integrasi
| Integrasi | Provider | Status |
|---|---|---|
| Auth | Emergent Google OAuth + JWT+bcrypt lokal | Live |
| WhatsApp OTP | Mock (default) / Fonnte / Twilio | Adapter siap |
| Email PDF | Emergent-managed Resend | Live (guardrail-compliant) |
| PDF Report | reportlab (lokal) | Live |

## Env (Backend)
| Variable | Default | Deskripsi |
|---|---|---|
| `MONGO_URL` / `DB_NAME` | local | database |
| `JWT_SECRET` | (dev) | secret |
| `SUPER_ADMIN_EMAILS` | — | Google email → SUPER ADMIN |
| `WA_PROVIDER` | `mock` | `mock` \| `fonnte` \| `twilio` |
| `WA_FONNTE_TOKEN` / `WA_TWILIO_*` | — | provider WA |
| `OTP_TTL_MINUTES` | 10 | masa berlaku OTP |
| `EMERGENT_EMAIL_KEY` | (auto) | key Resend proxy |
| `EMAIL_FROM_NAME` | `Export 7 AI` | display sender |
| `EMAIL_REPLY_TO` | — | reply-to opsional |

## Endpoint utama
- `POST /api/auth/login|session|verify-otp|resend-otp|logout` · `GET /api/auth/me`
- `GET /api/dashboard` (kini termasuk `job_stats`) · `GET /api/stats/jobs?days=`
- `GET/PATCH/POST /api/ai(/bulk)` · `GET /api/ai/feed`
- `GET/PATCH/POST /api/countries(/bulk)` · `GET /api/provinces`
- `GET/POST /api/server(/action)`
- `POST /api/interrogation(/pdf|/email)`
- `GET/POST/DELETE /api/settings/recipients`
- `GET/POST/PATCH/DELETE /api/users` · `POST /api/users/{id}/otp/resend`
- `GET /api/otp/outbox` (admin) · `GET /api/activity`

## Frontend struktur
```
src/
├── ControlCenter.tsx, api.ts, types.ts, theme.ts
├── components/  Header, Drawer, Status, MultiSelect, Feedback,
│                OtpSheet, JobTrendChart, EmailReportSheet
├── screens/     Login, Dashboard (+chart), AIPage (+live feed),
│                CountryPage, ServerPage,
│                InterrogationPage (+PDF + Email), AccessPage, SettingsPage
└── utils/       download.ts (PDF share)
```

## Testing
- Iter 6: 29/29 · Iter 7: 46/46 · Iter 8: 32/32 · Semua E2E frontend hijau.

Test credentials: `/app/memory/test_credentials.md`.
