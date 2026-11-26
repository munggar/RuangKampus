from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from ruangkampus.services.indonesian_normalizer import is_negated_phrase


AssistantIntent = Literal[
    "ROOM_SEARCH",
    "ROOM_AVAILABILITY",
    "ALTERNATIVE_SLOTS",
    "ROOM_DETAIL",
    "RESERVATION_HELP",
    "MY_RESERVATIONS",
    "RESERVATION_STATUS",
    "RESERVATION_CREATE_PREVIEW",
    "RESERVATION_CANCEL_PREVIEW",
    "FAQ",
    "SMALLTALK",
    "OUT_OF_SCOPE",
]


@dataclass(frozen=True)
class IntentDetection:
    """Deterministic result; numeric confidence is intentionally deferred."""

    intent: AssistantIntent
    matched_rule: str
    requires_clarification: bool = False
    clarification_message: str | None = None
    response_variant: str | None = None


ROOM_TERMS = (
    "ruang", "ruangan", "rgn", "rgnya", "kelas", "room", "lab", "laboratorium", "tempat",
)
RESERVATION_TERMS = (
    "reservasi", "booking", "peminjaman", "pinjaman",
)
AVAILABILITY_TERMS = (
    "kosong", "tersedia", "available", "availability", "bebas", "nganggur",
    "dipakai", "digunakan", "terpakai", "bentrok", "free",
    "masih ada yang kosong", "ada yang kosong", "masih tersedia", "ada yang tersedia",
)
SEARCH_VERBS = (
    "cari", "carikan", "mencari", "nyari", "temukan", "mencarikan",
    "butuh", "perlu", "meminjam", "pinjam", "booking", "pesan",
    "find", "search",
)
ALTERNATIVE_PHRASES = (
    "slot alternatif", "alternatif slot", "waktu alternatif", "jam alternatif",
    "waktu lain", "jam lain", "slot lain", "jadwal lain", "pilihan waktu lain",
    "pilihan lain", "waktu pengganti", "jam pengganti",
)
DETAIL_PHRASES = (
    "detail ruangan", "detail ruang", "informasi ruangan", "informasi ruang",
    "apa fasilitas", "fasilitas apa", "berapa kapasitas", "kapasitas ruang",
    "lokasi ruang", "lokasi ruangan", "di mana ruang", "dimana ruang",
    "lantai berapa",
)
HELP_PHRASES = (
    "cara reservasi", "bagaimana reservasi", "prosedur reservasi",
    "langkah reservasi", "cara booking", "bagaimana booking",
    "cara meminjam ruangan", "cara pinjam ruangan", "cara mengajukan reservasi",
)
CANCEL_VERBS = (
    "batalkan", "membatalkan", "dibatalkan", "pembatalan", "cancel", "cancellation",
)
STATUS_TERMS = (
    "status", "pending", "menunggu", "disetujui", "approved", "ditolak",
    "rejected", "dibatalkan", "cancelled", "selesai", "completed",
)
MY_RESERVATION_PHRASES = (
    "reservasi saya", "booking saya", "peminjaman saya",
    "riwayat reservasi", "daftar reservasi", "permohonan saya",
)
CREATE_RESERVATION_PHRASES = (
    "buat reservasi", "ajukan reservasi", "mengajukan reservasi",
    "reservasikan ruangan", "booking ruangan", "pesan ruangan",
    "buat booking", "submit reservasi",
)
SMALLTALK_GREETINGS = (
    "halo", "hai", "hello", "hi", "hey", "hei", "woy", "woi", "oy",
    "bro", "sis", "cuy", "min", "assalamualaikum", "selamat pagi",
    "selamat siang", "selamat sore", "selamat malam",
)
SMALLTALK_THANKS = (
    "terima kasih", "makasih", "thanks", "thank you", "tengkyu",
)
FAQ_PHRASES = (
    "apa itu ruangkampus", "tentang ruangkampus", "fitur ruangkampus",
    "fitur apa", "apa saja yang bisa kamu bantu", "kamu bisa apa",
    "apa yang bisa dibantu", "bantuan ruangkampus",
)

