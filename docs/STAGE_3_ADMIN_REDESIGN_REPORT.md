# Stage 3 — Redesain Dashboard TU/Admin

## Ringkasan

Redesain visual diterapkan pada workspace TU (`Staff Sekretariat`) dengan token dan aset resmi RuangKampus. Cakupan halaman mengikuti route admin yang sudah ada. Permission, route, kontrak endpoint, validasi server, serta urutan kerja bisnis tetap menggunakan implementasi yang sudah tersedia.

Implementasi tidak menambahkan tren pemakaian, okupansi aktual, atau status ketersediaan langsung karena endpoint yang tersedia tidak menyediakan metrik tersebut.

## Perubahan

- Dashboard menampilkan kartu ringkasan status reservasi dan inventaris, distribusi semua status, peringkat ruang berdasarkan jumlah reservasi disetujui/selesai, antrian permohonan pending, pemantauan jadwal hari ini, tabel permohonan terbaru, dan tautan akses cepat.
- Grafik memakai nilai nyata dari `GET /dashboard/summary` dan `GET /dashboard/room-statistics`. Label menerangkan cakupan hitungannya. Pemantauan hari ini menggunakan `dateFrom` dan `dateTo` agar daftar tidak menarik reservasi lama yang belum selesai.
- Aksi setujui/tolak dari antrian dashboard memakai endpoint reservasi yang sama seperti halaman tinjauan. Penolakan tetap memerlukan alasan minimal tiga karakter. Persetujuan tetap meminta konfirmasi dan pemeriksaan akhir backend.
- Halaman permohonan mendapat filter tanggal awal/akhir yang menggunakan parameter API `dateFrom`/`dateTo`, selain tab status dan pencarian yang sudah ada.
- Halaman jadwal menata dua formulir menjadi kolom sejajar pada layar lebar dan satu kolom pada layar sempit.
- Inventaris, editor ruangan, impor, jadwal, dashboard, serta halaman bersama profil/notifikasi/detail mendapat penyempurnaan tampilan yang dibatasi pada shell TU. Halaman mahasiswa tidak memakai modifier CSS admin.
- Tipe hasil endpoint ringkasan dashboard diperjelas menjadi `DashboardSummary`, sesuai model data yang sudah ada.
- Matriks visual admin ditambahkan di `frontend/e2e/stage3-admin-visual.spec.ts` untuk memeriksa keterlihatan heading, tema, overflow horizontal, dan menyimpan tangkapan layar.

## Halaman yang dicakup

- `/admin/dashboard`
- `/admin/reservations` dan `/admin/reservations/:reservationId`
- `/admin/rooms`, `/admin/rooms/new`, dan `/admin/rooms/:roomId/edit`
- `/admin/schedules`
- `/admin/data-imports`
- `/admin/notifications` dan `/admin/profile` (komponen berbagi dengan mahasiswa, styling dibatasi pada shell admin)

Detail reservasi, notifikasi, dan profil tetap menggunakan komponen serta alur yang sudah ada. Tidak ada route atau role baru.

## Identitas dan perilaku UI

- Warna, permukaan, status, fokus, radius, dan gerak merujuk pada design tokens RuangKampus; tidak ada palet brand atau font baru.
- Tipografi Plus Jakarta Sans, ikon Tabler, logo resmi, light/dark theme, dan preferensi reduced motion tetap dipakai.
- Konten statistik diberi label cakupan. Tidak ada angka tren atau okupansi hasil perkiraan.
- Grid dashboard menjadi 4 kolom di desktop, 2 kolom pada tablet, dan 1 kolom pada layar sempit. Analitik serta formulir jadwal berubah menjadi satu kolom di mobile.
- Tabel tetap dapat digulir di dalam pembungkusnya. Kontrol, tombol aksi, dialog, dan validasi yang ada dipertahankan.

## Verifikasi

- `npm test`: **8/8 tes unit lulus**.
- Build TypeScript dan Vite produksi: **lulus** dengan `npx tsc --noEmit` dan `npx vite build`.
- Playwright matriks visual: **lulus**, 60 screenshot untuk 10 route admin pada 1440 px (light/dark), 1280 px, 768 px, 390 px, dan 360 px. Pemeriksaan memastikan tidak ada overflow horizontal dan mock API tidak memiliki route yang tidak dipetakan.
- Playwright axe dan workflow admin: **39 kasus melaporkan `ok`** pada pemilihan test yang mencakup aksesibilitas semua halaman admin dalam light/dark, dialog keyboard, autentikasi/role guard, approve/reject, editor ruangan, jadwal, impor, dan navigasi mobile admin. Runner tetap terbuka setelah hasil terakhir dan perlu dihentikan manual, sehingga ringkasan akhir Playwright tidak tercetak.
- Screenshot tersimpan di `frontend/test-results/stage-3/`, dikelompokkan menurut ID route. Matriks menggunakan data fixture browser; bukan data production.

Catatan test environment: preview E2E memerlukan `VITE_API_BASE_URL=/api/v1` agar request melewati mock fixture. Percobaan pertama tanpa base API membuka preview/login statis dan tidak dianggap sebagai verifikasi. Percobaan build standar setelahnya sempat gagal pada langkah ekstraksi aset karena akses jaringan ke `raw.githubusercontent.com` diblokir; aset brand sudah tersedia dan terverifikasi pada workspace. TypeScript dan build Vite langsung berhasil setelahnya.

## Batas data dan cakupan

- `GET /dashboard/summary` memberi jumlah status, ruangan aktif/total, pengguna, dan total reservasi; hitungan status bersifat sepanjang waktu.
- `GET /dashboard/room-statistics` menghitung reservasi berstatus disetujui/selesai per ruang. Nilai ini bukan durasi okupansi.
- Tidak ada endpoint tren waktu, lama penggunaan, okupansi langsung, maupun utilisasi kapasitas; metrik itu tidak ditampilkan.
- Endpoint daftar reservasi dan ruangan tetap dibatasi pada halaman pertama hingga 100 item, sesuai perilaku yang sudah ada. Pagination baru tidak ditambahkan.
- Role admin yang tersedia tetap `Staff Sekretariat`; tidak ada role Admin terpisah pada route guard frontend.

## Status

Stage 3 selesai. Tidak ada perubahan pada redesign halaman mahasiswa (Stage 4).
