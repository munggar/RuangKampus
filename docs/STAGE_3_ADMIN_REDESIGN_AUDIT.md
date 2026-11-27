# Stage 3 — Audit Awal Dashboard TU/Admin

Tanggal: 27 November 2026  
Status: Audit selesai; implementasi belum dimulai.

## Cakupan route dan halaman

Semua route operasional memakai `/admin` dan dilindungi `RequireRole` untuk role `Staff Sekretariat`. Tipe role frontend hanya `Student` dan `Staff Sekretariat`; tidak ada role terpisah bernama Admin. Struktur route yang akan dipertahankan:

| Route | Halaman/kemampuan saat ini | Data dan workflow yang harus dipertahankan |
|---|---|---|
| `/admin/dashboard` | Ringkasan statistik, pemantauan sesi hari ini/keterlambatan, permohonan terbaru, statistik reservasi per ruangan, akses cepat. | `GET /dashboard/summary`, `/dashboard/recent-reservations`, `/dashboard/room-statistics`; daftar reservasi disetujui hari ini; aksi konfirmasi ruangan kosong memanggil endpoint complete setelah konfirmasi. |
| `/admin/reservations` | Filter status, pencarian nama/ruang/ID/tujuan, kartu permohonan, approve dan reject dengan alasan. | `GET /reservations`; `PATCH .../approve` dan `.../reject`; backend tetap memeriksa konflik, jadwal, kapasitas, dan permission. Saat ini meminta maksimum 100 dan pencarian dilakukan di browser. |
| `/admin/reservations/:reservationId` | Detail reservasi dan pembatalan override oleh TU dengan alasan. | `GET /reservations/:id`, `PATCH .../cancel`; kebijakan role dan alasan wajib tetap utuh. Komponen detail berbagi `ReservationDetailPage` dengan mahasiswa. |
| `/admin/rooms` | Inventaris dalam card, pencarian, filter status, pilih banyak, ubah status/jam operasional, edit, nonaktifkan. | `GET /rooms`, bulk status, bulk jam, delete soft; operasi massal tetap atomic dan gagal tanpa perubahan parsial. Saat ini mengambil maksimum 100 ruangan dan mencari di browser. |
| `/admin/rooms/new`, `/admin/rooms/:roomId/edit` | Form ruangan dan jam operasional. | `GET/POST/PATCH /rooms`; field dan validasi kapasitas, hari, jam, status, fasilitas, serta lokasi tetap. |
| `/admin/schedules` | Tambah jadwal kuliah atau blok pemeliharaan; tabel jadwal dan blok aktif. | `/admin/schedules`, `/admin/room-unavailability`; conflict check dan pembatalan/nonaktifkan existing tetap. Daftar ruang dibatasi ke permintaan 100. |
| `/admin/data-imports` | Impor XLSX ruangan: pilih/upload, pratinjau, validasi, commit dengan konfirmasi, riwayat; modul lain tampil nonaktif karena sumber belum ada. | `/admin/rooms/imports/preview`, `/commit`, dan riwayat. Batas 5 MB dan `.xlsx`, reset preview/error serta seluruh pemetaan workbook tidak berubah. |
| `/admin/notifications` | Notifikasi, status baca, delivery state, tandai dibaca. | `GET /notifications`, `PATCH /notifications/:id/read`; memicu event `rk-notifications-updated`. Halaman berbagi komponen dengan mahasiswa. |
| `/admin/profile` | Profil akun, ubah data, ubah password, tema. | `/users/me` dan `/users/me/password`, logout setelah password berubah; theme tetap menggunakan `rk-theme`, `data-theme`, dan `rk-theme-change`. Halaman berbagi komponen dengan mahasiswa. |

Komponen bersama yang tersedia untuk digunakan kembali: `PageTitle`, `PageSection`, `Button`, `Field`, `StatusBadge`, `Notice`, `Loading`, `EmptyState`, `Modal`, dan `ConfirmModal`. Style bersama ada di `frontend/src/styles.css`; semantic tokens dan tema ada di `frontend/src/styles/tokens.css`.

## Sumber data dashboard yang terverifikasi

