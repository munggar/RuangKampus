from __future__ import annotations

from typing import Any

import re


def compose_general_fallback(message: str, matched_rule: str | None = None) -> str:
    """Answer common uncertainty and unavailable-data questions without guessing."""
    text = " ".join(message.casefold().split())

    if matched_rule == "ACADEMIC_SCHEDULE_LOOKUP":
        weekdays = re.findall(
            r"\b(senin|selasa|rabu|kamis|jumat|jum'at|sabtu|minggu)\b", text
        )
        if len(set(weekdays)) > 1 or any(
            term in text for term in ("berbeda", "bertentangan", "tidak sama", "konflik")
        ):
            return (
                "Saya belum bisa memastikan jadwal ujian itu: informasi yang kamu terima saling berbeda. "
                "Data jadwal ujian, tanggal, jam, ruang, dan pengawas tidak tersedia di RUKKA, jadi saya tidak akan memilih salah satunya. "
                "Cek kalender akademik resmi atau konfirmasi ke dosen/program studi; nama mata kuliah dan semester akan membantu saat memverifikasi."
            )
        return (
            "Saya belum punya jadwal ujian terverifikasi, jadi belum bisa memastikan tanggal, jam, ruang, atau pengawasnya. "
            "Cek kalender akademik resmi atau konfirmasi ke dosen/program studi; kirim nama mata kuliah dan semester jika ingin dibantu menyusun pertanyaan verifikasi."
        )

    if any(term in text for term in ("whatsapp", "pesan wa", "isi pesan", "chat dosen")):
        return (
            "Saya tidak dapat mengakses WhatsApp atau pesan pribadi yang belum kamu berikan. "
            "Cek percakapanmu langsung atau tanyakan kepada dosen melalui kanal resmi."
        )
    if any(term in text for term in ("ipk", "nilai saya", "nilai tertinggi", "mahasiswa terbaik", "ranking mahasiswa")):
        return (
            "Saya tidak memiliki data nilai atau peringkat mahasiswa, jadi saya tidak bisa memastikan jawabannya. "
            "Untuk IPK, cek portal akademikmu; untuk peringkat, tanyakan apakah kampus menerbitkan informasi resmi tersebut."
        )
    if any(term in text for term in ("toilet", "kamar kecil", "sedang berada", "saat ini")) and any(
        term in text for term in ("jumlah", "berapa", "orang", "mahasiswa")
    ):
        return (
            "Saya tidak memiliki sensor atau data jumlah orang secara real time di toilet kampus. "
            "Coba cek langsung atau tanyakan kepada petugas kampus."
        )
    if any(term in text for term in ("berbohong", "bohong", "siapa yang berbohong", "siapa yang sedang berbohong")):
        return (
            "Saya tidak bisa mengetahui siapa yang berbohong tanpa bukti, dan tidak akan menebak tentang seseorang. "
            "Coba verifikasi informasinya lewat sumber yang dapat diperiksa atau bicarakan langsung dengan orang terkait."
        )
    if any(term in text for term in (
        "tidak yakin", "belum bisa memastikan", "informasi bertentangan", "informasi saling berbeda",
        "fallback", "penanganan kegagalan", "tidak memiliki data", "tidak tersedia di database",
        "sumber yang lebih valid", "meminta informasi tambahan", "mengarahkan saya",
    )):
        return (
            "Kalau belum yakin, saya tidak akan menebak. Saya akan menjelaskan bagian yang belum pasti, "
            "meminta konteks tambahan bila perlu, lalu memeriksa sumber resmi; jika datanya tidak tersedia atau bertentangan, "
            "saya akan menyarankan konfirmasi kepada dosen atau petugas kampus."
        )

    return (
        "Saya belum punya informasi yang cukup untuk menjawab itu dengan akurat. "
        "Saya bisa membantu mencari ruang, memeriksa ketersediaan, melihat fasilitas, atau menjelaskan alur reservasi."
    )


def compose_intent_response(intent: str, response_variant: str | None = None) -> str:
    """Create concise, casual text; all factual outputs must come from backend data."""
    if intent == "RESERVATION_HELP":
        return (
            "Buat ngajuin reservasi, pilih ruang, tentuin tanggal dan jam mulai/selesai, "
            "isi jumlah peserta serta tujuan kegiatan, terus kirim lewat fitur Reservasi. "
            "Permohonan bakal menunggu persetujuan Staff Sekretariat. Gue belum bikin reservasi dari chat ini."
        )
    if intent == "MY_RESERVATIONS":
        return "Gue tampilkan reservasi yang tercatat di akun lu."
    if intent == "RESERVATION_STATUS":
        return "Gue cek status reservasi yang tercatat di akun lu."
    if intent == "RESERVATION_CREATE_PREVIEW":
        return (
            "Bisa, gue bantu sampai formulirnya. Reservasi belum dikirim dari chat ini; "
            "pilih ruang di bawah untuk lanjut. Jadwal akan dicek lagi sebelum pengajuan dikirim."
        )
    if intent == "RESERVATION_CANCEL_PREVIEW":
        return (
            "Gue belum membatalkan reservasi apa pun. Pembatalan tetap harus dilakukan lewat "
            "detail reservasi di aplikasi dan dikonfirmasi pemilik reservasi sesuai aturan sistem."
        )
    if intent == "ROOM_DETAIL":
        return "Sebut nama atau kode ruangnya biar gue bisa tampilin detail yang tepat."
    if intent == "FAQ":
        return (
            "Gue bisa diajak diskusi, bantu cari ruang, cek ketersediaan, nyari slot alternatif, "
            "lihat detail ruang, dan jelasin alur reservasi. Mode AI ngikutin konfigurasi layanan, "
            "jadi tidak bisa diaktifkan hanya lewat chat."
        )
    if intent == "SMALLTALK":
        if response_variant == "THANKS":
            return "Santai! Semoga kegiatan kampus lu lancar. Ada lagi yang mau gue bantu?"
        if response_variant == "GREETING":
            return "Yo! Mau cari ruang, cek jadwal kosong, atau nanya soal fasilitas?"
        return "Wkwk, gue RUKKA, asisten virtual RuangKampus. Gas, mau cari ruang apa?"
    return "Gue bantu urusan ruang kampus: cari ruang, cek jadwal, fasilitas, dan info reservasi."


