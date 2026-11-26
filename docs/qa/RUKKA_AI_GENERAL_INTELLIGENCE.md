# RUKKA AI Upgrade — General Intelligence & Conversational Reasoning

## Purpose

RUKKA must support both (1) grounded RuangKampus actions and (2) natural conversation, reasoning, explanation, ideation, and planning. General questions must never be sent to the room-search query builder merely because they mention students, rooms, capacity, or facilities.

## Runtime configuration

The LLM provider is deliberately opt-in. Configure these variables on the **backend service only** (for example, Railway backend Variables):

- `ASSISTANT_AI_ENABLED=true`
- `ASSISTANT_AI_ENDPOINT_URL`: OpenAI-compatible chat-completions endpoint
- `ASSISTANT_AI_MODEL`: provider model identifier
- `ASSISTANT_AI_API_KEY`: provider key; keep it secret and never commit it
- `ASSISTANT_AI_TIMEOUT_SECONDS=8`

Do not put the provider key in a `VITE_*` frontend variable. If the provider is disabled, missing, or unavailable, the API deliberately falls back to deterministic responses and the UI will show **Mode standar**. A successful provider-generated response is identified as **AI aktif**. Merging code does not change Railway secrets or deploy the service.

## Architecture and safety rules

- Intent routing gives explicit room operations precedence, while hypothetical and general reasoning requests route to the conversational generation path.
- Room names, capacity, facilities, locations, and availability are grounded only in backend catalogue/database results.
- The model cannot issue SQL, change reservation records, approve/cancel bookings, or invent room availability.
- A failed exact search may offer alternative slots, but mandatory capacity and facility filters must be retained.
- The browser sends at most ten previous user/assistant turns with each request. They are bounded, PII-redacted before provider transmission, held only in the current tab, and not persisted as raw chat by the API.
- Private reservation data and user identity are not sent to the generation provider.
- Existing slang data, normalization rules, adaptive-learning feedback, deterministic search, availability, and reservation flows remain in place.

## Regression prompts — repeat after every upgrade

Run these in the student RUKKA chat. Items 1–15 should produce a reasoned conversational answer, not a room-search result.

1. "Kalau semua mahasiswa membutuhkan ruang belajar, tetapi tidak semua ruang belajar cocok untuk semua mahasiswa, menurut kamu sistem peminjaman ruang kampus yang ideal harus bekerja seperti apa? Jelaskan alasanmu."
2. "Ada 3 kelompok mahasiswa. Kelompok A membutuhkan ruangan untuk 15 orang, kelompok B untuk 25 orang, dan kelompok C untuk 40 orang. Hanya tersedia dua ruangan dengan kapasitas masing-masing 30 dan 50 orang. Bagaimana kamu mengatur pemakaiannya agar semua kelompok tetap bisa belajar?"
3. "Menurutmu, apakah ruangan dengan fasilitas paling lengkap selalu menjadi pilihan terbaik? Berikan contoh kondisi ketika ruangan sederhana justru lebih cocok."
4. "Aku ketua organisasi mahasiswa. Besok ada rapat mendadak, tapi anggota kami punya jadwal kuliah yang berbeda-beda. Ada yang hanya bisa pagi, ada yang siang, dan ada yang sore. Bagaimana cara terbaik menentukan jadwal rapat tanpa merugikan sebagian besar anggota?"
5. "Bayangkan kampus memiliki 100 ruangan, tetapi setiap hari masih banyak mahasiswa kesulitan mendapatkan tempat belajar. Menurutmu, apa kemungkinan penyebabnya? Jangan langsung menyimpulkan bahwa jumlah ruangan kurang."
6. "Ada mahasiswa yang selalu memesan ruangan tetapi sering tidak datang. Menurutmu, bagaimana kampus sebaiknya menangani masalah ini tanpa membuat aturan yang terlalu merugikan mahasiswa lain?"
7. "Rancang sebuah fitur AI yang belum ada di aplikasi peminjaman ruangan kampus pada umumnya. Fitur tersebut harus benar-benar menyelesaikan masalah mahasiswa, bukan sekadar terlihat canggih."
8. "Kalau kamu diberi kesempatan mengubah sistem penggunaan fasilitas kampus dari nol, tiga perubahan apa yang paling penting kamu lakukan? Jelaskan dampak masing-masing perubahan."
9. "Buat simulasi percakapan antara mahasiswa yang sedang frustrasi karena tidak mendapatkan ruangan dan AI asisten kampus yang berusaha menyelesaikan masalahnya. Jangan terdengar seperti robot atau customer service template."
10. "Apakah menurutmu penggunaan AI di lingkungan kampus justru bisa membuat mahasiswa semakin malas berpikir? Berikan argumen yang mendukung dan menentang, lalu simpulkan pendapatmu."
11. "Seorang mahasiswa mengatakan bahwa aplikasi peminjaman ruangan tidak berguna karena mahasiswa bisa langsung bertanya kepada satpam. Apakah pendapat tersebut benar? Analisis dari beberapa sudut pandang."
12. "Kalau data yang diberikan pengguna bertentangan dengan data di database kampus, informasi mana yang seharusnya kamu percaya? Apa yang harus kamu lakukan sebelum memberikan jawaban?"
13. "Jika kamu tidak memiliki data yang cukup untuk menjawab pertanyaan mahasiswa, apakah kamu akan tetap mencoba memberikan jawaban atau mengakui keterbatasanmu? Jelaskan bagaimana kamu menentukan keputusan tersebut."
14. "Apa perbedaan antara memberikan jawaban yang terdengar meyakinkan dan memberikan jawaban yang benar-benar bisa dipertanggungjawabkan?"
15. "Jika seseorang meminta kamu memastikan sebuah ruangan tersedia, tetapi kamu belum berhasil mengakses database reservasi, apa yang harus kamu katakan kepadanya?"

