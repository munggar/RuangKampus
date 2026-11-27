import { useEffect, useRef, useState, type ChangeEvent, type DragEvent } from "react";
import { IconAlertCircle as AlertCircle, IconBook2 as BookOpen, IconBuilding as Building2, IconCalendar as CalendarDays, IconCircleCheck as CheckCircle2, IconFileSpreadsheet as FileSpreadsheet, IconSchool as GraduationCap, IconInfoCircle as Info, IconUpload as UploadCloud } from "@tabler/icons-react";
import { Link } from "react-router";
import { PageTitle } from "./layout";
import { ApiError, formatDateTime, roomImportApi, type RoomImportBatch } from "./api";
import { Button, Notice } from "./ui";

type DatasetKey = "students" | "courses" | "rooms";
const tabs: Array<{ key: DatasetKey; label: string; icon: typeof GraduationCap }> = [
  { key: "students", label: "Data mahasiswa", icon: GraduationCap },
  { key: "courses", label: "Data mata kuliah", icon: BookOpen },
  { key: "rooms", label: "Data ruangan", icon: Building2 },
];

function fileSize(bytes: number) {
  return bytes < 1024 * 1024 ? (bytes / 1024).toFixed(1) + " KB" : (bytes / (1024 * 1024)).toFixed(2) + " MB";
}

