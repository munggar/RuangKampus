# RuangKampus — Brand, Typography, Icon & Login Refinement

**Stage:** 2.1  
**Tanggal:** 27 November 2026  
**Boundary:** visual-only; routes, API, authentication, state, form labels/validation, reservation workflows, and feature behavior remain unchanged.

## 1. Ringkasan

Stage 2.1 menyelaraskan logo resmi, font, ikon, dan halaman autentikasi di seluruh frontend. Wordmark tidak lagi tampil sebagai gambar di atas kartu putih; file transparan resmi ditempatkan pada bidang brand datar yang menyatu dengan area sidebar dan panel brand login. Plus Jakarta Sans Variable kini menjadi font UI utama. Semua ikon aplikasi berpindah dari Lucide ke Tabler React dengan stroke outline 2px. Halaman login mendapat hierarki dan komposisi baru untuk desktop dan mobile, sementara seluruh fungsi form dan alurnya tetap sama.

## 2. Logo dan aset resmi

Folder `frontend/public/brand/` berisi 14 aset asli yang diekstrak serta diverifikasi oleh script proyek. Audit menemukan:

- `logo-primary.png` — wordmark transparan resmi berwarna biru/navy, termasuk tagline.
- `logo-primary-white-bg.png` — wordmark resmi dengan latar putih yang menjadi bagian aset.
- `favicon/favicon-*.png`, `favicon/favicon.ico`, dan `favicon/site.webmanifest` — mark resmi untuk favicon/PWA.
- Tidak ada wordmark transparan putih-on-dark dalam aset repository.

Wordmark transparan dipakai utuh pada login, registrasi, reset password, layar pemuatan, dan sidebar desktop. Bidang brand menggunakan latar pucat yang datar dan tanpa radius/kartu terpisah. Bidang itu dipertahankan saat dark mode agar tulisan navy di aset tetap terbaca; area form dan konten lainnya tetap mengikuti token tema. Tidak ada filter warna, rekonstruksi, crop, maupun perubahan pada file logo. Header mobile menampilkan mark dari favicon resmi agar wordmark tidak mengecil pada topbar. Favicon browser, apple-touch icon, dan manifest tetap memakai file resmi yang sama.

## 3. Typography

| Sebelum | Sesudah |
|---|---|
| System sans stack dengan Inter sebagai fallback awal | Plus Jakarta Sans Variable, dibundel lokal melalui `@fontsource-variable/plus-jakarta-sans` versi 5.3.0 |
| Tidak ada runtime font package | Import keluarga font di entry point `frontend/src/main.tsx`; fallback platform sans tetap tersedia |

Keluarga variable mendukung weight 200–800 untuk heading, navigasi, body, form, tabel, badge, modal, dan assistant. `--font-family-sans` menjadi sumber utama di token dan body. System monospace tetap khusus untuk identifier/jam; angka statistik dan jadwal mempertahankan tabular numerals. Tidak ada permintaan font dari host eksternal saat aplikasi berjalan.

## 4. Icon system

| Sebelum | Sesudah |
|---|---|
| `lucide-react` | `@tabler/icons-react` versi 3.53.0 |

Semua pemakaian ikon UI pada tujuh modul frontend dimigrasikan dengan named import langsung agar tree shaking tetap tersedia. Padanan dipilih berdasarkan makna dan dipastikan sebagai export package sebelum digunakan. Ukuran inline yang sudah sesuai dipertahankan; gaya Tabler menggunakan outline dan stroke 2px.

Kategori yang dimigrasikan:

- Navigasi/dashboard, gedung/ruangan, pencarian, filter, dan pengguna.
- Reservasi, kalender/jadwal, jam, status persetujuan/penolakan, dan notifikasi.
- Import spreadsheet, sekolah/mahasiswa, dan data kampus.
- RUKKA AI/chatbot, sparkle, feedback, serta pengiriman pesan.
- Login, visibilitas password, keamanan, logout, tema, edit, hapus, dan tambah.
- Alert, informasi, loading, check, close, map pin, dan panah.

