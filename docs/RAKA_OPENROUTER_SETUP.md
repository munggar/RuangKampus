# RAKA — Panduan Memasang Gemma melalui OpenRouter

Panduan ini mengaktifkan model Google Gemma untuk menyusun jawaban chatbot RuangKampus. Identitas asisten adalah **RAKA (Ruang Asisten Kampus)**.

## 1. Buat API key OpenRouter

1. Buka [openrouter.ai](https://openrouter.ai/) dan login ke akunmu.
2. Buka halaman [Keys](https://openrouter.ai/keys).
3. Pilih **Create Key** dan beri nama yang mudah dikenali, misalnya `RuangKampus-Railway-API`.
4. Bila tersedia, tetapkan batas pengeluaran/key limit. Jangan membagikan key ini di chat, screenshot, frontend, atau repository.
5. Salin key yang biasanya diawali `sk-or-v1-`. Simpan sebagai secret; jangan commit ke Git.

Model gratis yang direkomendasikan:

- Nama: **Google Gemma 4 26B A4B Instruct (Free)**
- Model ID: `google/gemma-4-26b-a4b-it:free`
- Endpoint: `https://openrouter.ai/api/v1/chat/completions`
- Harga inferensi yang tercantum: gratis.
- Batas penggunaan free variant: 20 request/menit dan 50 request/hari pada batas standar. Batas harian dapat meningkat setelah akun membeli kredit sesuai kebijakan OpenRouter.

Rujukan: [halaman model Gemma 4 26B A4B Free](https://openrouter.ai/google/gemma-4-26b-a4b-it:free) dan [daftar model gratis serta batas penggunaan](https://openrouter.ai/collections/free-models).

## 2. Aktifkan untuk backend lokal (opsional)

Dari root repository, buka file `backend/.env`. Tambahkan atau sesuaikan:

```dotenv
ASSISTANT_AI_ENABLED=true
ASSISTANT_AI_ENDPOINT_URL=https://openrouter.ai/api/v1/chat/completions
ASSISTANT_AI_MODEL=google/gemma-4-26b-a4b-it:free
ASSISTANT_AI_API_KEY=sk-or-v1-ISI_SECRET_MU_DI_SINI
ASSISTANT_AI_TIMEOUT_SECONDS=6
```

Pastikan file `.env` tetap di-ignore Git. Jangan pernah menaruh key ke file `.env.example`, kode Python, React, atau variabel frontend yang diawali `VITE_`.

Jalankan ulang API lokal setelah menyimpan konfigurasi:

```powershell
cd backend
.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "src"
uvicorn ruangkampus.main:app --reload --host 127.0.0.1 --port 8000
```

## 3. Aktifkan di Railway (untuk aplikasi online)

API key harus dipasang pada **service backend/API**, bukan service frontend.

1. Buka [Railway Dashboard](https://railway.app/dashboard) dan pilih project RuangKampus.
2. Pilih service API/backend RuangKampus (bukan service web/frontend).
3. Buka tab **Variables**.
4. Tambahkan kelima variable berikut:

| Variable | Value |
|---|---|
| `ASSISTANT_AI_ENABLED` | `true` |
| `ASSISTANT_AI_ENDPOINT_URL` | `https://openrouter.ai/api/v1/chat/completions` |
| `ASSISTANT_AI_MODEL` | `google/gemma-4-26b-a4b-it:free` |
| `ASSISTANT_AI_API_KEY` | API key rahasia dari OpenRouter |
| `ASSISTANT_AI_TIMEOUT_SECONDS` | `6` |

5. Simpan variable. Tunggu Railway menyelesaikan deploy/restart service API.
6. Pastikan frontend tidak memiliki API key dan tidak memanggil OpenRouter secara langsung.

Perubahan ini tidak membutuhkan migration database. Apabila deployment API gagal karena konfigurasi, kembalikan sementara `ASSISTANT_AI_ENABLED=false`; asisten deterministik tetap dapat melayani chat.

## 4. Uji melalui API RuangKampus

1. Login sebagai akun **Student** dan dapatkan access token.
2. Buka Swagger API: `https://ALAMAT-API-RUANGKAMPUS/api/v1/docs`.
3. Tekan **Authorize**, masukkan access token Student, lalu jalankan `POST /api/v1/assistant/chat`.
4. Gunakan contoh pesan yang menyertakan filter nyata dari katalog ruangan, misalnya:

```json
{
  "message": "Bro, cariin ruang buat 20 orang di FTII yang ada proyektor."
}
```

5. Periksa hasil:
   - `assistant_name` harus bernilai `RAKA`.
   - `engine` akan bernilai `HYBRID` ketika model berhasil digunakan untuk menyusun jawaban.
   - `rooms` tetap berasal dari database RuangKampus.
   - Jawaban dapat lebih natural, menyebutkan hasil yang ditemukan, dan memberi langkah berikutnya.
   - Bila pesan menanyakan ketersediaan tanpa tanggal/jam, RAKA boleh menampilkan kandidat ruangan yang sesuai, tetapi wajib menyatakan bahwa slot kosong belum diverifikasi.

Jangan menganggap `engine=HYBRID` sebagai bukti bahwa isi ruangan dibuat oleh AI. Data ruangan dan hasil cek ketersediaan tetap berasal dari fungsi backend.

## 5. Cara kerja RAKA dan batasnya

- Backend mengklasifikasikan permintaan, mencari ruangan, mengecek jadwal, dan menghitung slot alternatif.
- Gemma hanya menyusun kalimat jawaban berdasarkan ringkasan hasil backend yang sudah tersedia. Model tidak diberi akses ke SQL, fungsi backend, atau operasi tulis.
- RAKA berusaha memberikan hasil terlebih dahulu dan hanya mengajukan satu pertanyaan lanjutan yang benar-benar diperlukan.
- Ketika tanggal dan rentang waktu belum lengkap, kandidat ruangan bukan berarti sudah dipastikan kosong.
- Chat pribadi seperti daftar/status reservasi tetap diproses backend tanpa mengirim isi reservasi ke Gemma. RAKA tidak dapat membuat, membatalkan, atau menyetujui reservasi lewat chat.
- Jika provider timeout, mencapai rate limit, atau mengembalikan JSON yang tidak valid, backend kembali ke jawaban deterministik.
- Dengan konfigurasi AI aktif, teks pesan saat ini yang telah disamarkan dan ringkasan terbatas fakta ruangan yang relevan dikirim ke OpenRouter. Riwayat percakapan, ID akun, dan data reservasi pribadi tidak dikirim.

Untuk tahap uji coba, pantau penggunaan dan batas harian pada dashboard OpenRouter. Free variant dapat terkena rate limit atau sesekali tidak tersedia; jangan mengandalkannya sebagai satu-satunya mekanisme jawaban.
