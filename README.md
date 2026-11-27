# RuangKampus

**Find the Room. Book the Space.**

RuangKampus adalah aplikasi web untuk pencarian, pemeriksaan ketersediaan, dan pengajuan reservasi ruangan kampus. Paket ini berisi source code backend dan frontend yang digunakan oleh service produksi Railway pada **27 November 2026**, beserta dokumentasi, konfigurasi contoh, migration database, serta test.

## Snapshot source produksi

Rilis source ini menyatukan dua service produksi yang memang dibangun dari direktori berbeda di repository yang sama:

| Komponen | Service Railway | Branch deploy | Commit produksi |
|---|---|---|---|
| Backend API | `ruangkampus-api` | `develop` | `b9443b173d7898b4647219d239c52dbf8c2a7c76` |
| Frontend web | `ruangkampus-web` | `deploy/frontend-audit-remediation` | `0b6dfb0f5a0351dd542b231af83d83a1753d751c` |
| Database | PostgreSQL Railway | — | Data produksi tidak disertakan |

Folder `backend/` dan `frontend/` pada paket ini diambil dari commit service masing-masing. GitHub `main` menjadi snapshot gabungan untuk distribusi ZIP; Railway tetap menggunakan branch deployment yang sudah dikonfigurasi.

**URL produksi**
- Web: https://ruangkampus-web-production.up.railway.app/
- API: https://ruangkampus-api-production.up.railway.app/
- Swagger: https://ruangkampus-api-production.up.railway.app/api/v1/docs
- Readiness: https://ruangkampus-api-production.up.railway.app/ready

## Fitur utama

### Mahasiswa
- Login, registrasi mahasiswa, profil, dan pemulihan akun.
- Direktori ruangan, foto, fasilitas, kapasitas, serta informasi lokasi.
- Pemeriksaan ketersediaan dan pengajuan reservasi.
- Riwayat/status reservasi dan pusat notifikasi.
- RUKKA AI untuk percakapan dan bantuan pencarian ruangan. Pemeriksaan fakta ruangan dan ketersediaan tetap memakai data terverifikasi dari backend. Lapisan bahasa AI bersifat opsional dan menggunakan konfigurasi server-side OpenRouter.

### Staff Sekretariat
- Dashboard operasional dan pengelolaan data ruangan.
- Impor inventaris ruangan Excel (.xlsx), termasuk kapasitas, fasilitas, fakultas, lokasi, dan foto tertanam.
- Pengelolaan jadwal kuliah serta pemeliharaan ruangan.
- Pemeriksaan, persetujuan, penolakan, dan pembatalan reservasi sesuai aturan akses.
- Notifikasi dan aktivitas administrasi.

## Teknologi

- **Frontend:** React 19, TypeScript, Vite 8, React Router.
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic.
- **Database:** PostgreSQL.
- **Deployment produksi:** Railway (frontend dan backend sebagai service terpisah).

## Cara tercepat menjalankan paket lengkap (Docker)

Prasyarat: Docker Desktop dengan Docker Compose aktif.

1. Ekstrak ZIP ke folder kerja.
2. Salin konfigurasi contoh:
   - Windows PowerShell: `Copy-Item .env.example .env`
   - macOS/Linux: `cp .env.example .env`
3. Buka `.env`, ganti `JWT_SECRET_KEY` dengan nilai acak lokal minimal 32 byte. Untuk penggunaan lokal, biarkan email di `console`; jangan masukkan secret produksi.
4. Jalankan dari root repository:

```bash
docker compose up --build
```

Compose akan menjalankan PostgreSQL lokal, menjalankan migration Alembic pada database lokal tersebut, menyalakan API, membangun frontend, lalu menjalankan web server frontend.

Buka:
- Web: http://localhost:5173
- API docs: http://localhost:8000/api/v1/docs
- API health: http://localhost:8000/health
- API readiness: http://localhost:8000/ready

Folder foto lokal disimpan pada `.room-media/`. Database lokal disimpan pada Docker volume `ruangkampus-postgres`.

Hentikan service dengan:

```bash
docker compose down
```

Untuk menghapus database lokal beserta seluruh data uji, gunakan `docker compose down -v`. Perintah ini destruktif untuk data lokal.

## Menjalankan tanpa Docker

Lihat:
- [Backend setup](backend/README.md)
- [Frontend setup](frontend/README.md)

Ringkasnya, jalankan PostgreSQL development, salin `backend/.env.example` ke `backend/.env`, jalankan migration, lalu hidupkan FastAPI. Setelah itu salin `frontend/.env.example` ke `frontend/.env`, install npm dependencies, dan jalankan Vite.

## Pengujian

Backend:

```powershell
cd backend
python -m pip install -r requirements.txt
python -m pip install pytest ruff
$env:PYTHONPATH = "src"
pytest -q
ruff check src tests alembic
```

Frontend:

```powershell
cd frontend
npm install
npm run test
npm run build
```

Browser end-to-end:

```powershell
cd frontend
npx playwright install chromium
npm run test:e2e
```

PostgreSQL integration/migration tests membutuhkan PostgreSQL test database terpisah. Jangan arahkan test, migration development, atau Docker Compose ke database produksi.

## Konfigurasi dan keamanan

- `.env.example`, `backend/.env.example`, dan `frontend/.env.example` adalah template. Salin menjadi `.env` lokal dan isi sendiri.
- Jangan memasukkan API key, JWT secret produksi, SMTP password, database URL produksi, token, atau file private key ke repository/ZIP.
- RUKKA AI menggunakan `OPENROUTER_API_KEY` pada backend saja. Jangan pernah memasukkan key ke variabel `VITE_*`.
- `VITE_API_BASE_URL` adalah alamat API publik, bukan secret; nilainya di-embed ke bundle frontend pada waktu build.
- Gunakan database development terpisah. Paket source tidak menyertakan akun, data mahasiswa, reservasi, atau isi database produksi.
- Untuk foto ruangan di deployment, siapkan persistent volume dan atur `ROOM_MEDIA_DIR` ke direktori mount tersebut.

## Struktur repository

```text
backend/       FastAPI API, model, router, migration, dan backend tests
frontend/      React app, styles, dan browser/unit tests
docs/          Architecture, API contract, schema, setup dan QA notes
.github/       GitHub Actions CI
docker-compose.yml
.env.example
RELEASE_SOURCE.md
```

## Dokumentasi

- [Catatan source release dan verifikasi Railway](RELEASE_SOURCE.md)
- [Backend README](backend/README.md)
- [Frontend README](frontend/README.md)
- [Project architecture](docs/PROJECT_ARCHITECTURE.md)
- [API contract](docs/API_CONTRACT.md)
- [Database schema](docs/DATABASE_SCHEMA.md)
- [Development status](docs/DEVELOPMENT_STATUS.md)
- [RUKKA AI API contract](docs/AI_ASSISTANT_API_CONTRACT.md)
- [RUKKA/OpenRouter setup](docs/RAKA_OPENROUTER_SETUP.md)
- [Email/Brevo setup](docs/BREVO_EMAIL_SETUP.md)
