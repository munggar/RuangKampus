# Stage 4 — Student Experience Redesign Report

## Ringkasan

Pengalaman mahasiswa diperbarui dengan memakai sistem tema, token, komponen, font Plus Jakarta Sans Variable, dan ikon Tabler yang sudah ada. Perubahan menjaga kontrak API, route, role, urutan booking, status reservasi, validasi bisnis, mekanisme RUKKA, dan penyimpanan tema.

Dashboard kini lebih berorientasi ke aktivitas personal. Pencarian ruang memperlihatkan filter aktif yang bisa dilepas satu per satu, booking memberi jalur ke pencarian alternatif saat waktu tidak tersedia, daftar reservasi mencakup semua status backend, dan RUKKA mendapat interaksi chat serta motion yang mengikuti respons nyata.

## Audit dan fondasi desain

Pra-implementasi dicatat di [STAGE_4_STUDENT_REDESIGN_AUDIT.md](STAGE_4_STUDENT_REDESIGN_AUDIT.md). Audit memetakan route mahasiswa, sumber API, shell responsif, theme, komponen, state, dan motion awal.

Skill yang dibaca kembali beserta referensi relevannya: `ui-ux-pro-max`, `web-design-guidelines` dan `references/command.md`, `ui-motion` dengan referensi timing/component interaction/code recipe/validation, `design-system` dengan arsitektur token/semantic/component/state, `ui-styling` dengan panduan aksesibilitas dan responsif, serta `brand` dan `design`. Project menggunakan CSS biasa, bukan Tailwind/shadcn; prinsip skill diterapkan tanpa menambah dependency. CLI Python `ui-ux-pro-max` tidak tersedia, jadi Quick Reference skill digunakan manual.

Identitas desain mengikuti token RuangKampus, logo resmi, Plus Jakarta Sans Variable, Tabler Icons, dan `data-theme`/`rk-theme`/`rk-theme-change`. Tidak ada sistem tema baru.

## Halaman yang diperbarui

Semua 11 route mahasiswa ini masuk cakupan visual QA light/dark:

| Halaman | Perubahan utama |
|---|---|
| Dashboard | Ringkasan enam status reservasi, shortcut ke pencarian/ketersediaan/reservasi/RUKKA, serta aktivitas terbaru. |
| Direktori ruang | Chip filter aktif yang dapat dilepas sendiri atau sekaligus; empty state menyediakan pemulihan filter. |
| Detail ruang | Masuk dalam alur discovery visual dan browser QA; informasi inventaris dan CTA existing tetap dipakai. |
| Ketersediaan | Cakupan responsif, tema, dan accessibility QA; pencarian tetap memakai endpoint ketersediaan yang ada. |
| Booking | Saat slot tidak tersedia, tautan pencarian alternatif membawa tanggal, durasi, peserta, fakultas, dan gedung. Keberhasilan tetap menunggu respons backend. |
| Slot alternatif | Kriteria dari booking dipertahankan di URL dan form; endpoint serta batas pencarian existing tetap digunakan. |
| Daftar reservasi | Tab khusus `Cancelled` dan `Completed` melengkapi All/Pending/Approved/Rejected. |
| Detail reservasi | Cakupan visual, tema, dan aksesibilitas; status dan aksi tetap mengikuti data/izin existing. |
| Notifikasi | Cakupan visual, tema, dan aksesibilitas; aksi baca tetap memakai API existing. |
| Profil | Cakupan visual, tema, dan aksesibilitas; profile/password/theme workflow tidak diubah. |
| RUKKA AI | Log percakapan yang dapat diumumkan screen reader, processing state nyata, retry yang mempertahankan draft, dan auto-scroll bersyarat. |

Dashboard tidak menampilkan rekomendasi personal karena backend belum menyediakan ranking atau preferensi personal. Foto ruang tetap berasal dari `photo_url` inventaris; fallback menggunakan ikon.

## Komponen dan file

