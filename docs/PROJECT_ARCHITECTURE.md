# Arsitektur Proyek RuangKampus

Dokumen ini menjelaskan susunan aplikasi, alur data, aturan keamanan, dan kondisi implementasi RuangKampus yang diperiksa pada 26 November 2026.

## 1. Stack dan layanan

| Lapisan | Teknologi | Peran |
|---|---|---|
| Frontend | React 19, TypeScript, Vite, React Router | Tampilan mahasiswa dan TU/Admin |
| Backend | Python, FastAPI | API, validasi, autentikasi, dan aturan bisnis |
| ORM | SQLAlchemy 2 | Membaca dan mengubah data database |
| Migrasi | Alembic | Mengelola perubahan struktur database |
| Database | PostgreSQL | Menyimpan akun, ruang, jadwal, reservasi, dan notifikasi |
| Hosting | Railway | Menjalankan frontend, API, dan PostgreSQL |
| CI | GitHub Actions | Tes otomatis dan pemeriksaan build |

Repository: `github.com/munggar/RuangKampus`. Pada saat pemeriksaan, Railway menggunakan branch `develop` sebagai sumber deployment. Perubahan perbaikan audit disimpan pada branch dan pull request terpisah; belum mengubah layanan produksi sebelum ditinjau, digabungkan, dan di-deploy.

## 2. Gambaran alur sistem

```text
Browser (Mahasiswa / TU-Admin)
          |
          v
React + TypeScript
          | HTTPS
          | access token + HttpOnly refresh cookie
          v
FastAPI /api/v1
          |
          +--> Authentication dan Role-Based Access Control
          |
          +--> Room, Availability, Reservation
          |
          +--> Schedule, Maintenance, Import
          |
          +--> User, Notification, Dashboard, Assistant
          |
          v
SQLAlchemy 2 + transaksi
          |
          v
PostgreSQL
```

Frontend menangani tampilan, formulir, navigasi, dan pemanggilan API. Backend menjadi sumber kebenaran untuk identitas pengguna, role, kapasitas ruang, benturan jadwal, serta status reservasi. Frontend tidak boleh menjadi satu-satunya lapisan yang memutuskan apakah pengguna boleh melakukan suatu tindakan.

## 3. Modul backend

- **Authentication:** login, refresh session, logout, reset kata sandi, dan pembatasan pendaftaran mahasiswa.
- **Users:** profil, pengelolaan akun, role, status, dan pencatatan perubahan Admin.
- **Rooms:** data ruang, lokasi, kapasitas, fasilitas, jam operasional, dan status.
- **Availability:** pemeriksaan ruang berdasarkan waktu, kapasitas, jadwal dan pemeliharaan.
- **Reservations:** pengajuan, pembatalan, persetujuan, penolakan, penyelesaian, dan pelacakan.
- **Schedules:** jadwal perkuliahan reguler/tanggal tertentu serta waktu ruang tidak tersedia.
- **Schedule imports:** unggah CSV/XLSX, pratinjau, validasi setiap baris, dan commit setelah konfirmasi Admin.
- **Notifications:** notifikasi in-app dan status percobaan email.
- **Discovery/Assistant:** pencarian ruang dan slot alternatif berbasis aturan dan data aplikasi.

## 4. Aturan ketersediaan dan reservasi

Sebuah ruang tidak langsung dianggap tersedia hanya karena belum memiliki reservasi. Backend memeriksa:

1. Status ruang masih aktif dan tidak sedang dihapus.
2. Kapasitas ruang cukup untuk jumlah peserta.
3. Waktu yang dipilih berada di dalam jam operasional ruang.
4. Tidak ada jadwal kuliah pada rentang waktu tersebut.
5. Tidak ada periode pemeliharaan atau penutupan ruang.
6. Tidak ada reservasi lain berstatus menunggu atau disetujui yang waktunya bertumpang tindih.

