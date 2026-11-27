# Audit Agent Skills Desain — RuangKampus

Tanggal audit: 27 November 2026  
Ruang lingkup: semua `SKILL.md` di `.agents/skills/` pada project, ditambah dua skill global yang diminta (`ui-motion` dan `find-skills`). Isi skill prioritas dibaca lengkap; referensi yang diwajibkan diperiksa, dan referensi motion dibaca lengkap. Audit ini hanya membuat laporan ini; kode, aset, dan desain aplikasi tidak diubah.

## Ringkasan

- Ada **8 skill project-local** dan **2 skill global** yang diminta untuk diperiksa. Semua file `SKILL.md` tersebut bisa dibaca dari workspace Codex.
- `ui-ux-pro-max` punya data dan script pencarian lokal, tetapi pencarian CLI belum bisa digunakan: environment tidak menyediakan `python`, `python3`, maupun `py`. Quick Reference tetap tersedia dan bisa diterapkan manual. Instruksi skill melarang memasang Python sendiri.
- Referensi Web Interface Guidelines tersedia dan SHA-256-nya cocok dengan checksum yang dipin di `SKILL.md`.
- Semua 7 referensi dan 7 contoh kode `ui-motion` tersedia di lokasi global.
- Path `.agents/skills/find-skills/SKILL.md` tidak ada di project. Skill itu ada dan terbaca di `~/.agents/skills/find-skills/SKILL.md`.
- Identitas produk mengikuti `docs/DESIGN_SYSTEM.md`, token di `frontend/src/styles/tokens.css`, dan aset resmi RuangKampus. Arahan umum yang bertentangan atau berada di luar stack web project harus disesuaikan dengan sumber tersebut.

## Daftar skill dan lokasi

| Skill | Lokasi | Status baca | Fungsi utama dan kesiapan |
|---|---|---|---|
| `ui-ux-pro-max` | `.agents/skills/ui-ux-pro-max/SKILL.md` | Terbaca lengkap (739 baris). Data CSV/JSON dan `scripts/search.py` tersedia. | Rekomendasi UI/UX untuk layout, visual style, warna, tipografi, aksesibilitas, interaksi, responsive, motion, chart, serta stack. Quick Reference bisa digunakan; pencarian berbasis CLI **belum tersedia** karena Python 3 tidak terpasang. |
| `web-design-guidelines` | `.agents/skills/web-design-guidelines/SKILL.md` | Terbaca lengkap. `references/command.md` tersedia; hash cocok dengan pin di skill. | Audit kode UI web terhadap aksesibilitas, fokus, form, motion, typography, konten, gambar, performa, state, responsive, tema, locale, dan hydration. Workflow meminta file/pola yang spesifik dan output temuan per file/baris. |
| `ui-motion` | `~/.agents/skills/ui-motion/SKILL.md` | Terbaca lengkap. 7 referensi dan 7 contoh React tersedia. | Menilai dan merancang motion yang bertujuan, cepat, bisa diinterupsi, menghormati reduced motion, dan memiliki cleanup. Panduan memperlakukan angka durasi sebagai preset, bukan hukum; tidak memberi izin untuk memasang library atau menjalankan browser. Skill ini berada di global Codex, bukan di project. |
| `find-skills` | Path yang diminta di project tidak ada; salinan global ada di `~/.agents/skills/find-skills/SKILL.md` | Terbaca lengkap (94 baris) dari lokasi global. | Mencari dan merekomendasikan skill ekosistem luar melalui leaderboard dan `npx skills`. Bukan panduan desain aplikasi. Pencarian atau pemasangan eksternal tidak dijalankan dalam audit ini. |
| `banner-design` | `.agents/skills/banner-design/SKILL.md` | Terbaca lengkap. | Membuat banner social, ads, hero, atau print; bukan desain dashboard penuh. Salah satu contoh referensi `references/nano-banana-pro-examples.md` tidak tersedia pada skill ini dan workflow merujuk ke sejumlah skill eksternal. |
| `brand` | `.agents/skills/brand/SKILL.md` | Terbaca lengkap; referensi dan script yang dicantumkan tersedia. | Voice, identitas visual, messaging, pengelolaan aset, dan konsistensi brand. Workflow default menunjuk ke `docs/brand-guidelines.md`, yang tidak ada pada RuangKampus. Jangan jalankan sinkronisasi token yang menganggap file tersebut sumber identitas project. |
| `design` | `.agents/skills/design/SKILL.md` | Terbaca lengkap; referensi lokal yang dicantumkan tersedia. | Skill payung untuk brand, token, logo, corporate identity, slide, banner, ikon, dan social images. Beberapa workflow mendelegasikan ke skill eksternal atau layanan AI; itu tidak dianggap terpasang/tersedia hanya karena disebut oleh skill. |
| `design-system` | `.agents/skills/design-system/SKILL.md` | Terbaca lengkap; 7 referensi yang dicantumkan tersedia. | Arsitektur token primitive → semantic → component, spesifikasi komponen, state, Tailwind, dan presentasi. Contohnya mengasumsikan `docs/brand-guidelines.md` dan `assets/design-tokens.json/css`; file itu tidak ada di project ini. |
| `slides` | `.agents/skills/slides/SKILL.md` | Terbaca lengkap; referensi yang dicantumkan tersedia. | Presentasi HTML strategis dengan layout, copywriting, strategi, token, dan chart. Berlaku untuk slide, bukan antarmuka aplikasi RuangKampus. |
| `ui-styling` | `.agents/skills/ui-styling/SKILL.md` | Terbaca lengkap; 7 referensi yang dicantumkan tersedia. | Implementasi komponen shadcn/Radix, Tailwind, accessibility, theme, responsive, serta visual canvas. Project RuangKampus menggunakan React + Vite + CSS, dan dependency frontend saat ini tidak mencakup Tailwind/shadcn; gunakan prinsipnya hanya jika cocok, jangan membawa asumsi stack atau dependency-nya. |

