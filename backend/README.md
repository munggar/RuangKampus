# RuangKampus Backend

Backend aplikasi RuangKampus menggunakan Python, FastAPI, SQLAlchemy 2, Alembic, dan PostgreSQL.

## Kondisi saat ini

- API backend berjalan di Railway bersama layanan frontend dan PostgreSQL.
- Branch produksi terhubung ke Railway adalah `develop`.
- Kode perbaikan hasil audit disiapkan melalui pull request terpisah dan belum mengubah layanan produksi sampai PR digabungkan dan berhasil di-deploy.
- GitHub Actions menguji backend menggunakan SQLite terisolasi dan PostgreSQL sementara, termasuk migrasi, pemeriksaan konkurensi reservasi, lint, audit kerentanan, dan Docker build.
- Email produksi pada audit terakhir masih dinonaktifkan karena mailbox dan SMTP operasional belum dikonfigurasi.

## Teknologi dan modul

- **FastAPI** — endpoint REST dan OpenAPI.
- **SQLAlchemy 2** — akses dan transaksi database.
- **Alembic** — migrasi database.
- **PostgreSQL** — database deployment.
- **Argon2id dan JWT** — hashing kata sandi, access token, dan refresh session.
- Router: auth, users, rooms, reservations, schedules, schedule imports, notifications, dashboard, dan discovery/assistant.
- Service: availability, schedule import, email, dan validasi reservasi.

## Persyaratan lokal

- Python 3.11+ (Python 3.12 direkomendasikan).
- PostgreSQL 15+ untuk lingkungan development bersama.
- pip.

Dari root repository, jalankan PowerShell:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Atur variabel privat di `.env`:

```dotenv
APP_ENV=development
DATABASE_URL=postgresql+psycopg://USERNAME:PASSWORD@HOST:5432/ruangkampus_dev
JWT_SECRET_KEY=replace-with-a-long-random-local-secret
CORS_ORIGINS=http://localhost:5173
COOKIE_SECURE=false
EMAIL_BACKEND=disabled
```

Untuk smoke test lokal terisolasi, SQLite dapat digunakan:

```dotenv
DATABASE_URL=sqlite:///./ruangkampus_local.db
```

SQLite tidak membuktikan perilaku row-lock PostgreSQL. Jangan menjalankan perintah migrasi atau tes terhadap database produksi.

## Variabel lingkungan

| Variabel | Kegunaan |
|---|---|
| `APP_ENV` | Mode `development` atau `production` |
| `DATABASE_URL` | URL koneksi SQLAlchemy |
| `JWT_SECRET_KEY`, `JWT_ALGORITHM` | Penandatanganan access token |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Masa berlaku access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Masa berlaku refresh session |
| `PASSWORD_RESET_EXPIRE_MINUTES` | Masa berlaku token reset kata sandi |
| `CORS_ORIGINS` | Daftar origin frontend tepercaya |
| `COOKIE_SECURE`, `COOKIE_SAMESITE` | Pengaturan cookie refresh |
| `CAMPUS_TIMEZONE` | Zona waktu kampus; default `Asia/Jakarta` |
| `EMAIL_BACKEND` | `console` untuk lokal, `smtp`, atau `disabled` |
| `PASSWORD_RESET_BASE_URL` | URL halaman reset pada frontend |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_USE_TLS` | Konfigurasi provider SMTP |

Jangan pernah memasukkan password, token, URL database berisi kredensial, atau rahasia lain ke Git. Variabel dengan awalan `VITE_` adalah konfigurasi frontend dan tidak boleh berisi rahasia.

## Migrasi database

Migrasi berada pada `alembic/versions/`.

```powershell
$env:PYTHONPATH = "src"
alembic upgrade head
alembic check
```

Periksa target `DATABASE_URL` sebelum setiap migrasi. Jalankan pada database development/staging terlebih dahulu. Jangan gunakan database produksi sebagai database tes.

## Akun Admin dan akun mahasiswa

- Akun Admin pertama dibuat oleh operator melalui CLI tepercaya: `PYTHONPATH=src python -m ruangkampus.cli create-admin`.
- Backend mendukung lebih dari satu akun TU/Admin.
- Pendaftaran mahasiswa mandiri sementara ditutup sampai NIM diverifikasi menggunakan daftar resmi kampus.
- TU/Admin dapat membuat akun mahasiswa melalui endpoint Admin setelah memeriksa nama, NIM, dan kontak dari sumber data kampus. Endpoint menolak email/NIM duplikat dan menyimpan kata sandi dalam bentuk hash.
- Perubahan status, role, serta penghapusan/nonaktif akun dicatat pada riwayat aktivitas Admin.
- Jangan menggunakan alamat contoh seperti `admin.uhamka@example.com` untuk pemulihan akun. Masukkan mailbox resmi yang benar melalui proses operasional dan uji pengiriman email.

## Menjalankan API

```powershell
$env:PYTHONPATH = "src"
uvicorn ruangkampus.main:app --reload --host 127.0.0.1 --port 8000
```

- Health check: `GET /health`
- Readiness check: `GET /ready`
- Swagger UI: `http://127.0.0.1:8000/api/v1/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/api/v1/openapi.json`