- [student-pages.tsx](../frontend/src/student-pages.tsx): dashboard personal, filter aktif, CTA slot alternatif, serta tab semua status reservasi.
- [feature-pages.tsx](../frontend/src/feature-pages.tsx): perilaku chat RUKKA, draft saat error, fokus input prompt, scroll yang mengikuti posisi pembaca, dan status pemrosesan.
- [layout.tsx](../frontend/src/layout.tsx): wrapper transisi route yang hanya membungkus konten Student.
- [styles.css](../frontend/src/styles.css): visual mahasiswa dan motion yang scoped agar gaya admin tidak berubah. Ringkasan status memakai grid tiga kolom pada desktop dan dua kolom pada mobile.
- [stage4-student-interactions.spec.ts](../frontend/e2e/stage4-student-interactions.spec.ts): uji alur dashboard, chip filter, discovery → detail → booking, slot alternatif, dan retry RUKKA.
- [stage4-student-visual.spec.ts](../frontend/e2e/stage4-student-visual.spec.ts): matriks screenshot, tema, ukuran, dan overflow.
- [support.ts](../frontend/e2e/support.ts): fixture browser mengenali respons 503 yang memang sengaja dipakai pada skenario retry RUKKA.

## Audit dan hasil motion

Sebelum perubahan, baseline memiliki transisi CSS pada tombol, navigasi, field, kartu ruang/reservasi, hover gambar, spinner request, dan timer. Transisi antar-route serta kemunculan pesan belum tersedia. Dialog sudah memiliki manajemen fokus, Escape, dan pemulihan fokus, tetapi tidak memiliki animasi mount/unmount.

Motion yang ditambahkan atau disempurnakan:

- **Perpindahan route mahasiswa:** opacity dan translasi vertikal 5 px selama 180 ms untuk menunjukkan perubahan halaman tanpa mengunci interaksi. Tidak diterapkan ke Admin.
- **Pesan baru RUKKA:** opacity dan translasi 4 px selama 180 ms agar pesan baru mudah dikenali. Pesan lama tidak dianimasikan ulang sebagai streaming.
- **Indikator pemrosesan:** tiga titik bergerak hanya selama request RUKKA benar-benar pending; tidak ada fake wait atau simulasi mengetik jawaban.
- **Auto-scroll:** mengikuti pesan baru hanya bila pembaca sudah berada dekat bagian bawah chat. `requestAnimationFrame` dibatalkan saat effect dibersihkan.
- **Kartu shortcut:** perubahan border/background dan elevasi kecil pada hover/press; fokus keyboard memakai outline yang terlihat.
- **Reduced motion:** route dan message entrance dimatikan, titik tidak bergerak, dan smooth scroll menjadi auto. Existing global policy tetap berlaku.

Animasi dialog tidak ditambahkan karena modal memakai siklus mount/unmount langsung dan mengubahnya membutuhkan perubahan lifecycle/focus di komponen bersama. Motion filter dan booking tidak menunda hasil atau submit: state feedback memakai update konten existing sehingga aksi langsung dapat diteruskan.

## Perubahan interaksi

### Dashboard mahasiswa

Ringkasan menampilkan Active, Pending, Approved, Rejected, Cancelled, dan Completed sesuai enum backend. Shortcut mengarah ke direktori ruang, availability, reservasi, dan RUKKA; notifikasi tetap tersedia di navigasi global. Aktivitas menggunakan reservasi mahasiswa dan tidak membuat data rekomendasi.

### Room discovery

Filter yang sudah diterapkan tampak sebagai chip dengan aksi hapus individual serta “Hapus semua”. Jumlah hasil diumumkan dengan live status. Empty state memberi jalan untuk menghapus filter dan mencoba kembali. Parameter yang dikirim tetap sesuai API existing.

### Booking dan alternatif

Jika pemeriksaan availability mengembalikan unavailable, mahasiswa dapat berpindah ke pencarian alternatif dengan kriteria booking saat ini. Form dan request alternatif masih mengikuti batas 7 hari, langkah 30 menit, maksimal 8 hasil. Submit booking tetap melalui dialog konfirmasi dan sukses hanya setelah API menerima permohonan.