Inventaris di atas mencakup direktori skill project yang ditemukan. Nama skill yang disebut oleh beberapa workflow—misalnya `frontend-design`, `ai-artist`, `ai-multimodal`, `chrome-devtools`, `project-management`, dan `assets-organizing`—tidak dihitung sebagai skill terpasang tanpa file yang tersedia di lokasi skill project/global yang diperiksa.

## Aturan integrasi dan identitas RuangKampus

### Sumber otoritatif

1. Ikuti instruksi pengguna dan batas perubahan untuk pekerjaan saat itu.
2. Untuk identitas produk, gunakan `docs/DESIGN_SYSTEM.md`, `frontend/src/styles/tokens.css`, dan aset resmi yang sudah disediakan. Ini menggantikan contoh generik atau placeholder pada skill.
3. Gunakan `frontend/src/styles.css` dan komponen yang sudah ada untuk implementasi CSS/React. Terapkan aturan skill hanya jika cocok dengan stack, platform web, fungsi halaman, dan aturan produk.
4. Pertahankan rute, label, perilaku, role, workflow, serta hierarki navigasi aplikasi saat tugas hanya meminta perubahan visual. Jangan menambah dependency atau mengubah token brand sebagai efek samping dari rekomendasi skill.

### UI/UX global

- Identitas: gunakan wordmark dan mark resmi dengan rasio serta warna asli; jangan menggambar ulang, memfilter, atau mengganti logo dengan mark generatif.
- Warna: gunakan token semantik RuangKampus untuk biru primer, teal pendukung yang terbatas, neutral surface, teks, border, dan status. Status tetap punya label atau ikon; warna saja tidak menyampaikan makna.
- Tipografi: gunakan Plus Jakarta Sans Variable dan skala yang ditetapkan design system project. Skala saat ini mengizinkan body 14px dan metadata lebih kecil; jangan menerapkan angka rekomendasi generik secara buta. Naikkan ukuran pada konteks mobile/form yang butuh keterbacaan dan jangan memperkecil teks esensial.
- Ikon: gunakan `@tabler/icons-react` sebagai satu keluarga ikon UI project, outline dengan stroke konsisten 2px. Ikon dekoratif disembunyikan dari screen reader jika teks sudah menjelaskan fungsi; tombol ikon saja harus punya nama aksesibel. Jangan gunakan emoji sebagai ikon kontrol.
- Layout dan state: gunakan ritme 4px, permukaan yang tenang, hierarchy lewat jarak/ukuran/kontras, dan desain light/dark berpasangan. Cek teks, border, fokus, loading, error, empty, dan disabled pada kedua tema.
- Aksesibilitas: pertahankan semantic HTML, label form, fokus terlihat, urutan keyboard, pembacaan status, recovery error, zoom, dan alternatif keyboard/tap untuk gesture. Pastikan konten tidak overflow horizontal di viewport kecil.
- Motion: default statis. Tambahkan gerak hanya untuk feedback, kontinuitas, atau pengungkapan yang punya manfaat jelas. Filter/tab berulang berubah segera; animasi tidak boleh menahan aksi, state, request, atau fokus. Hormati `prefers-reduced-motion` sejak render awal dan bersihkan subscription, timer, observer, atau animation handle.

### Dashboard TU/Sekretariat dan Admin

