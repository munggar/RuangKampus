# Laporan Redesign Visual RuangKampus

## Ringkasan

Redesign visual bertema **RuangKampus — Modern Academic Operations** diterapkan pada design tokens dan shared stylesheet. Perubahan mencakup warna light/dark, ritme layout, navigasi, hierarki halaman, panel, tabel, tombol, form, direktori ruang, RUKKA AI, autentikasi, dan breakpoint responsif.

Implementasi mengubah design tokens, shared CSS, satu baris JSX yang sebelumnya merender teks literal `\n` di layout aplikasi, dan dokumentasi. Route, label, form field, API, autentikasi, state, reservation lifecycle, notifikasi, dan alur RUKKA AI tidak diubah. Logo resmi tetap dipakai. Build memverifikasi serta mengekstrak 14 file aset brand resmi menggunakan script proyek yang sudah ada.

## Arah desain dan sistem visual

- Identitas biru institusional RuangKampus dipadukan dengan aksen teal terbatas, latar netral hangat, permukaan solid, dan divider halus.
- Dark mode memakai navy slate, teks terang, serta aksen biru/teal yang lebih terang. Semantik status tetap memakai token success, warning, error, dan information.
- Typography menggunakan Plus Jakarta Sans Variable yang dibundel lokal dari Fontsource, dengan fallback platform sans dan fallback monospace sistem hanya untuk identifier/waktu.
- Seluruh ikon UI menggunakan `@tabler/icons-react` dengan style outline dan ukuran yang konsisten; Lucide telah dihapus dari dependency frontend.
- Panel biasa tidak diberi shadow besar; shadow disisakan untuk popover dan navigasi mobile. Radius kontrol dan panel dibuat lebih terkendali.
- Sidebar, topbar, konten dashboard, tabel, room directory, reservations, RUKKA AI, authentication, dan layout kecil menerima treatment bersama melalui CSS.

## Perubahan fungsional

| Area | Perubahan Visual | Perubahan Fungsional |
|---|---|---|
| Navigation | Sidebar, active route marker, topbar, dan mobile navigation ditata ulang | Tidak ada |
| Dashboard | Hierarki statistik, panel, dan ruang konten dirapikan | Tidak ada |
| Room Directory | Kartu, media, chip fasilitas, dan grid responsif ditata ulang | Tidak ada |
| Reservation | Panel, status, form, dan tabel diberi treatment konsisten | Tidak ada |
| TU/Admin | Tabel, request card, room editor, import workspace, dan jadwal mengikuti token baru | Tidak ada |
| RUKKA AI | Intro, thread, bubble, composer, dan feedback dirapikan | Tidak ada |
| Authentication | Split brand/form, form control, dan panel diberi treatment konsisten | Tidak ada |
| Theme | Light dan dark palette diganti ke token baru | Tidak ada; `rk-theme`, `data-theme`, event, dan sinkronisasi tetap sama |

## Responsif dan aksesibilitas

Stylesheet mempertahankan navigasi mobile yang ada, menyesuaikan gutters dan grid, menjaga tabel dalam wrapper scroll, serta memberi batas viewport pada dialog. Di layar kecil, navigasi kini mengambil baris layout tersendiri dan konten utama scroll di area yang tersisa agar tombol/form tidak tertutup. Target touch controls utama berukuran sekitar 40px atau lebih. Focus ring yang sudah ada tetap dipertahankan; motion mengikuti `prefers-reduced-motion`.

Perhitungan kontras token representative menggunakan rumus WCAG menghasilkan rasio: light body 5.61:1, light primary/action 7.14:1, dark body 9.37:1, dark primary text 15.19:1, dark accent 7.73:1, dark action 7.13:1. Ini pemeriksaan pasangan token, bukan audit manual seluruh teks/runtime state.

## File yang diubah

