from __future__ import annotations

import base64
import binascii
import json
import re
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile

_ARCHIVE_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "ruangkampus_indonesian_slang_dataset_v1.zip.b64"
)
_ROOT = "ruangkampus_slang_dataset/"
_LEXICON_MEMBER = _ROOT + "backend/src/ruangkampus/data/indonesian_slang_lexicon.json"
_MAP_MEMBER = _ROOT + "backend/src/ruangkampus/data/indonesian_slang_normalization_map.json"
_EXAMPLES_MEMBER = _ROOT + "backend/src/ruangkampus/data/indonesian_slang_examples.jsonl"
_MANIFEST_MEMBER = _ROOT + "manifest.json"


@lru_cache(maxsize=1)
def _archive_bytes() -> bytes:
    encoded = _ARCHIVE_PATH.read_text(encoding="ascii").strip()
    try:
        return base64.b64decode(encoded, validate=True)
    except binascii.Error as exc:
        raise ValueError("Invalid bundled RUKKA slang dataset archive") from exc


@lru_cache(maxsize=4)
def _read_json_member(member: str) -> Any:
    try:
        with ZipFile(BytesIO(_archive_bytes())) as archive:
            return json.loads(archive.read(member).decode("utf-8"))
    except (BadZipFile, KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid RUKKA slang dataset member: {member}") from exc


@lru_cache(maxsize=1)
def dataset_manifest() -> dict[str, Any]:
    manifest = _read_json_member(_MANIFEST_MEMBER)
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "1.0.0":
        raise ValueError("Unsupported RUKKA slang dataset manifest")
    return manifest


@lru_cache(maxsize=1)
def load_slang_lexicon() -> dict[str, Any]:
    payload = _read_json_member(_LEXICON_MEMBER)
    manifest = dataset_manifest()
    entries = payload.get("entries") if isinstance(payload, dict) else None
    if (
        payload.get("schema_version") != manifest["schema_version"]
        or not isinstance(entries, list)
        or len(entries) != manifest.get("entry_count")
    ):
        raise ValueError("Unsupported RUKKA Indonesian slang lexicon schema")
    return payload


@lru_cache(maxsize=1)
def load_slang_normalization_map() -> dict[str, str]:
    mapping = _read_json_member(_MAP_MEMBER)
    expected = dataset_manifest().get("safe_normalization_pair_count")
    if (
        not isinstance(mapping, dict)
        or len(mapping) != expected
        or any(
            not isinstance(key, str)
            or not key.strip()
            or not isinstance(value, str)
            or not value.strip()
            for key, value in mapping.items()
        )
    ):
        raise ValueError("Invalid RUKKA safe-exact Indonesian slang normalization map")
    return {key.casefold(): value.casefold() for key, value in mapping.items()}


@lru_cache(maxsize=1)
def load_slang_examples() -> tuple[dict[str, Any], ...]:
    try:
        with ZipFile(BytesIO(_archive_bytes())) as archive:
            raw = archive.read(_EXAMPLES_MEMBER).decode("utf-8")
    except (BadZipFile, KeyError, UnicodeDecodeError) as exc:
        raise ValueError("Invalid RUKKA slang examples file") from exc
    examples = tuple(json.loads(line) for line in raw.splitlines() if line.strip())
    if len(examples) != dataset_manifest().get("example_count"):
        raise ValueError("RUKKA slang examples count does not match the manifest")
    return examples


def merge_slang_normalization_map(legacy_mapping: dict[str, str]) -> dict[str, str]:
    """Merge dataset mappings additively; existing project mappings always win conflicts."""
    additional = load_slang_normalization_map()
    legacy = {key.casefold(): value.casefold() for key, value in legacy_mapping.items()}
    return {**additional, **legacy}


def extract_slang_hints(message: str, *, limit: int = 8) -> list[dict[str, str]]:
    """Return only context-relevant language glosses; never treat them as campus facts.

    Short regional particles/pronouns need corroborating markers from the same region
    in the current message. Ambiguous words are hints only and are never auto-rewritten.
    """
    if not isinstance(message, str) or not message.strip() or limit < 1:
        return []
    limit = min(limit, 8)
    text = message.casefold()
    hits: list[tuple[int, int, dict[str, str]]] = []
    for entry in load_slang_lexicon()["entries"]:
        matched_at: int | None = None
        matched_form: str | None = None
        for form in entry.get("surface_forms", []):
            if not isinstance(form, str) or not form:
                continue
            pattern = rf"(?<![\w]){re.escape(form.casefold())}(?![\w])"
            match = re.search(pattern, text, flags=re.UNICODE)
            if match and (matched_at is None or match.start() < matched_at):
                matched_at, matched_form = match.start(), form
        if matched_at is not None:
            hits.append((matched_at, -len(matched_form or ""), {
                "surface_form": matched_form or str(entry.get("headword", "")),
                "headword": str(entry.get("headword", "")),
                "meaning": str(entry.get("meaning", "")),
                "region": str(entry.get("region", "")),
                "category": str(entry.get("category", "")),
                "register": str(entry.get("register", "")),
                "context_note": str(entry.get("context_note", "")),
            }))
    hits.sort(key=lambda item: (item[0], item[1]))

    regional_counts: dict[str, int] = {}
    for _, _, hit in hits:
        if hit["category"] == "ragam_daerah" and len(hit["surface_form"]) <= 4:
            region = hit["region"]
            regional_counts[region] = regional_counts.get(region, 0) + 1

    output: list[dict[str, str]] = []
    seen: set[str] = set()
    for _, _, hit in hits:
        if (
            hit["category"] == "ragam_daerah"
            and len(hit["surface_form"]) <= 4
            and regional_counts.get(hit["region"], 0) < 2
        ):
            continue
        if not hit["headword"] or hit["headword"] in seen:
            continue
        seen.add(hit["headword"])
        output.append(hit)
        if len(output) >= limit:
            break
    return output
