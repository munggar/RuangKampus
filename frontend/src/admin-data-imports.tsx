import { useRef, useState, type DragEvent, type ChangeEvent } from "react";
import {
  AlertCircle, BookOpen, Building2, CheckCircle2, Database, FileDown,
  FileSpreadsheet, GraduationCap, Info, UploadCloud,
} from "lucide-react";
import { Link } from "react-router";
import { PageTitle } from "./layout";
import { Button, Notice } from "./ui";

type DatasetKey = "students" | "courses" | "rooms";

type Column = {
  key: string;
  label: string;
  required: boolean;
  example: string;
};

type DatasetConfig = {
  title: string;
  eyebrow: string;
  description: string;
  helper: string;
  templateName: string;
  icon: typeof GraduationCap;
  columns: Column[];
  example: string[];
};

const datasets: Record<DatasetKey, DatasetConfig> = {
  students: {
    title: "Data mahasiswa",
    eyebrow: "STUDENT MASTER DATA",
    description: "Siapkan daftar mahasiswa resmi sebagai sumber verifikasi NIM, nama, dan email ketika pendaftaran mandiri diaktifkan.",
    helper: "Gunakan data dari unit akademik yang berwenang. Setiap NIM harus mewakili satu mahasiswa.",
    templateName: "template-data-mahasiswa",
    icon: GraduationCap,
    columns: [
      { key: "nim", label: "NIM", required: true, example: "2403045001" },
      { key: "nama", label: "Nama lengkap", required: true, example: "Nama Mahasiswa" },
      { key: "email", label: "Email kampus", required: true, example: "mahasiswa@kampus.ac.id" },
      { key: "program_studi", label: "Program studi", required: false, example: "Sistem dan Teknologi Informasi" },
      { key: "fakultas", label: "Fakultas", required: false, example: "FTII" },
      { key: "angkatan", label: "Tahun angkatan", required: false, example: "2024" },
      { key: "status", label: "Status mahasiswa", required: false, example: "AKTIF" },
    ],
    example: ["2403045001", "Nama Mahasiswa", "mahasiswa@kampus.ac.id", "Sistem dan Teknologi Informasi", "FTII", "2024", "AKTIF"],
  },
  courses: {
    title: "Data mata kuliah",
    eyebrow: "COURSE MASTER DATA",
    description: "Siapkan katalog mata kuliah kampus agar data akademik dapat dikelola dalam satu sumber yang konsisten.",
    helper: "Kode mata kuliah sebaiknya unik. Format kolom dapat disesuaikan dengan file resmi program studi.",
    templateName: "template-data-mata-kuliah",
    icon: BookOpen,
    columns: [
      { key: "kode_mata_kuliah", label: "Kode mata kuliah", required: true, example: "STI204" },
      { key: "nama_mata_kuliah", label: "Nama mata kuliah", required: true, example: "Basis Data" },
      { key: "program_studi", label: "Program studi", required: true, example: "Sistem dan Teknologi Informasi" },
      { key: "semester", label: "Semester", required: false, example: "4" },
      { key: "sks", label: "Jumlah SKS", required: true, example: "3" },
      { key: "kelompok", label: "Kelompok / jenis", required: false, example: "Wajib" },
      { key: "status", label: "Status mata kuliah", required: false, example: "AKTIF" },
    ],
    example: ["STI204", "Basis Data", "Sistem dan Teknologi Informasi", "4", "3", "Wajib", "AKTIF"],
  },
  rooms: {
    title: "Data ruangan",
    eyebrow: "ROOM MASTER DATA",
    description: "Siapkan inventaris ruangan kampus melalui satu file Excel, tanpa perlu memasukkan ruangan satu per satu.",
    helper: "Pastikan kode ruang unik. Pisahkan beberapa fasilitas dengan tanda | (pipa) dalam satu sel.",
    templateName: "template-data-ruangan",
    icon: Building2,
    columns: [
      { key: "kode_ruang", label: "Kode ruangan", required: true, example: "GKB-A201" },
      { key: "nama_ruang", label: "Nama ruangan", required: true, example: "Ruang Kelas A201" },
      { key: "gedung", label: "Gedung", required: true, example: "Gedung A" },
      { key: "kapasitas", label: "Kapasitas", required: true, example: "40" },
      { key: "lantai", label: "Lantai", required: false, example: "2" },
      { key: "fakultas", label: "Fakultas", required: false, example: "FTII" },
      { key: "fasilitas", label: "Fasilitas", required: false, example: "Proyektor|AC|Papan tulis" },
      { key: "lokasi", label: "Keterangan lokasi", required: false, example: "Dekat tangga timur" },
      { key: "status", label: "Status ruangan", required: false, example: "AKTIF" },
    ],
    example: ["GKB-A201", "Ruang Kelas A201", "Gedung A", "40", "2", "FTII", "Proyektor|AC|Papan tulis", "Dekat tangga timur", "AKTIF"],
  },
};

