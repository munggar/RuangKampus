from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

from ruangkampus.services.assistant_catalog import FACILITY_TERMS
from ruangkampus.services.indonesian_slang_data import merge_slang_normalization_map
from ruangkampus.schemas import (
    AssistantNormalizationResult,
    AssistantTextCorrection,
)


# Exact token mappings only: never use substring replacement for Indonesian slang.
LEGACY_SLANG_DICTIONARY: dict[str, str] = {
    "gmn": "bagaimana",
    "gimana": "bagaimana",
    "ga": "tidak",
    "gak": "tidak",
    "nggak": "tidak",
    "enggak": "tidak",
    "engga": "tidak",
    "lg": "lagi",
    "yg": "yang",
    "dmn": "di mana",
    "dpt": "dapat",
    "bs": "bisa",
    "bgt": "banget",
    "utk": "untuk",
    "krn": "karena",
    "sm": "sama",
    "mo": "mau",
    "pengen": "ingin",
    "cariin": "cari",
    "nyari": "mencari",
    "nugas": "mengerjakan tugas",
    "pinjem": "meminjam",
    "minjem": "meminjam",
    "dipake": "digunakan",
    "pake": "pakai",
    "dongg": "dong",
    "lu": "kamu",
    "lau": "kamu",
    "lo": "kamu",
    "elu": "kamu",
    "elo": "kamu",
    "gue": "aku",
    "gua": "aku",
    "sokap": "siapa",
    # Additive high-confidence campus-chat abbreviations. Existing entries remain unchanged.
    "gw": "aku",
    "mw": "mau",
    "msh": "masih",
    "jgn": "jangan",
    "rgn": "ruangan",
    "kaga": "tidak",
    "org": "orang",
}



# Preserve high-frequency fillers that the previous normalizer intentionally kept verbatim.
LEGACY_PRESERVED_SLANG: dict[str, str] = {
    "makasih": "makasih",
}

# Keep every existing project mapping and explicitly preserved form above any dataset pair.
try:
    SLANG_DICTIONARY: dict[str, str] = merge_slang_normalization_map(
        {**LEGACY_SLANG_DICTIONARY, **LEGACY_PRESERVED_SLANG}
    )
except (OSError, ValueError) as exc:
    logging.getLogger(__name__).error(
        "RUKKA slang dataset unavailable; using legacy dictionary only (error_type=%s)",
        type(exc).__name__,
    )
    SLANG_DICTIONARY = dict(LEGACY_SLANG_DICTIONARY)

# Only the requested, high-certainty spelling corrections are hard-coded.
TYPO_DICTIONARY: dict[str, str] = {
    "ruangn": "ruangan",
    "kosng": "kosong",
    "fasilits": "fasilitas",
    "proyektorr": "proyektor",
    "reservsi": "reservasi",
    "ksong": "kosong",
}

CONVERSATIONAL_FILLERS = frozenset({
    "bro", "kak", "dong", "nih", "wkwk", "hehe", "tolong", "halo", "hai", "hello", "hi", "permisi", "makasih", "terima", "kasih",
    "woy", "woi", "oy", "cuy", "min",
})

NEGATION_TOKENS = frozenset({
    "tidak", "bukan", "jangan", "tanpa", "kecuali",
})

