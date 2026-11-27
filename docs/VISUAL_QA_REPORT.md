# RuangKampus — Visual QA & Refinement (Stage 2)

**Tanggal:** 27 November 2026  
**Cakupan:** frontend presentation layer, deterministic Playwright fixture environment, installed Google Chrome.

## Ringkasan

Audit browser mencakup semua 25 leaf routes, tema terang dan gelap, state utama, workflow fixture Student dan Staff Sekretariat, serta viewport desktop sampai mobile kecil. Audit menemukan satu masalah konten tertutup di navigasi mobile, satu token warna status yang tidak tersedia, dan teks literal `\n` di app shell. Ketiganya diperbaiki tanpa mengubah route, API, autentikasi, field/validasi, state, maupun business workflow.

Hasil regresi browser terakhir: **237 kasus melaporkan lulus**. Proses Playwright tidak menutup sendiri setelah seluruh kasus selesai dan dihentikan saat teardown, sehingga command tidak menghasilkan exit code sukses. Satu test lama dijalankan terpisah dan gagal hanya pada assertion hex lama (`#111a20`), setelah pemeriksaan perubahan tema dan persistensi melewati langkahnya. Detailnya ada di bagian pengujian.

## Halaman yang diperiksa

| Kelompok | Route dan halaman |
|---|---|
| Publik (4) | `/login`, `/register`, `/forgot-password`, `/reset-password?token=fixture-reset-token` |
| Student (11) | `/student/dashboard`, `/student/rooms`, `/student/availability`, `/student/alternatives`, `/student/rooms/room-e2e-001`, `/student/rooms/room-e2e-001/book`, `/student/reservations`, `/student/reservations/reservation-pending-e2e`, `/student/notifications`, `/student/profile`, `/student/assistant` (RUKKA AI) |
| TU/Admin (10) | `/admin/dashboard`, `/admin/reservations`, `/admin/reservations/reservation-pending-e2e`, `/admin/rooms`, `/admin/data-imports`, `/admin/rooms/new`, `/admin/rooms/room-e2e-001/edit`, `/admin/schedules` (jadwal dan pemeliharaan), `/admin/notifications`, `/admin/profile` |
| Fallback (1 tambahan) | `/visual-qa-not-found` untuk memverifikasi tampilan not found |

Semua 25 route aplikasi diperiksa pada kedua tema. Not-found diperiksa sebagai route tambahan pada dua viewport Stage 2 dan dua tema.

## Viewport dan tema

Semua route dirender pada **1440×900** dalam light dan dark mode. Responsive coverage mencakup viewport berikut:

| Viewport | Asal pemeriksaan |
|---|---|
| 1440×900 | Desktop, responsive workflow |
| 1280×800 | Stage 2 route audit |
| 1024×768 | Laptop, responsive workflow |
| 820×1180 | Tablet, responsive workflow |
| 768×1024 | Tablet, responsive workflow |
| 390×844 | Mobile, responsive workflow |
| 360×800 | Stage 2 route audit |
| 320×800 | Small mobile, responsive workflow |

Suite responsive mengambil screenshot light mode di semua enam target awal (1440, 1024, 820, 768, 390, 320) untuk setiap route. Stage 2 menambahkan pemeriksaan dan screenshot di 1280×800 dan 360×800 untuk seluruh 25 route serta not-found, dalam light dan dark. Tidak ditemukan horizontal overflow pada pengecekan `documentElement` dan `body` di viewport tambahan; suite responsif juga memeriksa overflow dan navigasi mobile pada route yang dilindungi.

## Screenshot evidence

Screenshot tersimpan lokal di `frontend/test-results/screenshots/` (folder ini diabaikan oleh Git):

| Folder | Evidence |
|---|---|
| `baseline/` | 50 screenshot: 25 route × 1440×900 × dua tema. Nama folder berasal dari harness; file yang ada adalah hasil saat ini dan **bukan** screenshot sebelum redesign. |
| `final/responsive/` | 150 screenshot responsive light mode: 25 route × enam viewport. |
| `final/stage2/` | 104 screenshot: 26 path (25 route + not-found) × dua viewport (1280, 360) × dua tema. |
| `final/states/` | 8 state screenshot: filter/search, empty, loading, API error, menu akun, dialog approval, validasi booking, dan preview import. |

Contoh hasil mobile sesudah perbaikan: [Student booking 390×844](../frontend/test-results/screenshots/final/responsive/student/student-booking/student-booking-390-light.png) dan [Admin data import 390×844](../frontend/test-results/screenshots/final/responsive/admin/admin-data-imports/admin-data-imports-390-light.png). Screenshot import 360×800 kedua tema serta semua route lain tersedia di `final/stage2/`.

## Temuan dan perbaikan