- Pertahankan navigasi berbasis role dan susunan route saat ini; jangan mencampur pola sidebar, tab, dan bottom navigation pada tingkat yang sama.
- Dahulukan keterbacaan informasi operasional: pemesanan, ketersediaan ruang, status, review/approval, jadwal, pemeliharaan, dan impor data. Pertahankan density yang diperlukan tanpa menambah kartu dekoratif atau aksen berlebihan.
- Gunakan tabel dan filter dengan judul kolom, urutan angka/waktu yang mudah dipindai, state aktif yang jelas, dan semua aksi tetap ditemukan. Pada layar sempit, gunakan wrapper scroll tabel yang sudah ada atau reflow tanpa membuang kolom/informasi penting.
- Buat status pending/approved/rejected/maintenance terbaca lewat teks dan/atau ikon serta pasangan warna token yang tepat. Aksi destruktif perlu konfirmasi atau undo sesuai pola produk.
- Filter, pencarian, tab, dan aksi berulang merespons segera. Dialog operasional harus bernama, dapat digunakan keyboard, mendukung Escape, mengelola dan mengembalikan fokus, serta tidak menghalangi workflow saat motion dimatikan.
- Bedakan satu CTA halaman yang utama dari aksi kontekstual per baris; aturan “satu primary CTA per screen” tidak berarti menghapus operasi baris yang memang diperlukan.

### Halaman mahasiswa

- Jaga jalur utama untuk menemukan ruang, melihat ketersediaan, mengajukan booking, mengecek reservasi/notifikasi, dan memakai RUKKA AI. Jangan mengganti label, field, atau langkah workflow tanpa permintaan produk.
- Di mobile, tampilkan informasi dan kontrol esensial lebih dulu; pertahankan navigasi mobile yang ada. Jangan membuat fungsi penting bergantung pada hover atau gesture saja.
- Form booking/profil memakai label yang terlihat, input type/autofill yang sesuai, validasi dekat field, error dengan cara pemulihan, feedback submit, dan pencegahan submit ganda.
- Target sentuh utama dan tombol ikon harus mudah ditekan. Aturan ukuran native dalam pt/dp tidak disalin mentah ke CSS web; gunakan target CSS web dan beri ruang tambahan untuk kontrol sentuh yang sering dipakai.
- Perubahan filter dan state ringan harus instan. Loading yang nyata boleh memberi skeleton/status tanpa jeda buatan; hasil yang cepat langsung ditampilkan.

## Konflik dan penyelesaiannya