# Words that should not become SQL room-description search terms by themselves.
# This list affects only the existing ROOM_SEARCH parser; it does not delete them
# from raw_text, normalized_text, or normalized_tokens.
PARSER_STOP_WORDS = frozenset({
    "saya", "aku", "kami", "kita", "mau", "ingin", "bagaimana", "tolong",
    "carikan", "cari", "mencari", "ruangan", "ruang", "untuk", "orang",
    "peserta", "kapasitas", "di", "pada", "hari", "tanggal", "dengan",
    "yang", "ada", "buat", "booking", "reservasi", "peminjaman", "gedung",
    "fakultas", "dan", "atau", "butuh", "bisa", "apakah", "tidak", "bukan",
    "jangan", "tanpa", "kecuali", "hanya", "sedang", "bagaimana", "banget",
    "karena", "sama", "mengerjakan", "tugas", "meminjam", "pakai", "digunakan",
    "kosong", "kelas", "tempat", "fasilitas", "proyektor", "internet",
    "besok", "senin", "selasa", "rabu", "kamis", "jumat", "sabtu", "minggu",
    "bro", "kak", "dong", "nih", "wkwk", "hehe", "ber", "cara", "jam",
    "pukul", "sampai", "hingga", "berapa", "kapan", "siapa", "apa", "mana",
    "pagi", "siang", "sore", "malam", "perlu", "mohon", "selamat", "informasi",
    "tetapi", "melainkan", "namun", "lagi", "kamu", "robot", "ya",
    "cek", "benar", "wajib", "januari", "februari", "maret", "april",
    "mei", "juni", "juli", "agustus", "september", "oktober", "november", "desember",
    "jan", "feb", "mar", "apr", "may", "jun", "jul", "agu", "aug", "sep", "okt", "oct", "nov", "des", "dec",
    # Conversation, assistant addressing, and request-intent words are not room-name filters.
    "woy", "woi", "oy", "cuy", "min", "rukka", "bantu", "membantu", "mencari",
    "meminjam", "pinjam", "masih", "ada", "msh", "mw", "ad", "org", "rgn",
    "kaga", "ksong", "muat", "panas", "gerah", "sejuk", "adem", "dingin",
})

COMMON_TOKENS = PARSER_STOP_WORDS | frozenset({
    "rapat", "meeting", "diskusi", "seminar", "kuliah", "belajar", "ujian",
    "presentasi", "acara", "kegiatan", "organisasi", "mahasiswa", "dosen",
    "admin", "kelas", "lab", "laboratorium", "multimedia", "komputer",
    "projector", "whiteboard", "wifi", "wi-fi", "internet", "ac",
    "pendingin", "speaker", "audio", "sound", "system", "computer", "pc",
    "apa", "siapa", "kapan", "berapa", "mana", "mengapa", "kenapa", "tolong",
    "terima", "kasih", "makasih", "permisi", "halo", "hai", "oke", "ok",
    "tidak", "iya", "ya", "belum", "sudah", "masih", "akan", "sedang",
    "jam", "pukul", "sampai", "hingga", "hari", "tanggal", "minggu",
    "pagi", "siang", "sore", "malam", "luas", "besar", "kecil", "dekat",
    "lantai", "utama", "lantai", "lantai", "ber", "ada", "dipakai", "dipake",
    "dipergunakan", "ruang", "ruangan", "gedung", "bangunan", "fakultas",
    "universitas", "uhamka", "ftii", "fkip", "fikes", "feb", "fai",
})

_TOKEN_PATTERN = re.compile(
    r"20\d{2}-\d{2}-\d{2}"
    # General numeric ranges must precede clock-only ranges. Otherwise "18 sampai 25"
    # is partially tokenized as the valid hour range "18 sampai 2" plus "5".
    r"|\d{1,4}\s*(?:-|–|—|s/d|sd|sampai|hingga|to)\s*\d{1,4}"
    r"|(?:[01]?\d|2[0-3])(?:[:.][0-5]\d)?\s*(?:-|–|—|s/d|sd|sampai|hingga|to)\s*(?:[01]?\d|2[0-3])(?:[:.][0-5]\d)?"
    r"|(?:[01]?\d|2[0-3])[:.][0-5]\d"
    r"|[A-Za-z0-9]+(?:[-._/][A-Za-z0-9]+)+"
    r"|[^\W\d_]+"
    r"|\d+",
    re.IGNORECASE | re.UNICODE,
)
_CODE_OR_TIME = re.compile(r"^(?:20\d{2}-\d{2}-\d{2}|.*\d.*[-._/:].*\d.*)$")
_WORD = re.compile(r"^[^\W\d_]+$", re.UNICODE)
_REPEAT = re.compile(r"([^\W\d_])\1{2,}", re.IGNORECASE | re.UNICODE)
_PHRASE_TOKEN = re.compile(r"[^\W\d_]+|[A-Za-z0-9]+(?:[-._/][A-Za-z0-9]+)+", re.UNICODE)