Status `PENDING` dan `APPROVED` memblokir slot waktu. Status `REJECTED`, `CANCELLED`, dan `COMPLETED` tidak lagi memblokir pemakaian mendatang. Pembuatan dan persetujuan reservasi melakukan pemeriksaan ulang di dalam transaksi database dan mengunci ruang agar dua permintaan yang beradu tidak sama-sama mengambil slot yang sama.

## 5. Autentikasi dan hak akses

- Password di-hash menggunakan Argon2id.
- Access token JWT memiliki masa berlaku pendek.
- Refresh token dikirim dalam cookie HttpOnly dan disimpan sebagai hash di tabel session.
- Backend memeriksa session, status akun, dan role yang tersimpan di database pada endpoint terlindungi.
- Student dan TU/Admin memiliki batas akses berbeda; mahasiswa hanya dapat membaca reservasinya sendiri.
- Logout mencabut refresh session dan membersihkan cookie, termasuk setelah access token kedaluwarsa.
- Pendaftaran mandiri mahasiswa dinonaktifkan sampai NIM dapat dicocokkan dengan daftar kampus resmi. Admin dapat membuat akun setelah verifikasi manual berdasarkan sumber resmi. Integrasi otomatis dengan data induk kampus belum tersedia.

## 6. Email dan asisten pencarian

Email reset kata sandi serta notifikasi memakai layanan SMTP bila dikonfigurasi. Ketika audit dilakukan, email produksi masih dalam mode disabled dan alamat kontak Admin berupa alamat contoh. Karena itu, fitur email belum boleh dianggap siap sampai mailbox dan kredensial SMTP nyata tersedia dan pengiriman benar-benar diuji.

Asisten RuangKampus adalah asisten pencarian berbasis aturan, bukan AI generatif. Asisten mengurai permintaan umum seperti jumlah peserta, gedung, fasilitas, hari, dan jam untuk membantu pencarian. Reservasi tetap harus diajukan dan disetujui melalui alur normal.

## 7. Deployment dan pengujian

Railway menjalankan frontend, API, dan PostgreSQL di lingkungan produksi. CI backend menguji lint, tes SQLite, integrasi PostgreSQL, migrasi upgrade/downgrade, audit kerentanan dependensi, dan Docker build. CI frontend menjalankan tes dan production build. Hasil CI yang lulus bukan bukti bahwa semua alur pengguna sudah lulus uji browser; tes end-to-end dan uji beban tetap diperlukan di staging.

Branch produksi yang diperiksa adalah `develop`; sinkronisasi dengan `main` harus dilakukan melalui proses pull request dan pemeriksaan konflik, bukan merge paksa. Perubahan audit yang masih berada pada PR tidak otomatis masuk ke Railway.

## 8. Keterbatasan dan pekerjaan lanjutan

- Daftar NIM resmi, identitas, dan kontak mahasiswa harus disediakan unit kampus; sampai itu tersedia, pemeriksaan dilakukan manual oleh Admin.
- Mailbox operasional dan kredensial SMTP belum tersedia pada audit terakhir.
- Data ruang, kapasitas, jam buka, jadwal kuliah, serta pemeliharaan harus disahkan unit terkait.
- Format spreadsheet jadwal kampus aktual harus dicocokkan dengan parser CSV/XLSX sebelum digunakan.
- Rate limit saat ini disimpan per proses; sebelum menambah worker/replica, konfigurasi proxy tepercaya dan pembatasan terpusat melalui gateway/WAF atau Redis.
- Tes end-to-end browser dan load test dengan data realistis diperlukan sebelum aplikasi diluncurkan secara luas.
- Unggah foto langsung belum tersedia; profil masih menggunakan URL gambar.
- Asisten tetap berbasis aturan sampai ada kebutuhan dan keputusan khusus untuk memakai AI generatif.

## 9. Rekomendasi pelepasan versi

Lakukan uji coba terbatas setelah data mahasiswa dan data ruang/jadwal resmi divalidasi, proses pemulihan akun tersedia (SMTP atau prosedur manual aman), serta alur mahasiswa dan Admin diuji langsung pada staging. Jangan memperluas penggunaan kampus hanya berdasarkan keberhasilan build dan tes backend.
