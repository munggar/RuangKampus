import { ArrowRight, Bell, Building2, CalendarClock, ClipboardList, Clock3 } from "lucide-react";
import { Link } from "react-router";
import { EmptyState } from "../components/ui/EmptyState";
import { PageHeader } from "../components/ui/PageHeader";
import { StatCard } from "../components/ui/StatCard";

export function AdminDashboardPage() {
  return (
    <div className="dashboard-page">
      <PageHeader
        eyebrow="TU / ADMIN DASHBOARD"
        title="Ringkasan pengelolaan ruang"
        description="Pantau permohonan, informasi ruangan, dan aktivitas layanan reservasi."
      />

      <section className="dashboard-section" aria-labelledby="admin-summary-title">
        <div className="dashboard-section__heading">
          <div>
            <p className="eyebrow">OVERVIEW</p>
            <h2 id="admin-summary-title">Ringkasan permohonan</h2>
          </div>
          <Link className="section-link" to="/admin/reservations">
            Kelola permohonan <ArrowRight size={16} aria-hidden="true" />
          </Link>
        </div>
        <div className="stat-grid">
          <StatCard label="Menunggu keputusan" description="Permohonan yang perlu ditinjau." icon={Clock3} />
          <StatCard label="Disetujui" description="Permohonan yang telah disetujui." icon={ClipboardList} />
          <StatCard label="Ditolak" description="Permohonan yang ditolak." icon={Bell} />
          <StatCard label="Ruangan" description="Inventaris ruang yang terdaftar." icon={Building2} />
        </div>
      </section>

      <div className="dashboard-two-column">
        <section className="dashboard-panel" aria-labelledby="pending-title">
          <div className="dashboard-section__heading">
            <div>
              <p className="eyebrow">PERLU DITINJAU</p>
              <h2 id="pending-title">Permohonan terbaru</h2>
            </div>
            <Link className="section-link" to="/admin/reservations">Lihat semua</Link>
          </div>
          <EmptyState
            icon={<ClipboardList size={22} />}
            title="Data permohonan belum tersedia"
            description="Daftar permohonan akan muncul setelah endpoint administrasi diimplementasikan dan diverifikasi."
          />
        </section>

        <section className="dashboard-panel" aria-labelledby="room-usage-title">
          <div className="dashboard-section__heading">
            <div>
              <p className="eyebrow">JADWAL RUANG</p>
              <h2 id="room-usage-title">Penggunaan mendatang</h2>
            </div>
            <Link className="section-link" to="/admin/schedule">Buka jadwal</Link>
          </div>
          <EmptyState
            icon={<CalendarClock size={22} />}
            title="Belum ada jadwal untuk ditampilkan"
            description="Data penggunaan ruangan harus bersumber dari jadwal dan reservasi yang diverifikasi backend."
          />
        </section>
      </div>

      <section className="dashboard-panel dashboard-panel--activity" aria-labelledby="admin-activity-title">
        <div className="dashboard-section__heading">
          <div>
            <p className="eyebrow">RIWAYAT</p>
            <h2 id="admin-activity-title">Aktivitas administrasi</h2>
          </div>
        </div>
        <EmptyState
          icon={<Bell size={22} />}
          title="Belum ada aktivitas untuk ditampilkan"
          description="Riwayat tindakan administrator belum tersedia pada API contract yang aktif."
        />
      </section>
    </div>
  );
}