def _raw_tokens(value: str) -> list[str]:
    return [match.group(0) for match in _TOKEN_PATTERN.finditer(value)]


def _tokens(value: str) -> list[str]:
    return [token.casefold() for token in _raw_tokens(value)]


def _catalog_vocabulary(catalog: dict[str, Any] | None) -> tuple[set[str], dict[str, set[str]]]:
    tokens: set[str] = set()
    sources: dict[str, set[str]] = {}
    if not isinstance(catalog, dict):
        return tokens, sources

    def add_label(value: Any, source: str) -> None:
        if not isinstance(value, str):
            return
        for token in _tokens(value):
            if _WORD.fullmatch(token) and len(token) >= 3:
                tokens.add(token)
                sources.setdefault(token, set()).add(source)

    for section in ("faculties", "buildings"):
        for entry in catalog.get(section, []):
            if not isinstance(entry, dict):
                continue
            add_label(entry.get("value"), f"catalog.{section}")
            for value in entry.get("source_values", []):
                add_label(value, f"catalog.{section}")

    for entry in catalog.get("facilities", []):
        if not isinstance(entry, dict):
            continue
        if entry.get("canonical_name"):
            add_label(entry.get("canonical_name"), "catalog.facilities")
            for alias in entry.get("aliases", []):
                add_label(alias, "catalog.facilities.aliases")
        for value in entry.get("source_values", []):
            add_label(value, "catalog.facilities")

    for entry in catalog.get("rooms", []):
        if not isinstance(entry, dict):
            continue
        for field in ("room_name", "room_code", "faculty", "building", "floor", "location_description"):
            add_label(entry.get(field), f"catalog.rooms.{field}")
        for value in entry.get("facilities", []) if isinstance(entry.get("facilities"), list) else []:
            add_label(value, "catalog.rooms.facilities")

    return tokens, sources


def _levenshtein_at_most_one(left: str, right: str) -> int | None:
    if left == right:
        return 0
    if abs(len(left) - len(right)) > 1:
        return None
    if len(left) > len(right):
        left, right = right, left
    index_left = index_right = edits = 0
    while index_left < len(left) and index_right < len(right):
        if left[index_left] == right[index_right]:
            index_left += 1
            index_right += 1
            continue
        edits += 1
        if edits > 1:
            return None
        if len(left) == len(right):
            index_left += 1
            index_right += 1
        else:
            index_right += 1
    if index_left < len(left) or index_right < len(right):
        edits += 1
    return edits if edits <= 1 else None


def _dynamic_typo_candidate(token: str, vocabulary: set[str]) -> tuple[str, str] | None:
    if len(token) < 5 or token in COMMON_TOKENS or not _WORD.fullmatch(token):
        return None
    matches = sorted(
        candidate
        for candidate in vocabulary
        if len(candidate) >= 5
        and _levenshtein_at_most_one(token, candidate) == 1
    )
    # Ambiguous or equally plausible matches are intentionally not corrected.
    if len(matches) != 1:
        return None
    return matches[0], "catalog.domain_vocabulary"


