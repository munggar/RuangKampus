from __future__ import annotations

from typing import Any


def compose_intent_response(intent: str, response_variant: str | None = None) -> str:
    """Create short conversational text; all factual outputs must come from backend data."""
    if intent == "RESERVATION_HELP":
        return (
            "Untuk mengajukan reservasi, pilih ruangan, tentukan tanggal dan jam "
            "mulai/selesai, isi jumlah peserta serta tujuan kegiatan, lalu kirim "
            "permohonan melalui fitur Reservasi. Permohonan yang dikirim berstatus "
            "menunggu persetujuan Staff Sekretariat. Aku belum membuat reservasi dari chat ini."
        )
    if intent == "MY_RESERVATIONS":
        return "Aku akan menampilkan reservasi yang tercatat pada akunmu."
    if intent == "RESERVATION_STATUS":
        return "Aku akan memeriksa status reservasi yang tercatat pada akunmu."
    if intent == "RESERVATION_CREATE_PREVIEW":
        return (
            "Aku bisa membantu mencari ruangan terlebih dahulu. Pengajuan reservasi "
            "belum dibuat melalui chat ini. Setelah memilih ruangan dan jadwal, "
            "lanjutkan pengajuan melalui fitur Reservasi di aplikasi."
        )
    if intent == "RESERVATION_CANCEL_PREVIEW":
        return (
            "Aku belum membatalkan reservasi apa pun. Pembatalan harus dilakukan "
            "melalui detail reservasi di aplikasi dan dikonfirmasi oleh pemilik "
            "reservasi sesuai aturan sistem."
        )
    if intent == "ROOM_DETAIL":
        return "Sebutkan nama atau kode ruangan agar aku bisa menampilkan detail yang tepat."
    if intent == "FAQ":
        return (
            "Aku bisa membantu mencari ruangan, memeriksa ketersediaan berdasarkan "
            "tanggal dan waktu, menemukan alternatif slot, melihat detail ruangan, "
            "dan menjelaskan alur pengajuan reservasi RuangKampus."
        )
    if intent == "SMALLTALK":
        if response_variant == "THANKS":
            return "Sama-sama! Semoga kegiatan kampusmu lancar. Ada yang bisa kubantu lagi?"
        if response_variant == "GREETING":
            return "Halo! Mau mencari ruangan, mengecek ketersediaan, atau bertanya tentang fasilitas?"
        return "Wkwk, aku asisten virtual RuangKampus. Aku siap membantu urusan ruangan kampus."
    return (
        "Aku fokus membantu urusan ruangan kampus: pencarian, ketersediaan, "
        "fasilitas, alternatif waktu, dan informasi reservasi."
    )


def compose_room_detail(room: dict[str, Any]) -> str:
    facilities = ", ".join(room.get("facilities") or []) or "Belum ada fasilitas yang tercatat"
    faculty = f", {room['faculty']}" if room.get("faculty") else ""
    location = f", lantai {room['floor']}" if room.get("floor") else ""
    return (
        f"{room['room_name']} berada di {room['building']}{faculty}{location}. "
        f"Kapasitasnya {room['capacity']} orang. Fasilitas: {facilities}."
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
            "Aku bisa bantu mencari ruangan. Beri tahu fakultas atau gedung, "
            "fasilitas, kapasitas, atau kata kunci ruangan yang kamu butuhkan. "
            "Untuk mengecek ketersediaan, sertakan tanggal serta jam mulai dan selesai."
        )
    if intent == "ALTERNATIVE_SLOTS":
        return (
            f"Aku menemukan {alternative_count} pilihan slot alternatif."
            if alternative_count else
            "Belum menemukan slot alternatif yang cocok. Coba ubah fakultas, gedung, "
            "fasilitas, tanggal, atau durasi penggunaan."
        )
    if room_count:
        result = f"Aku menemukan {room_count} ruangan yang sesuai dengan kriteria pencarian."
        if has_complete_availability_window:
            result += " Slot tersebut lolos pemeriksaan ketersediaan saat ini."
        return result
    if alternative_count:
        return "Tidak ada ruangan yang tersedia pada slot persis tersebut. Berikut beberapa alternatif tanggal, waktu, atau ruangan."
    return "Belum ada ruangan yang cocok. Coba ubah fakultas, gedung, kapasitas, fasilitas, atau waktu."


def compose_reservation_result(reservations: list[dict], *, status_only: bool) -> str:
    if not reservations:
        return "Belum ada reservasi yang tercatat pada akunmu."
    if status_only:
        latest = reservations[0]
        return (
            f"Status reservasi terbarumu adalah {latest['status']} "
            f"untuk {latest['room_name']} pada {latest['date']}."
        )
    return f"Ini {len(reservations)} reservasi terbaru yang tercatat di akunmu."