### Reservasi

Tab Cancelled dan Completed menampilkan dua status yang sebelumnya hanya dapat dicari di tab All. Status tetap berupa teks dan warna semantik; izin pembatalan tetap ditentukan oleh helper/status existing.

### RUKKA AI

Percakapan ditandai sebagai `role="log"` dengan label yang jelas. Status “sedang memproses” hanya tampil selama request; saat error, teks pengguna tetap di composer agar bisa dikirim ulang. Input dibersihkan setelah respons sukses. Fokus composer dan auto-scroll menghormati posisi baca pengguna. Tidak ada streaming palsu atau perubahan endpoint/context/feedback AI.

## Responsive, theme, aksesibilitas, dan performa

Matriks mencakup lebar 360, 390, 430, 768, dan 1440 px untuk 11 halaman pada tema terang dan gelap. Bottom navigation tetap terlihat sampai breakpoint mobile/tablet yang diuji, dan pemeriksaan `scrollWidth` tidak menemukan overflow horizontal. Inspeksi manual screenshot dilakukan pada dashboard desktop/mobile, room directory desktop, serta RUKKA AI mobile.

Perbaikan aksesibilitas mencakup label live untuk jumlah hasil, status log untuk chat, status loading yang hanya aktif selama request, outline fokus shortcut, tombol chip filter dengan accessible name, dan kebijakan reduced motion. Axe WCAG 2.1 A/AA pada seluruh 11 halaman mahasiswa di dua tema lulus pemeriksaan critical/serious. Uji keyboard skip link/main landmark/account menu/Escape dan reduced-motion juga lulus.

Performance browser test memakai preview lokal dan fixture/mock API, bukan backend produksi. Snapshot dashboard mencatat load event 77.3 ms, FCP 84 ms, perkiraan CLS 0.04, 0 long task, 4 gambar terdeteksi lengkap, 0 gambar rusak; transfer terukur pada environment tersebut adalah 442,283 byte. Angka ini indikatif untuk test lokal, bukan SLA atau pengukuran jaringan pengguna. Build Vite melaporkan bundle JS 421.36 kB (120.90 kB gzip) dan CSS 102.19 kB (19.52 kB gzip).

## Validasi

- TypeScript `npx tsc --noEmit`: lulus.
- Unit `npm test`: 1 file, 8 test lulus.
- Local production build `VITE_API_BASE_URL='/api/v1' npx tsc --noEmit; npx vite build`: lulus, Vite 8.4.0.
- Playwright student visual matrix: 1 test lulus dan menyimpan **110 screenshot**.
- Interaksi Stage 4: 5 test lulus.
- Student login/role guard/workflows: 6 test lulus.
- Axe light/dark student, keyboard, reduced motion: 24 test lulus.
- State QA direktori/loading/error dan booking validation: 5 test lulus.
- Performance capture: 1 test lulus.
- Regresi visual TU/Admin Stage 3: 1 matriks test lulus.
- Total test browser pada rangkaian di atas: **43 lulus**.

Screenshot disimpan di `frontend/test-results/stage-4/<route>/<viewport>-<width>-<theme>.png`. Tiap route memiliki 10 screenshot (5 ukuran × 2 tema). Folder mencakup dashboard, rooms, room detail, availability, booking, alternatives, reservations, reservation detail, notifications, profile, dan assistant.

Browser E2E memakai fixture API lokal yang sudah ada di project. Backend langsung tidak diuji dengan akun/data live; API contract dan implementasi server tidak diubah.

## Kendala dan pekerjaan tersisa

Perintah wrapper `npm run build` berhenti pada `scripts/extract-brand-assets.mjs` karena script itu mengambil aset eksternal dari GitHub dan akses jaringan sandbox ditolak (`EACCES`). TypeScript check dan production build Vite lokal berhasil dijalankan terpisah menggunakan aset yang sudah ada di workspace. Tidak ada pekerjaan Stage 5 yang dimulai.
