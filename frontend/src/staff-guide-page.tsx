import {
  ArrowRight, Bell, BookOpen, Building2, CalendarCheck, CalendarDays, CheckCircle2,
  Clock3, ClipboardList, FileSpreadsheet, ShieldCheck, UserRound,
} from "lucide-react";
import { Link } from "react-router";
import { PageTitle } from "./layout";

const guideLinks = [
  { href: "#alur-kerja", label: "Alur kerja" },
  { href: "#reservasi", label: "Permohonan reservasi" },
  { href: "#ruangan-jadwal", label: "Ruangan & jadwal" },
  { href: "#monitoring", label: "Monitoring penggunaan" },
  { href: "#data-notifikasi", label: "Impor & notifikasi" },
  { href: "#faq", label: "FAQ" },
];

export function AdminGuidePage() {
  return (
    <div className="page-stack staff-guide-page">
      <PageTitle
        eyebrow="PUSAT BANTUAN · STAFF SEKRETARIAT"
        title="Panduan penggunaan RuangKampus"
        description="Panduan kerja Staff Tata Usaha untuk mengelola permohonan, fasilitas, jadwal, dan penggunaan ruang kampus."
        action={<Link className="button button--secondary" to="/admin/dashboard">Kembali ke dashboard</Link>}
      />

      <section className="panel staff-guide-hero">
        <div className="staff-guide-hero__icon"><BookOpen size={30} aria-hidden="true" /></div>
        <div className="staff-guide-hero__content">
          <p className="eyebrow">PANDUAN OPERASIONAL STAFF TU</p>
          <h2>Semua alur pengelolaan ruang dalam satu tempat.</h2>
          <p>Gunakan panduan ini sebagai referensi saat memeriksa pengajuan reservasi, memperbarui informasi fasilitas, mengatur jadwal, dan memastikan ruang digunakan sesuai waktu yang disetujui.</p>
          <div className="staff-guide-hero__meta">
            <span><ShieldCheck size={15} /> Akses khusus Staff Sekretariat</span>
            <span><Clock3 size={15} /> Waktu kampus menggunakan WIB</span>
          </div>
        </div>
      </section>

      <nav className="panel staff-guide-index" aria-label="Daftar isi panduan">
        <div>
          <b>Di halaman ini</b>
          <small>Pilih topik untuk langsung menuju bagian panduan.</small>
        </div>
        <div className="staff-guide-index__links">
          {guideLinks.map((item) => <a href={item.href} key={item.href}>{item.label}<ArrowRight size={13} /></a>)}
        </div>
      </nav>

      <section id="alur-kerja" className="panel staff-guide-section">
        <div className="staff-guide-section__heading">
          <span className="staff-guide-section__icon"><CheckCircle2 size={21} /></span>
          <div><p className="eyebrow">MULAI DI SINI</p><h2>Alur kerja Staff TU</h2><p>Ikuti urutan berikut untuk menjalankan pekerjaan administrasi harian.</p></div>
        </div>
        <div className="staff-guide-steps">
          <article className="staff-guide-step"><span className="staff-guide-step__number">01</span><div><b>Masuk ke akun Staff Sekretariat</b><p>Gunakan akun petugas yang telah diberikan. Setelah berhasil masuk, sistem akan membuka dashboard administrasi.</p></div><Link to="/admin/dashboard" aria-label="Buka dashboard"><ArrowRight size={17} /></Link></article>
          <article className="staff-guide-step"><span className="staff-guide-step__number">02</span><div><b>Periksa dashboard dan permohonan baru</b><p>Lihat ringkasan reservasi, permohonan yang menunggu, notifikasi, serta daftar penggunaan ruang hari ini.</p></div><Link to="/admin/reservations" aria-label="Buka permohonan reservasi"><ArrowRight size={17} /></Link></article>
          <article className="staff-guide-step"><span className="staff-guide-step__number">03</span><div><b>Tinjau dan putuskan permohonan</b><p>Periksa detail pengajuan sebelum menyetujui atau menolak. Sertakan alasan yang jelas ketika menolak permohonan.</p></div><Link to="/admin/reservations" aria-label="Tinjau reservasi"><ArrowRight size={17} /></Link></article>
          <article className="staff-guide-step"><span className="staff-guide-step__number">04</span><div><b>Pastikan data ruang dan jadwal akurat</b><p>Perbarui informasi fasilitas, jadwal akademik, dan periode pemeliharaan agar ketersediaan ruang tetap sesuai kondisi.</p></div><Link to="/admin/rooms" aria-label="Kelola ruangan"><ArrowRight size={17} /></Link></article>
          <article className="staff-guide-step"><span className="staff-guide-step__number">05</span><div><b>Pantau penggunaan sampai selesai</b><p>Gunakan jam kampus dan countdown untuk memantau reservasi. Konfirmasikan kondisi ruang secara langsung sebelum menandai penggunaan selesai.</p></div><Link to="/admin/dashboard" aria-label="Pantau dashboard"><ArrowRight size={17} /></Link></article>
        </div>
      </section>

      <section id="reservasi" className="panel staff-guide-section">
        <div className="staff-guide-section__heading">
          <span className="staff-guide-section__icon"><ClipboardList size={21} /></span>
          <div><p className="eyebrow">01 · RESERVATION REVIEW</p><h2>Meninjau permohonan reservasi</h2><p>Halaman Permohonan reservasi menjadi tempat utama untuk memeriksa dan memproses pengajuan mahasiswa.</p></div>
        </div>
        <ol className="staff-guide-list">
          <li>Buka menu <b>Permohonan</b> pada navigasi admin.</li>
          <li>Gunakan tab <b>Menunggu</b>, <b>Disetujui</b>, <b>Ditolak</b>, atau <b>Semua</b> untuk menyaring status pengajuan.</li>
          <li>Gunakan kolom pencarian untuk menemukan pengajuan berdasarkan nama pemohon, nama ruang, tujuan kegiatan, atau ID reservasi.</li>
          <li>Buka detail pengajuan. Periksa identitas pemohon, ruangan, tanggal, jam, jumlah peserta, dan tujuan penggunaan.</li>
          <li>Pilih tindakan setujui atau tolak sesuai hasil pemeriksaan. Untuk penolakan, masukkan alasan minimal 3 karakter agar pemohon memahami keputusan.</li>
          <li>Pastikan status terbaru sudah tampil setelah tindakan berhasil disimpan. Periksa notifikasi bila perlu memastikan pembaruan tersampaikan.</li>
        </ol>
        <div className="staff-guide-note"><ShieldCheck size={18} /><p><b>Periksa konflik sebelum menyetujui.</b> Pastikan waktu yang diminta tidak berbenturan dengan jadwal akademik, periode pemeliharaan, atau reservasi lain pada ruangan yang sama.</p></div>
        <Link className="text-link" to="/admin/reservations">Buka permohonan reservasi <ArrowRight size={14} /></Link>
      </section>

      <section id="ruangan-jadwal" className="staff-guide-card-grid">
        <article className="panel staff-guide-card">
          <span className="staff-guide-card__icon"><Building2 size={21} /></span>
          <p className="eyebrow">02 · ROOM MANAGEMENT</p>
          <h2>Mengelola ruangan</h2>
          <p>Gunakan halaman Kelola ruangan untuk menjaga inventaris dan informasi fasilitas tetap benar.</p>
          <ul>
            <li>Cari ruangan berdasarkan nama, gedung, atau kode.</li>
            <li>Tambah ruangan baru dan lengkapi nama, gedung, kapasitas, fasilitas, serta jam operasional.</li>
            <li>Edit data bila ada perubahan fasilitas atau informasi ruang.</li>
            <li>Perbarui status ruangan sesuai kondisinya: aktif, nonaktif, atau pemeliharaan.</li>
            <li>Gunakan pilihan beberapa ruangan sekaligus bila perlu memperbarui status secara massal.</li>
          </ul>
          <Link className="text-link" to="/admin/rooms">Buka kelola ruangan <ArrowRight size={14} /></Link>
        </article>
        <article className="panel staff-guide-card">
          <span className="staff-guide-card__icon"><CalendarDays size={21} /></span>
          <p className="eyebrow">03 · SCHEDULE & MAINTENANCE</p>
          <h2>Mengatur jadwal dan pemeliharaan</h2>
          <p>Gunakan menu Jadwal & pemeliharaan untuk mencatat waktu penggunaan terjadwal dan waktu ruang tidak tersedia.</p>
          <ul>
            <li>Pilih ruangan yang akan diatur.</li>
            <li>Tambahkan jadwal akademik satu tanggal tertentu atau jadwal mingguan.</li>
            <li>Isi nama kegiatan atau mata kuliah, tanggal/hari, serta jam mulai dan selesai.</li>
            <li>Untuk pemeliharaan atau penutupan sementara, tambahkan periode tidak tersedia beserta alasan minimal 3 karakter.</li>
            <li>Pastikan jam selesai lebih akhir daripada jam mulai, lalu periksa kembali daftar jadwal dan periode yang tersimpan.</li>
          </ul>
          <Link className="text-link" to="/admin/schedules">Buka jadwal & pemeliharaan <ArrowRight size={14} /></Link>
        </article>
      </section>

      <section id="monitoring" className="panel staff-guide-section">
        <div className="staff-guide-section__heading">
          <span className="staff-guide-section__icon"><CalendarCheck size={21} /></span>
          <div><p className="eyebrow">04 · LIVE ROOM MONITOR</p><h2>Memantau penggunaan ruangan</h2><p>Dashboard menampilkan jam kampus dan status reservasi yang dijadwalkan pada hari berjalan.</p></div>
        </div>
        <div className="staff-guide-monitor-grid">
          <div><span className="staff-guide-monitor-grid__label">Akan dimulai</span><b>Mulai sesuai jadwal</b><p>Perhatikan waktu mulai yang ditampilkan agar petugas mengetahui reservasi berikutnya.</p></div>
          <div><span className="staff-guide-monitor-grid__label">Sedang berlangsung</span><b>Countdown sisa waktu</b><p>Countdown berjalan berdasarkan waktu mulai dan berakhir sesuai jam selesai reservasi.</p></div>
          <div><span className="staff-guide-monitor-grid__label">Melewati jadwal</span><b>Perlu tindak lanjut</b><p>Gunakan informasi keterlambatan untuk menghubungi peminjam dan memeriksa kondisi ruangan.</p></div>
        </div>
        <ul className="staff-guide-list">
          <li>Jam pada dashboard menggunakan zona waktu kampus <b>WIB (Asia/Jakarta)</b> dan diperbarui setiap detik.</li>
          <li>Sebelum mulai, kartu menampilkan label “Mulai dalam”. Saat penggunaan berlangsung, label berubah menjadi “Sisa waktu”; peringatan “Segera berakhir” muncul ketika sisa waktu 5 menit atau kurang. Setelah melewati jam selesai, kartu menampilkan durasi keterlambatan.</li>
          <li>Hubungi peminjam atau petugas terkait jika penggunaan belum berakhir sesuai waktu yang disetujui.</li>
          <li>Setelah mahasiswa meninggalkan ruangan, lakukan pemeriksaan fisik untuk memastikan ruangan benar-benar kosong.</li>
        </ul>
        <div className="staff-guide-warning"><Clock3 size={18} /><p><b>Penting:</b> Sistem tidak mengeluarkan pengguna dari ruangan secara otomatis. Tombol penyelesaian hanya digunakan setelah petugas memastikan mahasiswa sudah meninggalkan ruangan.</p></div>
        <Link className="text-link" to="/admin/dashboard">Buka dashboard monitoring <ArrowRight size={14} /></Link>
      </section>

      <section id="data-notifikasi" className="staff-guide-card-grid">
        <article className="panel staff-guide-card">
          <span className="staff-guide-card__icon"><FileSpreadsheet size={21} /></span>
          <p className="eyebrow">05 · DATA IMPORT</p>
          <h2>Mengimpor data kampus</h2>
          <p>Halaman Impor data kampus menampilkan tiga jenis data. Saat ini, impor data ruangan sudah tersedia, sedangkan data mahasiswa dan mata kuliah masih menunggu file resmi dari unit akademik.</p>
          <ul>
            <li>Pilih tab jenis data yang akan diproses.</li>
            <li>Siapkan file sesuai format dan kolom yang diminta pada halaman impor.</li>
            <li>Untuk data ruangan, gunakan workbook <b>.xlsx</b> dengan ukuran maksimal <b>5 MB</b>.</li>
            <li>Jalankan <b>Pratinjau & validasi</b>, lalu periksa seluruh baris, pesan validasi, dan foto sebelum menyimpan.</li>
            <li>Konfirmasikan impor hanya setelah data yang valid sudah diperiksa.</li>
          </ul>
          <Link className="text-link" to="/admin/data-imports">Buka impor data kampus <ArrowRight size={14} /></Link>
        </article>
        <article className="panel staff-guide-card">
          <span className="staff-guide-card__icon"><Bell size={21} /></span>
          <p className="eyebrow">06 · NOTIFICATIONS</p>
          <h2>Memeriksa notifikasi</h2>
          <p>Notifikasi membantu petugas mengikuti perubahan dan aktivitas terkait reservasi.</p>
          <ul>
            <li>Ikon lonceng pada header menampilkan jumlah notifikasi yang belum dibaca.</li>
            <li>Buka halaman Notifikasi untuk membaca pembaruan dan membuka konteks reservasi terkait.</li>
            <li>Periksa status email: diterima penyedia email, tersimpan di kotak lokal, sedang diproses, gagal dikirim, atau email tidak diaktifkan.</li>
            <li>Jika email gagal dikirim, gunakan tombol coba ulang selama jumlah percobaan belum mencapai 3 kali.</li>
          </ul>
          <Link className="text-link" to="/admin/notifications">Buka notifikasi <ArrowRight size={14} /></Link>
        </article>
      </section>

      <section className="panel staff-guide-section">
        <div className="staff-guide-section__heading">
          <span className="staff-guide-section__icon"><UserRound size={21} /></span>
          <div><p className="eyebrow">07 · ACCOUNT & SECURITY</p><h2>Mengelola profil dan keamanan akun</h2><p>Perbarui informasi akun dan jaga akses Staff Sekretariat tetap aman.</p></div>
        </div>
        <ul className="staff-guide-list">
          <li>Buka menu <b>Profil</b> untuk memperbarui nama, email, atau nomor telepon.</li>
          <li>Periksa kembali email sebelum menyimpan perubahan karena email digunakan sebagai informasi akun.</li>
          <li>Gunakan bagian <b>Ubah password</b> untuk mengganti kata sandi. Masukkan password saat ini, password baru, lalu konfirmasi password baru dengan nilai yang sama.</li>
          <li>Gunakan pilihan tampilan terang atau gelap sesuai kenyamanan kerja.</li>
          <li>Jangan membagikan password atau membiarkan akun tetap terbuka pada perangkat bersama. Keluar dari aplikasi setelah selesai bertugas.</li>
        </ul>
        <Link className="text-link" to="/admin/profile">Buka profil akun <ArrowRight size={14} /></Link>
      </section>

      <section id="faq" className="panel staff-guide-section staff-guide-faq">
        <div className="staff-guide-section__heading">
          <span className="staff-guide-section__icon"><BookOpen size={21} /></span>
          <div><p className="eyebrow">HELP CENTER</p><h2>Pertanyaan yang sering diajukan</h2><p>Jawaban ringkas untuk situasi yang sering ditemui saat bertugas.</p></div>
        </div>
        <details><summary>Bagaimana cara menyetujui atau menolak permohonan?</summary><p>Buka Permohonan, pilih status yang ingin diperiksa, cari pengajuan, lalu buka detailnya. Periksa informasi pemohon, ruang, waktu, peserta, dan tujuan. Pilih tindakan yang sesuai. Jika menolak, tuliskan alasan yang jelas.</p></details>
        <details><summary>Apa yang harus diperiksa sebelum menyetujui reservasi?</summary><p>Pastikan ruangan sesuai kebutuhan, kapasitas mencukupi, jam operasional memungkinkan, serta tidak ada jadwal akademik, pemeliharaan, atau reservasi lain yang berbenturan.</p></details>
        <details><summary>Apa arti countdown pada monitoring reservasi?</summary><p>Countdown membantu melihat waktu menuju dimulainya atau berakhirnya sesi sesuai jadwal reservasi. Gunakan jam kampus WIB sebagai acuan dan perhatikan status reservasi yang ditampilkan.</p></details>
        <details><summary>Apakah sistem otomatis menghentikan penggunaan ruangan saat waktunya habis?</summary><p>Tidak. Sistem hanya menampilkan waktu dan status. Petugas tetap perlu menghubungi peminjam bila terlambat dan memastikan secara langsung bahwa ruangan sudah kosong sebelum menandai reservasi selesai.</p></details>
        <details><summary>Mengapa file impor ruangan tidak dapat diproses?</summary><p>Pastikan file menggunakan format .xlsx dan ukurannya tidak lebih dari 5 MB. Gunakan workbook dan kolom yang sesuai, lalu baca pesan validasi pada pratinjau sebelum mencoba menyimpan kembali.</p></details>
        <details><summary>Apa yang perlu disiapkan saat melaporkan kendala?</summary><p>Catat halaman yang dibuka, ID reservasi atau nama ruangan terkait, tanggal dan jam kejadian, pesan kesalahan yang tampil, serta tangkapan layar jika tersedia. Jangan sertakan password atau informasi rahasia akun.</p></details>
      </section>

      <section className="staff-guide-footer">
        <div><b>Butuh kembali ke pekerjaan?</b><p>Buka halaman yang sesuai dari pintasan berikut.</p></div>
        <div className="staff-guide-footer__links">
          <Link className="button button--secondary" to="/admin/reservations">Permohonan</Link>
          <Link className="button button--secondary" to="/admin/rooms">Kelola ruangan</Link>
          <Link className="button button--primary" to="/admin/dashboard">Dashboard</Link>
        </div>
      </section>
    </div>
  );
}