def compose_room_detail(room: dict[str, Any]) -> str:
    facilities = ", ".join(room.get("facilities") or []) or "Fasilitasnya belum tercatat"
    faculty = f", {room['faculty']}" if room.get("faculty") else ""
    location = f", lantai {room['floor']}" if room.get("floor") else ""
    return (
        f"{room['room_name']} ada di {room['building']}{faculty}{location}. "
        f"Kapasitas {room['capacity']} orang. Fasilitas: {facilities}."
    )


def compose_search_result(
    *,
    intent: str,
    room_count: int,
    alternative_count: int,
    has_complete_availability_window: bool,
    has_effective_search_criteria: bool,
    filters: dict[str, Any] | None = None,
    follow_up_facilities: list[str] | None = None,
) -> str:
    filters = filters or {}
    facility_labels = {
        "air conditioner": "AC",
        "wifi": "Wi-Fi",
        "projector": "proyektor",
        "whiteboard": "whiteboard",
    }

    def join_labels(items: list[str]) -> str:
        labels = [facility_labels.get(item.casefold(), item) for item in items if item]
        if len(labels) < 2:
            return "".join(labels)
        return ", ".join(labels[:-1]) + " dan " + labels[-1]

    def criteria_summary() -> str:
        criteria: list[str] = []
        capacity = filters.get("min_capacity")
        if capacity:
            criteria.append(f"kapasitas minimal {capacity} orang")
        facilities = filters.get("facilities") or []
        if facilities:
            criteria.append("fasilitas " + join_labels(facilities))
        if filters.get("faculty"):
            criteria.append("fakultas " + str(filters["faculty"]))
        if filters.get("building"):
            criteria.append("gedung " + str(filters["building"]))
        return ", ".join(criteria)

    if not has_effective_search_criteria:
        return (
            "Bisa. Ceritain kebutuhan ruangnya—misalnya kapasitas, fasilitas, fakultas, atau gedung yang lu mau."
        )
    if intent == "ALTERNATIVE_SLOTS":
        return (
            f"Ketemu {alternative_count} pilihan waktu yang masih cocok. Cek jadwalnya di bawah."
            if alternative_count else
            "Belum ketemu waktu pengganti yang cocok dengan kriteria tadi. Mau ubah hari atau jamnya?"
        )
    if room_count:
        if has_complete_availability_window:
            requested_date = filters.get("date")
            date_label = (
                requested_date.strftime("%d/%m/%Y").lstrip("0")
                if hasattr(requested_date, "strftime")
                else str(requested_date or "tanggal tersebut")
            )
            start_time = filters.get("start_time")
            end_time = filters.get("end_time")
            time_label = "–".join(
                value.strftime("%H.%M") if hasattr(value, "strftime") else str(value or "")[:5]
                for value in (start_time, end_time)
            )
            return (
                f"Ada {room_count} ruang yang cocok dan terkonfirmasi tersedia {date_label}, pukul {time_label}. "
                "Pilih salah satu kartu untuk lanjut ke formulir; pengajuan belum dikirim."
            )
        requested_facilities = join_labels(follow_up_facilities or [])
        if requested_facilities:
            return (
                f"Iya, ada {room_count} ruang dari kriteria tadi yang punya {requested_facilities}. "
                "Gue tampilkan pilihannya di bawah."
            )
        summary = criteria_summary()
        result = f"Ketemu {room_count} ruang"
        if summary:
            result += f" dengan {summary}"
        result += (
            ". Kartu di bawah gue urutin dari kapasitas yang paling dekat."
            if filters.get("min_capacity")
            else ". Cek kartu di bawah untuk detailnya."
        )
        if intent == "ROOM_SEARCH":
            result += " Kalau mau cek jadwalnya juga, kasih hari dan rentang jamnya."
        return result
    if alternative_count:
        return "Belum ada yang kosong di jam itu, tapi gue nemu beberapa waktu lain yang cocok. Cek alternatifnya di bawah."
    summary = criteria_summary()
    if follow_up_facilities:
        return (
            f"Belum ada ruang dari hasil tadi yang punya {join_labels(follow_up_facilities)} "
            "sekaligus memenuhi filter lainnya. Mau ubah salah satu kriterianya?"
        )
    if summary:
        return f"Belum ketemu ruang aktif yang memenuhi {summary}. Mau ubah salah satu kriterianya?"
    return "Belum ketemu ruang yang cocok. Coba ubah kebutuhan atau filter pencariannya."


def compose_reservation_result(reservations: list[dict], *, status_only: bool) -> str:
    if not reservations:
        return "Belum ada reservasi yang tercatat di akun lu."
    if status_only:
        latest = reservations[0]
        return (
            f"Status reservasi terbaru lu {latest['status']} "
            f"buat {latest['room_name']} tanggal {latest['date']}."
        )
    return f"Ini {len(reservations)} reservasi terbaru yang tercatat di akun lu."