Dependency Lucide dihapus dari `package.json` dan lockfile. Tidak ada penggunaan lucide-react tersisa di source frontend.

## 5. Login dan konsistensi brand

Perubahan komposisi login:

- Area brand memakai wordmark transparan pada bidang identitas datar dan berwarna netral kebiruan, bukan kartu putih mengambang.
- Headline mengecil ke skala yang lebih cocok untuk aplikasi operasional; body copy dan teks autentikasi memakai keluarga font yang sama.
- Form tetap berada di bidang yang jelas, dengan lebar terukur, jarak label/input konsisten, dan segmented choice Student/Staff yang lebih tegas.
- Focus, hover, active, disabled, error, show/hide password, lupa password, register, dan reset-password tetap memakai mekanisme/form lama.
- Mobile menumpuk area brand dan form tanpa memotong logo/tagline; wordmark tampil di area brand, mark favicon digunakan di topbar aplikasi.

Theme persistence masih menggunakan `rk-theme`, `data-theme`, dan event `rk-theme-change`. Test tema diperbarui agar memeriksa background auth terhadap token `--surface-card`, bukan hex lama.

## 6. Halaman terdampak

Sistem font dan ikon berlaku di semua 25 leaf routes:

- **Publik/auth (4):** login, register, forgot password, reset password.
- **Student (11):** dashboard, room directory/detail, availability, alternative slots, booking, reservation history/detail, notifications, profile, RUKKA AI.
- **TU/Admin (10):** dashboard, reservation management/detail, room management/create/edit, schedule/maintenance, data import, notifications, profile.
- Komponen bersama: sidebar, mobile navigation, header actions, button, form controls, table, status badge, modal, dropdown, notices, empty/loading/error states.

## 7. Screenshot evidence

Semua evidence berada di `frontend/test-results/brand-refinement/`:

| Folder | Isi |
|---|---|
| `before/` | 3 screenshot login Stage 2 sebelum perubahan Stage 2.1: desktop light/dark dan mobile light. Disalin dari screenshot lokal Stage 2 yang tersedia. |
| `after/` | 14 screenshot: login desktop/mobile light/dark, Student dashboard light/dark, room directory, booking mobile, Admin dashboard light/dark, reservation table, RUKKA AI light/dark, dan loading screen dark. |
| `after/routes/` | 104 screenshot route: 25 route + not-found, 1280×800 dan 360×800, tema light/dark. |

Contoh: [login desktop light](../frontend/test-results/brand-refinement/after/login-1440-light.png), [login desktop dark](../frontend/test-results/brand-refinement/after/login-1440-dark.png), [login mobile](../frontend/test-results/brand-refinement/after/login-390-light.png), [Student dashboard](../frontend/test-results/brand-refinement/after/student-dashboard-1440-light.png), [Admin dashboard](../frontend/test-results/brand-refinement/after/admin-dashboard-1440-light.png), [RUKKA AI dark](../frontend/test-results/brand-refinement/after/student-assistant-1440-dark.png), dan [loading screen dark](../frontend/test-results/brand-refinement/after/loading-screen-dark.png).

Selain ukuran screenshot di atas, existing responsive browser test memeriksa 1440×900, 1024×768, 820×1180, 768×1024, 390×844, dan 320×800. Audit Stage 2.1 menambah cek overflow semua route pada 1280×800 dan 360×800 untuk kedua tema. Screenshot before tersedia untuk login saja; baseline sebelum Stage 2 tidak ada.

## 8. File yang berubah