# These are explicit signs that a student wants explanation, analysis, or planning,
# not a database lookup. Domain-specific intents above retain precedence.
GENERAL_REASONING_PHRASES = (
    "menurutmu", "menurut kamu", "menurut pendapatmu", "bayangkan",
    "analisis", "analisa", "jelaskan", "berikan argumen", "berikan contoh",
    "dari beberapa sudut pandang", "apa perbedaan", "apa kemungkinan penyebab",
    "bagaimana kamu mengatur", "bagaimana sistem", "rancang", "buat simulasi",
    "simulasikan", "kalau semua mahasiswa", "jika semua mahasiswa",
    "ada 3 kelompok", "ada tiga kelompok", "apa saja yang perlu aku",
    "apa saja yang perlu saya", "buatkan rencana", "rencana acara",
    "apakah selalu", "apa dampak", "apa solusi", "menyelesaikan masalah",
    "kenapa", "mengapa",
)

ROOM_OPERATION_PATTERN = re.compile(
    r"\b(?:cari(?:kan)?|nyari|temukan|cek|periksa|booking|reservasi|"
    r"pinjam|meminjam|pesan|butuh|perlu|mau|ingin|alternatif|slot)\b"
    r".{0,100}\b(?:ruang(?:an)?|rgn|room|jadwal|slot)\b"
    r"|\b(?:ruang(?:an)?|rgn|room)\b.{0,90}"
    r"\b(?:kosong|tersedia|available|kapasitas|fasilitas|proyektor|"
    r"\bac\b|\bwi-?fi\b|jadwal|alternatif|booking|reservasi)\b",
    flags=re.IGNORECASE,
)


def is_room_operation_candidate(message: str) -> bool:
    """Return true only when the utterance plausibly asks the assistant to act on room data."""
    return bool(ROOM_OPERATION_PATTERN.search(" ".join(message.casefold().split())))


def _phrase_matches(text: str, phrase: str) -> list[re.Match[str]]:
    normalized = " ".join(phrase.casefold().split())
    if not normalized:
        return []
    pattern = rf"(?<![a-z0-9]){re.escape(normalized)}(?![a-z0-9])"
    return list(re.finditer(pattern, text.casefold()))


def _has_phrase(text: str, phrases: tuple[str, ...] | list[str]) -> bool:
    return any(_phrase_matches(text, phrase) for phrase in phrases)


def _has_unnegated_phrase(text: str, phrases: tuple[str, ...] | list[str]) -> bool:
    for phrase in phrases:
        for match in _phrase_matches(text, phrase):
            if not is_negated_phrase(text, match.start()):
                return True
    return False


def _has_room_reference(text: str, catalog: dict[str, Any] | None) -> bool:
    if _has_phrase(text, ROOM_TERMS):
        return True
    if not isinstance(catalog, dict):
        return False
    for room in catalog.get("rooms", []):
        if not isinstance(room, dict):
            continue
        for field in ("room_name", "room_code"):
            value = room.get(field)
            if isinstance(value, str) and value.strip() and _has_phrase(text, (value,)):
                return True
    return False


