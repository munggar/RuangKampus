import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  ArrowRight, Building2, CalendarClock, CalendarDays, CheckCircle2, Clock3, ClipboardList,
  Edit3, FileSpreadsheet, Plus, Search, Trash2, Users,
} from "lucide-react";
import { Link, useNavigate, useParams } from "react-router";
import {
  adminApi, apiAssetUrl, dashboardApi, formatDate, formatTime, localToday, reservationApi, roomApi,
  scheduleApi, statusLabel,
} from "./api";
import type { Reservation, Room, RoomStatus, RoomUnavailability, Schedule } from "./types";
import { PageTitle } from "./layout";
import { Button, ConfirmModal, EmptyState, Field, Loading, Modal, Notice, PageSection, StatusBadge } from "./ui";

export function AdminDashboardPage() {
  const [summary, setSummary] = useState<Record<string, number | string> | null>(null);
  const [recent, setRecent] = useState<Reservation[]>([]);
  const [stats, setStats] = useState<Array<{ room_id: string; room_name: string; building: string; reservation_count: number }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([dashboardApi.summary(), dashboardApi.recent(6), adminApi.roomStatistics()])
      .then(([overview, latest, usage]) => {
        if (!active) return;
        setSummary(overview); setRecent(latest.items); setStats(usage);
      })
      .catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "Dashboard belum dapat dimuat."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  return <div className="page-stack">
    <PageTitle eyebrow="TU / ADMIN DASHBOARD" title="Selamat datang, Administrator" description="Pantau pengajuan reservasi dan pengelolaan fasilitas kampus." action={<Link className="button button--primary" to="/admin/rooms/new"><Plus size={17} />Tambah ruang</Link>} />
    {error ? <Notice tone="error">{error}</Notice> : null}
    {loading ? <Loading label="Memuat ringkasan administrasi…" /> : <>
      <div className="stat-grid stat-grid--four">
        <article className="stat-card"><div className="stat-card__top"><span>Total reservasi</span><CalendarDays size={18} /></div><strong>{Number(summary?.total_reservations || 0)}</strong><small>Seluruh status</small></article>
        <article className="stat-card"><div className="stat-card__top"><span>Permohonan menunggu</span><Clock3 size={18} /></div><strong>{Number(summary?.pending || 0)}</strong><small>Menunggu peninjauan</small></article>
        <article className="stat-card"><div className="stat-card__top"><span>Disetujui</span><CheckCircle2 size={18} /></div><strong>{Number(summary?.approved || 0)}</strong><small>Reservasi terkonfirmasi</small></article>
        <article className="stat-card"><div className="stat-card__top"><span>Total ruangan</span><Building2 size={18} /></div><strong>{Number(summary?.total_rooms || 0)}</strong><small>{Number(summary?.active_rooms || 0)} ruangan aktif</small></article>
      </div>
      <PageSection title="Permohonan terbaru" action={<Link className="text-link" to="/admin/reservations">Lihat semua <ArrowRight size={15} /></Link>}>
        {recent.length ? <div className="table-wrap"><table className="data-table">
          <thead><tr><th>Pemohon</th><th>Ruangan</th><th>Tanggal & waktu</th><th>Status</th><th /></tr></thead>
          <tbody>{recent.map((item) => <tr key={item.id}>
            <td><b>{item.applicant?.name || "Mahasiswa"}</b><small>{item.applicant?.email || ""}</small></td>
            <td>{item.room?.room_name || "Ruangan"}</td>
            <td>{formatDate(item.reservation_date)}<small>{formatTime(item.start_time)}–{formatTime(item.end_time)} WIB</small></td>
            <td><StatusBadge status={item.status} /></td>
            <td><Link className="icon-link" to={"/admin/reservations/" + item.id} aria-label="Lihat detail"><ArrowRight size={17} /></Link></td>
          </tr>)}</tbody>
        </table></div> : <EmptyState title="Belum ada permohonan" description="Permohonan mahasiswa akan muncul setelah dikirim melalui aplikasi." icon={<ClipboardList size={22} />} />}
      </PageSection>
      <div className="dashboard-two-column">
        <PageSection title="Ringkasan penggunaan ruang">
          {stats.length ? <div className="usage-list">{stats.slice(0, 5).map((item) => <div key={item.room_id} className="usage-row"><span>{item.room_name}<small>{item.building}</small></span><b>{item.reservation_count}</b></div>)}</div> : <EmptyState title="Belum ada statistik ruang" description="Statistik akan muncul berdasarkan reservasi yang disetujui atau selesai." />}
        </PageSection>
        <PageSection title="Akses cepat">
          <div className="quick-links">
            <Link to="/admin/reservations"><ClipboardList size={19} /><span>Tinjau permohonan<small>Approval dan rejection</small></span><ArrowRight size={16} /></Link>
            <Link to="/admin/rooms"><Building2 size={19} /><span>Kelola ruangan<small>Inventaris fasilitas</small></span><ArrowRight size={16} /></Link>
            <Link to="/admin/schedules"><CalendarClock size={19} /><span>Jadwal & pemeliharaan<small>Jadwal akademik ruang</small></span><ArrowRight size={16} /></Link>
          </div>
        </PageSection>
      </div>
    </>}
  </div>;
}