- `frontend/package.json`, `frontend/package-lock.json` — memasang Fontsource/Tabler dan menghapus Lucide.
- `frontend/src/main.tsx` — import CSS Plus Jakarta Sans Variable.
- `frontend/src/styles/tokens.css` — font-family dan semantic brand identity tokens.
- `frontend/src/styles.css` — logo treatment, hierarchy/login, typography inheritance, dan Tabler stroke sizing.
- `frontend/index.html`, `frontend/src/styles.css` — treatment wordmark layar boot/loading tanpa kartu putih.
- `frontend/src/auth-pages.tsx` — area brand login/auth memakai aset resmi transparan.
- `frontend/src/layout.tsx` — full wordmark untuk sidebar dan mark-only resmi pada header mobile; penghapusan filter logo lama.
- `frontend/src/admin-data-imports.tsx`, `frontend/src/admin-pages.tsx`, `frontend/src/feature-pages.tsx`, `frontend/src/student-pages.tsx`, `frontend/src/ui.tsx` — migrasi named icon imports ke Tabler.
- `frontend/e2e/visual-responsive.spec.ts` — assertion tema auth menggunakan token design system, bukan hex usang.
- `docs/DESIGN_SYSTEM.md`, `docs/VISUAL_ONLY_REDESIGN_REPORT.md`, dan laporan ini.
- `frontend/test-results/brand-refinement/` — screenshot evidence before/after.

File aset logo resmi tidak diubah; build script memverifikasi dan mengekstrak kembali 14 file asli. Test/config screenshot sementara Stage 2.1 dihapus setelah verifikasi.

## 9. Hasil verifikasi

| Pemeriksaan | Hasil |
|---|---|
| Unit tests (`npm test`) | **8 passed**. |
| TypeScript (`npx tsc --noEmit`) | **Lulus**. Juga dijalankan oleh `npm run build`. |
| Production build | **Lulus**. Script memverifikasi 14 aset brand, lalu TypeScript dan Vite build sukses. CSS 84.01 KB; JS 409.38 KB; tiga subset font Latin/Latin-ext/Vietnamese dibundel sebagai WOFF2 lokal. |
| Playwright | **251 passed; 1 gagal saat penutupan browser karena trace artifact tidak ditemukan**, bukan assertion UI. Rinciannya: 134 existing suite tests + 104 route/viewport/theme overflow checks + 14 brand/loading screenshots. Cek yang gagal (Student notifications, 360px, dark theme) lulus saat diulang sendiri (**1 passed**). |
| Accessibility | **50 axe scans** (25 route × dua tema) lulus; keyboard flow, dialog focus, reduced motion, dan mobile nav checks lulus. Axe gate menghalangi critical/serious findings. |
| Theme | Theme toggle dan persistensi ke halaman lain serta auth lulus; key, attribute, dan event tidak berubah. |
| Workflow | Login fixture Student/Staff, registrasi/reset flow, reservation, approval/rejection, room editor, jadwal, import, profil, dan AI feedback lulus. |
| Responsive | Semua protected routes diperiksa di enam viewport existing; 25 route dan not-found lolos cek horizontal overflow pada 1280×800 dan 360×800 di kedua tema pada run terpisah maupun checks lain dalam run penuh. |

E2E memakai API mock fixture, bukan backend, staging, atau produksi. Verifikasi ini meliputi interaksi frontend dan screenshot visual, bukan validasi sesi autentikasi server atau penyimpanan data.

## Referensi resmi

- [Fontsource — Plus Jakarta Sans](https://fontsource.org/fonts/plus-jakarta-sans/use)
- [Tabler Icons — React package](https://docs.tabler.io/icons/libraries/react)

## 10. Kendala dan pekerjaan tersisa

- Untuk menjalankan build, akses jaringan diperlukan oleh script repository yang mengambil arsip logo resmi dari GitHub; arsip dan 14 file diperiksa checksum-nya. Font dan icon package telah masuk dependency manifest/lock.
- Tidak tersedia screenshot sebelum Stage 2, sehingga perbandingan before/after tersimpan untuk login Stage 2 ke Stage 2.1 saja.
- Backend/produksi tidak digunakan dalam QA fixture.
- Tidak ada pekerjaan implementasi yang tersisa pada cakupan visual Stage 2.1.
