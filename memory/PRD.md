# Export 7 AI — Control Center

Mobile control panel (Expo + FastAPI + MongoDB) untuk mengendalikan 7 AI ekspor + server dari satu tempat.

## Fitur
- **Auth**: Username/password JWT bcrypt, Google OAuth, WhatsApp OTP aktivasi.
- **Dashboard**: 
  - **Alert Banner** merah muncul saat ada error/warning AI 5 menit terakhir (polling 15 s).
  - Metrik server + tren job bar chart 7 hari.
  - **Peta Dunia** SVG dengan lampu amber di setiap negara aktif, dikelompokkan per region.
  - Aktivitas terbaru.
- **7 AI + Live Feed**: Toggle ON/OFF (RBAC), Live Feed 3 detik, level info/success/warning/error.
- **Pilih Negara**: 48 negara + lat/lng, search + region filter, toggle per-negara + bulk.
- **Server**: Metrik + ON/OFF/RESTART dengan konfirmasi.
- **Interogasi Server**: OK/WARNING/ERROR + Unduh PDF + Kirim ke Email (guardrail-compliant).
- **Akses / User**: Form lengkap + OTP WhatsApp aktivasi.
- **Pengaturan**: Profil, **Widget Preview** untuk Home Screen (perlu build native), audit log.

## Integrasi
| Integrasi | Provider | Status |
|---|---|---|
| Auth | Emergent Google OAuth + JWT+bcrypt lokal | Live |
| WhatsApp OTP | Mock / Fonnte / Twilio | Adapter siap |
| Email PDF | Emergent-managed Resend | Live (guardrail) |
| PDF Report | reportlab | Live |
| SVG Chart & Map | react-native-svg | Live |
| Widget Home | JSON endpoint (native build required) | Endpoint siap |

## Env (Backend)
Lihat versi sebelumnya. Baru: tidak ada — semua env sama.

## Endpoint utama
Baru di iterasi ini:
- `GET /api/alerts?minutes=1..60` — error/warning terakhir per window
- `GET /api/widget/status` — payload compact untuk widget iOS/Android

Semua endpoint lama tetap: `/api/dashboard`, `/api/ai(/bulk|/feed)`, `/api/countries(/bulk)`, `/api/provinces`, `/api/server(/action)`, `/api/interrogation(/pdf|/email)`, `/api/settings/recipients`, `/api/users(/status|/otp/resend)`, `/api/auth/*`, `/api/stats/jobs`, `/api/otp/outbox`, `/api/activity`.

## Frontend struktur
```
src/
├── ControlCenter.tsx, api.ts, types.ts, theme.ts
├── components/  Header, Drawer, Status, MultiSelect, Feedback,
│                OtpSheet, JobTrendChart, EmailReportSheet,
│                WorldMap, AlertBanner, WidgetPreview
├── screens/     Login, Dashboard (+alert +chart +map),
│                AIPage (+live feed), CountryPage, ServerPage,
│                InterrogationPage (+PDF +Email), AccessPage,
│                SettingsPage (+widget preview)
└── utils/       download.ts (PDF share)
```

## Widget Native Setup (post-Publish)
1. User klik Publish → Deploy → Generate iOS / Android build.
2. Widget iOS (WidgetKit) & Android (AppWidget) memanggil `GET /api/widget/status` dengan token pengguna.
3. Refresh interval: iOS ~30 menit (Timeline), Android via WorkManager 30 menit.

## Testing
- Iter 6: 29/29 · Iter 7: 46/46 · Iter 8: 32/32 · Iter 9: 42/42 · Iter 10 (security): 64/64 · Iter 11 (RBAC normalisasi): 84/84 · Semua E2E frontend hijau.

Test credentials: `/app/memory/test_credentials.md`.
