import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type AppLanguage = "id" | "en";

const pairs: Array<[string, string]> = [
  ["Lewati ke konten utama", "Skip to main content"],
  ["Student workspace", "Student workspace"],
  ["Student portal", "Student portal"],
  ["Dashboard", "Dashboard"],
  ["Beranda", "Home"],
  ["Ruang", "Room"],
  ["Rooms", "Rooms"],
  ["AI Assistant", "AI Assistant"],
  ["Asisten AI", "AI Assistant"],
  ["My bookings", "My bookings"],
  ["Profile", "Profile"],
  ["Profil", "Profile"],
  ["Profil akun", "Account profile"],
  ["Keluar", "Sign out"],
  ["Masuk", "Sign in"],
  ["Daftar", "Register"],
  ["Notifikasi", "Notifications"],
  ["Buka notifikasi", "Open notifications"],
  ["Mahasiswa", "Student"],
  ["Staff Sekretariat", "Secretariat Staff"],
  ["Jadwal & pemeliharaan", "Schedules & maintenance"],
  ["Impor data kampus", "Campus data import"],
  ["Impor data", "Import data"],
  ["Permohonan reservasi", "Reservation requests"],
  ["Reservation requests", "Reservation requests"],
  ["Manage rooms", "Manage rooms"],
  ["Kelola ruangan", "Manage rooms"],
  ["Detail ruangan", "Room details"],
  ["Direktori ruangan", "Room directory"],
  ["Kembali ke direktori", "Back to room directory"],
  ["Ajukan reservasi", "Request a reservation"],
  ["Edit ruangan", "Edit room"],
  ["Tambah ruangan", "Add room"],
  ["Hapus", "Delete"],
  ["Hapus pilihan", "Delete selected"],
  ["Cari ruangan", "Search rooms"],
  ["Cari nama, ruang, atau ID", "Search name, room, or ID"],
  ["Cari nama mahasiswa atau ruangan", "Search student or room"],
  ["Nama ruangan, gedung, atau kode", "Room name, building, or code"],
  ["Cari berdasarkan nama, fasilitas, atau lokasi", "Search by name, facilities, or location"],
  ["Cari berdasarkan nama, kode, atau lokasi", "Search by name, code, or location"],
  ["Cari", "Search"],
  ["Reset filter", "Reset filters"],
  ["Semua status", "All statuses"],
  ["Semua fakultas", "All faculties"],
  ["Semua gedung", "All buildings"],
  ["Semua", "All"],
  ["Status", "Status"],
  ["Aktif", "Active"],
  ["Nonaktif", "Inactive"],
  ["Pemeliharaan", "Maintenance"],
  ["Menunggu", "Pending"],
  ["Disetujui", "Approved"],
  ["Ditolak", "Rejected"],
  ["Dibatalkan", "Cancelled"],
  ["Selesai", "Completed"],
  ["Kapasitas", "Capacity"],
  ["Fasilitas", "Facilities"],
  ["Lokasi", "Location"],
  ["Gedung", "Building"],
  ["Fakultas", "Faculty"],
  ["Lantai", "Floor"],
  ["Jam operasional", "Operating hours"],
  ["Jam buka", "Opening time"],
  ["Jam tutup", "Closing time"],
  ["Buka", "Open"],
  ["Tutup", "Close"],
  ["Pilih semua yang tampil", "Select all visible"],
  ["Pilih status…", "Choose a status…"],
  ["Ubah status menjadi", "Change status to"],
  ["Terapkan status", "Apply status"],
  ["Atur jam operasional", "Set operating hours"],
  ["Batal pilih", "Clear selection"],
  ["ruangan dipilih", "rooms selected"],
  ["ruangan dalam inventaris kampus", "rooms in the campus inventory"],
  ["nonaktif atau pemeliharaan", "inactive or under maintenance"],
  ["Centang ruangan untuk mengubah status atau jam operasional beberapa ruangan sekaligus.", "Select rooms to change their status or operating hours in one action."],
  ["Memuat data…", "Loading data…"],
  ["Memuat inventaris ruangan…", "Loading room inventory…"],
  ["Memuat detail ruangan…", "Loading room details…"],
  ["Data ruangan belum dapat dimuat.", "Room data could not be loaded."],
  ["Detail ruangan belum dapat dimuat.", "Room details could not be loaded."],
  ["Ruangan tidak ditemukan", "Room not found"],
  ["Ruangan mungkin sudah tidak aktif atau tidak tersedia.", "This room may be inactive or unavailable."],
  ["Ruangan belum tersedia", "No rooms available"],
  ["Tambahkan ruangan baru untuk memulai pengelolaan inventaris.", "Add a room to start managing the inventory."],
  ["Tidak ada ruangan yang cocok", "No matching rooms found"],
  ["Ubah filter atau kata kunci pencarian.", "Change the filters or search terms."],
  ["Tentang ruangan ini", "About this room"],
  ["Fasilitas", "Facilities"],
  ["Belum ada fasilitas yang dicatat.", "No facilities have been recorded."],
  ["Informasi ruangan dikelola oleh administrator kampus.", "Room information is managed by the campus administrator."],
  ["Mengikuti jadwal terdaftar", "Follows the registered schedule"],
  ["Belum diatur", "Not configured"],
  ["orang", "people"],
  ["estimasi", "estimated"],
  ["Pilih minimal satu hari operasional.", "Select at least one operating day."],
  ["Jam tutup harus lebih akhir dari jam buka.", "The closing time must be later than the opening time."],
  ["Hari dan jam yang dipilih akan langsung diterapkan ke seluruh ruangan terpilih setelah disimpan.", "The selected days and hours will be applied to all selected rooms after saving."],
  ["Perubahan akan ditolak untuk semua ruangan apabila jadwal kuliah atau reservasi mendatang berada di luar jam yang dipilih. Tidak ada perubahan sebagian.", "The change will be rejected for every room if a class schedule or upcoming reservation falls outside the selected hours. Partial updates will not be applied."],
  ["Batal", "Cancel"],
  ["Kembali", "Back"],
  ["Simpan", "Save"],
  ["Menyimpan…", "Saving…"],
  ["Simpan jam operasional", "Save operating hours"],
  ["Memproses…", "Processing…"],
  ["Peringatan", "Warning"],
  ["Area bahaya", "Danger zone"],
  ["Hapus ruangan terpilih", "Delete selected rooms"],
  ["Hapus semua pilihan", "Delete all selected"],
  ["Konfirmasi penghapusan", "Confirm deletion"],
  ["Ketik HAPUS untuk melanjutkan", "Type DELETE to continue"],
  ["Data ruangan yang dipilih akan dihapus dari direktori.", "The selected rooms will be removed from the directory."],
  ["Data riwayat reservasi tetap dipertahankan.", "Reservation history will be retained."],
  ["Ruangan dengan reservasi mendatang yang masih menunggu atau disetujui tidak dapat dihapus.", "Rooms with upcoming pending or approved reservations cannot be deleted."],
  ["Jika satu ruangan terhalang, seluruh penghapusan dibatalkan.", "If even one room is blocked, the entire deletion is cancelled."],
  ["Tidak ada perubahan sebagian.", "No partial changes will be made."],
  ["Hapus ruangan", "Delete room"],
  ["Hapus ruangan terpilih?", "Delete selected rooms?"],
  ["Ya, hapus pilihan", "Yes, delete selected"],
  ["ruangan berhasil dihapus dari direktori.", "rooms were removed from the directory."],
  ["Riwayat reservasi tetap tersimpan.", "Reservation history has been retained."],
  ["Tidak ada ruangan yang dihapus.", "No rooms were deleted."],
  ["Berhasil", "Success"],
  ["Login belum berhasil. Periksa kembali data masuk Anda.", "Login failed. Please check your sign-in details."],
  ["Masuk dengan akun universitas yang terdaftar.", "Sign in with your registered university account."],
  ["Selamat datang kembali", "Welcome back"],
  ["Masukkan NIM Anda", "Enter your student ID"],
  ["Username Staff Sekretariat", "Secretariat staff username"],
  ["Masukkan password", "Enter your password"],
  ["Sembunyikan password", "Hide password"],
  ["Tampilkan password", "Show password"],
  ["Lupa password?", "Forgot password?"],
  ["Masuk ke RuangKampus", "Sign in to RuangKampus"],
  ["Memeriksa…", "Checking…"],
  ["Belum punya akun?", "Don't have an account?"],
  ["Daftar sebagai Student", "Register as a student"],
  ["Mengalami kendala? Hubungi administrator kampus untuk bantuan akun.", "Need help? Contact your campus administrator for account support."],
  ["Daftar RuangKampus", "Register for RuangKampus"],
  ["Nama lengkap", "Full name"],
  ["Nama sesuai identitas kampus", "Name as shown in your campus record"],
  ["Email kampus", "Campus email"],
  ["Masukkan NIM aktif Anda", "Enter your active student ID"],
  ["Nomor telepon (opsional)", "Phone number (optional)"],
  ["Konfirmasi password", "Confirm password"],
  ["Ulangi password", "Re-enter password"],
  ["Buat akun Student", "Create student account"],
  ["Membuat akun…", "Creating account…"],
  ["Sudah punya akun?", "Already have an account?"],
  ["Masuk di sini", "Sign in here"],
  ["Nama sesuai identitas kampus", "Name as shown in your campus record"],
  ["Pendaftaran publik otomatis membuat role Student. Akun Staff Sekretariat dibuat secara terpisah oleh operator.", "Public registration automatically creates a Student role. Secretariat Staff accounts are created separately by an operator."],
  ["Password harus terdiri dari minimal 8 karakter.", "Password must be at least 8 characters long."],
  ["Konfirmasi password belum sama.", "The passwords do not match."],
  ["Pendaftaran belum berhasil. Silakan coba kembali.", "Registration failed. Please try again."],
  ["Buat akun Student untuk mencari ruangan dan mengajukan reservasi kampus. NIM akan digunakan untuk login.", "Create a student account to find rooms and request campus reservations. Your student ID will be used to sign in."],
  ["WELCOME BACK", "WELCOME BACK"],
  ["CREATE YOUR ACCOUNT", "CREATE YOUR ACCOUNT"],
  ["CAMPUS FACILITY RESERVATIONS", "CAMPUS FACILITY RESERVATIONS"],
  ["Menyiapkan RuangKampus", "Preparing RuangKampus"],
  ["Menghubungkan sesi dan memuat aplikasi…", "Restoring your session and loading the app…"],
  ["ROOM MANAGEMENT", "ROOM MANAGEMENT"],
  ["RESERVATION REVIEW", "RESERVATION REVIEW"],
  ["STUDENT PORTAL", "STUDENT PORTAL"],
  ["ADMINISTRATION", "ADMINISTRATION"],
  ["Campus facilities", "Campus facilities"],
  ["Cari ruangan dengan kapasitas dan fasilitas tertentu", "Find rooms by capacity and facilities"],
  ["Pilih tanggal", "Select date"],
  ["Tanggal", "Date"],
  ["Waktu mulai", "Start time"],
  ["Waktu selesai", "End time"],
  ["Jumlah peserta", "Number of participants"],
  ["Tujuan penggunaan", "Purpose of use"],
  ["Catatan (opsional)", "Notes (optional)"],
  ["Kirim permohonan", "Submit request"],
  ["Ajukan permohonan", "Submit request"],
  ["Detail reservasi", "Reservation details"],
  ["Permohonan reservasi berhasil dikirim.", "Your reservation request has been submitted."],
  ["Tidak ada permohonan yang cocok", "No matching requests"],
  ["Tinjau detail pengajuan sebelum menetapkan keputusan.", "Review the request details before making a decision."],
  ["Setujui", "Approve"],
  ["Tolak", "Reject"],
  ["Alasan penolakan", "Rejection reason"],
  ["Alasan penolakan wajib dicatat dan akan terlihat oleh pemohon.", "A rejection reason is required and will be visible to the requester."],
  ["Kirim penolakan", "Submit rejection"],
  ["Setujui permohonan?", "Approve this request?"],
  ["Tolak permohonan", "Reject request"],
  ["Ya, ubah semua status", "Yes, update all statuses"],
  ["Semua ruangan terpilih akan diubah menjadi", "All selected rooms will be changed to"],
  ["Ubah status", "Change status"],
  ["Tanggal mulai", "Start date"],
  ["Tanggal akhir", "End date"],
  ["Cari ruang 20 orang + proyektor", "Find a room for 20 people with a projector"],
  ["Cek ruang kosong besok 10.00–12.00", "Check room availability tomorrow, 10:00–12:00"],
  ["Ada ruang dengan Wi-Fi?", "Are there rooms with Wi-Fi?"],
  ["Tulis pesan ke RUKKA AI…", "Message RUKKA AI…"],
  ["Kirim", "Send"],
  ["Jawaban ini membantu?", "Was this answer helpful?"],
  ["Mode standar", "Standard mode"],
  ["AI aktif", "AI active"],
  ["Bahasa", "Language"],
  ["Bahasa / Language", "Language"],
  ["Ketik HAPUS untuk mengonfirmasi", "Type DELETE to confirm"],
  ["Ketik HAPUS", "Type DELETE"],
  ["AREA BAHAYA", "DANGER ZONE"],
  ["Hapus pilihan", "Delete selected"],
  ["ruangan berhasil dihapus dari direktori", "rooms were removed from the directory"],
  ["Riwayat reservasi tetap tersimpan", "Reservation history has been retained"],
  ["Indonesia", "Indonesian"],
  ["Inggris", "English"],
  ["Pilih bahasa", "Choose language"],
  ["Find the Room. Book the Space.", "Find the Room. Book the Space."],
];