## Kelompok endpoint utama

| Area | Kegunaan |
|---|---|
| `/auth` | Login, refresh, logout, registrasi yang dibatasi, reset kata sandi |
| `/users` | Profil, daftar pengguna, pembuatan akun mahasiswa dan pengelolaan role/status |
| `/rooms` | Direktori, detail, dan pemeriksaan ketersediaan ruang |
| `/reservations` | Pengajuan, pembatalan, persetujuan, penolakan, dan penyelesaian reservasi |
| `/admin/schedules` | Jadwal kuliah dan periode pemeliharaan |
| `/admin/schedules/imports` | Pratinjau, validasi, konfirmasi, dan riwayat impor CSV/XLSX |
| `/admin/activity` | Riwayat perubahan yang dilakukan Admin |
| `/notifications` | Notifikasi in-app dan status pengiriman email |
| `/assistant` | Bantuan pencarian ruang berbasis aturan dan data aplikasi |

## Keamanan dan integritas data

- Kata sandi disimpan menggunakan Argon2id, bukan teks biasa.
- Access token berdurasi pendek; refresh token disimpan sebagai hash dan dikirim melalui HttpOnly cookie.
- API memeriksa status akun dan role yang tersimpan pada database.
- Mahasiswa hanya dapat melihat reservasi dan notifikasinya sendiri.
- Kapasitas, jam operasional, jadwal kuliah, periode pemeliharaan, serta reservasi aktif diperiksa sebelum ruang disetujui.
- Transaksi pembuatan dan persetujuan reservasi melakukan pemeriksaan ulang dengan lock pada database PostgreSQL.
- Logout mencabut refresh session dan membersihkan cookie, termasuk ketika access token sudah kedaluwarsa.
- Rate limit saat ini per proses. Gunakan shared gateway/WAF atau Redis sebelum meningkatkan jumlah worker/replica.

## Tes otomatis

Dari direktori `backend`:

```powershell
$env:PYTHONPATH = "src"
pytest -q
ruff check src tests
ruff format --check src tests
```

Tes PostgreSQL khusus dijalankan oleh GitHub Actions menggunakan database sementara. Jalankan tes hanya pada database terisolasi, bukan database kampus/produksi.

## Masih perlu disiapkan

1. Daftar NIM resmi dan kontak mahasiswa dari unit kampus yang berwenang.
2. Mailbox Admin serta host, port, username, password, dan alamat pengirim SMTP yang sah.
3. Dataset ruang dan jadwal resmi yang sudah divalidasi.
4. Validasi format Excel/CSV jadwal aktual sebelum impor operasional.
5. Uji end-to-end browser, mobile, dan load test di staging.
6. Konfigurasi proxy/IP tepercaya dan rate limit bersama sebelum horizontal scaling.

Untuk gambaran produk dan deployment secara menyeluruh, baca [README root](../README.md), [status pengembangan](../docs/DEVELOPMENT_STATUS.md), dan [arsitektur proyek](../docs/PROJECT_ARCHITECTURE.md).