export function AdminRequestsPage() {
  const [status, setStatus] = useState("PENDING");
  const [search, setSearch] = useState("");
  const [items, setItems] = useState<Reservation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<Reservation | null>(null);
  const [action, setAction] = useState<"approve" | "reject" | null>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const reload = () => {
    setLoading(true); setError("");
    const params = new URLSearchParams({ page: "1", limit: "100" });
    if (status) params.set("status", status);
    reservationApi.list(params).then((result) => setItems(result.items))
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Permohonan belum dapat dimuat."))
      .finally(() => setLoading(false));
  };
  useEffect(() => { reload(); }, [status]);
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
    <Modal open={action === "reject" && !!selected} title="Tolak permohonan" description="Alasan penolakan wajib dicatat dan akan terlihat oleh pemohon." onClose={() => { setAction(null); setSelected(null); setReason(""); }}>
      <Field label="Alasan penolakan"><textarea rows={4} minLength={3} maxLength={2000} value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Jelaskan alasan penolakan dengan jelas…" /></Field>
      {error ? <Notice tone="error">{error}</Notice> : null}
      <div className="modal-actions"><Button variant="secondary" onClick={() => { setAction(null); setSelected(null); setReason(""); }} disabled={busy}>Kembali</Button><Button variant="danger" disabled={busy || reason.trim().length < 3} onClick={() => void runAction()}>{busy ? "Memproses…" : "Kirim penolakan"}</Button></div>
    </Modal>
  </div>;
}

export function AdminRoomsPage() {
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
      {selectedIds.length > 0 ? <div className="room-selection-toolbar__actions">
        <Field label="Ubah status menjadi">
          <select value={bulkStatus} onChange={(event) => setBulkStatus(event.target.value as RoomStatus | "")} disabled={bulkUpdating}>
            <option value="">Pilih status…</option>
            <option value="ACTIVE">Aktif</option>
            <option value="INACTIVE">Nonaktif</option>
            <option value="MAINTENANCE">Pemeliharaan</option>
          </select>
        </Field>
        <Button disabled={!bulkStatus || bulkUpdating} onClick={() => setBulkConfirmOpen(true)}>Terapkan status</Button>
        <Button variant="secondary" disabled={bulkUpdating} onClick={() => setBulkHoursOpen(true)}><Clock3 size={15} />Atur jam operasional</Button>
        <Button variant="secondary" disabled={bulkUpdating} onClick={() => { setSelectedIds([]); setBulkStatus(""); }}>Batal pilih</Button>
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