pairs.push(
  ["Tinjau permohonan", "Review requests"],
  ["Menunggu peninjauan", "Awaiting review"],
  ["Permohonan berstatus pending", "Pending requests"],
  ["Reservasi disetujui", "Approved reservations"],
  ["Total sepanjang waktu", "All-time total"],
  ["Inventaris ruangan", "Room inventory"],
  ["Total reservasi", "Total reservations"],
  ["Gabungan seluruh status", "All statuses combined"],
  ["Distribusi status tidak dapat ditampilkan karena ringkasan belum tersedia.", "Status distribution is unavailable because the summary has not loaded."],
  ["Disetujui & selesai · sepanjang waktu", "Approved & completed · all time"],
  ["Buka antrian", "Open queue"],
  ["Lihat seluruh permohonan", "View all requests"],
  ["WAKTU KAMPUS · WIB", "CAMPUS TIME · WIB"],
  ["Data diperbarui otomatis · 30 detik", "Data refreshes automatically · 30 seconds"],
  ["Konfirmasi ruangan kosong", "Confirm room is vacant"],
  ["Lihat semua", "View all"],
  ["Pemohon", "Requester"],
  ["Ruangan", "Room"],
  ["Jadwal", "Schedule"],
  ["Keperluan", "Purpose"],
  ["Approval dan rejection", "Approval and rejection"],
  ["Inventaris fasilitas", "Facility inventory"],
  ["Jadwal akademik ruang", "Room academic schedule"],
  ["Informasi ruangan", "Room information"],
  ["Tambah jadwal akademik", "Add academic schedule"],
  ["Pilih ruangan", "Select a room"],
  ["Tanggal tertentu", "Specific date"],
  ["Berulang mingguan", "Repeats weekly"],
  ["Tambah periode pemeliharaan / tidak tersedia", "Add maintenance / unavailable period"],
  ["Kegiatan", "Activity"],
  ["Waktu", "Time"],
  ["Sumber", "Source"],
  ["Batalkan", "Cancel"],
  ["Alasan", "Reason"],
  ["Ringkasan operasional", "Operations overview"],
  ["Pantau permohonan, penggunaan ruang, dan pekerjaan administrasi dari satu tempat.", "Monitor requests, room usage, and administrative work in one place."],
  ["Memuat ringkasan administrasi…", "Loading administration summary…"],
  ["Distribusi status", "Status distribution"],
  ["Belum ada data reservasi", "No reservation data yet"],
  ["Distribusi status akan muncul setelah data reservasi tersedia.", "The status distribution will appear when reservation data is available."],
  ["Ruang dengan reservasi terbanyak", "Rooms with the most reservations"],
  ["Belum ada penggunaan tercatat", "No usage has been recorded"],
  ["Peringkat ini menghitung reservasi yang disetujui atau selesai dari data backend.", "This ranking counts approved or completed reservations from backend data."],
  ["Perlu ditinjau", "Needs review"],
  ["Memuat antrian permohonan…", "Loading request queue…"],
  ["Tidak ada permohonan menunggu", "No pending requests"],
  ["Antrian ini hanya menampilkan permohonan berstatus pending.", "This queue only shows pending requests."],
  ["Pemantauan reservasi & keterlambatan", "Reservation & overdue monitoring"],
  ["Tidak ada reservasi untuk dipantau", "No reservations to monitor"],
  ["Reservasi hari ini dan sesi terdahulu yang belum dikonfirmasi selesai akan muncul di sini.", "Today's reservations and earlier sessions not yet confirmed as completed will appear here."],
  ["Permohonan terbaru", "Latest requests"],
  ["Belum ada permohonan", "No requests yet"],
  ["Permohonan mahasiswa akan muncul setelah dikirim melalui aplikasi.", "Student requests will appear here after they are submitted through the app."],
  ["Akses cepat", "Quick access"],
  ["Konfirmasi ruangan sudah kosong?", "Confirm the room is vacant?"],
  ["Ya, ruangan sudah kosong", "Yes, the room is vacant"],
  ["Cari nama, ruang, atau ID", "Search name, room, or ID"],
  ["Dari tanggal", "From date"],
  ["Sampai tanggal", "To date"],
  ["Memuat permohonan…", "Loading requests…"],
  ["(tidak tersedia)", "(unavailable)"],
  ["Batalkan reservasi", "Cancel reservation"],
  ["Cek ketersediaan", "Check availability"],
  ["Tanya RUKKA AI", "Ask RUKKA AI"],
  ["Jelajahi ruang", "Explore rooms"],
  ["Temukan ruang sesuai kebutuhan", "Find a room that meets your needs"],
  ["Periksa tanggal dan waktu", "Check date and time"],
  ["Reservasi saya", "My reservations"],
  ["Pantau status pengajuan", "Track request status"],
  ["Ngobrol dengan RUKKA", "Chat with RUKKA"],
  ["Cari ruang lewat percakapan", "Find rooms through conversation"],
  ["SESI ANDA", "YOUR SESSION"],
  ["Terapkan filter", "Apply filters"],
  ["Filter aktif", "Active filters"],
  ["Hapus semua filter", "Clear all filters"],
  ["Informasi lokasi dan fasilitas dari inventaris kampus", "Location and facility information from the campus inventory"],
  ["Lihat detail", "View details"],
  ["Edit", "Edit"],
  ["Tidak ada fasilitas yang dicatat.", "No facilities have been recorded."],
  ["Ketersediaan waktu akan diperiksa kembali sebelum permohonan dikirim.", "Availability will be checked again before the request is submitted."],
  ["Pilih ruangan", "Select a room"],
  ["2. Detail permohonan", "2. Request details"],
  ["3. Tinjauan admin", "3. Staff review"],
  ["Detail kegiatan", "Activity details"],
  ["Waktu belum tersedia.", "The time slot is not available."],
  ["Cari waktu atau ruang alternatif", "Find an alternative time or room"],
  ["Tinjau dan kirim permohonan", "Review and submit request"],
  ["Ringkasan pilihan", "Selection summary"],
  ["Peserta", "Participants"],
  ["Permohonan berhasil dikirim. Status awalnya menunggu peninjauan TU/Admin.", "Your request has been submitted. Its initial status is awaiting Secretariat Staff review."],
  ["Alasan penolakan:", "Rejection reason:"],
  ["RUANGAN", "ROOM"],
  ["Tujuan kegiatan", "Activity purpose"],
  ["Catatan", "Notes"],
  ["ID reservasi", "Reservation ID"],
  ["Diajukan", "Submitted"],
  ["Status permohonan", "Request status"],
  ["Tandai dibaca", "Mark as read"],
  ["Dibaca", "Read"],
  ["Lihat reservasi", "View reservation"],
  ["Informasi profil", "Profile information"],
  ["Tampilan", "Appearance"],
  ["Pilih mode terang atau gelap.", "Choose light or dark mode."],
  ["☀ Terang", "☀ Light"],
  ["◐ Gelap", "◐ Dark"],
  ["Ubah password", "Change password"],
  ["Bantuan & FAQ", "Help & FAQ"],
  ["Informasi alur reservasi dan aturan layanan", "Reservation workflow and service rules"],
  ["Asisten AI belum tersedia pada MVP", "AI assistant is not available in this MVP"],
  ["404 · RUANGKAMPUS", "404 · RUANGKAMPUS"],
  ["Halaman tidak ditemukan", "Page not found"],
  ["Alamat yang Anda buka tidak tersedia.", "The address you opened is unavailable."],
  ["Kembali ke halaman utama", "Return to the home page"],
  ["Batalkan reservasi?", "Cancel this reservation?"],
  ["Alasan pembatalan (opsional)", "Cancellation reason (optional)"],
  ["Sedikit ruang untuk mewujudkan ide besar Anda.", "A little room to bring your big ideas to life."],
  ["Memuat ringkasan reservasi…", "Loading reservation summary…"],
  ["Ringkasan reservasi Anda", "Your reservation summary"],
  ["Mulai dari sini", "Get started here"],
  ["Sesi kampus berikutnya", "Your next campus session"],
  ["Belum ada sesi yang disetujui", "No approved sessions yet"],
  ["Reservasi mendatang akan muncul di sini setelah disetujui oleh TU/Admin.", "Upcoming reservations will appear here after they are approved by Secretariat Staff."],
  ["Aktivitas reservasi terbaru", "Latest reservation activity"],
  ["Mulai dengan memilih ruangan yang sesuai untuk kegiatan Anda.", "Start by choosing a room that suits your activity."],
  ["Direktori ruangan", "Room directory"],
  ["Temukan ruang berdasarkan fakultas, gedung, lokasi, kapasitas, dan fasilitas yang dibutuhkan.", "Find rooms by faculty, building, location, capacity, and required facilities."],
  ["Nama, kode, atau deskripsi ruangan", "Room name, code, or description"],
  ["Semua kapasitas", "All capacities"],
  ["Contoh: sayap timur", "Example: east wing"],
  ["Kapasitas minimum", "Minimum capacity"],
  ["Contoh: proyektor, Wi-Fi", "Example: projector, Wi-Fi"],
  ["Memuat direktori ruangan…", "Loading room directory…"],
  ["Coba ubah kata kunci, fakultas, gedung, kapasitas, atau fasilitas pencarian.", "Try changing the keyword, faculty, building, capacity, or facility filters."],
  ["Ajukan reservasi ruangan", "Request a room reservation"],
  ["Isi kebutuhan kegiatan Anda. Permohonan akan ditinjau oleh TU/Admin.", "Enter your activity requirements. Your request will be reviewed by Secretariat Staff."],
  ["Jam mulai", "Start time"],
  ["Jam selesai", "End time"],
  ["Contoh: Diskusi proyek kelompok", "Example: Group project discussion"],
  ["Catatan tambahan (opsional)", "Additional notes (optional)"],
  ["Tersedia saat dicek", "Available when checked"],
  ["Pilih slot ini", "Select this slot"],
  ["Hasil deteksi konflik", "Conflict detection results"],
  ["Cari slot alternatif", "Find alternative slots"],
  ["Tidak ada data ruangan yang cocok dengan filter. Coba kurangi fasilitas atau ubah lokasi.", "No room data matches these filters. Try removing a facility requirement or changing the location."],
  ["Waktu dan kebutuhan kegiatan", "Activity time and requirements"],
  ["Preferensi ruangan", "Room preferences"],
  ["Tersedia", "Available"],
  ["Sebelumnya", "Previous"],
  ["Berikutnya", "Next"],
  ["Tidak ada slot alternatif", "No alternative slots"],
  ["Ngobrol aja seperti biasa", "Just chat naturally"],
  ["Asisten kampusmu", "Your campus assistant"],
  ["Makasih, feedback lu bantu RUKKA makin paham.", "Thanks, your feedback helps RUKKA improve."],
  ["Apa yang perlu diperbaiki?", "What could be improved?"],
  ["RUKKA sedang memproses pertanyaan", "RUKKA is processing your question"],
  ["Contoh pertanyaan", "Example questions"],
  ["Tulis pertanyaan", "Ask a question"],
  ["Cek ketersediaan ruangan", "Check room availability"],
  ["Tanggal kegiatan", "Activity date"],
  ["Fasilitas wajib", "Required facilities"],
  ["Memeriksa jadwal dan ketersediaan ruangan...", "Checking room schedules and availability..."],
  ["Belum ada ruangan yang tersedia", "No rooms are currently available"],
  ["Rekomendasi jadwal alternatif", "Alternative schedule suggestions"],
  ["Mulai pencarian dari tanggal", "Start searching from"],
  ["Durasi kegiatan (menit)", "Activity duration (minutes)"],
  ["Waktu yang diutamakan", "Preferred time"],
  ["Opsional", "Optional"],
  ["Mencari slot yang cocok di jadwal ruangan...", "Searching for a matching slot in room schedules..."],
  ["Percakapan dengan RUKKA AI", "Conversation with RUKKA AI"],
  ["Jawaban membantu", "Helpful answer"],
  ["Membantu", "Helpful"],
  ["Jawaban kurang membantu", "Not helpful"],
  ["Kurang membantu", "Not helpful"],
  ["Kirim pertanyaan", "Send question"],
  ["Make room for great ideas.", "Make room for great ideas."],
  ["Temukan ruang kampus yang sesuai dan ajukan reservasi dalam satu tempat.", "Find the right campus room and request a reservation in one place."],
  ["Pilih jenis akun", "Choose account type"],
  ["ACCOUNT SUPPORT", "ACCOUNT SUPPORT"],
  ["← Kembali ke halaman masuk", "← Back to sign in"],
  ["Backend belum dikonfigurasi. Pendaftaran akan aktif setelah layanan API tersedia.", "The backend is not configured. Registration will be available when the API service is online."],
  ["Email kampus", "Campus email"],
  ["Password baru", "New password"],
  ["Nama sesuai identitas kampus", "Name as shown in your campus record"],
  ["Masukkan NIM aktif Anda", "Enter your active student ID"],
  ["Minimal 8 karakter", "At least 8 characters"],
  ["Ulangi password", "Re-enter password"],
  ["Senin", "Monday"],
  ["Selasa", "Tuesday"],
  ["Rabu", "Wednesday"],
  ["Kamis", "Thursday"],
  ["Jumat", "Friday"],
  ["Sabtu", "Saturday"],
  ["Minggu", "Sunday"],
  ["Mahasiswa", "Student"],
  ["Administrator", "Administrator"],
  ["Lihat detail", "View details"],
  ["Ketik DELETE to confirm", "Type DELETE to confirm"],
  ["Notifikasi belum dibaca", "Unread notifications"],
  ["Belum ada notifikasi", "No notifications yet"],
  ["Tandai semua dibaca", "Mark all as read"],
  ["Semua notifikasi", "All notifications"],
  ["Belum dibaca", "Unread"],
  ["Kirim ulang email", "Retry email"],
  ["Tidak ada notifikasi yang cocok", "No matching notifications"],
  ["Simpan perubahan", "Save changes"],
  ["Perubahan berhasil disimpan.", "Changes saved successfully."],
  ["Password saat ini", "Current password"],
  ["Password baru", "New password"],
  ["Konfirmasi password baru", "Confirm new password"],
  ["Minimal 8 karakter", "At least 8 characters"],
  ["Hari ini", "Today"],
  ["Besok", "Tomorrow"],
  ["Pagi", "Morning"],
  ["Siang", "Afternoon"],
  ["Sore", "Evening"],
  ["Malam", "Night"],
);

