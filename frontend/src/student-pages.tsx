import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  ArrowLeft, ArrowRight, Bell, Building2, CalendarDays, CalendarCheck, Check, Clock3, MapPin,
  Search, Users, XCircle,
} from "lucide-react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";
import {
  ApiError, apiAssetUrl, availabilityReasonLabel, dashboardApi, formatDate, formatTime, localToday,
  notificationApi, profileApi, reservationApi, roomApi, statusLabel,
} from "./api";
import { useAuth } from "./auth";
import type { AppNotification, AppRole, AuthUser, AvailabilityResult, Reservation, Room } from "./types";
import { PageTitle } from "./layout";
import { Button, ConfirmModal, EmptyState, Field, Loading, Modal, Notice, PageSection, StatusBadge } from "./ui";

function usePageError() {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return { error, setError, busy, setBusy };
}

function ReservationCard({ item }: { item: Reservation }) {
  return (
    <Link className="reservation-card" to={"/student/reservations/" + item.id}>
      <div className="reservation-card__top">
        <span className="reservation-card__id">RK-{item.id.slice(0, 8).toUpperCase()}</span>
        <StatusBadge status={item.status} />
      </div>
      <strong>{item.room?.room_name || "Ruangan"}</strong>
      <span className="muted">{item.room?.building || "Lokasi kampus belum tersedia"}</span>
      <div className="reservation-card__meta">
        <span><CalendarDays size={15} />{formatDate(item.reservation_date)}</span>
        <span><Clock3 size={15} />{formatTime(item.start_time)}–{formatTime(item.end_time)}</span>
      </div>
      <p>{item.purpose}</p>
    </Link>
  );
}


function RoomPhoto({ photoUrl, roomName, detail = false }: {
  photoUrl: string | null;
  roomName: string;
  detail?: boolean;
}) {
  const [failed, setFailed] = useState(false);

  useEffect(() => { setFailed(false); }, [photoUrl]);

  if (!photoUrl || failed) {
    return <div className={detail ? "room-detail__image room-detail__image--empty" : "room-card__placeholder"}>
      <Building2 size={detail ? 48 : 34} aria-hidden="true" />
    </div>;
  }

  return <img
    className={detail ? "room-detail__image" : undefined}
    src={apiAssetUrl(photoUrl)}
    alt={"Foto " + roomName}
    loading="lazy"
    decoding="async"
    onError={() => setFailed(true)}
  />;
}

