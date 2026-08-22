# Export 7 AI Control Center

## Problem statement
Aplikasi mobile berbahasa Indonesia untuk memantau dan mengendalikan server/backend serta tujuh AI ekspor dari satu control center yang aman dan mudah digunakan di HP.

## Architecture
- Expo SDK 54 / React Native mobile frontend.
- FastAPI + MongoDB backend melalui `/api`.
- APK hanya memanggil secure API; credential dan integrasi AI tetap server-side.
- Google OAuth terkelola ditukar sekali oleh backend menjadi session token 7 hari.
- RBAC server-side: SUPER ADMIN, ADMIN, KARYAWAN.

## User personas
- SUPER ADMIN: pemilik sistem dengan akses penuh.
- ADMIN: operator yang mengelola AI, target negara, dan server.
- KARYAWAN: operator read-only untuk dashboard dan interogasi.

## Core requirements (static)
- Dashboard telemetry server, status tujuh AI, target negara, aktivitas, dan error.
- Drawer navigation: Dashboard, 7 AI, Pilih Negara, Server, Interogasi Server, Akses/User, Pengaturan.
- Kontrol individual tujuh AI, bulk country controls, server actions, interrogation report.
- Authentication, RBAC, secure token storage, audit log, dan API terstruktur.

## Implemented (2026-02-14)
- Backend FastAPI dengan seed tujuh AI, daftar negara, telemetry server, session exchange, RBAC, audit log, dan endpoint control center.
- Frontend dark-first command center dengan Google login, secure session persistence, drawer navigation, dashboard, AI controls, country selector, server controls with confirmation, and diagnostics.
- UI mengikuti panduan amber/rust operational cards, status indicators, responsive mobile spacing, dan MaterialCommunityIcons.

## Prioritized backlog
- P0: Hubungkan adapter telemetry dan action ke server/AI production nyata; set `SUPER_ADMIN_EMAILS` dan `JWT_SECRET` production.
- P1: Implementasikan halaman Akses/User dan Pengaturan dengan permission matrix server-side.
- P1: Tambahkan push notifications untuk error dan perubahan status.
- P2: Tambahkan konfigurasi nama/fungsi AI dari backend dan dashboard histori metrik.
- P2: Tambahkan OpenAI hanya untuk fitur operasi yang didefinisikan; API key wajib tetap di backend.

## Next tasks
1. Berikan kontrak endpoint server/AI production untuk mengganti adapter control center.
2. Daftarkan akun Google operator dan masukkan email SUPER ADMIN di environment backend.
3. Tentukan use case OpenAI yang diperlukan (misalnya ringkasan log atau analisis buyer) sebelum menambahkan integrasi.