const idToEn = new Map<string, string>();
const enToId = new Map<string, string>();
for (const [id, en] of pairs) {
  if (id !== en) {
    idToEn.set(id.toLocaleLowerCase("id-ID"), en);
    enToId.set(en.toLocaleLowerCase("en"), id);
  }
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function translateAppText(value: string, language: AppLanguage): string {
  const source = value.trim();
  if (!source) return value;
  const table = language === "en" ? idToEn : enToId;
  const exact = table.get(source.toLocaleLowerCase(language === "en" ? "id-ID" : "en"));
  if (exact) return value.replace(source, exact);

  let translated = value;
  const replacements = Array.from(table.entries()).filter(([key]) => key.length >= 13).sort((a, b) => b[0].length - a[0].length);
  for (const [from, to] of replacements) {
    const expression = new RegExp(escapeRegExp(from), "gi");
    translated = translated.replace(expression, to);
  }
  return translated;
}

interface LanguageContextValue {
  language: AppLanguage;
  setLanguage: (language: AppLanguage) => void;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<AppLanguage>(() => {
    try {
      return window.localStorage.getItem("rk-language") === "en" ? "en" : "id";
    } catch {
      return "id";
    }
  });

  useEffect(() => {
    document.documentElement.lang = language;
    try {
      window.localStorage.setItem("rk-language", language);
    } catch {
      // Language remains active for this session when browser storage is unavailable.
    }

    const apply = (node: Node) => {
      if (node.nodeType === Node.TEXT_NODE) {
        const parent = node.parentElement;
        if (parent?.closest("script,style,textarea,[data-no-translate]")) return;
        const current = node.nodeValue || "";
        const translated = translateAppText(current, language);
        if (translated !== current) node.nodeValue = translated;
        return;
      }
      if (node.nodeType !== Node.ELEMENT_NODE && node !== document.body) return;
      const element = node instanceof Element ? node : null;
      if (element) {
        for (const attribute of ["placeholder", "title", "aria-label", "alt"]) {
          const current = element.getAttribute(attribute);
          if (!current) continue;
          const translated = translateAppText(current, language);
          if (translated !== current) element.setAttribute(attribute, translated);
        }
      }
      for (const child of Array.from(node.childNodes)) apply(child);
    };

    apply(document.body);
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === "characterData" && mutation.target instanceof Text) {
          apply(mutation.target);
        } else if (mutation.type === "attributes" && mutation.target instanceof Element) {
          apply(mutation.target);
        } else {
          mutation.addedNodes.forEach(apply);
        }
      }
    });
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true,
      attributeFilter: ["placeholder", "title", "aria-label", "alt"],
    });
    return () => observer.disconnect();
  }, [language]);

  const value = useMemo<LanguageContextValue>(() => ({
    language,
    setLanguage: setLanguageState,
  }), [language]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage(): LanguageContextValue {
  const context = useContext(LanguageContext);
  if (!context) throw new Error("useLanguage must be used inside LanguageProvider");
  return context;
}

export function LanguageSwitch({ className = "" }: { className?: string }) {
  const { language, setLanguage } = useLanguage();
  return (
    <div className={["language-switch", className].filter(Boolean).join(" ")} role="group" aria-label="Bahasa / Language">
      <button type="button" className={language === "id" ? "is-active" : ""} aria-pressed={language === "id"} title="Bahasa Indonesia" onClick={() => setLanguage("id")}>
        <span aria-hidden="true">🇮🇩</span><span>ID</span>
      </button>
      <button type="button" className={language === "en" ? "is-active" : ""} aria-pressed={language === "en"} title="English" onClick={() => setLanguage("en")}>
        <span aria-hidden="true">🇬🇧</span><span>EN</span>
      </button>
    </div>
  );
}
