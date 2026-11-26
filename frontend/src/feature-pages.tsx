import { useEffect, useState, type FormEvent } from "react";
import {
  ArrowRight, Bot, Building2, CalendarDays, CheckCircle2, Clock3,
  Search, Send, Sparkles, Users, WandSparkles,
} from "lucide-react";
import { Link, useSearchParams } from "react-router";
import {
  apiAssetUrl, availabilityReasonLabel, discoveryApi, formatDate, formatTime, localToday, roomApi,
} from "./api";
import type {
  AlternativeSlot, AlternativeSlotsResult, AssistantChatResult,
  AvailabilityResult, Room,
} from "./types";
import { PageTitle } from "./layout";
import { Button, EmptyState, Field, Loading, Notice, PageSection } from "./ui";

function makeAvailabilityParams(date: string, start: string, end: string, participants: string) {
  return new URLSearchParams({
    date, startTime: start, endTime: end, participantCount: String(Number(participants)),
  });
}
function roomBookingPath(roomId: string, date: string, start: string, end: string, participants = "1") {
  const params = makeAvailabilityParams(date, start, end, participants);
  return "/student/rooms/" + encodeURIComponent(roomId) + "/book?" + params.toString();
}
function roomDetailPath(roomId: string, date: string, start: string, end: string, participants: string) {
  const params = makeAvailabilityParams(date, start, end, participants);
  return "/student/rooms/" + encodeURIComponent(roomId) + "?" + params.toString();
}
function AvailabilityRoomPhoto({ room }: { room: Room }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [room.photo_url]);
  if (!room.photo_url || failed) return <span className="room-card__placeholder"><Building2 size={34} aria-hidden="true" /></span>;
  return <img src={apiAssetUrl(room.photo_url)} alt={"Foto " + room.room_name} loading="lazy" decoding="async" onError={() => setFailed(true)} />;
}
function roomLocation(room: Room) {
  return [room.faculty, room.building, room.floor ? "Lantai " + room.floor : null, room.location_description]
    .filter(Boolean).join(" · ");
}
function AlternativeCard({ slot }: { slot: AlternativeSlot }) {
  return <article className="recommendation-card">
    <div className="recommendation-card__top">
      <span className="status-badge status-badge--active"><CheckCircle2 size={13} />Tersedia saat dicek</span>
      <span className="muted small">{slot.duration_minutes} menit</span>
    </div>
    <h3>{slot.room.room_name}</h3>
    <p className="muted">{roomLocation(slot.room) || slot.room.building}</p>
    <div className="recommendation-card__facts">
      <span><CalendarDays size={15} />{formatDate(slot.date)}</span>
      <span><Clock3 size={15} />{formatTime(slot.start_time)}–{formatTime(slot.end_time)} WIB</span>
      <span><Users size={15} />{slot.participant_count} peserta</span>
    </div>
    <div className="chip-list">{slot.room.facilities.slice(0, 4).map((item) => <span key={item}>{item}</span>)}</div>
    <div className="chip-list">{slot.match_reasons.map((reason) => <span key={reason}>{reason.replaceAll("_", " ").toLowerCase()}</span>)}</div>
    <Link className="button button--primary button--wide" to={roomBookingPath(slot.room.id, slot.date, slot.start_time, slot.end_time, String(slot.participant_count))}>
      Pilih slot ini <ArrowRight size={16} />
    </Link>
  </article>;
}