const datasetOrder: DatasetKey[] = ["students", "courses", "rooms"];

function csvCell(value: string) {
  return '"' + value.replaceAll('"', '""') + '"';
}

function formatFileSize(bytes: number) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(2) + " MB";
}

export function AdminDataImportsPage() {
  const [active, setActive] = useState<DatasetKey>("students");
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const config = datasets[active];
  const DatasetIcon = config.icon;

  function selectFile(nextFile?: File) {
    setFileError("");
    if (!nextFile) return;
    const extension = nextFile.name.toLowerCase().split(".").pop();
    if (!extension || !["xlsx", "xls", "csv"].includes(extension)) {
      setFile(null);
      setFileError("Format file belum sesuai. Pilih file .xlsx, .xls, atau .csv.");
      return;
    }
    setFile(nextFile);
  }

  function handleInput(event: ChangeEvent<HTMLInputElement>) {
    selectFile(event.target.files?.[0]);
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    selectFile(event.dataTransfer.files?.[0]);
  }

  function downloadTemplate() {
    const headers = config.columns.map((column) => column.key);
    const csv = [headers, config.example].map((row) => row.map(csvCell).join(",")).join("\r\n");
    const blob = new Blob(["\uFEFF", csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = config.templateName + ".csv";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  function changeDataset(key: DatasetKey) {
    setActive(key);
    setFile(null);
    setFileError("");
    if (inputRef.current) inputRef.current.value = "";
  }

  return <div className="page-stack">
    <PageTitle
      eyebrow="CAMPUS MASTER DATA"
      title="Impor data kampus"
      description="Siapkan data mahasiswa, mata kuliah, dan inventaris ruangan melalui file Excel."
      action={<Link className="button button--secondary" to="/admin/schedule-imports"><FileSpreadsheet size={16} />Impor jadwal ruang</Link>}
    />

    <Notice tone="warning">
      **Tampilan tahap persiapan — belum terhubung ke backend.** File hanya dipilih di browser. Belum ada data yang dikirim, divalidasi, atau disimpan ke database RuangKampus.
    </Notice>

    <div className="data-import-overview">
      <article className="data-import-overview__card">
        <span className="data-import-overview__icon"><GraduationCap size={19} /></span>
        <div><b>Data mahasiswa</b><small>Menunggu daftar resmi</small></div>
        <span className="data-import-state">Belum tersedia</span>
      </article>
      <article className="data-import-overview__card">
        <span className="data-import-overview__icon"><BookOpen size={19} /></span>
        <div><b>Data mata kuliah</b><small>Menunggu data akademik</small></div>
        <span className="data-import-state">Belum tersedia</span>
      </article>
      <article className="data-import-overview__card">
        <span className="data-import-overview__icon"><Building2 size={19} /></span>
        <div><b>Data ruangan</b><small>Menunggu inventaris kampus</small></div>
        <span className="data-import-state">Belum tersedia</span>
      </article>
    </div>

    <section className="panel data-import-workspace">
      <div className="data-import-tabs" role="tablist" aria-label="Jenis data yang akan diimpor">
        {datasetOrder.map((key) => {
          const item = datasets[key];
          const Icon = item.icon;
          return <button
            key={key}
            type="button"
            role="tab"
            aria-selected={active === key}
            className={active === key ? "data-import-tab is-active" : "data-import-tab"}
            onClick={() => changeDataset(key)}
          >
            <Icon size={18} />
            <span>{item.title}</span>
          </button>;
        })}
      </div>

      <div className="data-import-layout">
        <div className="data-import-main">
          <div className="data-import-heading">
            <span className="data-import-heading__icon"><DatasetIcon size={22} /></span>
            <div>
              <p className="eyebrow">{config.eyebrow}</p>
              <h2>{config.title}</h2>
              <p>{config.description}</p>
            </div>
          </div>

          <div className="data-import-step-title">
            <span>01</span><div><b>Pilih file sumber</b><small>Unggah file dari unit kampus yang berwenang</small></div>
          </div>
          <label
            className="data-import-dropzone"
            onDragOver={(event) => event.preventDefault()}
            onDrop={handleDrop}
          >
            <input ref={inputRef} className="sr-only" type="file" accept=".xlsx,.xls,.csv" onChange={handleInput} />
            <span className="data-import-dropzone__icon"><UploadCloud size={25} /></span>
            <b>{file ? "File berhasil dipilih" : "Pilih file Excel atau tarik ke area ini"}</b>
            <span>{file ? file.name + " · " + formatFileSize(file.size) : "Format yang disiapkan: .xlsx, .xls, dan .csv"}</span>
            <span className="button button--secondary data-import-dropzone__button">{file ? "Ganti file" : "Pilih file"}</span>
          </label>
          {fileError ? <Notice tone="error"><span>{fileError}</span></Notice> : null}
          {file ? <div className="data-import-file">
            <FileSpreadsheet size={20} />
            <div><b>{file.name}</b><small>{formatFileSize(file.size)} · Tersimpan hanya sebagai pilihan lokal</small></div>
            <button type="button" onClick={() => { setFile(null); if (inputRef.current) inputRef.current.value = ""; }} aria-label="Hapus file terpilih">×</button>
          </div> : null}

          <div className="data-import-actions">
            <Button variant="secondary" onClick={downloadTemplate}><FileDown size={16} />Unduh template CSV</Button>
            <Button disabled><Database size={16} />Pratinjau & validasi belum tersedia</Button>
          </div>
          <p className="data-import-footnote"><Info size={15} />Template ini hanya contoh rancangan kolom dan masih dapat disesuaikan setelah file resmi tersedia.</p>

          <div className="data-import-next-steps">
            <div className="data-import-step-title"><span>02</span><div><b>Pratinjau dan validasi</b><small>Akan diaktifkan setelah backend impor disiapkan</small></div><span className="data-import-step-state">Belum aktif</span></div>
            <div className="data-import-step-title"><span>03</span><div><b>Konfirmasi impor</b><small>Data baru akan disimpan setelah proses ini tersedia</small></div><span className="data-import-step-state">Belum aktif</span></div>
          </div>
        </div>

        <aside className="data-import-guide">
          <div className="data-import-guide__header">
            <div><p className="eyebrow">FORMAT DATA</p><h3>Kolom yang disarankan</h3></div>
            <span>{config.columns.length} kolom</span>
          </div>
          <p className="muted">{config.helper}</p>
          <div className="data-import-columns">
            {config.columns.map((column) => <div key={column.key} className="data-import-column">
              <div><b>{column.label}</b><small><code>{column.key}</code></small></div>
              <span className={column.required ? "data-import-required" : "data-import-optional"}>{column.required ? "Wajib" : "Opsional"}</span>
            </div>)}
          </div>
          <div className="data-import-example">
            <span>Contoh nilai (dummy)</span>
            <b>{config.example[0]} · {config.example[1]}</b>
            <small>Bukan data mahasiswa, mata kuliah, atau ruangan yang sebenarnya.</small>
          </div>
        </aside>
      </div>
    </section>

    <section className="data-import-bottom">
      <div className="data-import-bottom__icon"><AlertCircle size={19} /></div>
      <div><b>Belum ada data yang akan diimpor</b><p>Ketika file resmi sudah selesai disiapkan, format kolom dapat disesuaikan terlebih dahulu. Backend, validasi data, riwayat impor, dan penyimpanan akan dibuat pada tahap berikutnya.</p></div>
    </section>
  </div>;
}
