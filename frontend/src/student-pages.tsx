import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  ArrowLeft, ArrowRight, Bell, Building2, CalendarDays, CalendarCheck, Check, Clock3, MapPin,
  Eye, EyeOff, Search, Users, XCircle,
} from "lucide-react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";
import {
  ApiError, apiAssetUrl, availabilityReasonLabel, canCancelReservation, dashboardApi, formatDate, formatDateTime, formatTime, localToday,
  notificationApi, profileApi, reservationApi, roomApi, statusLabel,
} from "./api";
import { useAuth } from "./auth";
import type { AppNotification, AppRole, AuthUser, AvailabilityResult, Reservation, Room } from "./types";
import { PageTitle } from "./layout";
import { Button, ConfirmModal, EmptyState, Field, initialsFromName, Loading, Modal, Notice, PageSection, StatusBadge } from "./ui";

function usePageError() {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return { error, setError, busy, setBusy };
}

function useReservationClock() {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const interval = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(interval);
  }, []);

  return now;
}

function campusTimestamp(date: string, time: string): number {
  return new Date(date + "T" + time.slice(0, 8) + "+07:00").getTime();
}

function countdownText(milliseconds: number): string {
  const seconds = Math.max(0, Math.floor(milliseconds / 1000));
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remaining = seconds % 60;
  return [hours, minutes, remaining].map((value) => String(value).padStart(2, "0")).join(":");
}

function reservationCardTiming(item: Reservation, now: number) {
  if (item.status === "COMPLETED") {
    return { caption: "Peminjaman", value: "Selesai", urgent: false };
  }
  if (item.status !== "APPROVED") return null;

  const startsAt = campusTimestamp(item.reservation_date, item.start_time);
  const endsAt = campusTimestamp(item.reservation_date, item.end_time);
  if (!Number.isFinite(startsAt) || !Number.isFinite(endsAt) || endsAt <= startsAt) return null;

  if (now < startsAt) {
    return { caption: "Mulai pukul", value: formatTime(item.start_time) + " WIB", urgent: false };
  }
  if (now < endsAt) {
    const remaining = endsAt - now;
    return {
      caption: "Sisa waktu peminjaman",
      value: countdownText(remaining),
      urgent: remaining <= 5 * 60 * 1000,
    };
  }
  return { caption: "Peminjaman", value: "Selesai", urgent: false };
}

