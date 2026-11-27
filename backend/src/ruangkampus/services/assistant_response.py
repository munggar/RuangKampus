from __future__ import annotations

from typing import Any


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
            "Gue bantu cari ruangannya dulu. Pengajuan reservasi belum dibuat lewat chat ini. "
            "Setelah lu pilih ruang dan jadwal, lanjut ajukan lewat fitur Reservasi."
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
            "jadi nggak bisa diaktifin cuma lewat chat."
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
) -> str:
    if not has_effective_search_criteria:
        return (
            "Gue bisa bantu cariin ruang. Kasih tahu fakultas atau gedung, fasilitas, "
            "kapasitas, atau kebutuhan ruang yang lu cari. Buat cek kosongnya, sebutin tanggal plus jam mulai–selesai."
        )
    if intent == "ALTERNATIVE_SLOTS":
        return (
            f"Gue nemu {alternative_count} pilihan slot alternatif."
            if alternative_count else
            "Belum nemu slot alternatif yang cocok. Coba ubah fakultas, gedung, fasilitas, "
            "tanggal, atau durasi pemakaian."
        )
    if room_count:
        result = f"Gue nemu {room_count} ruang yang cocok sama kriteria lu."
        if has_complete_availability_window:
            result += " Slotnya tersedia saat terakhir dicek."
        return result
    if alternative_count:
        return "Belum ada ruang yang kosong di jam itu. Gue cariin alternatif tanggal, jam, atau ruang yang masih cocok."
    return "Belum ada ruang yang cocok. Coba ubah fakultas, gedung, kapasitas, fasilitas, atau waktunya."


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