def detect_assistant_intent(
    normalized_text: str,
    catalog: dict[str, Any] | None = None,
    *,
    has_structured_room_filters: bool = False,
    has_complete_availability_window: bool = False,
) -> IntentDetection:
    """Classify a message into allowlisted deterministic RuangKampus intents."""
    text = " ".join(normalized_text.casefold().split())
    if not text:
        return IntentDetection(
            intent="OUT_OF_SCOPE",
            matched_rule="EMPTY_INPUT",
            requires_clarification=True,
            clarification_message=(
                "Tulis kebutuhanmu terlebih dahulu. Aku bisa membantu mencari "
                "ruangan dan memeriksa ketersediaannya."
            ),
        )

    has_room = _has_room_reference(text, catalog)
    has_reservation = _has_phrase(text, RESERVATION_TERMS)

    if has_reservation and _has_unnegated_phrase(text, CANCEL_VERBS):
        return IntentDetection(
            intent="RESERVATION_CANCEL_PREVIEW",
            matched_rule="RESERVATION_CANCEL_REQUEST",
        )

    if has_reservation and _has_phrase(text, STATUS_TERMS):
        return IntentDetection(
            intent="RESERVATION_STATUS",
            matched_rule="RESERVATION_STATUS_QUERY",
        )

    if _has_phrase(text, MY_RESERVATION_PHRASES):
        return IntentDetection(
            intent="MY_RESERVATIONS",
            matched_rule="MY_RESERVATION_LIST",
        )

    if _has_phrase(text, HELP_PHRASES) and (
        has_reservation or _has_phrase(text, ("cara pinjam ruangan", "cara meminjam ruangan"))
    ):
        return IntentDetection(
            intent="RESERVATION_HELP",
            matched_rule="RESERVATION_HELP_QUESTION",
        )

    if _has_phrase(text, CREATE_RESERVATION_PHRASES):
        return IntentDetection(
            intent="RESERVATION_CREATE_PREVIEW",
            matched_rule="RESERVATION_CREATE_REQUEST",
        )

    if has_room and _has_phrase(text, DETAIL_PHRASES):
        return IntentDetection(
            intent="ROOM_DETAIL",
            matched_rule="ROOM_DETAIL_QUESTION",
            requires_clarification=True,
            clarification_message=(
                "Ruangan mana yang ingin kamu ketahui? Sebutkan nama atau kode "
                "ruangannya agar informasinya tidak tertukar."
            ),
        )

    if _has_phrase(text, ALTERNATIVE_PHRASES):
        missing_window = not has_complete_availability_window
        return IntentDetection(
            intent="ALTERNATIVE_SLOTS",
            matched_rule="ALTERNATIVE_SLOT_REQUEST",
            requires_clarification=missing_window,
            clarification_message=(
                "Untuk mencari slot alternatif, beri tahu tanggal serta jam "
                "mulai dan selesai dari jadwal yang ingin diganti."
                if missing_window else None
            ),
        )

    if _has_phrase(text, GENERAL_REASONING_PHRASES):
        return IntentDetection(
            intent="OUT_OF_SCOPE",
            matched_rule="GENERAL_REASONING_REQUEST",
        )

    if has_room and (
        _has_phrase(text, AVAILABILITY_TERMS)
        or has_complete_availability_window
        or (
            re.search(r"\b(?:besok|hari ini|senin|selasa|rabu|kamis|jumat|sabtu|minggu)\b", text)
            and re.search(r"\b(?:jam|pukul)\b", text)
        )
    ):
        missing_window = not has_complete_availability_window
        return IntentDetection(
            intent="ROOM_AVAILABILITY",
            matched_rule="ROOM_AVAILABILITY_REQUEST",
            requires_clarification=missing_window,
            clarification_message=(
                "Bisa. Untuk memeriksa ketersediaan, sebutkan tanggal, jam mulai, "
                "dan jam selesai. Contoh: besok pukul 10.00 sampai 12.00."
                if missing_window else None
            ),
        )

    if has_structured_room_filters and has_complete_availability_window:
        return IntentDetection(
            intent="ROOM_AVAILABILITY",
            matched_rule="STRUCTURED_AVAILABILITY_FILTERS",
        )

    if has_room and _has_phrase(text, SEARCH_VERBS):
        return IntentDetection(
            intent="ROOM_SEARCH",
            matched_rule="ROOM_SEARCH_VERB",
        )

    if has_structured_room_filters:
        return IntentDetection(
            intent="ROOM_SEARCH",
            matched_rule="STRUCTURED_ROOM_FILTERS",
        )

    if _has_phrase(text, FAQ_PHRASES):
        return IntentDetection(
            intent="FAQ",
            matched_rule="RUANGKAMPUS_FAQ",
        )

    if _has_phrase(text, SMALLTALK_THANKS):
        return IntentDetection(
            intent="SMALLTALK",
            matched_rule="SMALLTALK_THANKS",
            response_variant="THANKS",
        )

    if _has_phrase(text, SMALLTALK_GREETINGS):
        return IntentDetection(
            intent="SMALLTALK",
            matched_rule="SMALLTALK_GREETING",
            response_variant="GREETING",
        )

    if _has_phrase(text, ("robot", "kamu siapa", "apa kabar", "wkwk", "hehe")):
        return IntentDetection(
            intent="SMALLTALK",
            matched_rule="SMALLTALK_CASUAL",
            response_variant="CASUAL",
        )

    if has_room:
        return IntentDetection(
            intent="ROOM_SEARCH",
            matched_rule="ROOM_REFERENCE_NEEDS_CRITERIA",
            requires_clarification=True,
            clarification_message=(
                "Kamu ingin mencari ruangan, melihat detailnya, atau mengecek "
                "ketersediaannya? Ceritakan sedikit kebutuhanmu."
            ),
        )

    return IntentDetection(
        intent="OUT_OF_SCOPE",
        matched_rule="NO_SUPPORTED_INTENT",
        requires_clarification=True,
        clarification_message=(
            "Aku fokus membantu urusan ruangan kampus: pencarian, ketersediaan, "
            "fasilitas, alternatif waktu, dan informasi reservasi."
        ),
    )