- **Ringkasan:** `GET /dashboard/summary` mengembalikan hitungan total reservasi lintas status; untuk TU juga `total_rooms`, `active_rooms`, dan `total_users`. Nilai status adalah total historis, bukan periode berjalan.
- **Aktivitas hari ini:** dashboard meminta reservasi berstatus `APPROVED` sampai tanggal hari ini, `limit=100`, lalu menghitung timer berdasarkan waktu kampus Asia/Jakarta. Endpoint ini juga menjaga aksi “konfirmasi ruangan kosong”.
- **Permohonan terbaru:** `GET /dashboard/recent-reservations?limit=...` mengurutkan berdasarkan `submitted_at` terbaru. Data mengandung pemohon dan ringkasan ruang untuk TU.
- **Popular rooms:** `GET /dashboard/room-statistics` menghitung jumlah reservasi berstatus `APPROVED` dan `COMPLETED` per ruang. Endpoint menerima `dateFrom`/`dateTo`; tanpa parameter hasilnya sepanjang waktu. Ini adalah jumlah reservasi, bukan persentase okupansi atau durasi penggunaan.
- **Belum tersedia pada endpoint yang ditemukan:** tren reservasi harian/mingguan, durasi okupansi aktual, kapasitas waktu operasional agregat, dan slot bebas real-time seluruh gedung. Jangan membuat seri statistik, persentase, atau ketersediaan langsung dari angka total ini. Dashboard boleh menunjukkan distribusi status dari summary dan jumlah reservasi per ruang; label dan periode harus eksplisit. Untuk tren, tunjukkan empty state atau tidak tampilkan grafik sampai ada sumber data memadai.
- **Ketersediaan aktual:** layanan backend memeriksa jam operasional, jadwal, blok tidak tersedia, status ruang, kapasitas, serta reservasi untuk ruang/tanggal/waktu tertentu. Tidak ada endpoint agregasi “tersedia sekarang” yang cocok untuk angka dashboard umum.

## Komponen, state, dan potensi regresi

- Pola data tabel sudah menggunakan wrapper `.table-wrap`; daftar reservasi TU saat ini berupa kartu, daftar ruang berupa grid card, dan jadwal/riwayat/impor menggunakan tabel. Halaman data import berisi preview tabel lebar yang memang memerlukan scroll terkurung.
- `PageResult<T>` mengandung `meta` pagination, dan backend daftar room/reservations mengembalikan `page`, `limit`, `total`, `total_pages`. UI TU sekarang umumnya meminta `limit=100` dan belum menyajikan pagination pada kedua list utama. Apabila pagination diperbaiki, parameter API tetap sama; tidak boleh hanya membatasi data secara lokal tanpa memberi tahu total.
- Halaman notifikasi dan profil berbagi implementasi dengan mahasiswa. Perubahan CSS harus dibatasi selector admin atau komponen tanpa mengubah tampilan/flow mahasiswa yang bukan cakupan Stage 3.
- `ConfirmModal`/`Modal`, status, validasi, loading, empty, error, dan disabled states sudah tersedia; tingkatkan style tanpa mengganti semantik atau callback.
- Potensi regresi paling tinggi: role guard, event/theme persistence, aksi complete di dashboard, approval/rejection, atomic bulk room edits, import preview/commit, serta pembacaan keyboard/focus pada dialog.
- Tidak ada perubahan backend/API/database yang dibutuhkan untuk ringkasan status dan ranking jumlah reservasi per ruang. Tren waktu dan okupansi tidak dapat dipenuhi dengan data saat ini dan tetap di luar cakupan backend stage ini.

## Aturan desain yang dipakai

Identitas visual mengikuti `docs/DESIGN_SYSTEM.md`: wordmark resmi tanpa modifikasi; Plus Jakarta Sans Variable; `@tabler/icons-react`; token warna dan surface resmi; radius/spacing yang sudah ditetapkan; serta tema `data-theme` dengan mekanisme `rk-theme` yang ada. Dashboard berorientasi kerja: hirarki informasi jelas, statistik berlabel definisi/periode, warna status tidak berdiri sendiri, tabel tetap dapat dipindai di layar sempit, dan motion tidak menghambat aksi. Tidak menggunakan data palsu, angka ilustrasi, dependency visualisasi baru, atau fitur yang tidak memiliki dukungan route/data.

## Pemeriksaan skill untuk Stage 3

- Skill prioritas beserta isi lengkap dan audit ketersediaannya tercatat di `docs/INSTALLED_DESIGN_SKILLS_AUDIT.md`.
- Untuk Stage 3, referensi yang relevan sudah dibaca: panduan web `references/command.md`, token/component/state milik `design-system`, accessibility/theme/responsive milik `ui-styling`, visual identity/logo/color/typography milik `brand`, dan seluruh referensi `ui-motion`.
- CLI `ui-ux-pro-max` tidak dijalankan karena Python tidak tersedia; aturan Quick Reference digunakan secara manual sesuai instruksi skill.
- `ui-styling` dipakai sebagai panduan prinsip aksesibilitas dan komposisi saja; contoh Tailwind/shadcn tidak diterapkan karena frontend ini memakai React/Vite/CSS dan tidak memasang stack tersebut.