def _normalize_token(token: str, vocabulary: set[str]) -> tuple[list[str], AssistantTextCorrection | None]:
    original = token
    value = unicodedata.normalize("NFKC", token).casefold()
    lowercased = value != original

    if _CODE_OR_TIME.fullmatch(value) or value.isdigit():
        correction = AssistantTextCorrection(
            original_token=original,
            normalized_token=value,
            correction_type="LOWERCASE_NORMALIZATION",
            source="preprocessing.casefold",
            confidence=None,
        ) if lowercased else None
        return [value], correction

    laughter = None
    if re.fullmatch(r"(?:wkwk|wk){2,}", value):
        laughter = "wkwk"
    elif re.fullmatch(r"(?:he){2,}", value):
        laughter = "hehe"
    if laughter and laughter != value:
        return [laughter], AssistantTextCorrection(
            original_token=original,
            normalized_token=laughter,
            correction_type="CONVERSATIONAL_VARIANT",
            source="normalizer.laughter_patterns",
            confidence=None,
        )

    if value in SLANG_DICTIONARY:
        mapped = SLANG_DICTIONARY[value]
        if mapped == value:
            correction = AssistantTextCorrection(
                original_token=original,
                normalized_token=value,
                correction_type="LOWERCASE_NORMALIZATION",
                source="preprocessing.casefold",
                confidence=None,
            ) if lowercased else None
            return [value], correction
        return mapped.split(), AssistantTextCorrection(
            original_token=original,
            normalized_token=mapped,
            correction_type="SLANG_ABBREVIATION",
            source="dictionary.indonesian_student_slang",
            confidence=None,
        )

    if value in TYPO_DICTIONARY:
        mapped = TYPO_DICTIONARY[value]
        return mapped.split(), AssistantTextCorrection(
            original_token=original,
            normalized_token=mapped,
            correction_type="STATIC_TYPO",
            source="dictionary.indonesian_typo",
            confidence=None,
        )

    repeated = _REPEAT.sub(r"\1", value)
    if repeated != value:
        mapped = SLANG_DICTIONARY.get(repeated) or TYPO_DICTIONARY.get(repeated) or repeated
        return mapped.split(), AssistantTextCorrection(
            original_token=original,
            normalized_token=mapped,
            correction_type="REPEATED_CHARACTER",
            source="normalizer.repeated_character_rule",
            confidence=None,
        )

    dynamic = _dynamic_typo_candidate(value, vocabulary)
    if dynamic:
        mapped, source = dynamic
        return [mapped], AssistantTextCorrection(
            original_token=original,
            normalized_token=mapped,
            correction_type="DOMAIN_TYPO",
            source=source,
            confidence=None,
        )

    correction = AssistantTextCorrection(
        original_token=original,
        normalized_token=value,
        correction_type="LOWERCASE_NORMALIZATION",
        source="preprocessing.casefold",
        confidence=None,
    ) if lowercased else None
    return [value], correction


def is_negated_phrase(message: str, phrase_start: int, lookback_tokens: int = 6) -> bool:
    """Return true only if a negation occurs after the nearest contrast word."""
    prefix = message[:phrase_start]
    words = [match.group(0).casefold() for match in _PHRASE_TOKEN.finditer(prefix)]
    words = words[-lookback_tokens:]
    last_negation = max((i for i, word in enumerate(words) if word in NEGATION_TOKENS), default=-1)
    last_contrast = max((i for i, word in enumerate(words) if word in {"tetapi", "melainkan", "namun"}), default=-1)
    return last_negation > last_contrast


def _phrase_occurrences(message: str, phrase: str) -> list[re.Match[str]]:
    phrase = " ".join(_tokens(phrase))
    if not phrase:
        return []
    return list(re.finditer(rf"(?<!\w){re.escape(phrase)}(?!\w)", message, flags=re.IGNORECASE))


def find_positive_catalog_values(message: str, entries: list[dict[str, Any]]) -> list[str]:
    """Return unique exact catalogue labels mentioned outside a negated context."""
    found: dict[str, str] = {}
    for entry in entries:
        value = entry.get("value")
        candidates = [value, *entry.get("source_values", [])]
        for candidate in candidates:
            if not isinstance(candidate, str) or not candidate.strip():
                continue
            for match in _phrase_occurrences(message, candidate):
                if not is_negated_phrase(message, match.start()):
                    found.setdefault(" ".join(candidate.split()).casefold(), value)
    return sorted(found.values(), key=lambda item: (item.casefold(), item))


