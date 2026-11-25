import { ArrowRight, Bell, CalendarClock, ClipboardList, Search, Sparkles } from "lucide-react";
import { Link } from "react-router";
import { EmptyState } from "../components/ui/EmptyState";
import { PageHeader } from "../components/ui/PageHeader";
import { StatCard } from "../components/ui/StatCard";

export function StudentDashboardPage() {
  return (
    <div className="dashboard-page">
      <PageHeader
        eyebrow="STUDENT DASHBOARD"
        title="Selamat datang di RuangKampus"
        description="Temukan ruang yang sesuai dan pantau permohonan reservasi Anda dari satu tempat."
      />

      <section className="quick-action-card" aria-labelledby="quick-action-title">
        <div className="quick-action-card__icon"><Search size={21} aria-hidden="true" /></div>
        <div className="quick-action-card__copy">
          <p className="eyebrow">MULAI DARI SINI</p>
          <h2 id="quick-action-title">Sedang mencari ruang kampus?</h2>
          <p>Jelajahi ruang berdasarkan kebutuhan kegiatan Anda.</p>
        </div>
        <Link className="button button--primary" to="/student/rooms">
          Cari ruangan <ArrowRight size={17} aria-hidden="true" />
        </Link>
      </section>

      <section className="dashboard-section" aria-labelledby="reservation-summary-title">
        <div className="dashboard-section__heading">
          <div>
            <p className="eyebrow">RINGKASAN</p>
            <h2 id="reservation-summary-title">Reservasi saya</h2>
          </div>
          <Link className="section-link" to="/student/reservations">
            Lihat semua <ArrowRight size={16} aria-hidden="true" />
          </Link>
        </div>
        <div className="stat-grid stat-grid--three">
          <StatCard label="Menunggu" description="Permohonan yang menunggu keputusan." icon={CalendarClock} />
          <StatCard label="Disetujui" description="Reservasi yang telah dikonfirmasi." icon={ClipboardList} />
          <StatCard label="Notifikasi" description="Pembaruan untuk akun Anda." icon={Bell} />
        </div>
      </section>

      <div className="dashboard-two-column">
        <section className="dashboard-panel" aria-labelledby="upcoming-title">
          <div className="dashboard-section__heading">
            <div>
              <p className="eyebrow">JADWAL</p>
              <h2 id="upcoming-title">Reservasi mendatang</h2>
            </div>
          </div>
          <EmptyState
            icon={<CalendarClock size={22} />}
            title="Belum ada jadwal untuk ditampilkan"
            description="Informasi reservasi akan muncul setelah data akun tersedia dari layanan RuangKampus."
          />
        </section>

        <section className="dashboard-panel" aria-labelledby="activity-title">
          <div className="dashboard-section__heading">
            <div>
              <p className="eyebrow">PEMBARUAN</p>
              <h2 id="activity-title">Aktivitas terbaru</h2>
            </div>
          </div>
          <EmptyState
            icon={<Bell size={22} />}
            title="Belum ada aktivitas"
            description="Riwayat aktivitas dan notifikasi akan ditampilkan setelah API terkait tersedia."
            action={<Link className="section-link" to="/student/notifications">Buka notifikasi</Link>}
          />
        </section>
      </div>

      <section className="assistant-teaser" aria-label="RuangKampus assistant">
        <div className="assistant-teaser__icon"><Sparkles size={19} aria-hidden="true" /></div>
        <div>
          <strong>Smart Room Recommendation</strong>
          <p>Antarmuka rekomendasi akan tersedia setelah layanan AI dan data ruangan terverifikasi.</p>
        </div>
        <span className="assistant-teaser__status">Segera tersedia</span>
      </section>
    </div>
  );
}