export function StudentDashboardPage() {
  const { user } = useAuth();
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
        {recent.length ? <div className="card-list">{recent.slice(0, 3).map((item) => <ReservationCard key={item.id} item={item} />)}</div>
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
  const [participants, setParticipants] = useState("1");
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
    {loading ? <Loading label="Memuat reservasi…" /> : filtered.length ? <div className="card-list">{filtered.map((item) => <ReservationCard key={item.id} item={item} />)}</div>
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
  const canCancel = (item.status === "PENDING" || item.status === "APPROVED") && item.reservation_date >= localToday();
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
    <Modal open={cancelOpen} title="Batalkan reservasi?" description="Pembatalan akan diproses oleh layanan RuangKampus." onClose={() => setCancelOpen(false)}>
      <Field label="Alasan pembatalan (opsional)"><textarea rows={3} value={cancelReason} onChange={(e) => setCancelReason(e.target.value)} maxLength={2000} /></Field>
      <div className="modal-actions"><Button variant="secondary" onClick={() => setCancelOpen(false)} disabled={busy}>Kembali</Button><Button variant="danger" onClick={() => void cancel()} disabled={busy}>{busy ? "Memproses…" : "Ya, batalkan"}</Button></div>
    </Modal>
  </div>;
}

export function NotificationsPage({ role }: { role: AppRole }) {
  const [items, setItems] = useState<AppNotification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState("");
  const root = role === "Student" ? "/student" : "/admin";
  useEffect(() => {
    let active = true; setLoading(true);
    notificationApi.list(new URLSearchParams({ page: "1", limit: "100" }))
      .then((result) => { if (active) setItems(result.items); })
      .catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "Notifikasi belum dapat dimuat."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
  async function markRead(id: string) {
    setBusyId(id);
    try { const updated = await notificationApi.markRead(id); setItems((current) => current.map((item) => item.id === id ? updated : item)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Notifikasi gagal diperbarui."); }
    finally { setBusyId(""); }
  }
  return <div className="page-stack">
    <PageTitle eyebrow="UPDATES" title="Notifikasi" description="Tetap terhubung dengan informasi terbaru reservasi ruangan." />
    {error ? <Notice tone="error">{error}</Notice> : null}
    {loading ? <Loading label="Memuat notifikasi…" /> : items.length ? <div className="card-list">
      {items.map((item) => <article className={"notification-card" + (!item.read_at ? " is-unread" : "")} key={item.id}>
        <div className="notification-card__icon"><Bell size={18} /></div>
        <div className="notification-card__content"><div className="notification-card__heading"><strong>{item.title}</strong><span>{formatDate(item.created_at)}</span></div><p>{item.message}</p>
          <small>In-app: {item.delivery_status.replaceAll("_", " ").toLowerCase()} · Email: {item.email_delivery_status.replaceAll("_", " ").toLowerCase()}</small>
        </div>
        {!item.read_at ? <Button variant="secondary" disabled={busyId === item.id} onClick={() => void markRead(item.id)}>Tandai dibaca</Button> : <span className="read-mark"><Check size={15} />Dibaca</span>}
      </article>)}
    </div> : <EmptyState title="Belum ada notifikasi" description="Pembaruan permohonan dan informasi akun akan muncul di sini." icon={<Bell size={22} />} />}
    <Link className="button button--primary" to={root + (role === "Student" ? "/reservations" : "/reservations")}>Lihat reservasi</Link>
  </div>;
}

export function ProfilePage({ role }: { role: AppRole }) {
  const { user, replaceUser, logout } = useAuth();
  const [profile, setProfile] = useState<AuthUser | null>(user);
  const [name, setName] = useState(user?.name || "");
  const [phone, setPhone] = useState(user?.phone || "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [theme, setTheme] = useState<"light" | "dark">(document.documentElement.dataset.theme === "dark" ? "dark" : "light");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const navigate = useNavigate();
  const accountRoot = role === "Student" ? "/student" : "/admin";

  useEffect(() => {
    let active = true;
    profileApi.me().then((item) => { if (!active) return; setProfile(item); setName(item.name); setPhone(item.phone || ""); replaceUser(item); })
      .catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "Profil belum dapat dimuat."); });
    return () => { active = false; };
  }, [replaceUser]);

  async function saveProfile(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError(""); setMessage("");
    try { const updated = await profileApi.update({ name: name.trim(), phone: phone.trim() || null }); setProfile(updated); replaceUser(updated); setMessage("Profil berhasil diperbarui."); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Profil belum berhasil disimpan."); }
    finally { setSaving(false); }
  }

  async function savePassword(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError(""); setMessage("");
    try {
      await profileApi.changePassword(currentPassword, newPassword);
      setMessage("Password berhasil diubah. Silakan masuk kembali.");
      await logout(); navigate("/login", { replace: true });
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Password belum berhasil diubah."); }
    finally { setSaving(false); }
  }

  function changeTheme(next: "light" | "dark") {
    setTheme(next); document.documentElement.dataset.theme = next;
    localStorage.setItem("rk-theme", next);
  }
  const initials = (profile?.name || "RK").split(/\\s+/).slice(0, 2).map((p) => p[0] || "").join("").toUpperCase();

  return <div className="page-stack">
    <PageTitle eyebrow="YOUR ACCOUNT" title="Profil" description="Kelola informasi akun dan preferensi tampilan Anda." />
    {error ? <Notice tone="error">{error}</Notice> : null}
    {message ? <Notice tone="success">{message}</Notice> : null}
    <section className="panel profile-summary"><span className="avatar avatar--large">{initials}</span><div><h2>{profile?.name || "Pengguna"}</h2><p>{role === "Student" ? "Mahasiswa" : "TU / Administrator"} · {profile?.account_status === "ACTIVE" ? "Aktif" : "Nonaktif"}</p><small>{profile?.email}</small></div></section>
    <div className="profile-grid">
      <form className="panel stack-form" onSubmit={saveProfile}>
        <h2>Informasi profil</h2>
        <Field label="Nama lengkap"><input value={name} onChange={(e) => setName(e.target.value)} minLength={2} maxLength={160} required /></Field>
        <Field label="Email"><input type="email" value={profile?.email || ""} readOnly disabled /></Field>
        <Field label="Nomor telepon"><input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} maxLength={40} /></Field>
        {profile?.student_identifier ? <Field label="Nomor induk mahasiswa"><input value={profile.student_identifier} disabled readOnly /></Field> : null}
        <Button type="submit" disabled={saving}>{saving ? "Menyimpan…" : "Simpan perubahan"}</Button>
      </form>
      <div className="stack-form">
        <section className="panel">
          <h2>Appearance</h2><p className="muted">Pilih Light atau Dark mode.</p>
          <div className="segmented-tabs theme-selector">
            <button type="button" className={theme === "light" ? "is-active" : ""} onClick={() => changeTheme("light")}>☀ Light</button>
            <button type="button" className={theme === "dark" ? "is-active" : ""} onClick={() => changeTheme("dark")}>◐ Dark</button>
          </div>
        </section>
        <form className="panel stack-form" onSubmit={savePassword}>
          <h2>Ubah password</h2>
          <Field label="Password saat ini"><input type="password" autoComplete="current-password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} required /></Field>
          <Field label="Password baru" hint="Minimal 10 karakter sesuai validasi server."><input type="password" minLength={10} autoComplete="new-password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required /></Field>
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