function ReservationCard({ item, now, showCancel = false, onUpdated }: { item: Reservation; now: number; showCancel?: boolean; onUpdated?: (updated: Reservation) => void }) {
  const [currentItem, setCurrentItem] = useState(item);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [cancelError, setCancelError] = useState("");

  useEffect(() => { setCurrentItem(item); }, [item]);

  const canCancel = showCancel && canCancelReservation(currentItem.status, currentItem.reservation_date);
  const timing = reservationCardTiming(currentItem, now);

  async function cancelReservation() {
    setBusy(true);
    setCancelError("");
    try {
      const updated = await reservationApi.cancel(currentItem.id, cancelReason.trim() || undefined);
      setCurrentItem(updated);
      onUpdated?.(updated);
      setCancelReason("");
      setCancelOpen(false);
    } catch (cause) {
      setCancelError(cause instanceof Error ? cause.message : "Pembatalan belum berhasil. Silakan coba kembali.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="reservation-card">
      <Link className="reservation-card__link" to={"/student/reservations/" + currentItem.id}>
        <div className="reservation-card__top">
          <span className="reservation-card__id">RK-{currentItem.id.slice(0, 8).toUpperCase()}</span>
          <StatusBadge status={currentItem.status} />
        </div>
        {currentItem.room?.photo_url ? <RoomPhoto photoUrl={currentItem.room.photo_url} roomName={currentItem.room.room_name} className="reservation-card__image" /> : null}
        <strong>{currentItem.room?.room_name || "Ruangan"}</strong>
        <span className="muted">{currentItem.room?.building || "Lokasi kampus belum tersedia"}</span>
        <div className="reservation-card__meta">
          <span><CalendarDays size={15} />{formatDate(currentItem.reservation_date)}</span>
          {timing ? (
            <span className={"reservation-card__countdown" + (timing.urgent ? " reservation-card__countdown--urgent" : "")}>
              <Clock3 size={15} />
              <span className="reservation-card__countdown-copy">
                <small>{timing.caption}</small>
                <strong>{timing.value}</strong>
              </span>
            </span>
          ) : (
            <span><Clock3 size={15} />{formatTime(currentItem.start_time)}–{formatTime(currentItem.end_time)}</span>
          )}
        </div>
        <p>{currentItem.purpose}</p>
      </Link>
      {cancelError ? <div className="reservation-card__feedback"><Notice tone="error">{cancelError}</Notice></div> : null}
      {canCancel ? (
        <div className="reservation-card__actions">
          <Button variant="danger" onClick={() => { setCancelError(""); setCancelOpen(true); }}>
            <XCircle size={15} />Batalkan reservasi
          </Button>
        </div>
      ) : null}
      <Modal
        open={cancelOpen}
        closeDisabled={busy}
        title="Batalkan reservasi?"
        description="Reservasi ini akan berubah menjadi Dibatalkan dan slot ruangan dapat digunakan kembali sesuai validasi sistem."
        onClose={() => { if (!busy) setCancelOpen(false); }}
      >
        {cancelError ? <Notice tone="error">{cancelError}</Notice> : null}
        <Field label="Alasan pembatalan (opsional)">
          <textarea rows={3} value={cancelReason} onChange={(event) => setCancelReason(event.target.value)} maxLength={2000} />
        </Field>
        <div className="modal-actions">
          <Button variant="secondary" onClick={() => setCancelOpen(false)} disabled={busy}>Kembali</Button>
          <Button variant="danger" onClick={() => void cancelReservation()} disabled={busy}>
            {busy ? "Memproses…" : "Ya, batalkan"}
          </Button>
        </div>
      </Modal>
    </article>
  );
}


function RoomPhoto({ photoUrl, roomName, detail = false, className }: {
  photoUrl: string | null;
  roomName: string;
  detail?: boolean;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);

  useEffect(() => { setFailed(false); }, [photoUrl]);

  if (!photoUrl || failed) {
    return <div className={detail ? "room-detail__image room-detail__image--empty" : className || "room-card__placeholder"}>
      <Building2 size={detail ? 48 : 34} aria-hidden="true" />
    </div>;
  }

  return <img
    className={detail ? "room-detail__image" : className}
    src={apiAssetUrl(photoUrl)}
    alt={"Foto " + roomName}
    loading="lazy"
    decoding="async"
    onError={() => setFailed(true)}
  />;
}

export function StudentDashboardPage() {
  const { user } = useAuth();
  const reservationNow = useReservationClock();
  const [summary, setSummary] = useState<Record<string, number | string> | null>(null);
  const [recent, setRecent] = useState<Reservation[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    Promise.all([dashboardApi.summary(), dashboardApi.recent(8)])
      .then(([stats, latest]) => {
        if (!active) return;
        setSummary(stats);
        setRecent(latest.items);
      })
      .catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "Data dashboard belum dapat dimuat."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const upcoming = recent.filter((item) => item.status === "APPROVED" && item.reservation_date >= localToday()).slice(0, 1)[0];
  const pending = Number(summary?.pending || 0);
  const approved = Number(summary?.approved || 0);
  const greeting = new Intl.DateTimeFormat("id-ID", { hour: "numeric", timeZone: "Asia/Jakarta" }).format(new Date());
  const hour = Number(greeting.split(".")[0]);
  const welcome = hour < 11 ? "Selamat pagi" : hour < 15 ? "Selamat siang" : hour < 18 ? "Selamat sore" : "Selamat malam";

  return <div className="page-stack">
    <PageTitle eyebrow={new Intl.DateTimeFormat("id-ID", { weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: "Asia/Jakarta" }).format(new Date()).toUpperCase()}
      title={welcome + ", " + (user?.name?.split(" ")[0] || "Mahasiswa")}
      description="Sedikit ruang untuk mewujudkan ide besar Anda."
      action={<Link className="button button--primary" to="/student/availability"><CalendarCheck size={17} />Cek ketersediaan</Link>} />
    {error ? <Notice tone="error">{error}</Notice> : null}
    {loading ? <Loading label="Memuat ringkasan reservasi…" /> : <>
      <div className="stat-grid stat-grid--two">
        <article className="stat-card"><div className="stat-card__top"><span>Reservasi aktif</span><CalendarCheck size={18} /></div><strong>{pending + approved}</strong><small>Menunggu atau sudah disetujui</small></article>
        <article className="stat-card"><div className="stat-card__top"><span>Menunggu persetujuan</span><Clock3 size={18} /></div><strong>{pending}</strong><small>Dalam peninjauan TU/Admin</small></article>
      </div>
      <PageSection title="Sesi kampus berikutnya" action={<Link className="text-link" to="/student/reservations">Lihat semua</Link>}>
        {upcoming ? (
          <article className="next-session-card">
            <div className="next-session-card__top"><span>SESI ANDA</span><StatusBadge status={upcoming.status} /></div>
            {upcoming.room?.photo_url ? <RoomPhoto photoUrl={upcoming.room.photo_url} roomName={upcoming.room.room_name} className="next-session-card__image" /> : null}
            <h2>{upcoming.room?.room_name || "Ruangan"}</h2>
            <p>{upcoming.room?.building || "Lokasi kampus"}</p>
            <div className="next-session-card__details">
              <span>{formatDate(upcoming.reservation_date)}<b>{formatTime(upcoming.start_time)}–{formatTime(upcoming.end_time)}</b></span>
              <span>{upcoming.purpose}<b>{upcoming.participant_count} peserta</b></span>
            </div>
          </article>
        ) : <EmptyState title="Belum ada sesi yang disetujui" description="Reservasi mendatang akan muncul di sini setelah disetujui oleh TU/Admin." action={<Link to="/student/rooms" className="button button--secondary">Cari ruang</Link>} icon={<CalendarDays size={23} />} />}
      </PageSection>
      <PageSection title="Permohonan terbaru" action={<Link className="text-link" to="/student/reservations">Lihat riwayat</Link>}>
        {recent.length ? <div className="card-list">{recent.slice(0, 3).map((item) => <ReservationCard key={item.id} item={item} now={reservationNow} />)}</div>
          : <EmptyState title="Belum ada permohonan" description="Mulai dengan memilih ruangan yang sesuai untuk kegiatan Anda." action={<Link className="button button--primary" to="/student/rooms">Cari ruangan</Link>} icon={<CalendarCheck size={22} />} />}
      </PageSection>
    </>}
  </div>;
}

export function RoomDirectoryPage({ role }: { role: AppRole }) {
  const [search, setSearch] = useState("");
  const [faculty, setFaculty] = useState("");
  const [building, setBuilding] = useState("");
  const [location, setLocation] = useState("");
  const [capacity, setCapacity] = useState("");
  const [facility, setFacility] = useState("");
  const [applied, setApplied] = useState({ search: "", faculty: "", building: "", location: "", capacity: "", facility: "" });
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [meta, setMeta] = useState<{ total: number } | undefined>();

  useEffect(() => {
    let active = true;
    setLoading(true); setError("");
    const params = new URLSearchParams({ page: "1", limit: "100", sortBy: "room_name", sortOrder: "asc" });
    if (applied.search) params.set("search", applied.search);
    if (applied.faculty) params.set("faculty", applied.faculty);
    if (applied.building) params.set("building", applied.building);
    if (applied.location) params.set("location", applied.location);
    if (applied.capacity) params.set("min_capacity", applied.capacity);
    if (applied.facility) params.append("facilities", applied.facility);
    roomApi.list(params).then((result) => {
      if (!active) return;
      setRooms(result.items); setMeta(result.meta ? { total: result.meta.total } : undefined);
    }).catch((cause) => {
      if (active) setError(cause instanceof Error ? cause.message : "Daftar ruangan belum dapat dimuat.");
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [applied]);

  function applyFilters(event: FormEvent) {
    event.preventDefault();
    setApplied({ search: search.trim(), faculty: faculty.trim(), building: building.trim(),
      location: location.trim(), capacity, facility: facility.trim() });
  }
  function resetFilters() {
    setSearch(""); setFaculty(""); setBuilding(""); setLocation(""); setCapacity(""); setFacility("");
    setApplied({ search: "", faculty: "", building: "", location: "", capacity: "", facility: "" });
  }

  return <div className="page-stack">
    <PageTitle eyebrow="CAMPUS ROOM DIRECTORY" title="Direktori ruangan"
      description="Temukan ruang berdasarkan fakultas, gedung, lokasi, kapasitas, dan fasilitas yang dibutuhkan."
      action={role === "Student" ? <Link className="button button--primary" to="/student/availability"><CalendarDays size={16} />Cek ketersediaan</Link> : undefined} />
    <form className="filter-panel filter-panel--room" onSubmit={applyFilters}>
      <Field label="Cari ruangan"><span className="input-with-icon"><Search size={17} /><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Nama, kode, atau deskripsi ruangan" /></span></Field>
      <div className="filter-grid">
        <Field label="Fakultas"><input value={faculty} onChange={(e) => setFaculty(e.target.value)} placeholder="Semua fakultas" /></Field>
        <Field label="Gedung"><input value={building} onChange={(e) => setBuilding(e.target.value)} placeholder="Semua gedung" /></Field>
        <Field label="Lokasi detail"><input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Contoh: sayap timur" /></Field>
        <Field label="Kapasitas minimum"><input type="number" min="1" max="10000" value={capacity} onChange={(e) => setCapacity(e.target.value)} placeholder="Semua kapasitas" /></Field>
        <Field label="Fasilitas"><input value={facility} onChange={(e) => setFacility(e.target.value)} placeholder="Contoh: proyektor, Wi-Fi" /></Field>
      </div>
      <div className="filter-panel__actions">
        <Button type="submit"><Search size={16} />Terapkan filter</Button>
        <Button type="button" variant="secondary" onClick={resetFilters}>Reset</Button>
      </div>
    </form>
    <div className="list-summary"><strong>{meta?.total ?? rooms.length} ruangan</strong><span>Informasi lokasi dan fasilitas dari inventaris kampus</span></div>
    {error ? <Notice tone="error">{error}</Notice> : null}
    {loading ? <Loading label="Memuat direktori ruangan…" /> : rooms.length ? (
      <div className="room-grid">
        {rooms.map((room) => <article className="room-card" key={room.id}>
          <Link className="room-card__media" to={(role === "Student" ? "/student/rooms/" : "/admin/rooms/") + room.id}>
            <RoomPhoto photoUrl={room.photo_url} roomName={room.room_name} />
          </Link>
          <div className="room-card__body">
            <div className="room-card__top"><StatusBadge status={room.room_status} /><span><Users size={14} />{room.capacity} orang{room.capacity_estimate ? " · estimasi " + room.capacity_estimate : ""}</span></div>
            <Link className="room-card__title" to={(role === "Student" ? "/student/rooms/" : "/admin/rooms/") + room.id}>{room.room_name}</Link>
            <p>{[room.faculty, room.building, room.floor ? "Lantai " + room.floor : null, room.location_description].filter(Boolean).join(" · ")}</p>
            <div className="chip-list">{room.facilities.slice(0, 4).map((item) => <span key={item}>{item}</span>)}</div>
            {role === "Student" ? <Link className="button button--secondary button--wide" to={"/student/rooms/" + room.id}>Lihat detail</Link> : <Link className="button button--secondary button--wide" to={"/admin/rooms/" + room.id + "/edit"}>Edit ruangan</Link>}
          </div>
        </article>)}
      </div>
    ) : <EmptyState title="Tidak ada ruangan yang cocok" description="Coba ubah kata kunci, fakultas, gedung, kapasitas, atau fasilitas pencarian." icon={<Search size={22} />} />}
  </div>;
}

export function RoomDetailPage({ role }: { role: AppRole }) {
  const { roomId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const [room, setRoom] = useState<Room | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true; setLoading(true); setError("");
    roomApi.get(roomId).then((item) => { if (active) setRoom(item); })
      .catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "Detail ruangan belum dapat dimuat."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [roomId]);

  if (loading) return <Loading label="Memuat detail ruangan…" />;
  if (error) return <Notice tone="error">{error}</Notice>;
  if (!room) return <EmptyState title="Ruangan tidak ditemukan" description="Ruangan mungkin sudah tidak aktif atau tidak tersedia." />;
  const base = role === "Student" ? "/student/rooms" : "/admin/rooms";
  return <div className="page-stack">
    <Link className="back-link" to={base}><ArrowLeft size={16} />Kembali ke direktori</Link>
    <div className="room-detail">
      <div className="room-detail__main">
        <p className="eyebrow">{[room.faculty, room.building, room.floor ? "LANTAI " + room.floor : null].filter(Boolean).join(" · ").toUpperCase()}</p>
        <h1>{room.room_name}</h1>
        <p className="page-description">{room.description || "Informasi ruangan dikelola oleh administrator kampus."}</p>
        <StatusBadge status={room.room_status} />
        <RoomPhoto photoUrl={room.photo_url} roomName={room.room_name} detail />
        <section className="panel">
          <h2>Tentang ruangan ini</h2>
          <p>{room.description || "Belum ada deskripsi tambahan untuk ruangan ini."}</p>
          <h3>Fasilitas</h3>
          {room.facilities.length ? <div className="chip-list">{room.facilities.map((item) => <span key={item}>{item}</span>)}</div> : <p className="muted">Belum ada fasilitas yang dicatat.</p>}
        </section>
      </div>
      <aside className="room-detail__side">
        <div className="room-fact"><Users size={19} /><span>Kapasitas<b>{room.capacity} orang{room.capacity_estimate ? " (estimasi " + room.capacity_estimate + ")" : ""}</b></span></div>
        <div className="room-fact"><Clock3 size={19} /><span>Jam operasional<b>{Object.keys(room.operating_hours || {}).length ? "Mengikuti jadwal terdaftar" : "Belum diatur"}</b></span></div>
        <div className="room-fact"><MapPin size={19} /><span>Lokasi<b>{[room.building, room.floor ? "Lantai " + room.floor : null, room.location_description].filter(Boolean).join(" · ")}</b></span></div>
        {room.faculty ? <div className="room-fact"><Building2 size={19} /><span>Fakultas<b>{room.faculty}</b></span></div> : null}
        {role === "Student" ? <Link className="button button--primary button--wide" to={"/student/rooms/" + room.id + "/book" + (searchParams.toString() ? "?" + searchParams.toString() : "")}>Ajukan reservasi</Link> : <Link className="button button--primary button--wide" to={"/admin/rooms/" + room.id + "/edit"}>Edit ruangan</Link>}
        <p className="muted small">Ketersediaan waktu akan diperiksa kembali sebelum permohonan dikirim.</p>
      </aside>
    </div>
  </div>;
}

export function BookingPage() {
  const { roomId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [room, setRoom] = useState<Room | null>(null);
  const [loadingRoom, setLoadingRoom] = useState(true);
  const [date, setDate] = useState(searchParams.get("date") || localToday());
  const [start, setStart] = useState(searchParams.get("startTime") || "");
  const [end, setEnd] = useState(searchParams.get("endTime") || "");
  const [participants, setParticipants] = useState(searchParams.get("participantCount") || "1");
  const [purpose, setPurpose] = useState("");
  const [notes, setNotes] = useState("");
  const [availability, setAvailability] = useState<AvailabilityResult | null>(null);
  const [checking, setChecking] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);

  useEffect(() => {
    let active = true; setLoadingRoom(true);
    roomApi.get(roomId).then((item) => { if (active) setRoom(item); })
      .catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "Ruangan tidak ditemukan."); })
      .finally(() => { if (active) setLoadingRoom(false); });
    return () => { active = false; };
  }, [roomId]);

  async function checkAvailability() {
    setError(""); setAvailability(null);
    if (!date || !start || !end || Number(participants) < 1) { setError("Lengkapi tanggal, jam mulai, jam selesai, dan jumlah peserta."); return; }
    if (end <= start) { setError("Jam selesai harus lebih akhir dari jam mulai."); return; }
    setChecking(true);
    try {
      const params = new URLSearchParams({
        date, startTime: start, endTime: end, participantCount: String(Number(participants)),
      });
      const result = await roomApi.availability(roomId, params);
      setAvailability(result);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Pemeriksaan ketersediaan gagal."); }
    finally { setChecking(false); }
  }

  async function submitReservation() {
    setSubmitting(true); setError("");
    try {
      const reservation = await reservationApi.create({
        room_id: roomId, purpose: purpose.trim(), date, start_time: start,
        end_time: end, participant_count: Number(participants), notes: notes.trim() || undefined,
      });
      navigate("/student/reservations/" + reservation.id + "?created=1");
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Permohonan belum berhasil dikirim.");
      setAvailability(null);
    } finally { setSubmitting(false); setConfirmOpen(false); }
  }

  if (loadingRoom) return <Loading label="Memuat formulir reservasi…" />;
  if (!room) return <Notice tone="error">{error || "Ruangan tidak ditemukan."}</Notice>;

  return <div className="page-stack">
    <Link className="back-link" to={"/student/rooms/" + roomId}><ArrowLeft size={16} />Kembali ke {room.room_name}</Link>
    <PageTitle eyebrow="YOUR NEXT COLLABORATION STARTS HERE" title="Ajukan reservasi ruangan" description="Isi kebutuhan kegiatan Anda. Permohonan akan ditinjau oleh TU/Admin." />
    <div className="steps-indicator"><span className="is-complete"><Check size={14} />Pilih ruangan</span><i /><span className="is-current">2. Detail permohonan</span><i /><span>3. Tinjauan admin</span></div>
    <div className="booking-layout">
      <form className="panel stack-form" onSubmit={(event) => { event.preventDefault(); if (availability?.available) setConfirmOpen(true); else void checkAvailability(); }}>
        <h2>Detail kegiatan</h2>
        <div className="selected-room"><span className="eyebrow">RUANGAN PILIHAN</span><strong>{room.room_name}</strong><span>{room.building}{room.floor ? " · Lantai " + room.floor : ""} · Kapasitas {room.capacity} orang{room.capacity_estimate ? " (estimasi " + room.capacity_estimate + ")" : ""}</span></div>
        <div className="form-grid">
          <Field label="Tanggal"><input type="date" min={localToday()} value={date} onChange={(e) => { setDate(e.target.value); setAvailability(null); }} required /></Field>
          <Field label="Jumlah peserta"><input type="number" min="1" max={room.capacity} value={participants} onChange={(e) => { setParticipants(e.target.value); setAvailability(null); }} required /></Field>
          <Field label="Jam mulai"><input type="time" value={start} onChange={(e) => { setStart(e.target.value); setAvailability(null); }} required /></Field>
          <Field label="Jam selesai"><input type="time" value={end} onChange={(e) => { setEnd(e.target.value); setAvailability(null); }} required /></Field>
        </div>
        <Field label="Tujuan kegiatan"><input value={purpose} onChange={(e) => setPurpose(e.target.value)} maxLength={240} placeholder="Contoh: Diskusi proyek kelompok" required minLength={3} /></Field>
        <Field label="Catatan tambahan (opsional)"><textarea rows={3} maxLength={5000} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Informasi tambahan untuk administrator" /></Field>
        <Button type="button" variant="secondary" onClick={() => void checkAvailability()} disabled={checking || !date || !start || !end}>
          {checking ? "Memeriksa…" : "Periksa ketersediaan"}
        </Button>
        {availability ? <Notice tone={availability.available ? "success" : "warning"}>
          {availability.available ? "Waktu yang dipilih tercatat tersedia saat pemeriksaan. Backend tetap melakukan validasi ulang saat pengajuan." :
            <><b>Waktu belum tersedia.</b><ul>{availability.reasons.map((reason) => <li key={reason}>{availabilityReasonLabel(reason)}</li>)}</ul></>}
        </Notice> : null}
        {error ? <Notice tone="error">{error}</Notice> : null}
        <Button type="submit" disabled={!availability?.available || !purpose.trim() || submitting} className="button--wide">Tinjau dan kirim permohonan <ArrowRight size={17} /></Button>
      </form>
      <aside className="panel booking-summary">
        <h2>Ringkasan pilihan</h2>
        <strong>{room.room_name}</strong>
        <span>{room.building}</span>
        <div className="summary-line"><span>Tanggal</span><b>{date ? formatDate(date) : "—"}</b></div>
        <div className="summary-line"><span>Waktu</span><b>{start && end ? start + "–" + end + " WIB" : "—"}</b></div>
        <div className="summary-line"><span>Peserta</span><b>{participants || "—"} orang</b></div>
        <p className="muted small">Waktu menggunakan zona Asia/Jakarta (WIB). Pemeriksaan ketersediaan berlaku hanya untuk rentang waktu yang dipilih.</p>
      </aside>
    </div>
    <ConfirmModal open={confirmOpen} title="Kirim permohonan reservasi?" description="Permohonan akan dikirim ke TU/Admin untuk ditinjau. Status dapat dipantau pada menu Reservasi saya." confirmText="Kirim permohonan" loading={submitting} onClose={() => setConfirmOpen(false)} onConfirm={() => void submitReservation()} />
  </div>;
}

export function StudentReservationsPage() {
  const reservationNow = useReservationClock();
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [items, setItems] = useState<Reservation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true; setLoading(true); setError("");
    const params = new URLSearchParams({ page: "1", limit: "100" });
    if (status) params.set("status", status);
    reservationApi.list(params).then((result) => { if (active) setItems(result.items); })
      .catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "Riwayat belum dapat dimuat."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [status]);

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return items;
    return items.filter((item) => (item.room?.room_name || "").toLowerCase().includes(term)
      || item.id.toLowerCase().includes(term) || item.purpose.toLowerCase().includes(term));
  }, [items, search]);

  const tabs = [{ id: "", label: "Semua" }, { id: "PENDING", label: "Menunggu" }, { id: "APPROVED", label: "Disetujui" }, { id: "REJECTED", label: "Ditolak" }];
  return <div className="page-stack">
    <PageTitle eyebrow="YOUR CAMPUS PLANS, IN ONE PLACE" title="Reservasi saya" description="Pantau permohonan, keputusan, dan persiapan sesi kampus Anda." action={<Link className="button button--primary" to="/student/rooms">+ Pesan ruangan</Link>} />
    <div className="panel reservation-filters">
      <div className="segmented-tabs">{tabs.map((tab) => <button key={tab.id || "all"} type="button" className={status === tab.id ? "is-active" : ""} onClick={() => setStatus(tab.id)}>{tab.label}</button>)}</div>
      <Field label="Cari reservasi"><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Cari ruang, tujuan, atau ID reservasi" /></Field>
    </div>
    {error ? <Notice tone="error">{error}</Notice> : null}
    {loading ? <Loading label="Memuat reservasi…" /> : filtered.length ? <div className="card-list">{filtered.map((item) => <ReservationCard key={item.id} item={item} now={reservationNow} showCancel onUpdated={(updated) => setItems((current) => current.map((entry) => entry.id === updated.id ? updated : entry))} />)}</div>
      : <EmptyState title="Belum ada reservasi" description="Belum ada permohonan yang sesuai dengan filter Anda." action={<Link to="/student/rooms" className="button button--primary">Cari ruangan</Link>} icon={<CalendarCheck size={22} />} />}
  </div>;
}

export function ReservationDetailPage({ role }: { role: AppRole }) {
  const { reservationId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const [item, setItem] = useState<Reservation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [success, setSuccess] = useState(searchParams.get("created") === "1");

  useEffect(() => {
    let active = true; setLoading(true);
    reservationApi.get(reservationId).then((result) => { if (active) setItem(result); })
      .catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "Detail reservasi belum dapat dimuat."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [reservationId]);

  async function cancel() {
    setBusy(true); setError("");
    try { const updated = await reservationApi.cancel(reservationId, cancelReason.trim() || undefined); setItem(updated); setCancelOpen(false); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Pembatalan belum berhasil."); }
    finally { setBusy(false); }
  }

  if (loading) return <Loading label="Memuat detail reservasi…" />;
  if (!item) return <Notice tone="error">{error || "Reservasi tidak ditemukan."}</Notice>;
  const canCancel = canCancelReservation(item.status, item.reservation_date);
  const root = role === "Student" ? "/student" : "/admin";
  return <div className="page-stack">
    <Link className="back-link" to={root + "/reservations"}><ArrowLeft size={16} />Kembali ke reservasi</Link>
    <PageTitle eyebrow="RESERVATION DETAILS" title="Detail reservasi" description="Periksa informasi permohonan dan keputusan administrator." action={<StatusBadge status={item.status} />} />
    {success ? <Notice tone="success">Permohonan berhasil dikirim. Status awalnya menunggu peninjauan TU/Admin.</Notice> : null}
    {error ? <Notice tone="error">{error}</Notice> : null}
    {item.rejection_reason ? <Notice tone="warning"><b>Alasan penolakan:</b> {item.rejection_reason}</Notice> : null}
    <div className="detail-layout">
      <section className="panel">
        <p className="eyebrow">RUANGAN</p>
        <h2>{item.room?.room_name || "Ruangan"}</h2>
        <p className="muted">{item.room?.building || "Lokasi kampus"}</p>
        <div className="detail-facts">
          <div><CalendarDays size={17} /><span>Tanggal<b>{formatDate(item.reservation_date)}</b></span></div>
          <div><Clock3 size={17} /><span>Waktu<b>{formatTime(item.start_time)}–{formatTime(item.end_time)} WIB</b></span></div>
          <div><Users size={17} /><span>Peserta<b>{item.participant_count} orang</b></span></div>
        </div>
        <h3>Tujuan kegiatan</h3><p>{item.purpose}</p>
        {item.notes ? <><h3>Catatan</h3><p>{item.notes}</p></> : null}
        <div className="summary-line"><span>ID reservasi</span><b className="mono">{item.id}</b></div>
        <div className="summary-line"><span>Diajukan</span><b>{formatDate(item.submitted_at)}</b></div>
      </section>
      <aside className="panel detail-status-panel">
        <h2>Status permohonan</h2>
        <StatusBadge status={item.status} />
        <p>{item.status === "PENDING" ? "Permohonan sedang menunggu pemeriksaan administrator." :
          item.status === "APPROVED" ? "Permohonan telah disetujui. Pastikan hadir sesuai jadwal." :
          item.status === "REJECTED" ? "Permohonan ditolak oleh administrator." :
          item.status === "CANCELLED" ? "Permohonan telah dibatalkan." : "Sesi reservasi telah selesai."}</p>
        {canCancel ? <Button variant="danger" onClick={() => setCancelOpen(true)} className="button--wide">Batalkan reservasi</Button> : null}
      </aside>
    </div>
    <Modal open={cancelOpen} title="Batalkan reservasi?" description="Pembatalan akan diproses oleh layanan RuangKampus." onClose={() => setCancelOpen(false)} closeDisabled={busy}>
      <Field label="Alasan pembatalan (opsional)"><textarea rows={3} value={cancelReason} onChange={(e) => setCancelReason(e.target.value)} maxLength={2000} /></Field>
      <div className="modal-actions"><Button variant="secondary" onClick={() => setCancelOpen(false)} disabled={busy}>Kembali</Button><Button variant="danger" onClick={() => void cancel()} disabled={busy}>{busy ? "Memproses…" : "Ya, batalkan"}</Button></div>
    </Modal>
  </div>;
}

const notificationTitles: Record<string, string> = {
  RESERVATION_NEW: "Pengajuan reservasi baru",
  RESERVATION_APPROVED: "Reservasi disetujui",
  RESERVATION_REJECTED: "Reservasi ditolak",
  RESERVATION_CANCELLED: "Reservasi dibatalkan",
  RESERVATION_CANCELLED_BY_STUDENT: "Reservasi dibatalkan mahasiswa",
  RESERVATION_COMPLETED: "Reservasi selesai",
};

function localizedNotificationMessage(item: AppNotification): string {
  const legacy = item.message;
  let match: RegExpMatchArray | null = null;
  switch (item.notification_type) {
    case "RESERVATION_NEW":
      match = legacy.match(/^A new request was submitted for (.+) on (\d{4}-\d{2}-\d{2})\.$/);
      return match ? `Ada pengajuan reservasi baru untuk ${match[1]} pada ${formatDate(match[2])}.` : legacy;
    case "RESERVATION_APPROVED":
      match = legacy.match(/^Your reservation for (.+) has been approved\.$/);
      return match ? `Reservasi ${match[1]} telah disetujui oleh Admin.` : legacy;
    case "RESERVATION_REJECTED":
      match = legacy.match(/^Your reservation was rejected\. Reason: (.*)$/);
      return match ? `Pengajuan reservasi kamu ditolak. Alasan: ${match[1]}` : legacy;
    case "RESERVATION_CANCELLED":
      match = legacy.match(/^Your reservation for (.+) was cancelled by the administrator\.$/);
      return match ? `Reservasi ${match[1]} dibatalkan oleh Admin.` : legacy;
    case "RESERVATION_CANCELLED_BY_STUDENT":
      match = legacy.match(/^A reservation for (.+) on (\d{4}-\d{2}-\d{2}) was cancelled by the applicant\.$/);
      return match ? `Reservasi ${match[1]} pada ${formatDate(match[2])} dibatalkan oleh mahasiswa.` : legacy;
    default:
      return legacy;
  }
}

export function NotificationsPage({ role }: { role: AppRole }) {
  const [items, setItems] = useState<AppNotification[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState("");
  const [retryingId, setRetryingId] = useState("");
  const [markingAll, setMarkingAll] = useState(false);
  const [filter, setFilter] = useState<"all" | "unread">("all");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [allTotal, setAllTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [unreadTotal, setUnreadTotal] = useState(0);
  const root = role === "Student" ? "/student" : "/admin";
  const pageSize = 20;

  useEffect(() => {
    let active = true;
    const loadFirstPage = async (silent = false) => {
      if (!silent) { setLoading(true); setError(""); }
      try {
        const params = new URLSearchParams({ page: "1", limit: String(pageSize) });
        if (filter === "unread") params.set("unreadOnly", "true");
        const [result, allNotifications, unread] = await Promise.all([
          notificationApi.list(params),
          notificationApi.list(new URLSearchParams({ page: "1", limit: "1" })),
          notificationApi.list(new URLSearchParams({ unreadOnly: "true", page: "1", limit: "1" })),
        ]);
        if (!active) return;
        setItems((current) => {
          if (!silent) return result.items;
          const firstPageIds = new Set(result.items.map((item) => item.id));
          const olderLoadedItems = current.filter((item) => !firstPageIds.has(item.id));
          return [...result.items, ...olderLoadedItems].sort(
            (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
          );
        });
        setTotal(result.meta?.total ?? result.items.length);
        setAllTotal(allNotifications.meta?.total ?? allNotifications.items.length);
        setTotalPages(result.meta?.total_pages ?? 1);
        setUnreadTotal(unread.meta?.total ?? unread.items.filter((item) => !item.read_at).length);
        setPage((current) => silent ? current : 1);
      } catch (cause) {
        if (active && !silent) setError(cause instanceof Error ? cause.message : "Notifikasi belum dapat dimuat.");
      } finally {
        if (active && !silent) setLoading(false);
      }
    };
    void loadFirstPage();
    const refreshWhenVisible = () => {
      if (document.visibilityState === "visible") void loadFirstPage(true);
    };
    const interval = window.setInterval(() => void loadFirstPage(true), 15_000);
    window.addEventListener("focus", refreshWhenVisible);
    document.addEventListener("visibilitychange", refreshWhenVisible);
    window.addEventListener("rk-notifications-updated", refreshWhenVisible);
    return () => {
      active = false;
      window.clearInterval(interval);
      window.removeEventListener("focus", refreshWhenVisible);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
      window.removeEventListener("rk-notifications-updated", refreshWhenVisible);
    };
  }, [filter]);

  async function loadMore() {
    if (loadingMore || page >= totalPages) return;
    const nextPage = page + 1;
    setLoadingMore(true);
    setError("");
    try {
      const params = new URLSearchParams({ page: String(nextPage), limit: String(pageSize) });
      if (filter === "unread") params.set("unreadOnly", "true");
      const result = await notificationApi.list(params);
      setItems((current) => {
        const known = new Set(current.map((item) => item.id));
        return [...current, ...result.items.filter((item) => !known.has(item.id))];
      });
      setPage(nextPage);
      setTotal(result.meta?.total ?? total);
      setTotalPages(result.meta?.total_pages ?? totalPages);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Notifikasi berikutnya belum dapat dimuat.");
    } finally {
      setLoadingMore(false);
    }
  }

  async function markRead(id: string) {
    setBusyId(id);
    setError("");
    try {
      const updated = await notificationApi.markRead(id);
      setItems((current) => filter === "unread" ? current.filter((item) => item.id !== id) : current.map((item) => item.id === id ? updated : item));
      setUnreadTotal((current) => Math.max(0, current - 1));
      setTotal((current) => filter === "unread" ? Math.max(0, current - 1) : current);
      window.dispatchEvent(new Event("rk-notifications-updated"));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Notifikasi gagal diperbarui.");
    } finally {
      setBusyId("");
    }
  }

  async function markAllRead() {
    setMarkingAll(true);
    setError("");
    try {
      const result = await notificationApi.markAllRead();
      const readAt = result.read_at || new Date().toISOString();
      setItems((current) => filter === "unread" ? [] : current.map((item) => ({ ...item, read_at: item.read_at || readAt })));
      if (filter === "unread") setTotal(0);
      setUnreadTotal(0);
      window.dispatchEvent(new Event("rk-notifications-updated"));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Semua notifikasi belum berhasil ditandai dibaca.");
    } finally {
      setMarkingAll(false);
    }
  }

  async function retryEmail(id: string) {
    setRetryingId(id);
    setError("");
    try {
      const updated = await notificationApi.retryEmail(id);
      setItems((current) => current.map((item) => item.id === id ? updated : item));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Pengiriman email belum berhasil dicoba ulang.");
    } finally {
      setRetryingId("");
    }
  }

  const emailStatusLabel = (status: string) => ({
    SENT: "Diterima penyedia email",
    LOCAL_MAILBOX_WRITTEN: "Tersimpan di kotak lokal",
    FAILED: "Gagal dikirim",
    ATTEMPTED: "Sedang diproses",
    NOT_CONFIGURED: "Email tidak diaktifkan",
  }[status] || "Belum dikirim");

  return <div className="page-stack">
    <PageTitle
      eyebrow="PEMBARUAN AKUN & RESERVASI"
      title="Notifikasi"
      description="Pantau setiap perubahan status reservasi dan informasi penting akun."
      action={unreadTotal > 0 ? <Button variant="secondary" onClick={() => void markAllRead()} disabled={markingAll}>{markingAll ? "Memproses…" : "Tandai semua dibaca"}</Button> : undefined}
    />
    <div className="panel notification-toolbar">
      <div className="segmented-tabs" aria-label="Filter notifikasi">
        <button type="button" className={filter === "all" ? "is-active" : ""} aria-pressed={filter === "all"} onClick={() => setFilter("all")}>Semua ({allTotal})</button>
        <button type="button" className={filter === "unread" ? "is-active" : ""} aria-pressed={filter === "unread"} onClick={() => setFilter("unread")}>Belum dibaca ({unreadTotal})</button>
      </div>
      <span className="muted small">Diperbarui otomatis setiap 15 detik · Status email menunjukkan hasil penyedia, bukan konfirmasi masuk ke kotak masuk.</span>
    </div>
    {error ? <Notice tone="error">{error}</Notice> : null}
    {loading ? <Loading label="Memuat notifikasi…" /> : items.length ? <>
      <div className="card-list">
        {items.map((item) => {
          const actionUrl = item.action_url?.startsWith("/") && !item.action_url.startsWith("//") ? item.action_url : null;
          const emailFailed = item.email_delivery_status === "FAILED";
          const canRetryEmail = emailFailed && item.email_attempt_count < 3;
          return <article className={"notification-card" + (!item.read_at ? " is-unread" : "")} key={item.id}>
            <div className="notification-card__icon"><Bell size={18} /></div>
            <div className="notification-card__content">
              <div className="notification-card__heading">
                <strong>{notificationTitles[item.notification_type] || item.title}</strong>
                <time dateTime={item.created_at}>{formatDateTime(item.created_at)}</time>
              </div>
              <p>{localizedNotificationMessage(item)}</p>
              <div className="notification-card__delivery">
                <span>Aplikasi: Tersimpan</span>
                <span className={emailFailed ? "notification-card__email--failed" : ""}>Email: {emailStatusLabel(item.email_delivery_status)}{item.email_attempt_count > 0 ? ` · ${item.email_attempt_count}/3 percobaan` : ""}</span>
                {item.email_sent_at ? <span>Dikirim {formatDateTime(item.email_sent_at)}</span> : null}
              </div>
              <div className="notification-card__actions">
                {actionUrl ? <Link className="text-link" to={actionUrl}>Lihat detail reservasi <ArrowRight size={14} /></Link> : null}
                {canRetryEmail ? <Button variant="secondary" disabled={retryingId === item.id} onClick={() => void retryEmail(item.id)}>{retryingId === item.id ? "Mencoba…" : "Coba kirim email lagi"}</Button> : null}
              </div>
            </div>
            {!item.read_at ? <Button variant="secondary" disabled={busyId === item.id} onClick={() => void markRead(item.id)}>{busyId === item.id ? "Memproses…" : "Tandai dibaca"}</Button> : <span className="read-mark"><Check size={15} />Dibaca</span>}
          </article>;
        })}
      </div>
      {page < totalPages ? <div className="notification-load-more"><Button variant="secondary" onClick={() => void loadMore()} disabled={loadingMore}>{loadingMore ? "Memuat…" : "Muat lebih banyak"}</Button></div> : null}
    </> : <EmptyState title={filter === "unread" ? "Semua notifikasi sudah dibaca" : "Belum ada notifikasi"} description={filter === "unread" ? "Tidak ada notifikasi yang menunggu perhatian." : "Pembaruan reservasi dan informasi akun akan muncul di sini."} icon={<Bell size={22} />} />}
    <Link className="button button--primary notification-reservation-link" to={root + "/reservations"}>Lihat reservasi</Link>
  </div>;
}

export function ProfilePage({ role }: { role: AppRole }) {
  const { user, replaceUser, logout } = useAuth();
  const [profile, setProfile] = useState<AuthUser | null>(user);
  const [name, setName] = useState(user?.name || "");
  const [email, setEmail] = useState(user?.email || "");
  const [phone, setPhone] = useState(user?.phone || "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">(document.documentElement.dataset.theme === "dark" ? "dark" : "light");
  useEffect(() => {
    const syncTheme = () => setTheme(document.documentElement.dataset.theme === "dark" ? "dark" : "light");
    window.addEventListener("rk-theme-change", syncTheme);
    return () => window.removeEventListener("rk-theme-change", syncTheme);
  }, []);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const navigate = useNavigate();
  const accountRoot = role === "Student" ? "/student" : "/admin";

  useEffect(() => {
    let active = true;
    profileApi.me().then((item) => { if (!active) return; setProfile(item); setName(item.name); setEmail(item.email); setPhone(item.phone || ""); replaceUser(item); })
      .catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "Profil belum dapat dimuat."); });
    return () => { active = false; };
  }, [replaceUser]);

  async function saveProfile(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError(""); setMessage("");
    try {
      const updated = await profileApi.update({ name: name.trim(), email: email.trim(), phone: phone.trim() || null });
      setProfile(updated); setName(updated.name); setEmail(updated.email); setPhone(updated.phone || "");
      replaceUser(updated); setMessage("Profil berhasil diperbarui.");
    }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Profil belum berhasil disimpan."); }
    finally { setSaving(false); }
  }

  async function savePassword(event: FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    if (newPassword !== confirmPassword) {
      setError("Konfirmasi password baru tidak cocok.");
      return;
    }
    setSaving(true);
    try {
      await profileApi.changePassword(currentPassword, newPassword);
      setMessage("Password berhasil diubah. Silakan masuk kembali.");
      await logout(); navigate("/login", { replace: true });
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Password belum berhasil diubah."); }
    finally { setSaving(false); }
  }

  function changeTheme(next: "light" | "dark") {
    setTheme(next);
    document.documentElement.dataset.theme = next;
    localStorage.setItem("rk-theme", next);
    window.dispatchEvent(new Event("rk-theme-change"));
  }
  const initials = initialsFromName(profile?.name);

  return <div className="page-stack">
    <PageTitle eyebrow="YOUR ACCOUNT" title="Profil" description="Kelola informasi akun dan preferensi tampilan Anda." />
    {error ? <Notice tone="error">{error}</Notice> : null}
    {message ? <Notice tone="success">{message}</Notice> : null}
    <section className="panel profile-summary"><span className="avatar avatar--large">{initials}</span><div><h2>{profile?.name || "Pengguna"}</h2><p>{role === "Student" ? "Mahasiswa" : "Staff Sekretariat"} · {profile?.account_status === "ACTIVE" ? "Aktif" : "Nonaktif"}</p><small>{profile?.email}</small></div></section>
    <div className="profile-grid">
      <form className="panel stack-form" onSubmit={saveProfile}>
        <h2>Informasi profil</h2>
        <Field label="Nama lengkap"><input value={name} onChange={(e) => setName(e.target.value)} minLength={2} maxLength={160} required /></Field>
        <Field label="Email"><input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} maxLength={320} required /></Field>
        <Field label="Nomor telepon"><input type="tel" autoComplete="tel" value={phone} onChange={(e) => setPhone(e.target.value)} maxLength={40} /></Field>
        {role === "Staff Sekretariat"
          ? <Field label="Username admin"><input value={profile?.student_identifier || ""} autoComplete="username" disabled readOnly /></Field>
          : profile?.student_identifier
            ? <Field label="Nomor induk mahasiswa"><input value={profile.student_identifier} disabled readOnly /></Field>
            : null}
        <Button type="submit" disabled={saving}>{saving ? "Menyimpan…" : "Simpan perubahan"}</Button>
      </form>
      <div className="stack-form">
        <section className="panel">
          <h2>Tampilan</h2><p className="muted">Pilih mode terang atau gelap.</p>
          <div className="segmented-tabs theme-selector">
            <button type="button" className={theme === "light" ? "is-active" : ""} aria-pressed={theme === "light"} onClick={() => changeTheme("light")}>☀ Terang</button>
            <button type="button" className={theme === "dark" ? "is-active" : ""} aria-pressed={theme === "dark"} onClick={() => changeTheme("dark")}>◐ Gelap</button>
          </div>
        </section>
        <form className="panel stack-form" onSubmit={savePassword}>
          <h2>Ubah password</h2>
          <Field label="Password saat ini">
            <div className="input-with-action">
              <input type={showCurrentPassword ? "text" : "password"} autoComplete="current-password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} required />
              <button
                className="field-action"
                type="button"
                aria-label={showCurrentPassword ? "Sembunyikan password saat ini" : "Tampilkan password saat ini"}
                aria-pressed={showCurrentPassword}
                onClick={() => setShowCurrentPassword((visible) => !visible)}
              >
                {showCurrentPassword ? <EyeOff size={17} aria-hidden="true" /> : <Eye size={17} aria-hidden="true" />}
              </button>
            </div>
          </Field>
          <Field label="Password baru" hint="Minimal 8 karakter.">
            <div className="input-with-action">
              <input type={showNewPassword ? "text" : "password"} minLength={8} maxLength={128} autoComplete="new-password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required />
              <button
                className="field-action"
                type="button"
                aria-label={showNewPassword ? "Sembunyikan password baru" : "Tampilkan password baru"}
                aria-pressed={showNewPassword}
                onClick={() => setShowNewPassword((visible) => !visible)}
              >
                {showNewPassword ? <EyeOff size={17} aria-hidden="true" /> : <Eye size={17} aria-hidden="true" />}
              </button>
            </div>
          </Field>
          <Field label="Konfirmasi password baru">
            <div className="input-with-action">
              <input type={showConfirmPassword ? "text" : "password"} minLength={8} maxLength={128} autoComplete="new-password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required />
              <button
                className="field-action"
                type="button"
                aria-label={showConfirmPassword ? "Sembunyikan konfirmasi password" : "Tampilkan konfirmasi password"}
                aria-pressed={showConfirmPassword}
                onClick={() => setShowConfirmPassword((visible) => !visible)}
              >
                {showConfirmPassword ? <EyeOff size={17} aria-hidden="true" /> : <Eye size={17} aria-hidden="true" />}
              </button>
            </div>
          </Field>
          <Button type="submit" variant="secondary" disabled={saving}>Ubah password</Button>
        </form>
      </div>
    </div>
    <Link className="panel profile-link" to={accountRoot + "/assistant"}><span><b>Bantuan & FAQ</b><small>Informasi alur reservasi dan aturan layanan</small></span><ArrowRight size={18} /></Link>
  </div>;
}

export function AssistantUnavailablePage({ role }: { role: AppRole }) {
  return <div className="page-stack">
    <PageTitle eyebrow="SMART CAMPUS SUPPORT" title={role === "Student" ? "AI Room Assistant" : "AI Facility Assistant"} description="Bantuan informasi ruang dan proses reservasi." />
    <div className="panel assistant-notice">
      <div className="assistant-notice__icon"><InfoIcon /></div>
      <h2>Asisten AI belum tersedia pada MVP</h2>
      <p>Desain Figma memuat halaman assistant, tetapi API RuangKampus saat ini belum menyediakan endpoint atau provider AI yang tervalidasi. Halaman ini tidak akan menghasilkan jawaban atau rekomendasi yang dibuat-buat.</p>
      <Link className="button button--primary" to={role === "Student" ? "/student/rooms" : "/admin/reservations"}>{role === "Student" ? "Cari ruangan" : "Tinjau permohonan"}</Link>
    </div>
  </div>;
}
function InfoIcon() { return <XCircle size={28} />; }

export function NotFoundPage() {
  return <main className="not-found"><div><p className="eyebrow">404 · RUANGKAMPUS</p><h1>Halaman tidak ditemukan</h1><p className="muted">Alamat yang Anda buka tidak tersedia.</p><Link className="button button--primary" to="/">Kembali ke halaman utama</Link></div></main>;
}