| Prioritas | Temuan | Perbaikan |
|---|---|---|
| P0 | Navigasi mobile fixed menutupi bagian bawah form booking dan workspace import. | Pada breakpoint ≤920px, shell kini menggunakan grid dengan baris konten dan baris navigasi terpisah. Konten utama scroll pada area yang tersedia; nav tetap terlihat dan safe-area inset tetap dihormati. Screenshot booking/import mobile diperiksa ulang sesudah fix. |
| P1 | Status impor yang diblokir merujuk `--status-danger` dan `--status-danger-surface`, yang tidak didefinisikan dalam token. | Keduanya diganti dengan pasangan semantik yang tersedia, `--status-error` dan `--status-error-surface`. |
| P2 | Teks literal `\n` di app shell tampil pada bagian atas halaman protected. | Whitespace JSX di [layout.tsx](../frontend/src/layout.tsx) dirapikan sehingga backslash-n tidak dirender. |
| P2 | Aturan mobile sebelumnya masih menyisakan padding bawah besar untuk navigasi fixed setelah navigasi dipindahkan ke alur layout. | Konten mobile sekarang memiliki scroll container dan padding bawah yang wajar; nav memperoleh ruang layoutnya sendiri. |

Inspeksi visual juga memeriksa hierarki judul, gutter, form, badge/status, tabel dalam wrapper scroll, dialog, kontrol tema, dan kepadatan navigasi di seluruh route. Tidak ada perubahan komposisi halaman besar yang diperlukan.

## Accessibility dan interaction

- **50 axe scans** (25 route × light/dark, cakupan tag WCAG 2.0/2.1 A/AA) dilaporkan lulus, tanpa pelanggaran axe pada semua impact level.
- Pemeriksaan keyboard: skip link dan main landmark, menu akun dan Escape, dialog approval dengan focus trap serta pemulihan fokus, dan `prefers-reduced-motion` lulus.
- Playwright memeriksa navigasi mobile tampil dan ukuran link minimal 44px pada breakpoint yang diuji; link Jadwal dan Impor tersedia di nav Staff.
- Pemeriksaan otomatis ini tidak menggantikan pengujian screen reader manual atau audit kesesuaian WCAG penuh.

## Regression testing dan build

| Pemeriksaan | Hasil |
|---|---|
| Frontend unit tests (`npm test`) | **Lulus: 8 tes**. |
| TypeScript (`npx tsc --noEmit`) | **Lulus**, sebagai bagian dari build production. |
| Production build (`VITE_API_BASE_URL=http://127.0.0.1:4173/api/v1 npm run build`) | **Lulus**; ekstraksi/verifikasi 14 aset brand berhasil, `tsc` dan Vite build sukses. Hasil build terakhir: CSS 78.22 KB dan JS 414.44 KB. |
| Playwright final batch | **237 kasus melaporkan lulus**: 133 kasus suite yang dijalankan (dari 134 existing, satu test palette dikecualikan) ditambah 104 route/viewport/theme checks Stage 2. Seluruh workflow fixture, 50 axe scan, keyboard, reduced motion, route visual, dan responsive case yang termasuk batch melaporkan lulus. |
| Existing theme persistence test | Secara terpisah memeriksa toggle, perpindahan halaman, dan tema auth yang persisten; gagal pada assert literal `background === "#111a20"`. Token tema baru adalah `#0d1219`. Test tidak diubah, sesuai batas perubahan. Ini stale expected color, bukan kegagalan interaksi tema. |

Batch terakhir dijalankan dengan Chrome yang sudah terpasang dan konfigurasi Playwright sementara. Setelah baris terakhir seluruh 237 kasus menunjukkan `ok`, proses tidak keluar dari teardown; proses dihentikan manual. Karena itu hasil dilaporkan sebagai jumlah assertion yang lulus, bukan command runner dengan exit code 0. Unduhan Chromium dan perubahan versi dependency tidak diperlukan.

API browser dipetakan ke fixture in-memory; backend, staging, dan produksi tidak dipanggil. Workflow E2E membuktikan interaksi frontend terhadap fixture, bukan persistensi database, parsing Excel di backend, atau otorisasi server.

## File yang berubah pada rangkaian visual

- `frontend/src/styles/tokens.css` — semantic palette light/dark dan token visual.
- `frontend/src/styles.css` — treatment komponen, status import, breakpoint, layout scroll/navigasi mobile, dan reduced motion.
- `frontend/src/layout.tsx` — koreksi whitespace JSX yang tampil sebagai teks literal.
- `frontend/public/brand/` — 14 aset brand resmi yang diverifikasi oleh build script.
- `docs/DESIGN_SYSTEM.md` — panduan token dan perilaku responsive mobile yang diperbarui.
- `docs/VISUAL_ONLY_REDESIGN_REPORT.md` — laporan tahap awal diperbarui dengan hasil Stage 2.
- `docs/VISUAL_QA_REPORT.md` — laporan audit ini.

Konfigurasi Chrome dan spec audit tambahan adalah file sementara yang dihapus setelah QA. Tidak ada pengujian permanen yang diubah atau dihapus.

## Keterbatasan baseline dan repository

Tidak tersedia screenshot sebelum redesign dalam snapshot ini; perbandingan visual sebelum/sesudah tidak dapat dibuat. Git metadata juga tidak tersedia pada workspace, jadi branch aktif dan daftar perubahan tracked tidak dapat diverifikasi. Hasil browser menggunakan data fixture dan inspeksi screenshot, bukan backend/produksi.