def find_positive_facility_filters(message: str, catalog: dict[str, Any]) -> list[str]:
    """Preserve known facility requests even when no active room currently advertises them.

    Known aliases remain explicit constraints so an unavailable facility returns no match
    instead of silently being dropped from alternative-slot recommendations.
    """
    matches: set[str] = set()
    for canonical, aliases in FACILITY_TERMS.items():
        for candidate in (canonical, *aliases):
            if any(
                not is_negated_phrase(message, match.start())
                for match in _phrase_occurrences(message, candidate)
            ):
                matches.add(canonical)

    for entry in catalog.get("facilities", []):
        canonical = entry.get("canonical_name")
        source_values = [
            value for value in entry.get("source_values", [])
            if isinstance(value, str) and value.strip()
        ]
        aliases = [
            value for value in entry.get("aliases", [])
            if isinstance(value, str) and value.strip()
        ]
        if canonical:
            candidates = [canonical, *source_values, *aliases]
            if any(
                not is_negated_phrase(message, match.start())
                for candidate in candidates
                for match in _phrase_occurrences(message, candidate)
            ):
                matches.add(canonical)
        else:
            # An unmapped facility may still be filtered by its exact observed
            # database label; it is never assigned to a different canonical term.
            for source_value in source_values:
                if any(
                    not is_negated_phrase(message, match.start())
                    for match in _phrase_occurrences(message, source_value)
                ):
                    matches.add(source_value)
    # A common student preference ("jangan yang panas") means the room should have
    # cooling. Treat it as an AC constraint, never as a free-text room-name keyword.
    heat_avoidance_patterns = (
        r"\b(?:jangan|jgn)\s+(?:ruangan\s+)?(?:yang\s+|yg\s+)?panas\b",
        r"\b(?:tidak|ga|gak|nggak|enggak|kaga)\s+(?:mau|ingin)\s+(?:ruangan\s+)?(?:yang\s+|yg\s+)?panas\b",
        r"\b(?:tidak|ga|gak|nggak|enggak|kaga)\s+(?:yang\s+|yg\s+)?panas\b",
    )
    if any(re.search(pattern, message, flags=re.IGNORECASE) for pattern in heat_avoidance_patterns):
        matches.add("air conditioner")

    for comfort_word in ("sejuk", "adem", "dingin"):
        for match in _phrase_occurrences(message, comfort_word):
            if not is_negated_phrase(message, match.start()):
                matches.add("air conditioner")

    return sorted(matches, key=lambda item: (item.casefold(), item))


def normalize_indonesian_message(
    raw_text: str,
    catalog: dict[str, Any] | None = None,
) -> AssistantNormalizationResult:
    """Normalize student chat deterministically while retaining raw and negation context."""
    normalized_raw = unicodedata.normalize("NFKC", raw_text)
    raw_tokens = _raw_tokens(normalized_raw)
    original_tokens = [token.casefold() for token in raw_tokens]
    vocabulary, _sources = _catalog_vocabulary(catalog)

    normalized_tokens: list[str] = []
    corrections: list[AssistantTextCorrection] = []
    fillers: list[str] = []
    for original in raw_tokens:
        mapped_tokens, correction = _normalize_token(original, vocabulary)
        if correction:
            corrections.append(correction)
        for mapped in mapped_tokens:
            token = mapped.casefold()
            normalized_tokens.append(token)
            if token in CONVERSATIONAL_FILLERS:
                fillers.append(token)

    normalized_text = " ".join(normalized_tokens)
    parser_tokens = [token for token in normalized_tokens if token not in CONVERSATIONAL_FILLERS]
    parser_text = " ".join(parser_tokens)

    known_tokens = COMMON_TOKENS | vocabulary | set(SLANG_DICTIONARY) | set(SLANG_DICTIONARY.values())
    known_tokens |= set(TYPO_DICTIONARY) | set(TYPO_DICTIONARY.values())
    unknown = sorted({
        token for token in normalized_tokens
        if _WORD.fullmatch(token)
        and token not in known_tokens
        and token not in CONVERSATIONAL_FILLERS
        and token not in NEGATION_TOKENS
    })

    normalization_applied = (
        normalized_text != normalized_raw.strip()
        or parser_text != normalized_text
        or bool(corrections)
    )
    return AssistantNormalizationResult(
        raw_text=raw_text,
        normalized_text=normalized_text,
        tokens=original_tokens,
        normalized_tokens=normalized_tokens,
        filler_tokens=fillers,
        corrections=corrections,
        unknown_tokens=unknown,
        normalization_applied=normalization_applied,
        parser_text=parser_text,
    )
