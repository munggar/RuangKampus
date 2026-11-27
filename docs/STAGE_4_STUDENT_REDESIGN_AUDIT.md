# Stage 4 — Audit pra-implementasi Student Experience

## Cakupan route mahasiswa

| Halaman | Route | Kondisi awal dan sumber data |
|---|---|---|
| Dashboard | `/student/dashboard` | Ringkasan personal dari `/dashboard/summary`, 8 reservasi terbaru dari `/dashboard/recent-reservations`; menampilkan jumlah aktif (pending + approved), satu approved mendatang, dan 3 aktivitas terakhir. Belum ada shortcut sekumpulan fitur. Tidak ada ranking rekomendasi personal. |
| Direktori ruang | `/student/rooms` | Search, fakultas, gedung, lokasi, kapasitas minimum, fasilitas memakai parameter endpoint `/rooms`; hasil menampilkan ruang aktif dengan status inventaris, foto/reserve fallback, lokasi, fasilitas. Filter diterapkan saat submit form dan dapat di-reset. |
| Detail ruang | `/student/rooms/:roomId` | `/rooms/:id` mengembalikan detail resmi. Ada foto jika URL tersedia, kapasitas, jam/lokasi, fasilitas, CTA booking. Tidak ada jadwal slot atau ketersediaan yang dipastikan pada halaman ini. |
| Ketersediaan | `/student/availability` | Daftar ruang aktif difilter backend dengan tanggal/jam/peserta; saat halaman pertama kosong, aplikasi mengambil kandidat dan meminta alasan availability untuk maksimal 15 ruang. Menyebut hasil sebagai pemeriksaan pada saat halaman dimuat dan menyatakan backend akan memvalidasi ulang. |
| Booking | `/student/rooms/:roomId/book` | Satu form existing dengan parameter deep-link, pemeriksaan `/rooms/:id/availability`, validasi field di frontend, dialog review/konfirmasi, lalu `POST /reservations`. Navigasi ke detail dengan `?created=1` hanya setelah respons sukses. |
| Alternatif waktu | `/student/alternatives` | Form memakai `POST /rooms/alternative-slots`, rentang pencarian 7 hari, langkah 30 menit, hingga 8 rekomendasi; kartu slot mengarah ke booking dengan waktu/peserta yang dikembalikan API. |
| Reservasi | `/student/reservations` | List 100 teratas, tab Semua/Pending/Approved/Rejected, pencarian lokal, batal untuk status/tanggal yang memenuhi `canCancelReservation`. Belum ada tab khusus cancelled/completed. |
| Detail reservasi | `/student/reservations/:reservationId` | `GET /reservations/:id`; status, data ruang/waktu/keperluan, alasan penolakan dan dialog batal menurut status. Success awal memakai query `created=1`. |
| Notifikasi | `/student/notifications` | List API, mark read individual/semua, unread state dan empty/loading/error. Komponen dipakai bersama TU. |
| Profil | `/student/profile` | Data `GET/PATCH /users/me`, ubah password, theme toggle, bantuan. Komponen dipakai bersama TU. |
| RUKKA AI | `/student/assistant` | Satu request `POST /assistant/chat` per pesan; context sampai 10 turn di tab; hasil dapat berisi rooms, alternatif, reservations, follow-up dan metadata intent/engine. Feedback memakai `/assistant/feedback`. Tidak ada streaming; loading spinner ditampilkan selama request aktual. |

Routing juga memiliki halaman 404, reset/auth publik, dan halaman assistant fallback yang tidak dipakai route RUKKA aktif. Route mahasiswa dilindungi `RequireRole("Student")`.

## Komponen, tema, responsive

- `PageTitle`, `PageSection`, `Field`, `Button`, `Notice`, `Loading`, `EmptyState`, `Modal`, `ConfirmModal`, `StatusBadge`, `ReservationCard`, serta kartu ruang dipakai lintas halaman.
- Shell memakai sidebar desktop, header akun/theme/notifikasi, dan bottom navigation mobile lima item. RUKKA sudah tersedia di navigation.
- Token CSS menyediakan palet semantic light/dark, Plus Jakarta Sans Variable, spacing, radius, status, dan motion 120/180 ms. `data-theme`, `rk-theme`, serta event `rk-theme-change` adalah kontrak theme yang harus tetap.
- Breakpoint shell berpindah ke navigasi mobile pada 920px, kisi/form reflow di breakpoint lebih kecil, dan bottom nav memperhitungkan safe-area. Pemeriksaan harus tetap mencakup 360, 390, 430, serta 768 px.

## Audit motion baseline

- Tombol, navigation link, field, room/reservation card, recommendation card, dan beberapa panel punya transisi CSS eksplisit pada warna/border/transform. Hover card ruang mengubah transform gambar.
- Motion utama saat ini spinner request dan beberapa jam/countdown timer; tidak ditemukan page transition, state transition hasil pencarian, animasi masuk pesan, atau indikator proses RUKKA khusus.
- Modal sudah mempunyai label, fokus awal, focus containment, Escape, serta pemulihan fokus, tetapi mount/unmount visualnya langsung. Jangan mengganti manajemen fokus untuk menambahkan animasi.
- `prefers-reduced-motion` global memang memendekkan animasi dan mematikan smooth scroll. Dekorasi gerak baru harus ikut kebijakan ini.
- RUKKA tidak melakukan stream. Animasi per karakter atau simulasi typing akan memberi kesan proses yang tidak terjadi dan dikecualikan.

## Batas integrasi dan keputusan desain

- `dashboard/summary` serta recent reservations bersifat spesifik user untuk Student; `room-statistics` justru TU-only. Shortcut dan activity student dapat memakai sumber personal tersebut.
- Belum ada endpoint rekomendasi personal atau data histori preferensi; kartu “direkomendasikan untuk Anda” tidak didukung data. Direktori/ketersediaan dapat ditonjolkan dengan CTA yang jelas tanpa mengarang ranking.
- Status reservasi yang sah: `PENDING`, `APPROVED`, `REJECTED`, `CANCELLED`, `COMPLETED`. Status warna selalu disertai teks.
- Foto ruang hanya dari `photo_url` inventaris; fallback menggunakan ikon Tabler, bukan foto sintetis.
- Tidak mengubah API, auth/role, path, urutan alur booking, status, validasi server, integrasi AI, maupun mekanisme theme.
- Untuk motion: route enter singkat opacity/translate pada wrapper Student; animasi masuk pesan hanya pada pesan baru; indikator AI tampil hanya saat request berlangsung; auto-scroll hanya jika pembaca sudah dekat dasar chat. Semua interaksi langsung, bisa diinterupsi, dan gerak spasial hilang di reduced motion.

## Referensi skill dibaca

Skill utama dibaca ulang: `ui-ux-pro-max`, `web-design-guidelines`, `ui-motion`, `design-system`, `ui-styling`, `brand`, dan `design`. Referensi terapan yang dibaca mencakup guidelines command, token/semantic/component/state specs, shadcn accessibility, responsive guidance, brand identity/consistency/logo/typography, serta ui-motion timing, component interaction, code recipe, dan validation. Project menggunakan CSS biasa dan Tabler, bukan Tailwind/shadcn; karena itu contoh skill dipakai sebagai prinsip, bukan alasan menambah dependency. Python CLI `ui-ux-pro-max` tidak tersedia; Quick Reference lokal diterapkan manual.
