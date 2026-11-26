# RuangKampus

RuangKampus adalah aplikasi pencarian dan peminjaman ruang kampus. Mahasiswa dapat mencari ruang, memeriksa ketersediaan, mengajukan reservasi, dan memantau keputusannya. TU/Admin mengelola data ruang, jadwal, pemeliharaan, akun, serta persetujuan peminjaman.

## Kondisi aplikasi saat ini

- Frontend, API, dan PostgreSQL sudah berjalan di Railway.
- Branch produksi yang terhubung ke Railway adalah `develop`.
- Frontend: [RuangKampus Web](https://ruangkampus-web-production.up.railway.app/).
- API: [RuangKampus API](https://ruangkampus-api-production.up.railway.app/).
- Dokumentasi API: [Swagger UI](https://ruangkampus-api-production.up.railway.app/api/v1/docs).
- Kode perbaikan audit sedang disiapkan pada pull request terpisah. Perubahan di pull request belum mengubah aplikasi produksi sampai ditinjau, digabungkan ke `develop`, dan berhasil di-deploy.

## Fitur yang tersedia

### Mahasiswa
- Melihat dan mencari ruang berdasarkan nama, gedung, fakultas, kapasitas, dan fasilitas.
- Memeriksa ketersediaan berdasarkan waktu yang diminta.
- Mengajukan reservasi, melihat status, membatalkan, dan menerima notifikasi.
- Mengelola profil, kata sandi, tema tampilan, dan menggunakan asisten pencarian berbasis aturan.

### TU/Admin
- Mengelola ruang, kapasitas, fasilitas, dan jam operasional.
- Mengatur jadwal kuliah dan periode pemeliharaan.
- Memeriksa, menyetujui, menolak, dan menyelesaikan reservasi.
- Mengelola akun pengguna dan melihat riwayat aktivitas.
- Memeriksa file jadwal CSV/XLSX sebelum mengimpor data.

## Teknologi

| Bagian | Teknologi |
|---|---|
| Frontend | React 19, TypeScript, Vite, React Router |
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| ORM dan migrasi | SQLAlchemy 2, Alembic |
| Login | JWT access token, HttpOnly refresh cookie, Argon2id |
| Hosting | Railway |
| Otomatisasi tes | GitHub Actions |

## Alur data singkat

Browser mahasiswa/Admin → frontend React → API FastAPI melalui HTTPS → SQLAlchemy → PostgreSQL.

Backend memeriksa role pengguna, status akun, kapasitas ruang, jam operasional, jadwal kuliah, masa pemeliharaan, dan reservasi lain sebelum menerima atau menyetujui peminjaman. Pembuatan dan persetujuan reservasi memeriksa ulang ketersediaan dalam transaksi database agar dua peminjaman tidak memakai ruang yang sama pada waktu tumpang tindih.

## Keamanan akun mahasiswa

Pendaftaran mandiri sementara dinonaktifkan sampai NIM dapat dicocokkan dengan daftar resmi mahasiswa. TU/Admin dapat membuat akun setelah memeriksa nama, NIM, dan kontak dengan sumber data kampus yang berwenang. Sistem belum terhubung otomatis ke basis data induk UHAMKA, sehingga pemeriksaan ini masih dilakukan oleh Admin.

## Pengaturan email dan pemulihan kata sandi

Backend sudah memiliki alur token reset kata sandi dan dukungan SMTP. Namun, pada pemeriksaan terakhir pengiriman email produksi masih dinonaktifkan. Pemulihan email belum bisa diandalkan sampai alamat pengirim resmi, host SMTP, kredensial, dan alamat email operasional Admin dikonfigurasi dan diuji.

## Menjalankan aplikasi secara lokal

### Backend
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Atur `DATABASE_URL`, `JWT_SECRET_KEY`, `CORS_ORIGINS`, dan konfigurasi email sesuai kebutuhan lokal. Gunakan database pengembangan terpisah, bukan database produksi.

```powershell
$env:PYTHONPATH = "src"
alembic upgrade head
uvicorn ruangkampus.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend
```powershell
cd frontend
npm install
```

Atur `VITE_API_BASE_URL=http://localhost:8000/api/v1` di file environment frontend, lalu jalankan:

```powershell
npm run dev
```

Lihat [backend/README.md](backend/README.md) untuk konfigurasi variabel, migrasi, pembuatan akun Admin, dan cara menjalankan tes.

## Pemeriksaan otomatis

GitHub Actions menjalankan tes backend, pemeriksaan migrasi PostgreSQL, tes konkurensi, audit kerentanan dependensi, tes frontend, dan production build. Keberhasilan CI menunjukkan pemeriksaan otomatis lulus; hal itu tidak menggantikan tes alur pengguna langsung di browser dan uji beban.

## Batasan yang masih perlu ditangani

1. Daftar NIM resmi dan kontak mahasiswa harus disediakan serta divalidasi oleh unit kampus.
2. Email pemulihan perlu alamat pengirim dan kredensial SMTP yang sah.
3. Data ruang, kapasitas, jam operasional, jadwal kuliah, dan pemeliharaan perlu disahkan unit terkait.
4. Proxy dan pembatasan permintaan perlu ditinjau sebelum menambah worker/replica; rate limit saat ini disimpan per proses.
5. Tes browser end-to-end dan uji beban dengan data realistis tetap diperlukan sebelum peluncuran luas.

## Dokumentasi proyek

- [Status pengembangan](docs/DEVELOPMENT_STATUS.md)
- [Arsitektur proyek](docs/PROJECT_ARCHITECTURE.md)
- [Kontrak API](docs/API_CONTRACT.md)
- [Skema database](docs/DATABASE_SCHEMA.md)
- [Kepemilikan fitur](docs/FEATURE_OWNERSHIP.md)