| Konflik/risiko | Ditemukan pada | Resolusi untuk RuangKampus |
|---|---|---|
| Ikon default Phosphor/Heroicons pada aturan `ui-ux-pro-max` berlawanan dengan keluarga Tabler yang sudah ditetapkan produk. | `ui-ux-pro-max` bagian Common Rules; `docs/DESIGN_SYSTEM.md`. | Tabler tetap satu-satunya keluarga ikon UI. Terapkan prinsip bersama: vector, konsisten, semantik, label aksesibel, dan tanpa emoji. Jangan migrasi ikon demi rekomendasi generik. |
| Arahan tipografi generik menyebut body 16px dan teks mobile minimum 16px; sistem RuangKampus menetapkan body 14px dan metadata 10–12px. | `ui-ux-pro-max` Quick Reference; `docs/DESIGN_SYSTEM.md`. | Skala produk tetap sumber utama untuk kepadatan desktop dashboard. Jaga teks esensial tetap terbaca; khusus input/interaksi mobile, evaluasi ukuran lebih besar (seringnya 16px) dan uji layout/zoom. Jangan mengecilkan teks esensial demi density. |
| Target 44pt iOS/48dp Android tercampur dengan target pointer web 24 CSS px dan kontrol project 40–46px. | `ui-ux-pro-max`; `docs/DESIGN_SYSTEM.md`; UI web guidelines. | Terapkan unit sesuai platform. Untuk web, jangan menyebut CSS px sebagai pt/dp; penuhi aturan web yang sesuai dan utamakan sekitar 44 CSS px untuk kontrol sentuh berfrekuensi tinggi bila layout memungkinkan. Catat pengecualian yang sempit/berdampingan dan pastikan dapat dioperasikan. |
| `ui-ux-pro-max` menganjurkan transisi state yang halus, sedangkan `ui-motion` menerapkan removal test, motion default statis, dan state frekuensi tinggi 0ms. | Quick Reference §7 dan `ui-motion` decision gates. | Untuk product UI ikuti motion contract `ui-motion`: aksi/state tidak menunggu; gerak opsional dan bermakna; reduced-motion punya hasil statis. Transisi visual singkat hanya bila membantu membaca perubahan dan tidak mengubah layout. |
| Contoh UI mengasumsikan shadcn/Radix + Tailwind, sedangkan RuangKampus adalah React/Vite/CSS dengan Tabler. | `ui-styling`; `frontend/package.json`. | Gunakan prinsip komposisi, aksesibilitas, responsive, dan token. Jangan pasang Tailwind/shadcn atau menyalin API/class contoh tanpa permintaan dan alasan stack yang jelas. |
| Design/brand helper mengasumsikan `docs/brand-guidelines.md`, `assets/design-tokens.json`, dan `assets/design-tokens.css`, yang tidak ada di project. `brand` juga menunjuk sinkronisasi dari file brand guidelines tersebut. | `brand`, `design-system`, `design`; pemeriksaan path project. | Sumber saat ini adalah `docs/DESIGN_SYSTEM.md` dan `frontend/src/styles/tokens.css`. Jangan menjalankan script sync yang membaca input hilang atau membuat sumber identitas kedua tanpa tugas eksplisit.
| Skill `design` menyatakan hasil logo generatif harus berlatar putih; pedoman proyek mengharuskan aset resmi dan logo tidak dimodifikasi. | `design` bagian Logo Design; `docs/DESIGN_SYSTEM.md`. | Untuk produk gunakan aset logo resmi yang sudah ada, bukan logo yang baru digenerasi. Aturan latar putih hanya bisa berlaku pada deliverable logo generatif yang memang diminta terpisah dan disetujui, bukan penggantian logo aplikasi.
| Beberapa aturan Web Interface Guidelines memakai aturan copy yang berorientasi bahasa Inggris (Title Case, placeholder berakhiran ellipsis) dan menyebut keyboard handler untuk elemen interaktif secara luas. | `web-design-guidelines/references/command.md`. | Pertahankan bahasa, gaya copy, dan locale aplikasi. Ikuti aksesibilitas dengan semantic control asli; tambahkan handler keyboard untuk widget custom bila dibutuhkan, bukan mengulang perilaku native button/link.
| Aturan platform native seperti haptic, Dynamic Type, safe area OS, dan 44pt/48dp tidak seluruhnya berlaku pada aplikasi web desktop/mobile. | Quick Reference dan Common Rules `ui-ux-pro-max`; `ui-motion`. | Terapkan hanya yang relevan pada web responsif. Jangan mengklaim haptic atau kepatuhan native; safe area CSS hanya untuk layout yang benar-benar edge-to-edge pada perangkat pendukung.
| Skill `find-skills` mendorong discovery/pemasangan lewat CLI eksternal; beberapa skill lain menyebut skill/tool yang tidak ada di inventaris lokal. | `find-skills`, `banner-design`, `design`, dan skill terkait. | Gunakan `find-skills` hanya saat pengguna meminta pencarian kemampuan baru. Penyebutan skill atau tool eksternal bukan bukti bahwa ia terpasang; jangan instal atau ubah dependency sebagai bagian dari audit desain.

## Keterbatasan operasional yang perlu diketahui

- Data dan CLI `ui-ux-pro-max` tersedia di project, tetapi pencarian belum dapat dijalankan karena Python 3 tidak ditemukan. Instruksi skill menyebut agar Python tidak dipasang oleh agent; gunakan Quick Reference secara manual sampai lingkungan Python tersedia.
- `web-design-guidelines` mematok snapshot lokal; checksum `references/command.md` cocok, sehingga tidak ada kebutuhan mengambil aturan terbaru dari internet untuk audit ini.
- `ui-motion` menyatakan browser checks conditional pada izin eksplisit. Instruksi tersebut berlaku pada implementasi motion berikutnya; bukan alasan untuk mengubah atau menjalankan browser dalam audit ini.
- Skill global `find-skills` bisa dibaca oleh Codex pada mesin ini, tetapi bukan skill project-local. CLI discovery/pemasangan tidak diuji karena bukan bagian dari permintaan.
- “Terpasang” di sini berarti file ada pada direktori skill project atau global yang diperiksa. Referensi eksternal, API key, dan layanan pembuatan gambar tidak diuji atau diasumsikan tersedia.

## Hasil akhir audit

Aturan integrasi ditetapkan sebagai berikut: **arahan umum skill memberi checklist dan opsi; identitas, aset, token, stack, konten, dan workflow RuangKampus tetap mengatur keputusan akhir**. Untuk audit web, `web-design-guidelines` memberi format temuan; untuk motion, gunakan batas yang lebih spesifik dari `ui-motion`; untuk pilihan UI yang belum diputuskan, `ui-ux-pro-max` menjadi katalog referensi manual sampai CLI Python tersedia. Skill `brand` dan `design-system` boleh membantu prinsip, tetapi tidak boleh menganggap template token generik sebagai sumber resmi RuangKampus.
