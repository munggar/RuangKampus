import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import {
  IconArrowRight as ArrowRight, IconBuilding as Building2, IconCalendarClock as CalendarClock,
  IconCalendar as CalendarDays, IconCircleCheck as CheckCircle2, IconClock as Clock3,
  IconClipboardList as ClipboardList, IconEdit as Edit3, IconFileSpreadsheet as FileSpreadsheet,
  IconPlus as Plus, IconSearch as Search, IconTrash as Trash2, IconUsers as Users, IconAlertTriangle as AlertTriangle,
} from "@tabler/icons-react";
import { Link, useNavigate, useParams } from "react-router";
import {
  adminApi, apiAssetUrl, dashboardApi, formatDate, formatTime, localToday, reservationApi, roomApi,
  scheduleApi, statusLabel,
} from "./api";
import type { DashboardSummary, Reservation, Room, RoomStatus, RoomUnavailability, Schedule } from "./types";
import { PageTitle } from "./layout";
import { Button, cleanLocationLabel, ConfirmModal, EmptyState, Field, Loading, Modal, Notice, PageSection, StatusBadge } from "./ui";
import { useLanguage } from "./i18n";

function campusTimestamp(date: string, time: string): number {
  return new Date(date + "T" + time.slice(0, 8) + "+07:00").getTime();
}
function formatCampusClock(timestamp: number): string {
  return new Intl.DateTimeFormat(typeof document !== "undefined" && document.documentElement.lang === "en" ? "en-US" : "id-ID", {
    timeZone: "Asia/Jakarta",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
  }).format(timestamp);
}
function formatCampusDate(timestamp: number): string {
  return new Intl.DateTimeFormat(typeof document !== "undefined" && document.documentElement.lang === "en" ? "en-US" : "id-ID", {
    timeZone: "Asia/Jakarta",
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(timestamp);
}
function timerText(milliseconds: number): string {
  const seconds = Math.max(0, Math.floor(milliseconds / 1000));
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remaining = seconds % 60;
  return [hours, minutes, remaining].map((value) => String(value).padStart(2, "0")).join(":");
}
function reservationTiming(item: Reservation, now: number) {
  const startsAt = campusTimestamp(item.reservation_date, item.start_time);
  const endsAt = campusTimestamp(item.reservation_date, item.end_time);
  if (now < startsAt) {
    return { kind: "upcoming" as const, title: "Akan dimulai", caption: "Mulai dalam", value: timerText(startsAt - now), urgent: false };
  }
  if (now < endsAt) {
    const remaining = endsAt - now;
    const urgent = remaining <= 5 * 60 * 1000;
    return {
      kind: "active" as const,
      title: urgent ? "Segera berakhir" : "Sedang berlangsung",
      caption: "Sisa waktu",
      value: timerText(remaining),
      urgent,
    };
  }
  return { kind: "overdue" as const, title: "Melewati jadwal", caption: "Terlambat", value: timerText(now - endsAt), urgent: true };
}

export function AdminDashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [recent, setRecent] = useState<Reservation[]>([]);
  const [stats, setStats] = useState<Array<{ room_id: string; room_name: string; building: string; reservation_count: number }>>([]);
  const [loading, setLoading] = useState(true);
  const [summaryError, setSummaryError] = useState("");
  const [recentError, setRecentError] = useState("");
  const [statsError, setStatsError] = useState("");
  const [pending, setPending] = useState<Reservation[]>([]);
  const [pendingLoading, setPendingLoading] = useState(true);
  const [pendingError, setPendingError] = useState("");
  const [todayReservations, setTodayReservations] = useState<Reservation[]>([]);
  const [monitorNow, setMonitorNow] = useState(() => Date.now());
  const [monitorError, setMonitorError] = useState("");
  const [finishTarget, setFinishTarget] = useState<Reservation | null>(null);
  const [finishing, setFinishing] = useState(false);
  const [reviewTarget, setReviewTarget] = useState<Reservation | null>(null);
  const [reviewAction, setReviewAction] = useState<"approve" | "reject" | null>(null);
  const [reviewReason, setReviewReason] = useState("");
  const [reviewBusy, setReviewBusy] = useState(false);
  const [reviewError, setReviewError] = useState("");

  useEffect(() => {
    let active = true;
    Promise.allSettled([dashboardApi.summary(), dashboardApi.recent(6), adminApi.roomStatistics()])
      .then(([overview, latest, usage]) => {
        if (!active) return;
        if (overview.status === "fulfilled") { setSummary(overview.value); setSummaryError(""); }
        else setSummaryError(overview.reason instanceof Error ? overview.reason.message : "Ringkasan dashboard belum dapat dimuat.");
        if (latest.status === "fulfilled") { setRecent(latest.value.items); setRecentError(""); }
        else setRecentError(latest.reason instanceof Error ? latest.reason.message : "Permohonan terbaru belum dapat dimuat.");
        if (usage.status === "fulfilled") { setStats(usage.value); setStatsError(""); }
        else setStatsError(usage.reason instanceof Error ? usage.reason.message : "Statistik penggunaan ruang belum dapat dimuat.");
      })
      .finally(() => { if (active) setLoading(false); });
    const pendingParams = new URLSearchParams({ page: "1", limit: "5", status: "PENDING" });
    reservationApi.list(pendingParams)
      .then((result) => { if (active) setPending(result.items); })
      .catch((cause) => { if (active) setPendingError(cause instanceof Error ? cause.message : "Antrian permohonan belum dapat dimuat."); })
      .finally(() => { if (active) setPendingLoading(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;
    const refreshToday = () => {
      const today = localToday();
      const params = new URLSearchParams({ page: "1", limit: "100", status: "APPROVED", dateFrom: today, dateTo: today });
      reservationApi.list(params)
        .then((result) => {
          if (active) setTodayReservations(result.items.sort((a, b) => a.reservation_date.localeCompare(b.reservation_date) || a.start_time.localeCompare(b.start_time)));
        })
        .catch((cause) => {
          if (active) setMonitorError(cause instanceof Error ? cause.message : "Pemantauan reservasi belum dapat diperbarui.");
        });
    };
    refreshToday();
    const clockTimer = window.setInterval(() => setMonitorNow(Date.now()), 1000);
    const refreshTimer = window.setInterval(refreshToday, 30_000);
    window.addEventListener("focus", refreshToday);
    return () => {
      active = false;
      window.clearInterval(clockTimer);
      window.clearInterval(refreshTimer);
      window.removeEventListener("focus", refreshToday);
    };
  }, []);

  async function confirmRoomVacant() {
    if (!finishTarget) return;
    setFinishing(true);
    setMonitorError("");
    try {
      await reservationApi.complete(finishTarget.id);
      setTodayReservations((current) => current.filter((item) => item.id !== finishTarget.id));
      setFinishTarget(null);
    } catch (cause) {
      setMonitorError(cause instanceof Error ? cause.message : "Status reservasi belum dapat diselesaikan.");
    } finally {
      setFinishing(false);
    }
  }

  function openReview(item: Reservation, nextAction: "approve" | "reject") {
    setReviewTarget(item);
    setReviewAction(nextAction);
    setReviewReason("");
    setReviewError("");
  }

  async function submitReview() {
    if (!reviewTarget || !reviewAction || reviewBusy) return;
    if (reviewAction === "reject" && reviewReason.trim().length < 3) {
      setReviewError("Alasan penolakan minimal 3 karakter.");
      return;
    }
    setReviewBusy(true);
    setReviewError("");
    try {
      if (reviewAction === "approve") await reservationApi.approve(reviewTarget.id);
      else await reservationApi.reject(reviewTarget.id, reviewReason.trim());
      setPending((current) => current.filter((item) => item.id !== reviewTarget.id));
      setReviewTarget(null);
      setReviewAction(null);
      setReviewReason("");
      const [overview, latest, usage] = await Promise.allSettled([
        dashboardApi.summary(), dashboardApi.recent(6), adminApi.roomStatistics(),
      ]);
      if (overview.status === "fulfilled") { setSummary(overview.value); setSummaryError(""); }
      else setSummaryError(overview.reason instanceof Error ? overview.reason.message : "Ringkasan dashboard belum dapat dimuat.");
      if (latest.status === "fulfilled") { setRecent(latest.value.items); setRecentError(""); }
      else setRecentError(latest.reason instanceof Error ? latest.reason.message : "Permohonan terbaru belum dapat dimuat.");
      if (usage.status === "fulfilled") { setStats(usage.value); setStatsError(""); }
      else setStatsError(usage.reason instanceof Error ? usage.reason.message : "Statistik penggunaan ruang belum dapat dimuat.");
    } catch (cause) {
      setReviewError(cause instanceof Error ? cause.message : "Keputusan belum berhasil disimpan.");
      if (reviewAction === "approve") { setReviewTarget(null); setReviewAction(null); }
    } finally {
      setReviewBusy(false);
    }
  }

  const statusRows = [
    { key: "pending", label: "Menunggu", tone: "pending" },
    { key: "approved", label: "Disetujui", tone: "approved" },
    { key: "rejected", label: "Ditolak", tone: "rejected" },
    { key: "cancelled", label: "Dibatalkan", tone: "cancelled" },
    { key: "completed", label: "Selesai", tone: "completed" },
  ] as const;
  const statusTotal = statusRows.reduce((sum, item) => sum + (summary?.[item.key] || 0), 0);
  const topRoomCount = Math.max(0, ...stats.map((item) => item.reservation_count));

  return <div className="page-stack">
    <PageTitle eyebrow="PUSAT OPERASI KAMPUS" title="Ringkasan operasional" description="Pantau permohonan, penggunaan ruang, dan pekerjaan administrasi dari satu tempat." action={<Link className="button button--primary" to="/admin/reservations?status=PENDING"><ClipboardList size={17} />Tinjau permohonan</Link>} />
    {loading ? <Loading label="Memuat ringkasan administrasi…" /> : <>
      {summaryError ? <Notice tone="error">{summaryError} Ringkasan status dan inventaris tidak ditampilkan sampai data berhasil dimuat.</Notice> : <div className="admin-stat-grid">
        <Link className="admin-stat-card admin-stat-card--action" to="/admin/reservations?status=PENDING">
          <span className="admin-stat-card__icon admin-stat-card__icon--pending"><Clock3 size={18} /></span>
          <span className="admin-stat-card__label">Menunggu peninjauan</span>
          <strong>{summary?.pending ?? 0}</strong>
          <small>Permohonan berstatus pending</small><ArrowRight className="admin-stat-card__arrow" size={16} />
        </Link>
        <article className="admin-stat-card">
          <span className="admin-stat-card__icon admin-stat-card__icon--approved"><CheckCircle2 size={18} /></span>
          <span className="admin-stat-card__label">Reservasi disetujui</span>
          <strong>{summary?.approved ?? 0}</strong>
          <small>Total sepanjang waktu</small>
        </article>
        <Link className="admin-stat-card admin-stat-card--action" to="/admin/rooms">
          <span className="admin-stat-card__icon admin-stat-card__icon--rooms"><Building2 size={18} /></span>
          <span className="admin-stat-card__label">Inventaris ruangan</span>
          <strong>{summary?.total_rooms ?? 0}</strong>
          <small>{summary?.active_rooms ?? 0} aktif · sisanya nonaktif/pemeliharaan</small><ArrowRight className="admin-stat-card__arrow" size={16} />
        </Link>
        <article className="admin-stat-card">
          <span className="admin-stat-card__icon admin-stat-card__icon--total"><CalendarDays size={18} /></span>
          <span className="admin-stat-card__label">Total reservasi</span>
          <strong>{summary?.total_reservations ?? 0}</strong>
          <small>Gabungan seluruh status</small>
        </article>
      </div>}
      <div className="admin-analytics-grid">
        <PageSection title="Distribusi status" action={<span className="admin-chart-caption">Total {statusTotal} reservasi</span>}>
          <div className="admin-chart-panel">
            {summaryError ? <Notice tone="error">Distribusi status tidak dapat ditampilkan karena ringkasan belum tersedia.</Notice> : statusTotal ? <div className="admin-status-chart">
              {statusRows.map((item) => {
                const value = summary?.[item.key] || 0;
                const percent = Math.round(value / statusTotal * 100);
                return <label className="admin-status-row" key={item.key}>
                  <span className={"admin-status-dot admin-status-dot--" + item.tone} aria-hidden="true" />
                  <span className="admin-status-row__label">{item.label}</span>
                  <progress className={"admin-progress admin-progress--" + item.tone} max={statusTotal} value={value} aria-label={item.label + ": " + value + " reservasi"} />
                  <strong>{value}</strong><small>{percent}%</small>
                </label>;
              })}
            </div> : <EmptyState title="Belum ada data reservasi" description="Distribusi status akan muncul setelah data reservasi tersedia." icon={<ClipboardList size={21} />} />}
          </div>
        </PageSection>
        <PageSection title="Ruang dengan reservasi terbanyak" action={<span className="admin-chart-caption">Disetujui & selesai · sepanjang waktu</span>}>
          <div className="admin-chart-panel">
            {statsError ? <Notice tone="error">{statsError}</Notice> : stats.length && topRoomCount > 0 ? <div className="admin-room-chart">
              {stats.slice(0, 5).map((item, index) => <div className="admin-room-chart__row" key={item.room_id}>
                <span className="admin-room-chart__rank">{String(index + 1).padStart(2, "0")}</span>
                <span className="admin-room-chart__name"><b>{item.room_name}</b><small>{item.building}</small></span>
                <progress className="admin-progress admin-progress--room" max={topRoomCount} value={item.reservation_count} aria-label={item.room_name + ": " + item.reservation_count + " reservasi disetujui atau selesai"} />
                <strong>{item.reservation_count}</strong>
              </div>)}
            </div> : <EmptyState title="Belum ada penggunaan tercatat" description="Peringkat ini menghitung reservasi yang disetujui atau selesai dari data backend." icon={<Building2 size={21} />} />}
          </div>
        </PageSection>
      </div>
      <PageSection title="Perlu ditinjau" action={<Link className="text-link" to="/admin/reservations?status=PENDING">Buka antrian <ArrowRight size={15} /></Link>}>
        {pendingError ? <Notice tone="error">{pendingError}</Notice> : null}
        {reviewError && reviewAction !== "reject" ? <Notice tone="error">{reviewError}</Notice> : null}
        {pendingLoading ? <Loading label="Memuat antrian permohonan…" /> : pending.length ? <div className="admin-pending-list">
          {pending.map((item) => <article className="admin-pending-row" key={item.id}>
            <div className="admin-pending-row__main">
              <div className="admin-pending-row__title"><b>{item.applicant?.name || "Mahasiswa"}</b><StatusBadge status={item.status} /></div>
              <p>{item.room?.room_name || "Ruangan"} · {item.room?.building || "Lokasi kampus"}</p>
              <small>{formatDate(item.reservation_date)} · {formatTime(item.start_time)}–{formatTime(item.end_time)} WIB · {item.participant_count} peserta</small>
              <span className="admin-pending-row__purpose">{item.purpose}</span>
            </div>
            <div className="admin-pending-row__actions">
              <Link className="button button--secondary" to={"/admin/reservations/" + item.id}>Detail</Link>
              <Button disabled={reviewBusy} onClick={() => openReview(item, "approve")}>Setujui</Button>
              <Button variant="danger" disabled={reviewBusy} onClick={() => openReview(item, "reject")}>Tolak</Button>
            </div>
          </article>)}
        </div> : <EmptyState title="Tidak ada permohonan menunggu" description="Antrian ini hanya menampilkan permohonan berstatus pending." action={<Link className="button button--secondary" to="/admin/reservations">Lihat seluruh permohonan</Link>} icon={<CheckCircle2 size={21} />} />}
      </PageSection>
      <PageSection title="Pemantauan reservasi & keterlambatan" action={<div className="reservation-monitor-toolbar">
          <div className="campus-clock" aria-label={`Waktu kampus ${formatCampusClock(monitorNow)} WIB`}>
            <Clock3 size={16} aria-hidden="true" />
            <span><small>WAKTU KAMPUS · WIB</small><strong>{formatCampusClock(monitorNow)}</strong><small>{formatCampusDate(monitorNow)}</small></span>
          </div>
          <span className="muted small">Data diperbarui otomatis · 30 detik</span>
        </div>}>
        {monitorError ? <Notice tone="warning">{monitorError}</Notice> : null}
        {todayReservations.length ? <div className="reservation-monitor-list">
          {todayReservations.map((item) => {
            const timing = reservationTiming(item, monitorNow);
            const endsAt = campusTimestamp(item.reservation_date, item.end_time);
            const nextSession = todayReservations
              .filter((candidate) => candidate.room_id === item.room_id && candidate.id !== item.id)
              .filter((candidate) => campusTimestamp(candidate.reservation_date, candidate.start_time) >= endsAt)
              .sort((a, b) => campusTimestamp(a.reservation_date, a.start_time) - campusTimestamp(b.reservation_date, b.start_time))[0];
            return <article className={"reservation-monitor-item reservation-monitor-item--" + timing.kind} key={item.id}>
              <div className="reservation-monitor-item__details">
                <div className="reservation-monitor-item__heading">
                  <b>{item.room?.room_name || "Ruangan"}</b>
                  <span className={"reservation-monitor-state reservation-monitor-state--" + timing.kind}>{timing.title}</span>
                </div>
                <p>{item.applicant?.name || "Mahasiswa"} · {item.room?.building || "Lokasi kampus"}</p>
                <small>{formatDate(item.reservation_date)} · {formatTime(item.start_time)}–{formatTime(item.end_time)} WIB · {item.participant_count} peserta</small>
                {timing.kind === "active" && timing.urgent ? <p className="reservation-monitor-warning">Sisa waktu kurang dari 5 menit. Ingatkan mahasiswa untuk bersiap meninggalkan ruangan tepat waktu.</p> : null}
                {timing.kind === "overdue" ? <p className="reservation-monitor-warning">Jadwal berakhir. Pastikan ruangan sudah dikosongkan. Reservasi tetap menahan ketersediaan ruang sampai Admin mengonfirmasi ruangan kosong.</p> : null}
                {timing.kind === "overdue" && nextSession ? <p className="reservation-monitor-warning">PERHATIAN: sudah ada reservasi berikutnya untuk ruangan ini pada {formatDate(nextSession.reservation_date)} pukul {formatTime(nextSession.start_time)} WIB. Koordinasikan kondisi ruangan sebelum sesi tersebut dimulai.</p> : null}
              </div>
              <div className="reservation-monitor-item__timer">
                <small>{timing.caption}</small>
                <strong>{timing.value}</strong>
                <Link className="text-link" to={"/admin/reservations/" + item.id}>Detail reservasi</Link>
              </div>
              {timing.kind === "overdue" ? <Button variant="secondary" onClick={() => setFinishTarget(item)}>Konfirmasi ruangan kosong</Button> : null}
            </article>;
          })}
        </div> : <EmptyState title="Tidak ada reservasi untuk dipantau" description="Reservasi hari ini dan sesi terdahulu yang belum dikonfirmasi selesai akan muncul di sini." icon={<Clock3 size={22} />} />}
      </PageSection>
      <PageSection title="Permohonan terbaru" action={<Link className="text-link" to="/admin/reservations">Lihat semua <ArrowRight size={15} /></Link>}>
        {recentError ? <Notice tone="error">{recentError}</Notice> : recent.length ? <div className="table-wrap"><table className="data-table">
          <thead><tr><th>Pemohon</th><th>Ruangan</th><th>Jadwal</th><th>Keperluan</th><th>Status</th><th /></tr></thead>
          <tbody>{recent.map((item) => <tr key={item.id}>
            <td><b>{item.applicant?.name || "Mahasiswa"}</b><small>{item.applicant?.email || ""}</small></td>
            <td>{item.room?.room_name || "Ruangan"}</td>
            <td>{formatDate(item.reservation_date)}<small>{formatTime(item.start_time)}–{formatTime(item.end_time)} WIB</small></td>
            <td className="admin-recent-purpose">{item.purpose}</td>
            <td><StatusBadge status={item.status} /></td>
            <td><Link className="icon-link" to={"/admin/reservations/" + item.id} aria-label="Lihat detail"><ArrowRight size={17} /></Link></td>
          </tr>)}</tbody>
        </table></div> : <EmptyState title="Belum ada permohonan" description="Permohonan mahasiswa akan muncul setelah dikirim melalui aplikasi." icon={<ClipboardList size={22} />} />}
      </PageSection>
      <div className="dashboard-two-column">
        <PageSection title="Akses cepat">
          <div className="quick-links">
            <Link to="/admin/reservations"><ClipboardList size={19} /><span>Tinjau permohonan<small>Approval dan rejection</small></span><ArrowRight size={16} /></Link>
            <Link to="/admin/rooms"><Building2 size={19} /><span>Kelola ruangan<small>Inventaris fasilitas</small></span><ArrowRight size={16} /></Link>
            <Link to="/admin/schedules"><CalendarClock size={19} /><span>Jadwal & pemeliharaan<small>Jadwal akademik ruang</small></span><ArrowRight size={16} /></Link>
          </div>
        </PageSection>
      </div>
    </>}
    <ConfirmModal
      open={!!finishTarget}
      title="Konfirmasi ruangan sudah kosong?"
      description="Lanjutkan hanya setelah petugas memastikan mahasiswa sudah meninggalkan ruangan. Tindakan ini menandai reservasi selesai; sistem tidak mengeluarkan pengguna secara otomatis."
      confirmText="Ya, ruangan sudah kosong"
      loading={finishing}
      onClose={() => { if (!finishing) setFinishTarget(null); }}
      onConfirm={() => void confirmRoomVacant()}
    />
    <ConfirmModal
      open={reviewAction === "approve" && !!reviewTarget}
      title="Setujui permohonan?"
      description={reviewTarget ? `Permohonan ${reviewTarget.applicant?.name || "mahasiswa"} untuk ${reviewTarget.room?.room_name || "ruangan"} akan dikirim ke backend untuk pemeriksaan ulang kapasitas, jam operasional, jadwal, dan benturan reservasi.` : ""}
      confirmText="Setujui permohonan"
      loading={reviewBusy}
      onClose={() => { if (!reviewBusy) { setReviewAction(null); setReviewTarget(null); setReviewError(""); } }}
      onConfirm={() => void submitReview()}
    />
    <Modal
      open={reviewAction === "reject" && !!reviewTarget}
      title="Tolak permohonan"
      description="Alasan penolakan wajib dicatat dan akan terlihat oleh pemohon."
      closeDisabled={reviewBusy}
      onClose={() => { if (!reviewBusy) { setReviewAction(null); setReviewTarget(null); setReviewReason(""); setReviewError(""); } }}
    >
      <Field label="Alasan penolakan"><textarea rows={4} minLength={3} maxLength={2000} value={reviewReason} onChange={(event) => setReviewReason(event.target.value)} placeholder="Jelaskan alasan penolakan dengan jelas…" /></Field>
      {reviewError ? <Notice tone="error">{reviewError}</Notice> : null}
      <div className="modal-actions"><Button variant="secondary" disabled={reviewBusy} onClick={() => { setReviewAction(null); setReviewTarget(null); setReviewReason(""); setReviewError(""); }}>Kembali</Button><Button variant="danger" disabled={reviewBusy || reviewReason.trim().length < 3} onClick={() => void submitReview()}>{reviewBusy ? "Memproses…" : "Kirim penolakan"}</Button></div>
    </Modal>
  </div>;
}

export function AdminRequestsPage() {
  const [status, setStatus] = useState("PENDING");
  const [search, setSearch] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [items, setItems] = useState<Reservation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<Reservation | null>(null);
  const [action, setAction] = useState<"approve" | "reject" | null>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const listRequestId = useRef(0);
  const reload = () => {
    const requestId = ++listRequestId.current;
    setLoading(true); setError("");
    const params = new URLSearchParams({ page: "1", limit: "100" });
    if (status) params.set("status", status);
    if (dateFrom) params.set("dateFrom", dateFrom);
    if (dateTo) params.set("dateTo", dateTo);
    reservationApi.list(params).then((result) => {
      if (requestId === listRequestId.current) setItems(result.items);
    })
      .catch((cause) => {
        if (requestId === listRequestId.current) setError(cause instanceof Error ? cause.message : "Permohonan belum dapat dimuat.");
      })
      .finally(() => { if (requestId === listRequestId.current) setLoading(false); });
  };
  useEffect(() => {
    reload();
    return () => { listRequestId.current += 1; };
  }, [status, dateFrom, dateTo]);
  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return items;
    return items.filter((item) => (item.applicant?.name || "").toLowerCase().includes(term)
      || (item.room?.room_name || "").toLowerCase().includes(term)
      || item.purpose.toLowerCase().includes(term)
      || item.id.toLowerCase().includes(term));
  }, [items, search]);

  async function runAction() {
    if (!selected || !action) return;
    if (action === "reject" && reason.trim().length < 3) { setError("Alasan penolakan minimal 3 karakter."); return; }
    setBusy(true); setError("");
    try {
      if (action === "approve") await reservationApi.approve(selected.id);
      else await reservationApi.reject(selected.id, reason.trim());
      setSelected(null); setAction(null); setReason(""); reload();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Keputusan belum berhasil disimpan.");
    } finally { setBusy(false); }
  }

  const tabs = [{ key: "PENDING", text: "Menunggu" }, { key: "APPROVED", text: "Disetujui" }, { key: "REJECTED", text: "Ditolak" }, { key: "", text: "Semua" }];
  return <div className="page-stack">
    <PageTitle eyebrow="RESERVATION REVIEW" title="Permohonan reservasi" description="Tinjau detail pengajuan sebelum menetapkan keputusan." />
    <div className="panel request-filter-panel">
      <div className="segmented-tabs">{tabs.map((tab) => <button key={tab.key || "all"} type="button" className={status === tab.key ? "is-active" : ""} onClick={() => setStatus(tab.key)}>{tab.text}</button>)}</div>
      <Field label="Cari nama, ruang, atau ID"><span className="input-with-icon"><Search size={17} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Cari nama mahasiswa atau ruangan" /></span></Field>
      <Field label="Dari tanggal"><input type="date" value={dateFrom} max={dateTo || undefined} onChange={(event) => setDateFrom(event.target.value)} /></Field>
      <Field label="Sampai tanggal"><input type="date" value={dateTo} min={dateFrom || undefined} onChange={(event) => setDateTo(event.target.value)} /></Field>
      {status !== "PENDING" || search || dateFrom || dateTo ? <div className="request-filter-reset"><Button variant="secondary" onClick={() => { setStatus("PENDING"); setSearch(""); setDateFrom(""); setDateTo(""); }}>Reset filter</Button></div> : null}
    </div>
    {error ? <Notice tone="error">{error}</Notice> : null}
    {loading ? <Loading label="Memuat permohonan…" /> : filtered.length ? <div className="request-list">
      {filtered.map((item) => <article className="request-card" key={item.id}>
        <div className="request-card__top"><div><b>{item.applicant?.name || "Mahasiswa"}</b><small>{item.applicant?.email || "Identitas pemohon"}</small></div><StatusBadge status={item.status} /></div>
        <small className="mono">RK-{item.id.slice(0, 8).toUpperCase()}</small>
        <h3>{item.room?.room_name || "Ruangan"}</h3>
        <p>{item.room?.building || "Lokasi kampus"} · {formatDate(item.reservation_date)} · {formatTime(item.start_time)}–{formatTime(item.end_time)} WIB</p>
        <p className="request-card__purpose">{item.purpose} · {item.participant_count} peserta</p>
        <div className="request-card__actions">
          <Link className="button button--secondary" to={"/admin/reservations/" + item.id}>Detail</Link>
          {item.status === "PENDING" ? <>
            <Button onClick={() => { setSelected(item); setAction("approve"); }}>Setujui</Button>
            <Button variant="danger" onClick={() => { setSelected(item); setAction("reject"); }}>Tolak</Button>
          </> : null}
        </div>
      </article>)}
    </div> : <EmptyState title="Tidak ada permohonan yang cocok" description="Ubah filter atau kata kunci pencarian." icon={<ClipboardList size={22} />} />}
    <ConfirmModal open={action === "approve" && !!selected} title="Setujui permohonan?" description="Backend akan memeriksa kembali kapasitas, jam operasional, jadwal, dan benturan reservasi sebelum menyetujui." confirmText="Setujui permohonan" loading={busy} onClose={() => { setAction(null); setSelected(null); }} onConfirm={() => void runAction()} />
    <Modal open={action === "reject" && !!selected} title="Tolak permohonan" description="Alasan penolakan wajib dicatat dan akan terlihat oleh pemohon." onClose={() => { setAction(null); setSelected(null); setReason(""); }} closeDisabled={busy}>
      <Field label="Alasan penolakan"><textarea rows={4} minLength={3} maxLength={2000} value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Jelaskan alasan penolakan dengan jelas…" /></Field>
      {error ? <Notice tone="error">{error}</Notice> : null}
      <div className="modal-actions"><Button variant="secondary" onClick={() => { setAction(null); setSelected(null); setReason(""); }} disabled={busy}>Kembali</Button><Button variant="danger" disabled={busy || reason.trim().length < 3} onClick={() => void runAction()}>{busy ? "Memproses…" : "Kirim penolakan"}</Button></div>
    </Modal>
  </div>;
}

export function AdminRoomsPage() {
  const { language } = useLanguage();
  const [rooms, setRooms] = useState<Room[]>([]);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [selected, setSelected] = useState<Room | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [bulkStatus, setBulkStatus] = useState<RoomStatus | "">("");
  const [bulkConfirmOpen, setBulkConfirmOpen] = useState(false);
  const [bulkHoursOpen, setBulkHoursOpen] = useState(false);
  const [bulkHoursDays, setBulkHoursDays] = useState<string[]>(["monday", "tuesday", "wednesday", "thursday", "friday"]);
  const [bulkHoursStart, setBulkHoursStart] = useState("08:00");
  const [bulkHoursEnd, setBulkHoursEnd] = useState("17:00");
  const [bulkUpdating, setBulkUpdating] = useState(false);
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false);
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [bulkDeleteConfirmation, setBulkDeleteConfirmation] = useState("");
  const [bulkDeleteError, setBulkDeleteError] = useState("");

  const reload = () => {
    setLoading(true); setError(""); setNotice("");
    const params = new URLSearchParams({ page: "1", limit: "100", sortBy: "room_name", sortOrder: "asc" });
    if (status) params.set("status", status);
    roomApi.list(params).then((result) => setRooms(result.items))
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Data ruangan belum dapat dimuat."))
      .finally(() => setLoading(false));
  };
  useEffect(() => { setSelectedIds([]); setBulkStatus(""); reload(); }, [status]);

  const visible = rooms.filter((room) =>
    (!status || room.room_status === status)
    && (!search || (room.room_name + " " + room.building + " " + (room.room_code || "")).toLowerCase().includes(search.toLowerCase()))
  );
  const visibleIds = visible.map((room) => room.id);
  const allVisibleSelected = visibleIds.length > 0 && visibleIds.every((id) => selectedIds.includes(id));
  const active = rooms.filter((room) => room.room_status === "ACTIVE").length;
  const bulkStatusLabel: Record<RoomStatus, string> = {
    ACTIVE: "Aktif",
    INACTIVE: "Nonaktif",
    MAINTENANCE: "Pemeliharaan",
  };

  function toggleRoom(id: string, checked: boolean) {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (checked) next.add(id);
      else next.delete(id);
      return Array.from(next);
    });
  }

  function toggleVisibleRooms() {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (allVisibleSelected) visibleIds.forEach((id) => next.delete(id));
      else visibleIds.forEach((id) => next.add(id));
      return Array.from(next);
    });
  }

  function toggleBulkHoursDay(day: string) {
    setBulkHoursDays((current) => current.includes(day)
      ? current.filter((value) => value !== day)
      : [...current, day]);
  }

  async function applyBulkStatus() {
    if (!bulkStatus || selectedIds.length === 0) return;
    setBulkUpdating(true); setError("");
    try {
      const result = await roomApi.bulkUpdateStatus(selectedIds, bulkStatus);
      const updatedById = new Map(result.rooms.map((room) => [room.id, room]));
      setRooms((current) => current.map((room) => updatedById.get(room.id) || room));
      const targetLabel = bulkStatusLabel[bulkStatus].toLowerCase();
      const unchangedText = result.unchanged_count ? " " + result.unchanged_count + " ruangan sudah memiliki status tersebut." : "";
      setNotice(result.updated_count + " ruangan berhasil diubah menjadi " + targetLabel + "." + unchangedText);
      setSelectedIds([]);
      setBulkStatus("");
      setBulkConfirmOpen(false);
    } catch (cause) {
      setBulkConfirmOpen(false);
      setError(cause instanceof Error ? cause.message : "Status ruangan belum berhasil diperbarui. Tidak ada perubahan yang diterapkan.");
    } finally {
      setBulkUpdating(false);
    }
  }

  async function applyBulkOperatingHours() {
    if (selectedIds.length === 0) return;
    if (!bulkHoursDays.length) {
      setError("Pilih minimal satu hari operasional.");
      return;
    }
    if (bulkHoursEnd <= bulkHoursStart) {
      setError("Jam tutup harus lebih akhir dari jam buka.");
      return;
    }
    const operatingHours = Object.fromEntries(
      bulkHoursDays.map((day) => [day, [{ start: bulkHoursStart, end: bulkHoursEnd }]])
    );
    setBulkUpdating(true); setError("");
    try {
      const result = await roomApi.bulkUpdateOperatingHours(selectedIds, operatingHours);
      const updatedById = new Map(result.rooms.map((room) => [room.id, room]));
      setRooms((current) => current.map((room) => updatedById.get(room.id) || room));
      const unchangedText = result.unchanged_count ? " " + result.unchanged_count + " ruangan sudah memiliki jam tersebut." : "";
      setNotice("Jam operasional " + result.updated_count + " ruangan berhasil diperbarui." + unchangedText);
      setSelectedIds([]);
      setBulkStatus("");
      setBulkHoursOpen(false);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Jam operasional belum berhasil diperbarui. Tidak ada perubahan yang diterapkan.");
    } finally {
      setBulkUpdating(false);
    }
  }

  async function removeRoom() {
    if (!selected) return;
    setDeleting(true); setError("");
    try { await roomApi.remove(selected.id); setSelected(null); reload(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Ruangan belum dapat dihapus."); }
    finally { setDeleting(false); }
  }

  async function removeSelectedRooms() {
    if (!selectedIds.length) return;
    const confirmationWord = language === "id" ? "HAPUS" : "DELETE";
    if (bulkDeleteConfirmation.trim().toUpperCase() !== confirmationWord) return;
    setBulkDeleting(true);
    setBulkDeleteError("");
    try {
      const result = await roomApi.bulkDelete(selectedIds);
      const removedIds = new Set(result.room_ids);
      setRooms((current) => current.filter((room) => !removedIds.has(room.id)));
      setNotice(result.deleted_count + " ruangan berhasil dihapus dari direktori. Riwayat reservasi tetap tersimpan.");
      setSelectedIds([]);
      setBulkStatus("");
      setBulkDeleteConfirmation("");
      setBulkDeleteOpen(false);
    } catch (cause) {
      setBulkDeleteError(cause instanceof Error ? cause.message : "Tidak ada ruangan yang dihapus. Periksa reservasi mendatang pada ruangan terpilih.");
    } finally {
      setBulkDeleting(false);
    }
  }

  return <div className="page-stack">
    <PageTitle eyebrow="ROOM MANAGEMENT" title="Kelola ruangan" description={rooms.length + " ruangan dalam inventaris kampus."} action={<Link className="button button--primary" to="/admin/rooms/new"><Plus size={17} />Tambah ruangan</Link>} />
    <div className="panel list-toolbar">
      <Field label="Cari ruangan"><span className="input-with-icon"><Search size={17} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Nama ruangan, gedung, atau kode" /></span></Field>
      <Field label="Status"><select value={status} onChange={(event) => { setSelectedIds([]); setBulkStatus(""); setStatus(event.target.value); }}><option value="">Semua status</option><option value="ACTIVE">Aktif</option><option value="INACTIVE">Nonaktif</option><option value="MAINTENANCE">Pemeliharaan</option></select></Field>
      <Link className="button button--secondary" to="/admin/schedules"><CalendarDays size={16} />Jadwal & pemeliharaan</Link>
      <Link className="button button--secondary" to="/admin/data-imports"><FileSpreadsheet size={16} />Impor data</Link>
    </div>
    <div className="list-summary"><b>{active} aktif</b><span>{rooms.length - active} nonaktif atau pemeliharaan</span></div>
    <div className="room-selection-toolbar">
      <label className="checkbox-line room-selection-toolbar__all">
        <input type="checkbox" checked={allVisibleSelected} onChange={toggleVisibleRooms} disabled={!visible.length || loading || bulkUpdating} />
        <span>Pilih semua yang tampil</span>
        <b>{visible.length}</b>
      </label>
      <span className="room-selection-toolbar__count">{selectedIds.length} ruangan dipilih</span>
      {selectedIds.length > 0 ? <div className="room-selection-toolbar__bulk-row">
        <div className="room-selection-toolbar__danger">
          <div className="room-selection-toolbar__danger-label"><AlertTriangle size={16} /><span>AREA BAHAYA</span></div>
          <Button variant="danger" disabled={bulkUpdating || bulkDeleting} onClick={() => { setBulkDeleteConfirmation(""); setBulkDeleteError(""); setBulkDeleteOpen(true); }}>
            <Trash2 size={15} />Hapus pilihan ({selectedIds.length})
          </Button>
        </div>
        <div className="room-selection-toolbar__actions">
          <Field label="Ubah status menjadi">
            <select value={bulkStatus} onChange={(event) => setBulkStatus(event.target.value as RoomStatus | "")} disabled={bulkUpdating || bulkDeleting}>
              <option value="">Pilih status…</option>
              <option value="ACTIVE">Aktif</option>
              <option value="INACTIVE">Nonaktif</option>
              <option value="MAINTENANCE">Pemeliharaan</option>
            </select>
          </Field>
          <Button disabled={!bulkStatus || bulkUpdating || bulkDeleting} onClick={() => setBulkConfirmOpen(true)}>Terapkan status</Button>
          <Button variant="secondary" disabled={bulkUpdating || bulkDeleting} onClick={() => setBulkHoursOpen(true)}><Clock3 size={15} />Atur jam operasional</Button>
          <Button variant="secondary" disabled={bulkUpdating || bulkDeleting} onClick={() => { setSelectedIds([]); setBulkStatus(""); }}>Batal pilih</Button>
        </div>
      </div> : <small className="room-selection-toolbar__hint">Centang ruangan untuk mengubah status atau jam operasional beberapa ruangan sekaligus.</small>}
    </div>
    {error ? <Notice tone="error">{error}</Notice> : null}
    {notice ? <Notice tone="success">{notice}</Notice> : null}
    {loading ? <Loading label="Memuat inventaris ruangan…" /> : visible.length ? <div className="room-grid">
      {visible.map((room) => {
        const isSelected = selectedIds.includes(room.id);
        return <article className={"room-card" + (isSelected ? " is-selected" : "")} key={room.id}>
          <label className="room-card__select" title={"Pilih " + room.room_name}>
            <input type="checkbox" checked={isSelected} onChange={(event) => toggleRoom(room.id, event.target.checked)} aria-label={"Pilih " + room.room_name} disabled={bulkUpdating} />
          </label>
          <div className="room-card__media">{room.photo_url ? <img src={apiAssetUrl(room.photo_url)} alt={room.room_name} loading="lazy" /> : <span className="room-card__placeholder"><Building2 size={36} /></span>}</div>
          <div className="room-card__body">
            <div className="room-card__top"><StatusBadge status={room.room_status} /><span><Users size={14} />{room.capacity} orang{room.capacity_estimate ? " · estimasi " + room.capacity_estimate : ""}</span></div>
            <strong className="room-card__title">{room.room_name}</strong>
            <p>{room.building}{room.floor ? " · Lantai " + room.floor : ""}</p>
            <div className="chip-list">{room.facilities.slice(0, 3).map((item) => <span key={item}>{item}</span>)}</div>
            <div className="room-card__actions">
              <Link className="button button--secondary" to={"/admin/rooms/" + room.id + "/edit"}><Edit3 size={15} />Edit</Link>
              <Button variant="danger" onClick={() => setSelected(room)}><Trash2 size={15} />Hapus</Button>
            </div>
          </div>
        </article>;
      })}
    </div> : <EmptyState title="Ruangan belum tersedia" description="Tambahkan ruangan baru untuk memulai pengelolaan inventaris." action={<Link to="/admin/rooms/new" className="button button--primary">Tambah ruangan</Link>} icon={<Building2 size={22} />} />}
    <ConfirmModal
      open={bulkConfirmOpen}
      title={"Ubah status " + selectedIds.length + " ruangan sekaligus?"}
      description={bulkStatus ? "Semua ruangan terpilih akan diubah menjadi " + bulkStatusLabel[bulkStatus] + ". Jika ada ruangan dengan reservasi mendatang yang masih menunggu atau disetujui, seluruh perubahan akan dibatalkan." : ""}
      confirmText="Ya, ubah semua status"
      loading={bulkUpdating}
      onClose={() => setBulkConfirmOpen(false)}
      onConfirm={() => void applyBulkStatus()}
    />
    <Modal
      open={bulkHoursOpen}
      closeDisabled={bulkUpdating}
      title={"Atur jam operasional " + selectedIds.length + " ruangan"}
      description="Hari dan jam yang dipilih akan langsung diterapkan ke seluruh ruangan terpilih setelah disimpan."
      onClose={() => { if (!bulkUpdating) setBulkHoursOpen(false); }}
    >
      <div className="stack-form">
        <div className="weekday-grid">
          {weekdays.map(([day, label]) => <label key={day} className="checkbox-card">
            <input type="checkbox" checked={bulkHoursDays.includes(day)} onChange={() => toggleBulkHoursDay(day)} disabled={bulkUpdating} />
            <span>{label}</span>
          </label>)}
        </div>
        <div className="form-grid form-grid--narrow">
          <Field label="Buka"><input type="time" value={bulkHoursStart} onChange={(event) => setBulkHoursStart(event.target.value)} disabled={bulkUpdating} /></Field>
          <Field label="Tutup"><input type="time" value={bulkHoursEnd} onChange={(event) => setBulkHoursEnd(event.target.value)} disabled={bulkUpdating} /></Field>
        </div>
        <Notice tone="info">Perubahan akan ditolak untuk semua ruangan apabila jadwal kuliah atau reservasi mendatang berada di luar jam yang dipilih. Tidak ada perubahan sebagian.</Notice>
        <div className="modal-actions">
          <Button variant="secondary" disabled={bulkUpdating} onClick={() => setBulkHoursOpen(false)}>Batal</Button>
          <Button disabled={bulkUpdating || !bulkHoursDays.length || bulkHoursEnd <= bulkHoursStart} onClick={() => void applyBulkOperatingHours()}>{bulkUpdating ? "Menyimpan…" : "Simpan jam operasional"}</Button>
        </div>
      </div>
    </Modal>
    <Modal
      open={bulkDeleteOpen}
      title={"Hapus " + selectedIds.length + " ruangan terpilih?"}
      description="Penghapusan massal akan mengeluarkan ruangan dari direktori aktif. Riwayat reservasi tetap dipertahankan."
      closeDisabled={bulkDeleting}
      onClose={() => { if (!bulkDeleting) { setBulkDeleteOpen(false); setBulkDeleteConfirmation(""); setBulkDeleteError(""); } }}
    >
      <div className="stack-form">
        <div className="danger-zone-callout">
          <strong><AlertTriangle size={17} />PERINGATAN — AREA BAHAYA</strong>
          <p>Ruangan terpilih akan dihapus dari direktori. Data riwayat reservasi dan audit tetap disimpan.</p>
          <ul>
            <li>Ruangan dengan reservasi mendatang berstatus Menunggu atau Disetujui akan memblokir penghapusan.</li>
            <li>Jika satu ruangan terblokir, seluruh proses dibatalkan. Tidak ada penghapusan sebagian.</li>
            <li>Penghapusan menggunakan soft-delete agar histori tidak rusak.</li>
          </ul>
        </div>
        {bulkDeleteError ? <Notice tone="error">{bulkDeleteError}</Notice> : null}
        <Field label={language === "id" ? "Ketik HAPUS untuk mengonfirmasi" : "Type DELETE to confirm"}>
          <input value={bulkDeleteConfirmation} onChange={(event) => setBulkDeleteConfirmation(event.target.value)} placeholder={language === "id" ? "Ketik HAPUS" : "Type DELETE"} autoComplete="off" disabled={bulkDeleting} />
        </Field>
        <div className="modal-actions">
          <Button variant="secondary" disabled={bulkDeleting} onClick={() => { setBulkDeleteOpen(false); setBulkDeleteConfirmation(""); setBulkDeleteError(""); }}>Batal</Button>
          <Button variant="danger" disabled={bulkDeleting || bulkDeleteConfirmation.trim().toUpperCase() !== (language === "id" ? "HAPUS" : "DELETE")} onClick={() => void removeSelectedRooms()}>
            <Trash2 size={15} />{bulkDeleting ? "Menghapus…" : "Hapus " + selectedIds.length + " ruangan"}
          </Button>
        </div>
      </div>
    </Modal>
    <ConfirmModal open={!!selected} title="Nonaktifkan ruangan?" description={selected ? selected.room_name + " akan dihapus secara soft-delete. Ruangan dengan reservasi mendatang yang masih aktif tidak dapat dihapus." : ""} confirmText="Nonaktifkan ruangan" destructive loading={deleting} onClose={() => setSelected(null)} onConfirm={() => void removeRoom()} />
  </div>;
}

const weekdays = [
  ["monday", "Senin"], ["tuesday", "Selasa"], ["wednesday", "Rabu"], ["thursday", "Kamis"],
  ["friday", "Jumat"], ["saturday", "Sabtu"], ["sunday", "Minggu"],
] as const;

export function AdminRoomEditorPage() {
  const { roomId = "" } = useParams();
  const editMode = !!roomId;
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [building, setBuilding] = useState("");
  const [faculty, setFaculty] = useState("");
  const [floor, setFloor] = useState("");
  const [locationDescription, setLocationDescription] = useState("");
  const [capacity, setCapacity] = useState("8");
  const [description, setDescription] = useState("");
  const [facilities, setFacilities] = useState("");
  const [photoUrl, setPhotoUrl] = useState("");
  const [status, setStatus] = useState<RoomStatus>("ACTIVE");
  const [days, setDays] = useState<string[]>(["monday", "tuesday", "wednesday", "thursday", "friday"]);
  const [start, setStart] = useState("08:00");
  const [end, setEnd] = useState("17:00");
  const [loading, setLoading] = useState(editMode);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!editMode) return;
    let active = true;
    roomApi.get(roomId).then((room) => {
      if (!active) return;
      setName(room.room_name); setCode(room.room_code || ""); setBuilding(room.building);
      setFaculty(room.faculty || ""); setFloor(room.floor || ""); setLocationDescription(room.location_description || "");
      setCapacity(String(room.capacity)); setDescription(room.description || "");
      setFacilities(room.facilities.join(", ")); setPhotoUrl(room.photo_url || ""); setStatus(room.room_status);
      const configured = Object.keys(room.operating_hours || {}).filter((day) => Array.isArray(room.operating_hours[day]) && room.operating_hours[day].length);
      setDays(configured);
      const first = configured.length ? room.operating_hours[configured[0]][0] : undefined;
      if (first) { setStart(first.start.slice(0, 5)); setEnd(first.end.slice(0, 5)); }
    }).catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "Data ruangan belum dapat dimuat."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [editMode, roomId]);

  function toggleDay(day: string) {
    setDays((current) => current.includes(day) ? current.filter((value) => value !== day) : [...current, day]);
  }

  async function save(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError("");
    if (!days.length) { setError("Pilih minimal satu hari operasional agar backend dapat mengevaluasi ketersediaan."); setSaving(false); return; }
    if (end <= start) { setError("Jam selesai harus lebih akhir dari jam mulai."); setSaving(false); return; }
    const operating_hours: Record<string, Array<{ start: string; end: string }>> = {};
    days.forEach((day) => { operating_hours[day] = [{ start, end }]; });
    const payload = {
      room_name: name.trim(), room_code: code.trim() || null, building: building.trim(),
      faculty: faculty.trim() || null, floor: floor.trim() || null, location_description: locationDescription.trim() || null,
      capacity: Number(capacity), description: description.trim() || null,
      facilities: facilities.split(",").map((value) => value.trim()).filter(Boolean),
      operating_hours, room_status: status, photo_url: photoUrl.trim() || null,
    };
    try {
      if (editMode) await roomApi.update(roomId, payload);
      else await roomApi.create(payload);
      navigate("/admin/rooms", { replace: true });
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Data ruangan belum berhasil disimpan."); }
    finally { setSaving(false); }
  }

  if (loading) return <Loading label="Memuat data ruangan…" />;
  return <div className="page-stack">
    <Link className="back-link" to="/admin/rooms">← Kembali ke kelola ruangan</Link>
    <PageTitle eyebrow="ROOM MANAGEMENT" title={editMode ? "Edit ruangan" : "Tambah ruangan"} description="Lengkapi informasi ruangan dan jam operasional yang berlaku." />
    {error ? <Notice tone="error">{error}</Notice> : null}
    <form className="panel stack-form room-editor-form" onSubmit={save}>
      <h2>Informasi ruangan</h2>
      <div className="form-grid">
        <Field label="Nama ruangan"><input value={name} onChange={(e) => setName(e.target.value)} minLength={2} maxLength={160} required placeholder="Contoh: Discussion Room A201" /></Field>
        <Field label="Kode ruangan (opsional)"><input value={code} onChange={(e) => setCode(e.target.value)} maxLength={80} placeholder="Contoh: RK-A201" /></Field>
        <Field label="Fakultas"><input value={faculty} onChange={(e) => setFaculty(e.target.value)} maxLength={160} placeholder="Nama fakultas" /></Field>
        <Field label="Gedung"><input value={building} onChange={(e) => setBuilding(e.target.value)} maxLength={160} required placeholder="Nama gedung" /></Field>
        <Field label="Lantai"><input value={floor} onChange={(e) => setFloor(e.target.value)} maxLength={40} placeholder="Contoh: 2" /></Field>
        <Field label="Lokasi detail"><input value={locationDescription} onChange={(e) => setLocationDescription(e.target.value)} maxLength={500} placeholder="Contoh: dekat lift, sayap timur" /></Field>
        <Field label="Kapasitas"><input type="number" min="1" max="10000" value={capacity} onChange={(e) => setCapacity(e.target.value)} required /></Field>
        <Field label="Status ruangan"><select value={status} onChange={(e) => setStatus(e.target.value as RoomStatus)}><option value="ACTIVE">Aktif</option><option value="INACTIVE">Nonaktif</option><option value="MAINTENANCE">Pemeliharaan</option></select></Field>
      </div>
      <Field label="Fasilitas" hint="Pisahkan setiap fasilitas dengan koma."><input value={facilities} onChange={(e) => setFacilities(e.target.value)} placeholder="Whiteboard, Wi-Fi, Stop kontak" /></Field>
      <Field label="Deskripsi"><textarea rows={3} maxLength={5000} value={description} onChange={(e) => setDescription(e.target.value)} /></Field>
      <Field label="URL atau path foto ruangan (opsional)" hint="Bisa memakai URL lengkap atau path foto hasil impor, misalnya /media/rooms/nama-file.jpg."><input type="text" inputMode="url" autoComplete="off" maxLength={2048} value={photoUrl} onChange={(e) => setPhotoUrl(e.target.value)} placeholder="/media/rooms/nama-file.jpg atau https://…" /></Field>
      <div className="form-divider" />
      <div><h2>Jam operasional</h2><p className="muted">Field ini diperlukan oleh backend untuk memeriksa ketersediaan. Jam yang sama akan diterapkan ke hari yang dipilih.</p></div>
      <div className="weekday-grid">{weekdays.map(([day, label]) => <label key={day} className="checkbox-card"><input type="checkbox" checked={days.includes(day)} onChange={() => toggleDay(day)} /><span>{label}</span></label>)}</div>
      <div className="form-grid form-grid--narrow">
        <Field label="Buka"><input type="time" value={start} onChange={(e) => setStart(e.target.value)} required /></Field>
        <Field label="Tutup"><input type="time" value={end} onChange={(e) => setEnd(e.target.value)} required /></Field>
      </div>
      <div className="form-actions">
        <Button type="submit" disabled={saving}>{saving ? "Menyimpan…" : "Simpan ruangan"}</Button>
        <Button type="button" variant="secondary" onClick={() => navigate("/admin/rooms")}>Batal</Button>
      </div>
    </form>
  </div>;
}