- `frontend/src/styles/tokens.css` — semantic color, typography, spacing, radius, elevation, icon, dan motion tokens light/dark.
- `frontend/src/styles.css` — shared visual treatment, component refinements, breakpoints, mobile content/navigation layout, status token fix, dan reduced-motion overrides.
- `frontend/src/layout.tsx` — logo wordmark di sidebar dan mark resmi di mobile header; koreksi whitespace JSX yang tampil sebagai teks literal.
- `frontend/src/auth-pages.tsx` — markup area logo login/registrasi/reset tetap memakai aset resmi tanpa kartu terpisah.
- `frontend/src/main.tsx` — import font variable secara lokal.
- `frontend/package.json` dan `frontend/package-lock.json` — Fontsource dan Tabler ditambahkan; Lucide dihapus.
- `docs/DESIGN_SYSTEM.md` — aturan visual dan panduan penggunaan token.
- `docs/VISUAL_ONLY_REDESIGN_REPORT.md` — laporan ini.
- `frontend/public/brand/` — 14 aset logo/favicon resmi diekstrak dan hash-verified oleh build script proyek.

File yang mengatur route dan perilaku seperti `App.tsx`, halaman Student/Admin, `api.ts`, dan `auth.tsx` tidak diedit. `layout.tsx` hanya disentuh untuk menghapus teks whitespace literal yang tampil di halaman.

## Verifikasi

| Pemeriksaan | Hasil |
|---|---|
| Frontend unit tests (`npm test`) | Lulus: 1 file, 8 tes |
| TypeScript (`npx tsc --noEmit`) | Lulus |
| Production build (`npm run build`) | Lulus; brand assets terverifikasi; Vite build sukses |
| E2E Playwright dan workflow | Stage 2 melaporkan 237 kasus terpilih lulus, termasuk workflow Student/Admin, keyboard, reduced motion, dan route/responsive checks. Runner tidak keluar setelah seluruh kasus melaporkan lulus dan dihentikan saat teardown; satu test theme persistence dikeluarkan dari batch karena stale assertion yang masih mengharapkan `#111a20`, sedangkan token baru adalah `#0d1219`. Test itu secara terpisah melewati toggle dan persistence checks sebelum gagal hanya pada perbandingan warna literal. |
| Screenshot | Evidence disimpan di `frontend/test-results/screenshots/`: 50 screenshot route × tema, 150 screenshot responsive light mode, 104 tambahan untuk 26 path × dua viewport × dua tema, dan 8 state screenshot. Folder `baseline/` dari suite bernama demikian, namun pada snapshot ini berisi screenshot saat ini, bukan pre-redesign. |
| Visual audit browser | Chrome terpasang digunakan lewat konfigurasi Playwright sementara. Semua 25 route diverifikasi dalam light/dark pada 1440×900; responsive coverage mencakup 1440×900, 1280×800, 1024×768, 820×1180, 768×1024, 390×844, 360×800, dan 320×800. Semua route diuji overflow horizontal di tambahan 1280×800 dan 360×800; not-found juga dicakup. Lihat [laporan Stage 2](VISUAL_QA_REPORT.md). |
| Backend/produksi | Tidak disentuh dan tidak digunakan untuk test. |

Tidak tersedia screenshot pre-redesign atau Git metadata untuk perbandingan baseline dan inspeksi diff. Hasil dan keterbatasan QA lengkap tercatat pada [docs/VISUAL_QA_REPORT.md](VISUAL_QA_REPORT.md).

Perbaikan identitas logo, tipografi Plus Jakarta Sans, migrasi Tabler, dan refinement login Stage 2.1 didokumentasikan di [docs/BRAND_TYPOGRAPHY_ICON_REFINEMENT_REPORT.md](BRAND_TYPOGRAPHY_ICON_REFINEMENT_REPORT.md).

## Batasan repository

Direktori kerja ini tidak memiliki `.git` metadata. Karena itu branch aktif, working tree, branch `develop`, dan user changes yang terlacak tidak dapat diverifikasi; branch `frontend/visual-only-redesign` tidak dapat dibuat dari snapshot ini. Tidak ada Git operation yang dilakukan. Untuk integrasi, bawa perubahan source dan dokumen ini ke clone Git proyek pada branch yang diminta, setelah memeriksa status lokal.