export function AdminDataImportsPage() {
  const [active, setActive] = useState<DatasetKey>("rooms");
  const [file, setFile] = useState<File | null>(null);
  const [batch, setBatch] = useState<RoomImportBatch | null>(null);
  const [history, setHistory] = useState<RoomImportBatch[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  async function loadHistory() {
    try { setHistory(await roomImportApi.list()); } catch { /* history is supplementary */ }
  }
  useEffect(() => { void roomImportApi.list().then(setHistory).catch(() => undefined); }, []);

  function selectFile(next?: File) {
    setError(""); setMessage(""); setBatch(null);
    if (!next) return;
    if (!next.name.toLowerCase().endsWith(".xlsx")) {
      setFile(null);
      setError("File harus berformat .xlsx. Workbook .xls, CSV, dan file bermacro belum didukung.");
      return;
    }
    if (next.size > 5 * 1024 * 1024) {
      setFile(null); setError("Ukuran file maksimal 5 MB."); return;
    }
    setFile(next);
  }
  function onInput(event: ChangeEvent<HTMLInputElement>) { selectFile(event.target.files?.[0]); }
  function onDrop(event: DragEvent<HTMLLabelElement>) { event.preventDefault(); selectFile(event.dataTransfer.files?.[0]); }

  async function preview() {
    if (!file) return;
    setBusy(true); setError(""); setMessage(""); setBatch(null);
    try {
      const result = await roomImportApi.preview(file);
      setBatch(result);
      setMessage("Pratinjau selesai. Periksa seluruh baris dan foto sebelum menyimpan.");
      await loadHistory();
    } catch (e) {
      setError(e instanceof Error ? e.message : "File gagal diproses.");
    } finally { setBusy(false); }
  }

  async function commit() {
    if (!batch) return;
    const restoreCount = batch.row_results.filter((row) => row.status === "VALID" && row.import_action === "RESTORE").length;
    const createCount = batch.row_results.filter((row) => row.status === "VALID" && row.import_action !== "RESTORE").length;
    const confirmation = "Simpan " + batch.valid_count + " data ruangan? " +
      createCount + " data baru dan " + restoreCount + " data lama dipulihkan. Data yang sudah ada tidak dihapus saat impor berikutnya.";
    if (!window.confirm(confirmation)) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const result = await roomImportApi.commit(batch.batch_id);
      setMessage(
        result.imported + " ruangan berhasil diproses: " + result.inserted +
        " data baru dan " + result.restored + " data lama dipulihkan. " +
        result.invalid_count + " baris tidak diimpor."
      );
      setBatch(null); setFile(null);
      if (inputRef.current) inputRef.current.value = "";
      await loadHistory();
    } catch (e) {
      const detail = e instanceof Error ? e.message : "Impor gagal disimpan.";
      setBatch(null);
      setError(
        (e instanceof ApiError && e.status === 409 ? detail + " " : detail + " ") +
        "Pratinjau direset; tekan Pratinjau & validasi kembali sebelum mencoba impor."
      );
      await loadHistory();
    } finally { setBusy(false); }
  }

  return <div className="page-stack">
    <PageTitle
      eyebrow="CAMPUS MASTER DATA"
      title="Impor data kampus"
      description="Impor data inventaris ruangan dari workbook Excel resmi, periksa hasilnya, lalu simpan melalui akun TU/Admin."
      action={<div className="data-import-page-actions"><Link className="button button--secondary" to="/admin/rooms"><Building2 size={16} />Kelola ruangan</Link><Link className="button button--secondary" to="/admin/schedules"><CalendarDays size={16} />Jadwal & pemeliharaan</Link></div>}
    />

    <div className="data-import-overview">
      <article className="data-import-overview__card"><span className="data-import-overview__icon"><GraduationCap size={19} /></span><div><b>Data mahasiswa</b><small>Menunggu file roster resmi</small></div><span className="data-import-state">Belum aktif</span></article>
      <article className="data-import-overview__card"><span className="data-import-overview__icon"><BookOpen size={19} /></span><div><b>Data mata kuliah</b><small>Menunggu katalog akademik</small></div><span className="data-import-state">Belum aktif</span></article>
      <article className="data-import-overview__card"><span className="data-import-overview__icon"><Building2 size={19} /></span><div><b>Data ruangan</b><small>Impor Excel + foto dokumentasi</small></div><span className="data-import-state">Tersedia</span></article>
    </div>

    <section className="panel data-import-workspace">
      <div className="data-import-tabs" role="tablist" aria-label="Jenis data yang akan diimpor">
        {tabs.map(({ key, label, icon: Icon }) => <button key={key} type="button" role="tab" aria-selected={active === key} className={active === key ? "data-import-tab is-active" : "data-import-tab"} onClick={() => { setActive(key); setFile(null); setBatch(null); setError(""); setMessage(""); if (inputRef.current) inputRef.current.value = ""; }}>
          <Icon size={18} /><span>{label}</span>
        </button>)}
      </div>

      {active !== "rooms" ? <div className="data-import-main" style={{ padding: 24 }}>
        <Notice tone="info"><b>Belum diaktifkan.</b> Modul ini menunggu file Excel resmi dari unit akademik. Kolom dan validasinya akan dibuat berdasarkan file asli, bukan template perkiraan.</Notice>
      </div> : <div className="data-import-layout">
        <div className="data-import-main">
          <div className="data-import-heading"><span className="data-import-heading__icon"><Building2 size={22} /></span><div><p className="eyebrow">ROOM MASTER DATA</p><h2>Impor data ruangan</h2><p>Format mendukung workbook inventaris ruang: nama, kapasitas, fasilitas, fakultas, alamat lokasi, dan foto yang tertanam di baris Excel.</p></div></div>

          <div className="data-import-step-title"><span>01</span><div><b>Pilih workbook Excel</b><small>Format .xlsx, ukuran maksimal 5 MB</small></div></div>
          <label className="data-import-dropzone" onDragOver={(event) => event.preventDefault()} onDrop={onDrop}>
            <input ref={inputRef} className="sr-only" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={onInput} />
            <span className="data-import-dropzone__icon"><UploadCloud size={25} /></span>
            <b>{file ? "File siap diproses" : "Pilih file Excel atau tarik ke area ini"}</b>
            <span>{file ? file.name + " · " + fileSize(file.size) : "Header dikenali otomatis: Nomor Ruangan, Kapasitas, Fasilitas, Dokumentasi, Lokasi Gedung, dan Fakultas. Urutan kolom bebas."}</span>
            <span className="button button--secondary data-import-dropzone__button">{file ? "Ganti file" : "Pilih file"}</span>
          </label>
          {file && <div className="data-import-file"><FileSpreadsheet size={20} /><div><b>{file.name}</b><small>{fileSize(file.size)} · File akan dikirim ke API setelah tombol pratinjau ditekan</small></div><button type="button" onClick={() => { setFile(null); setBatch(null); if (inputRef.current) inputRef.current.value = ""; }} aria-label="Hapus file terpilih">×</button></div>}

          <div className="data-import-actions"><Button variant="secondary" disabled={!file || busy} onClick={preview}>{busy ? "Memproses…" : "Pratinjau & validasi"}</Button><Button disabled={!batch || batch.valid_count === 0 || busy} onClick={commit}>{busy ? "Menyimpan…" : "Konfirmasi & impor " + (batch?.valid_count ?? "")}</Button></div>
          {error && <Notice tone="error"><span>{error}</span></Notice>}
          {message && <Notice tone="success"><span>{message}</span></Notice>}

          {batch && <div className="data-import-preview">
            <div className="data-import-step-title"><span>02</span><div><b>Hasil pratinjau</b><small>{batch.source_filename}</small></div></div>
            <div className="data-import-overview">
              <article className="data-import-overview__card"><div><b>{batch.row_count}</b><small>Total baris</small></div></article>
              <article className="data-import-overview__card"><div><b>{batch.valid_count}</b><small>Valid</small></div></article>
              <article className="data-import-overview__card"><div><b>{batch.invalid_count}</b><small>Perlu diperbaiki</small></div></article>
            </div>
            <div className="table-wrap data-import-preview__table-wrap"><table className="data-table data-import-preview__table"><thead><tr><th>Baris</th><th>Nama ruangan</th><th>Lantai</th><th>Kapasitas estimasi</th><th>Fasilitas terdeteksi</th><th>Fakultas</th><th>Alamat/lokasi</th><th>Rencana aksi</th><th>Foto</th><th>Status / catatan</th></tr></thead><tbody>
              {batch.row_results.map((row) => <tr key={row.row_number}>
                <td>{row.row_number}</td>
                <td>{row.room_name}</td>
                <td>{row.floor ? "Lantai " + row.floor : "Belum diketahui"}</td>
                <td>{row.capacity_estimate || "—"}</td>
                <td>{row.facilities?.length ? row.facilities.join(", ") : "Tidak terdeteksi"}</td>
                <td>{row.faculty || "—"}</td>
                <td>{row.location_description || "—"}</td>
                <td>
                  {row.import_action === "RESTORE"
                    ? <span className="data-import-action data-import-action--restore">Pulihkan data lama</span>
                    : row.import_action === "BLOCKED"
                      ? <span className="data-import-action data-import-action--blocked">Sudah aktif</span>
                      : <span className="data-import-action data-import-action--create">Buat data baru</span>}
                </td>
                <td>{row.has_photo ? "Tersedia" : "Tidak ada"}</td>
                <td>{row.status === "VALID" ? <span className="status-pill status-pill--success"><CheckCircle2 size={13} />Valid</span> : <span className="status-pill status-pill--danger">{row.errors.join(", ")}</span>}</td>
              </tr>)}
            </tbody></table></div>
            <Notice tone="warning">Kapasitas operasional menggunakan batas bawah rentang (misalnya 20–25 menjadi 20), sedangkan rentang asli tetap disimpan. Fakultas dan alamat pada kolom Lokasi Gedung akan dipetakan otomatis. Kolom tersebut berisi alamat, bukan nama gedung, sehingga label gedung tetap “Belum ditentukan”. Jam operasional juga belum ada di workbook; ruangan tetap nonaktif sampai Admin melengkapi nama gedung dan jam operasional.</Notice>
          </div>}
        </div>

        <aside className="data-import-guide"><div className="data-import-guide__header"><div><p className="eyebrow">PEMETAAN KOLOM</p><h3>Struktur workbook</h3></div><span>6 kolom</span></div>
          <div className="data-import-columns">
            <div className="data-import-column"><div><b>Nomor Ruangan</b><small>Nama ruang sesuai file</small></div><span className="data-import-required">Wajib</span></div>
            <div className="data-import-column"><div><b>Kapasitas / Kapasitas (estimasi)</b><small>Angka atau rentang, mis. 40–45 mahasiswa</small></div><span className="data-import-required">Wajib</span></div>
            <div className="data-import-column"><div><b>Fasilitas</b><small>Deskripsi lengkap disimpan; label fasilitas dikenali otomatis</small></div><span className="data-import-required">Wajib</span></div>
            <div className="data-import-column"><div><b>Dokumentasi</b><small>Foto yang tertanam di baris terkait</small></div><span className="data-import-optional">Opsional</span></div>
            <div className="data-import-column"><div><b>Lokasi Gedung</b><small>Disimpan sebagai alamat/lokasi ruangan</small></div><span className="data-import-optional">Opsional</span></div>
            <div className="data-import-column"><div><b>Fakultas</b><small>Disimpan ke data fakultas ruangan</small></div><span className="data-import-optional">Opsional</span></div>
          </div>
          <div className="data-import-example"><span>Aturan impor</span><b>Kapasitas konservatif</b><small>Nilai minimum menjadi kapasitas operasional; rentang perkiraan asli tetap disimpan untuk ditampilkan.</small></div>
          <Notice tone="info"><Info size={15} />Header dikenali berdasarkan nama, jadi urutan kolom bebas. Kode internal dibuat otomatis. Lantai lab ditetapkan ke lantai 2; ruangan bernomor memakai angka pertama pada nama. Alamat tidak dianggap sebagai nama gedung. Nama gedung dan jam operasional tetap perlu dilengkapi Admin sebelum ruangan diaktifkan.</Notice>
        </aside>
      </div>}
    </section>

    <section className="panel data-import-history"><div className="data-import-step-title"><span>03</span><div><b>Riwayat impor ruangan</b><small>Proses impor yang dibuat oleh akun Admin ini</small></div></div>
      {history.length ? <div className="table-wrap"><table className="data-table"><thead><tr><th>File</th><th>Tanggal</th><th>Baris</th><th>Valid</th><th>Gagal</th><th>Status</th></tr></thead><tbody>{history.map((item) => <tr key={item.batch_id}><td>{item.source_filename}</td><td>{formatDateTime(item.created_at)}</td><td>{item.row_count}</td><td>{item.valid_count}</td><td>{item.invalid_count}</td><td>{item.status}</td></tr>)}</tbody></table></div> : <p className="muted">Belum ada riwayat impor.</p>}
    </section>
    <section className="data-import-bottom"><div className="data-import-bottom__icon"><AlertCircle size={19} /></div><div><b>Data mahasiswa dan mata kuliah belum diproses</b><p>Hanya workbook ruangan yang tersedia saat ini. Modul mahasiswa dan mata kuliah akan diaktifkan setelah file resmi masing-masing diterima.</p></div></section>
  </div>;
}