### Multi-turn context test

Use one chat session:

1. "Aku sedang membuat acara seminar teknologi untuk 80 mahasiswa. Aku punya anggaran terbatas dan ingin menggunakan fasilitas kampus semaksimal mungkin."
2. "Menurutmu, apa saja yang perlu aku persiapkan?"
3. "Aku tidak punya banyak anggaran untuk konsumsi. Ada solusi lain?"
4. "Kalau ternyata pesertanya bertambah menjadi 120 orang, apakah rencana sebelumnya masih relevan?"
5. "Sekarang buatkan rencana acara yang sudah disesuaikan dengan kondisi terbaru."

RUKKA must retain the seminar context, update attendance from 80 to 120, and not ask the user to repeat unchanged details.

### Domain regression

Repeat the previously approved parser scenarios:

- "Woy RUKKA, lu bisa bantu gua nyari ruangan kaga?"
- "Gw mw pinjem rgn buat rapat besok, msh ad yg ksong g?"
- "Gue mau cari ruangan buat rapat organisasi, kapasitas 35 orang, besok jam 10 pagi. Fasilitasnya wajib ada proyektor dan AC. Kalau nggak ada, cariin alternatifnya. Jangan ubah kapasitas dan fasilitas yang gue minta tadi. Sekarang coba jelasin kenapa ruangan itu jadi rekomendasi lu."
- "Jelasin cara booking ruangan secara singkat."
- "Aktifkan mode AI."
- "Carikan ruangan kosong besok jam 10 pagi untuk 35 orang."

For the last request, RUKKA must preserve the date and parsed 10:00 start time, then ask only for the missing end time. For alternative recommendations, keep 35 participants, projector, and AC as mandatory filters.

## Acceptance criteria

- General reasoning prompts return conversational answers, not "belum ada ruangan yang cocok".
- Hypothetical capacity arithmetic is handled correctly and clearly.
- Follow-up turns retain relevant context from earlier messages.
- A room search still returns only database-backed candidates.
- The model never claims availability without a successful live check.
- No alternatives silently relax capacity or required facilities.
- Reservation instructions never claim a booking was submitted.
- Existing slang-normalization and adaptive-learning regression suites remain green.
- With provider disabled/unavailable, deterministic fallback remains safe and the UI accurately reports standard mode.
