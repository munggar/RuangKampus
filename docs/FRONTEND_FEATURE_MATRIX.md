# RuangKampus — Frontend Feature Matrix

Dokumen ini memetakan 15 fitur utama ke halaman frontend dan kontrak API. Seluruh halaman dibuat agar dapat ditampilkan sebelum backend dipublikasikan; operasi data memerlukan API yang aktif dan `VITE_API_BASE_URL` yang sesuai.

| No. | Fitur | Tampilan / halaman frontend | Kontrak backend |
|---:|---|---|---|
| 1 | Authentication & Authorization | Login, pemulihan kata sandi, route guard Student dan Staff Sekretariat | `/auth/login`, `/auth/refresh`, `/auth/logout`, route authorization |
| 2 | Student Dashboard | `/student/dashboard` — ringkasan aktivitas, sesi berikutnya, permohonan terbaru | `/dashboard/summary`, `/dashboard/recent-reservations` |
| 3 | Staff Sekretariat Dashboard | `/admin/dashboard` — ringkasan reservasi dan inventaris | `/dashboard/summary`, `/dashboard/room-statistics` |
| 4 | Room Management | `/admin/rooms`, tambah/edit ruangan; termasuk jam operasi dan status | `/rooms` (GET/POST), `/rooms/{id}` (GET/PATCH/DELETE) |
| 5 | Smart Room Availability | `/student/availability` — pemeriksaan tanggal, waktu, peserta, dan hasil ruang tersedia | `GET /rooms` dengan date/time filter; `GET /rooms/{id}/availability` |
| 6 | Room Search & Filter | `/student/rooms` — pencarian, fakultas, gedung, lokasi, kapasitas, fasilitas; waktu di halaman ketersediaan | `GET /rooms` dengan search, faculty, building, location, capacity, facilities, date, startTime, endTime |
| 7 | Online Room Reservation | `/student/rooms/{id}/book` — formulir, validasi, tinjauan, pengajuan | `POST /reservations` |
| 8 | Staff Sekretariat Approval System | `/admin/reservations` dan detail — persetujuan/penolakan dengan alasan | `PATCH /reservations/{id}/approve`, `PATCH /reservations/{id}/reject` |
| 9 | Conflict Detection | Di halaman ketersediaan dan formulir booking; Staff Sekretariat mendapat validasi ulang saat approve | `GET /rooms/{id}/availability`; approval mengembalikan konflik sebagai HTTP 409 |
| 10 | Reservation Tracking | `/student/reservations` dan `/student/reservations/{id}` — status, detail, pembatalan | `GET /reservations`, `GET /reservations/{id}`, `PATCH /reservations/{id}/cancel` |
| 11 | Chatbot / AI Room Assistant | `/student/assistant` — percakapan pencarian ruangan khusus Mahasiswa; tidak ada halaman atau menu assistant untuk Staff Sekretariat | `POST /assistant/chat` hanya mengizinkan role Student; tidak ada endpoint assistant khusus Staff Sekretariat |
| 12 | Notification System | `/student/notifications`, `/admin/notifications` — feed, status baca, status email | `GET /notifications`, `PATCH /notifications/{id}/read` |
| 13 | Room Location Information | Detail ruangan dan form Staff Sekretariat menampilkan/mengelola fakultas, gedung, lantai, lokasi detail | Field `faculty`, `building`, `floor`, `location_description` pada Room |
| 14 | Room Facility Information | Kartu/detail ruangan dan form Staff Sekretariat: fasilitas, kapasitas, deskripsi/perlengkapan | Field `facilities`, `capacity`, `description` pada Room |
| 15 | Alternative Slot Recommendation | `/student/alternatives`; dapat dibuka dari hasil ketersediaan | `POST /rooms/alternative-slots` |

## Catatan integrasi

- Frontend menggunakan prefix API `/api/v1` melalui `VITE_API_BASE_URL`.
- Availability dan rekomendasi alternatif merupakan hasil pemeriksaan pada saat permintaan dijalankan. Backend tetap wajib memvalidasi ulang ketika reservasi dikirim dan disetujui.
- Endpoint assistant menghasilkan pencarian berbasis aturan (`RULE_BASED`), bukan layanan LLM eksternal. Fitur ini hanya tersedia untuk Mahasiswa. Frontend tidak menampilkan AI Assistant pada workspace Staff Sekretariat, route lama `/admin/assistant` mengarahkan kembali ke dashboard, dan backend tetap menolak akses Staff Sekretariat ke endpoint chat maupun alternative-slots.
- Konflik tidak menjadi keputusan yang dihitung oleh frontend. Informasi alasan konflik berasal dari backend; proses approve adalah pemeriksaan final.
- Halaman dapat dibuka setelah frontend di-build, tetapi autentikasi dan data dinamis belum berfungsi sampai API tersedia serta konfigurasi CORS/cookie sesuai dengan domain frontend.