export function StudentRoomAvailabilityPage() {
  const [searchParams] = useSearchParams();
  const [date, setDate] = useState(searchParams.get("date") || localToday());
  const [start, setStart] = useState(searchParams.get("startTime") || "10:00");
  const [end, setEnd] = useState(searchParams.get("endTime") || "12:00");
  const [participants, setParticipants] = useState(searchParams.get("participantCount") || "1");
  const [faculty, setFaculty] = useState(searchParams.get("faculty") || "");
  const [building, setBuilding] = useState(searchParams.get("building") || "");
  const [location, setLocation] = useState(searchParams.get("location") || "");
  const [facility, setFacility] = useState(searchParams.get("facility") || "");
  const [available, setAvailable] = useState<Room[]>([]);
  const [blocked, setBlocked] = useState<Array<{ room: Room; result: AvailabilityResult }>>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [request, setRequest] = useState<{ filters: URLSearchParams; timeParams: URLSearchParams; date: string; start: string; end: string; participants: string } | null>(null);

  async function searchAvailability(event: FormEvent) {
    event.preventDefault();
    setError(""); setAvailable([]); setBlocked([]); setSearched(false);
    if (!date || !start || !end || end <= start || Number(participants) < 1) {
      setError("Periksa kembali tanggal, jam, dan jumlah peserta. Jam selesai harus setelah jam mulai.");
      return;
    }
    const filters = new URLSearchParams({ limit: "30", sortBy: "room_name", sortOrder: "asc", status: "ACTIVE" });
    if (faculty.trim()) filters.set("faculty", faculty.trim());
    if (building.trim()) filters.set("building", building.trim());
    if (location.trim()) filters.set("location", location.trim());
    filters.set("min_capacity", String(Number(participants)));
    if (facility.trim()) filters.append("facilities", facility.trim());
    const timeParams = new URLSearchParams(filters);
    makeAvailabilityParams(date, start, end, participants).forEach((value, key) => timeParams.set(key, value));
    setPage(1);
    setRequest({ filters, timeParams, date, start, end, participants });
  }

  useEffect(() => {
    if (!request) return;
    let active = true;
    setLoading(true); setError(""); setAvailable([]); setBlocked([]);
    const query = new URLSearchParams(request.timeParams);
    query.set("page", String(page));
    roomApi.list(query).then(async (result) => {
      if (!active) return;
      setAvailable(result.items);
      setTotalPages(result.meta?.total_pages || 1);
      if (!result.items.length && page === 1) {
        const candidateParams = new URLSearchParams(request.filters);
        candidateParams.set("page", "1");
        const candidates = await roomApi.list(candidateParams);
        const checks = await Promise.allSettled(candidates.items.slice(0, 15).map(async (room) => ({
          room, result: await roomApi.availability(room.id, makeAvailabilityParams(request.date, request.start, request.end, request.participants)),
        })));
        if (!active) return;
        setBlocked(checks.filter((item): item is PromiseFulfilledResult<{ room: Room; result: AvailabilityResult }> => item.status === "fulfilled")
          .map((item) => item.value).filter((item) => !item.result.available));
      }
      if (active) setSearched(true);
    }).catch((cause) => {
      if (active) setError(cause instanceof Error ? cause.message : "Ketersediaan ruangan belum dapat diperiksa.");
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [request, page]);

  const alternativeQuery = "/student/alternatives?date=" + encodeURIComponent(date)
    + "&durationMinutes=" + Math.max(15, Math.round((new Date("1970-01-01T" + end).getTime() - new Date("1970-01-01T" + start).getTime()) / 60000))
    + "&participantCount=" + encodeURIComponent(participants)
    + "&faculty=" + encodeURIComponent(faculty)
    + "&building=" + encodeURIComponent(building)
    + "&facility=" + encodeURIComponent(facility)
    + "&preferredStartTime=" + encodeURIComponent(start);

  return <div className="page-stack">
    <PageTitle eyebrow="KETERSEDIAAN RUANG KAMPUS" title="Cek ketersediaan ruangan"
      description="Pilih tanggal, waktu, dan kebutuhan ruang. Hasil diperiksa berdasarkan jadwal, kapasitas, jam operasional, pemeliharaan, dan reservasi aktif."
      action={<Link className="button button--secondary" to="/student/rooms"><Search size={16} />Direktori ruangan</Link>} />
    <form className="panel stack-form" onSubmit={searchAvailability}>
      <h2>Waktu dan kebutuhan kegiatan</h2>
      <div className="form-grid">
        <Field label="Tanggal kegiatan"><input type="date" min={localToday()} value={date} onChange={(e) => setDate(e.target.value)} required /></Field>
        <Field label="Jumlah peserta"><input type="number" min="1" max="10000" value={participants} onChange={(e) => setParticipants(e.target.value)} required /></Field>
        <Field label="Jam mulai"><input type="time" value={start} onChange={(e) => setStart(e.target.value)} required /></Field>
        <Field label="Jam selesai"><input type="time" value={end} onChange={(e) => setEnd(e.target.value)} required /></Field>
      </div>
      <div className="form-divider" />
      <h2>Preferensi ruangan</h2>
      <div className="form-grid">
        <Field label="Fakultas"><input value={faculty} onChange={(e) => setFaculty(e.target.value)} placeholder="Semua fakultas" /></Field>
        <Field label="Gedung"><input value={building} onChange={(e) => setBuilding(e.target.value)} placeholder="Semua gedung" /></Field>
        <Field label="Lokasi detail"><input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Contoh: dekat lift / sayap timur" /></Field>
        <Field label="Fasilitas wajib"><input value={facility} onChange={(e) => setFacility(e.target.value)} placeholder="Contoh: proyektor, Wi-Fi" /></Field>
      </div>
      {error ? <Notice tone="error">{error}</Notice> : null}
      <Button type="submit" disabled={loading}><Search size={16} />{loading ? "Memeriksa..." : "Cari ruangan tersedia"}</Button>
    </form>
    {loading ? <Loading label="Memeriksa jadwal dan ketersediaan ruangan..." /> : null}
    {searched && available.length ? <PageSection title={available.length + " ruangan tersedia"} action={<span className="muted small">{formatDate(date)} · {start}–{end} WIB</span>}>
      <div className="room-grid">
        {available.map((room) => <article className="room-card availability-result-card" key={room.id}>
          <div className="room-card__media"><AvailabilityRoomPhoto room={room} /></div>
          <div className="room-card__body">
            <div className="room-card__top"><span className="status-badge status-badge--active">Tersedia</span><span><Users size={14} />{room.capacity} orang</span></div>
            <Link className="room-card__title" to={roomDetailPath(room.id, date, start, end, participants)}>{room.room_name}</Link>
            <p>{roomLocation(room) || room.building}</p>
            <div className="chip-list">{room.facilities.slice(0, 4).map((item) => <span key={item}>{item}</span>)}</div>
            <Link className="button button--primary button--wide" to={roomBookingPath(room.id, date, start, end, participants)}>Pilih ruangan</Link>
          </div>
        </article>)}
      </div>
      {totalPages > 1 ? <div className="form-actions availability-pagination">
        <Button variant="secondary" disabled={page <= 1 || loading} onClick={() => setPage((value) => value - 1)}>Sebelumnya</Button>
        <span className="muted">Halaman {page} dari {totalPages}</span>
        <Button variant="secondary" disabled={page >= totalPages || loading} onClick={() => setPage((value) => value + 1)}>Berikutnya</Button>
      </div> : null}
      <Notice tone="info">Ketersediaan ini merupakan hasil pemeriksaan saat halaman dimuat. Backend akan memvalidasi ulang ketika permohonan diajukan dan saat TU menyetujui.</Notice>
    </PageSection> : null}
    {searched && !available.length ? <section className="panel stack-form">
      <EmptyState title="Belum ada ruangan yang tersedia" description="Tidak ditemukan ruang yang memenuhi kriteria pada waktu tersebut. Periksa penyebab bentrok atau cari jadwal alternatif." icon={<CalendarDays size={23} />} />
      {blocked.length ? <div className="conflict-list">
        <h3>Hasil deteksi konflik</h3>
        {blocked.map(({ room, result }) => <article className="conflict-row" key={room.id}>
          <div><strong>{room.room_name}</strong><p className="muted small">{roomLocation(room)}</p></div>
          <ul>{result.reasons.map((reason) => <li key={reason}>{availabilityReasonLabel(reason)}</li>)}</ul>
        </article>)}
      </div> : null}
      <Link className="button button--primary" to={alternativeQuery}><WandSparkles size={16} />Cari slot alternatif</Link>
    </section> : null}
    {searched && available.length === 0 && !blocked.length ? <Notice tone="warning">Tidak ada data ruangan yang cocok dengan filter. Coba kurangi fasilitas atau ubah lokasi.</Notice> : null}
  </div>;
}

export function AlternativeSlotsPage() {
  const [params] = useSearchParams();
  const [date, setDate] = useState(params.get("date") || localToday());
  const [duration, setDuration] = useState(params.get("durationMinutes") || "120");
  const [participants, setParticipants] = useState(params.get("participantCount") || "1");
  const [faculty, setFaculty] = useState(params.get("faculty") || "");
  const [building, setBuilding] = useState(params.get("building") || "");
  const [facility, setFacility] = useState(params.get("facility") || "");
  const [preferredTime, setPreferredTime] = useState(params.get("preferredStartTime") || "10:00");
  const [result, setResult] = useState<AlternativeSlotsResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function findAlternatives(event: FormEvent) {
    event.preventDefault(); setError(""); setResult(null); setLoading(true);
    try {
      const data = await discoveryApi.alternatives({
        date, duration_minutes: Number(duration), participant_count: Number(participants),
        faculty: faculty.trim() || null, building: building.trim() || null,
        facilities: facility.trim() ? [facility.trim()] : [],
        preferred_start_time: preferredTime || null, search_days: 7, slot_step_minutes: 30, limit: 8,
      });
      setResult(data);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Rekomendasi slot alternatif belum dapat dimuat.");
    } finally { setLoading(false); }
  }

  return <div className="page-stack">
    <PageTitle eyebrow="REKOMENDASI JADWAL ALTERNATIF" title="Rekomendasi jadwal alternatif"
      description="Cari waktu atau ruangan lain saat slot awal tidak tersedia. Setiap rekomendasi diperiksa terhadap jadwal dan data reservasi terkini."
      action={<Link className="button button--secondary" to="/student/availability"><CalendarDays size={16} />Cek ketersediaan</Link>} />
    <form className="panel stack-form" onSubmit={findAlternatives}>
      <div className="form-grid">
        <Field label="Mulai pencarian dari tanggal"><input type="date" min={localToday()} value={date} onChange={(e) => setDate(e.target.value)} required /></Field>
        <Field label="Durasi kegiatan (menit)"><input type="number" min="15" max="480" step="15" value={duration} onChange={(e) => setDuration(e.target.value)} required /></Field>
        <Field label="Jumlah peserta"><input type="number" min="1" max="10000" value={participants} onChange={(e) => setParticipants(e.target.value)} required /></Field>
        <Field label="Waktu yang diutamakan"><input type="time" value={preferredTime} onChange={(e) => setPreferredTime(e.target.value)} /></Field>
        <Field label="Fakultas"><input value={faculty} onChange={(e) => setFaculty(e.target.value)} placeholder="Opsional" /></Field>
        <Field label="Gedung"><input value={building} onChange={(e) => setBuilding(e.target.value)} placeholder="Opsional" /></Field>
      </div>
      <Field label="Fasilitas wajib"><input value={facility} onChange={(e) => setFacility(e.target.value)} placeholder="Contoh: proyektor" /></Field>
      {error ? <Notice tone="error">{error}</Notice> : null}
      <Button type="submit" disabled={loading}><WandSparkles size={16} />{loading ? "Mencari alternatif..." : "Temukan slot alternatif"}</Button>
    </form>
    {loading ? <Loading label="Mencari slot yang cocok di jadwal ruangan..." /> : null}
    {result ? <PageSection title={result.items.length + " rekomendasi ditemukan"}>
      <Notice tone="info">{result.availability_note}</Notice>
      {result.items.length ? <div className="recommendation-list">{result.items.map((slot, index) => <AlternativeCard key={slot.room.id + slot.date + slot.start_time + index} slot={slot} />)}</div>
        : <EmptyState title="Belum ada slot alternatif" description="Belum ditemukan ruang dan waktu yang sesuai pada rentang pencarian. Ubah tanggal, durasi, atau kebutuhan fasilitas." icon={<CalendarDays size={22} />} />}
    </PageSection> : null}
  </div>;
}

type AssistantTurn = {
  id: number;
  sender: "assistant" | "user";
  message: string;
  rooms?: Room[];
  alternatives?: AlternativeSlot[];
  followUps?: string[];
};
const assistantPrompts = [
  "Cari ruang untuk 20 orang dengan proyektor",
  "Temukan ruang tersedia besok pukul 10:00 sampai 12:00",
  "Cari ruang di fakultas saya dengan Wi-Fi",
];

export function RoomAssistantPage() {
  const [message, setMessage] = useState("");
  const [turns, setTurns] = useState<AssistantTurn[]>([{
    id: 1, sender: "assistant",
    message: "Halo! Saya dapat membantu mencari ruangan berdasarkan jumlah peserta, fasilitas, fakultas, gedung, tanggal, dan waktu. Sertakan tanggal serta rentang jam untuk memeriksa ketersediaan.",
  }]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function sendMessage(event: FormEvent) {
    event.preventDefault();
    const text = message.trim();
    if (text.length < 3 || loading) return;
    setMessage(""); setError("");
    setTurns((current) => [...current, { id: Date.now(), sender: "user", message: text }]);
    setLoading(true);
    try {
      const response: AssistantChatResult = await discoveryApi.chat({ message: text });
      setTurns((current) => [...current, {
        id: Date.now() + 1, sender: "assistant", message: response.message,
        rooms: response.rooms, alternatives: response.alternative_slots, followUps: response.follow_up_questions,
      }]);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Asisten belum dapat memproses pertanyaan.");
    } finally { setLoading(false); }
  }

  return <div className="page-stack">
    <PageTitle eyebrow="BANTUAN LAYANAN KAMPUS" title="AI Room Assistant"
      description="Tanyakan kebutuhan ruangan dan dapatkan hasil pencarian berdasarkan informasi fasilitas serta pemeriksaan ketersediaan." />
    <section className="panel assistant-intro">
      <span className="assistant-intro__icon"><Bot size={25} /></span>
      <div><h2>Teman pencarian ruangan</h2><p className="muted">Ceritakan kebutuhan acara Anda. Asisten akan menyaring data ruangan dan menampilkan slot alternatif jika tersedia.</p></div>
    </section>
    <section className="panel assistant-chat-panel">
      <div className="assistant-engine-label"><span className="online-dot" />Asisten berbasis aturan · data backend</div>
      <div className="assistant-chat-list" aria-live="polite">
        {turns.map((turn) => <article key={turn.id} className={"assistant-message assistant-message--" + turn.sender}>
          <span className="assistant-message__avatar">{turn.sender === "assistant" ? <Sparkles size={16} /> : <Users size={16} />}</span>
          <div className="assistant-message__body">
            <p>{turn.message}</p>
            {turn.rooms?.length ? <div className="assistant-inline-results">
              {turn.rooms.map((room) => <Link className="assistant-room-link" key={room.id} to={"/student/rooms/" + room.id}>
                <span><b>{room.room_name}</b><small>{roomLocation(room) || room.building} · {room.capacity} orang</small></span><ArrowRight size={16} />
              </Link>)}
            </div> : null}
            {turn.alternatives?.length ? <div className="recommendation-list">{turn.alternatives.map((slot, index) => <AlternativeCard key={slot.room.id + slot.date + slot.start_time + index} slot={slot} />)}</div> : null}
            {turn.followUps?.map((question) => <button className="assistant-follow-up" type="button" key={question} onClick={() => setMessage(question)}>{question}</button>)}
          </div>
        </article>)}
        {loading ? <Loading label="Asisten sedang memeriksa kebutuhan ruangan..." /> : null}
      </div>
      {error ? <Notice tone="error">{error}</Notice> : null}
      <div className="assistant-suggestions">
        <span className="muted small">Contoh pertanyaan</span>
        {assistantPrompts.map((prompt) => <button type="button" key={prompt} onClick={() => setMessage(prompt)}>{prompt}</button>)}
      </div>
      <form className="assistant-compose" onSubmit={sendMessage}>
        <label className="sr-only" htmlFor="assistant-message">Tulis pertanyaan</label>
        <textarea id="assistant-message" value={message} onChange={(e) => setMessage(e.target.value)} rows={2}
          maxLength={1000} minLength={3} placeholder="Contoh: Saya butuh ruang untuk 20 orang besok pukul 10:00–12:00 dengan proyektor..." required />
        <Button type="submit" disabled={loading || message.trim().length < 3} title="Kirim pertanyaan"><Send size={17} />Kirim</Button>
      </form>
    </section>
    <Notice tone="info">Asisten menggunakan pencarian berbasis aturan dari data RuangKampus, bukan model AI generatif. Pesan tidak membuat reservasi otomatis; permohonan tetap harus dikirim melalui halaman reservasi.</Notice>
  </div>;
}