export function AdminSchedulesPage() {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [items, setItems] = useState<Schedule[]>([]);
  const [blocks, setBlocks] = useState<RoomUnavailability[]>([]);
  const [roomId, setRoomId] = useState("");
  const [course, setCourse] = useState("");
  const [mode, setMode] = useState<"date" | "weekly">("date");
  const [date, setDate] = useState(localToday());
  const [day, setDay] = useState("0");
  const [start, setStart] = useState("08:00");
  const [end, setEnd] = useState("10:00");
  const [blockDate, setBlockDate] = useState(localToday());
  const [blockStart, setBlockStart] = useState("08:00");
  const [blockEnd, setBlockEnd] = useState("17:00");
  const [blockReason, setBlockReason] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  function reload() {
    setLoading(true);
    Promise.all([
      roomApi.list(new URLSearchParams({ page: "1", limit: "100" })),
      scheduleApi.list(),
      scheduleApi.listUnavailability(),
    ]).then(([roomData, scheduleData, blockData]) => {
      setRooms(roomData.items);
      setItems(scheduleData.items);
      setBlocks(blockData);
      if (!roomId && roomData.items.length) setRoomId(roomData.items[0].id);
    }).catch((cause) => setError(cause instanceof Error ? cause.message : "Data jadwal belum dapat dimuat."))
      .finally(() => setLoading(false));
  }
  useEffect(() => { reload(); }, []);

  async function create(event: FormEvent) {
    event.preventDefault(); setError(""); setSuccess("");
    if (!roomId) { setError("Pilih ruangan terlebih dahulu."); return; }
    if (end <= start) { setError("Jam selesai harus lebih akhir dari jam mulai."); return; }
    setSaving(true);
    try {
      await scheduleApi.create({
        room_id: roomId, course_name: course.trim(),
        ...(mode === "date" ? { schedule_date: date } : { day_of_week: Number(day) }),
        start_time: start, end_time: end, data_source: "ADMIN_MANUAL",
      });
      setCourse(""); setSuccess("Jadwal berhasil ditambahkan."); reload();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Jadwal belum berhasil disimpan."); }
    finally { setSaving(false); }
  }

  async function createBlock(event: FormEvent) {
    event.preventDefault(); setError(""); setSuccess("");
    if (!roomId) { setError("Pilih ruangan terlebih dahulu."); return; }
    if (blockEnd <= blockStart) { setError("Jam selesai harus lebih akhir dari jam mulai."); return; }
    if (blockReason.trim().length < 3) { setError("Alasan periode tidak tersedia minimal 3 karakter."); return; }
    setSaving(true);
    try {
      await scheduleApi.createUnavailability({
        room_id: roomId,
        unavailable_date: blockDate,
        start_time: blockStart,
        end_time: blockEnd,
        reason: blockReason.trim(),
      });
      setBlockReason("");
      setSuccess("Periode tidak tersedia berhasil ditambahkan.");
      reload();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Periode tidak tersedia belum berhasil disimpan.");
    } finally { setSaving(false); }
  }

  async function cancel(id: string) {
    if (!window.confirm("Batalkan jadwal akademik ini?")) return;
    setError("");
    try { await scheduleApi.cancel(id); reload(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Jadwal belum berhasil dibatalkan."); }
  }

  async function deactivateBlock(id: string) {
    if (!window.confirm("Nonaktifkan periode pemeliharaan ini?")) return;
    setError("");
    try { await scheduleApi.deactivateUnavailability(id); reload(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Periode belum berhasil dinonaktifkan."); }
  }

  const dayNames = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"];
  return <div className="page-stack">
    <PageTitle eyebrow="ROOM SCHEDULES" title="Jadwal & pemeliharaan" description="Catat jadwal akademik dan periode ruangan tidak tersedia agar backend dapat memeriksa benturan reservasi." />
    {error ? <Notice tone="error">{error}</Notice> : null}
    {success ? <Notice tone="success">{success}</Notice> : null}
    <div className="admin-schedule-forms">
    <form className="panel stack-form" onSubmit={create}>
      <h2>Tambah jadwal akademik</h2>
      <Field label="Ruangan"><select value={roomId} onChange={(e) => setRoomId(e.target.value)} required><option value="">Pilih ruangan</option>{rooms.map((room) => <option key={room.id} value={room.id}>{room.room_name} · {room.building}</option>)}</select></Field>
      <Field label="Nama mata kuliah / kegiatan"><input value={course} onChange={(e) => setCourse(e.target.value)} maxLength={200} minLength={2} required /></Field>
      <Field label="Jenis jadwal"><select value={mode} onChange={(e) => setMode(e.target.value as "date" | "weekly")}><option value="date">Tanggal tertentu</option><option value="weekly">Berulang mingguan</option></select></Field>
      {mode === "date" ? <Field label="Tanggal"><input type="date" min={localToday()} value={date} onChange={(e) => setDate(e.target.value)} required /></Field>
        : <Field label="Hari"><select value={day} onChange={(e) => setDay(e.target.value)}>{dayNames.map((name, index) => <option key={name} value={String(index)}>{name}</option>)}</select></Field>}
      <div className="form-grid form-grid--narrow">
        <Field label="Jam mulai"><input type="time" value={start} onChange={(e) => setStart(e.target.value)} required /></Field>
        <Field label="Jam selesai"><input type="time" value={end} onChange={(e) => setEnd(e.target.value)} required /></Field>
      </div>
      <Button type="submit" disabled={saving}>{saving ? "Menyimpan…" : "Simpan jadwal"}</Button>
    </form>
    <form className="panel stack-form" onSubmit={createBlock}>
      <h2>Tambah periode pemeliharaan / tidak tersedia</h2>
      <p className="muted">Periode ini akan menjadi penghalang ketersediaan ruang pada tanggal dan waktu yang ditentukan.</p>
      <Field label="Ruangan"><select value={roomId} onChange={(e) => setRoomId(e.target.value)} required><option value="">Pilih ruangan</option>{rooms.map((room) => <option key={room.id} value={room.id}>{room.room_name} · {room.building}</option>)}</select></Field>
      <Field label="Tanggal"><input type="date" min={localToday()} value={blockDate} onChange={(e) => setBlockDate(e.target.value)} required /></Field>
      <div className="form-grid form-grid--narrow">
        <Field label="Jam mulai"><input type="time" value={blockStart} onChange={(e) => setBlockStart(e.target.value)} required /></Field>
        <Field label="Jam selesai"><input type="time" value={blockEnd} onChange={(e) => setBlockEnd(e.target.value)} required /></Field>
      </div>
      <Field label="Alasan"><input value={blockReason} onChange={(e) => setBlockReason(e.target.value)} minLength={3} maxLength={240} required placeholder="Contoh: Pemeliharaan fasilitas" /></Field>
      <Button type="submit" variant="secondary" disabled={saving}>{saving ? "Menyimpan…" : "Simpan periode"}</Button>
    </form>
    </div>
    <PageSection title="Jadwal akademik tercatat">
      {loading ? <Loading label="Memuat jadwal…" /> : items.length ? <div className="table-wrap"><table className="data-table">
        <thead><tr><th>Ruangan</th><th>Kegiatan</th><th>Waktu</th><th>Sumber</th><th /></tr></thead>
        <tbody>{items.map((item) => <tr key={item.id}>
          <td>{rooms.find((room) => room.id === item.room_id)?.room_name || item.room_id.slice(0, 8)}</td>
          <td><b>{item.course_name}</b><small>{item.schedule_date ? formatDate(item.schedule_date) : "Berulang · " + dayNames[item.day_of_week ?? 0]}</small></td>
          <td>{formatTime(item.start_time)}–{formatTime(item.end_time)}</td>
          <td>{item.data_source}</td>
          <td><Button variant="ghost" onClick={() => void cancel(item.id)}>Batalkan</Button></td>
        </tr>)}</tbody>
      </table></div> : <EmptyState title="Belum ada jadwal" description="Jadwal yang ditambahkan di sini akan digunakan backend saat mengevaluasi benturan reservasi." icon={<CalendarClock size={22} />} />}
    </PageSection>
    <PageSection title="Periode pemeliharaan / tidak tersedia">
      {loading ? <Loading label="Memuat periode…" /> : blocks.length ? <div className="table-wrap"><table className="data-table">
        <thead><tr><th>Ruangan</th><th>Tanggal</th><th>Waktu</th><th>Alasan</th><th /></tr></thead>
        <tbody>{blocks.map((block) => <tr key={block.id}>
          <td>{rooms.find((room) => room.id === block.room_id)?.room_name || block.room_id.slice(0, 8)}</td>
          <td>{formatDate(block.unavailable_date)}</td>
          <td>{formatTime(block.start_time)}–{formatTime(block.end_time)}</td>
          <td>{block.reason}</td>
          <td><Button variant="ghost" onClick={() => void deactivateBlock(block.id)}>Nonaktifkan</Button></td>
        </tr>)}</tbody>
      </table></div> : <EmptyState title="Belum ada periode pemeliharaan" description="Tambahkan periode ketika ruangan ditutup sementara atau sedang diperbaiki." />}
    </PageSection>
  </div>;
}
