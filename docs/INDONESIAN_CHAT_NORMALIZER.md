# Indonesian Chat Normalizer — RuangKampus (Stage 2.2)

This document describes the deterministic Indonesian text-normalization layer connected to the existing Student-only `ROOM_SEARCH` endpoint. It is not a new intent engine and does not use an LLM or an external AI provider.

## 1. Module structure

| File | Responsibility |
|---|---|
| `backend/src/ruangkampus/services/indonesian_normalizer.py` | Preprocessing, token-level slang/typo rules, catalogue vocabulary, filler separation, negation-aware catalogue matching, and normalization result construction |
| `backend/src/ruangkampus/schemas.py` | Pydantic models `AssistantTextCorrection` and `AssistantNormalizationResult`; optional `normalization` field on the existing assistant response |
| `backend/src/ruangkampus/routers/discovery.py` | Runs normalization before the existing ROOM_SEARCH filter parser and passes a filler-free parser text to it |
| `backend/src/ruangkampus/services/assistant_catalog.py` | Existing read-only source of active room, faculty, building, and facility vocabulary |
| `backend/tests/test_indonesian_normalizer.py` | 148 parameterized golden normalization cases plus structure, catalogue, typo, filler, code, and negation tests |
| `backend/tests/test_discovery.py` | Existing ROOM_SEARCH regressions plus end-to-end normalization, negative-facility, faculty contrast, ambiguity, and empty-input tests |

No frontend file, database model, migration, Availability Engine, or reservation endpoint is changed by Stage 2.2.

## 2. Processing flow

The current `POST /api/v1/assistant/chat` flow is:

1. Validate the existing `AssistantChatIn` request.
2. Read the current active-room Assistant Data Catalog using `build_assistant_data_catalog(db)`.
3. Normalize the original `message` through `normalize_indonesian_message(raw_text, catalog)`.
4. Preserve the original request text in `normalization.raw_text`.
5. Create an in-memory Pydantic request copy whose `message` is `normalization.parser_text`.
6. Run the pre-existing `ROOM_SEARCH` filter parser and candidate query.
7. Run the existing availability/alternative-slot logic unchanged.
8. Return the previous response fields plus an additive `normalization` object.

There is no database write for a chat message and no conversation history. The normalizer does not call an LLM.

## 3. Text preprocessing and dictionaries

### Preprocessing

- Unicode NFKC normalization and case folding.
- Tokenization that keeps ISO dates, time values/ranges, and alphanumeric room-code forms together.
- Whitespace normalization by rebuilding a consistent token sequence.
- Removal of punctuation that is not part of a date, time, or code token.
- Repeated-character reduction for runs of three or more letters.
- Raw input preservation for traceability.

### Student slang and abbreviations

The current exact-token dictionary includes the specified forms: `gmn/gimana`, `ga/gak/nggak/enggak`, `lg/lagi`, `yg`, `dmn`, `dpt`, `bs`, `bgt`, `utk`, `krn`, `sm`, `mo`, `pengen`, `cariin`, `nyari`, `nugas`, `pinjem/minjem`, `pake/dipake`, and `dongg`.

The requested typo dictionary includes `ruangn`, `kosng`, `fasilits`, `proyektorr`, and `reservsi`.

Mappings use exact token matching, not substring replacement. For example, `ga` becomes `tidak`, but a larger token merely containing those letters is untouched.

### Conversational fillers

The current filler set is `bro`, `kak`, `dong`, `nih`, `wkwk`, `hehe`, and `tolong`. Common repeated laughter forms such as `wkwkwk` and `hehehehe` are reduced to their filler token.

Filler words remain in `normalized_text` and `normalized_tokens`, and are recorded in `filler_tokens`. They are removed only from `parser_text` so the current room-search parser does not use them as room-description keywords.

## 4. Assistant Data Catalog integration

The normalizer receives the in-memory catalogue created from active, non-deleted `Room` records. It uses the current catalogue fields:

- `Room.room_name` and `Room.room_code`.
- `Room.faculty`.
- `Room.building`.
- `Room.floor` and `Room.location_description`.
- `Room.facilities`.

Faculty and building labels are recognized only when present in the current catalogue. No UHAMKA faculty list is hard-coded as an authoritative list.

A facility is normalized to a canonical name only when the existing Assistant Data Catalog reports a known alias group for that facility. An unmapped facility remains its observed source label and is matched only by that exact observed label; it is not re-labelled as projector, wifi, AC, or another canonical facility.

Room codes and numeric code/date/time tokens are protected from repeated-character and fuzzy typo rules. Source database values are never rewritten.

## 5. Typo correction policy

The static correction dictionary handles the explicitly requested high-certainty typos. In addition, the normalizer uses a small Levenshtein distance check against tokens found in the current catalogue:

- Only alphabetic tokens with at least five characters are considered.
- Only an edit distance of one is considered.
- Exactly one best catalogue candidate must exist.
- Multiple candidates at the same distance are treated as ambiguous and are left unchanged.
- Known common tokens, valid slang, protected codes, numeric values, dates, and times are not fuzzy-corrected.
- The normalizer does not invent a confidence score; `confidence` remains `null`.

This is intentionally conservative. It does not use external libraries or LLM typo correction.

## 6. Negation and context preservation

The normalized message preserves `tidak`, `bukan`, `jangan`, `tanpa`, and `kecuali`. It also preserves `hanya` as a restriction; `hanya` is not treated as a negative word.

For faculty, building, and facility catalogue matching, a candidate inside a locally negated clause is not selected as a positive filter. A later contrast word such as `tetapi`, `melainkan`, or `namun` starts a new positive context. For example:

- `bukan fakultas teknik tetapi fakultas ekonomi` can select the observed `Fakultas Ekonomi` catalogue entry, not the negated `Fakultas Teknik` entry.
- `jangan cari ruangan dengan proyektor` does not add `projector` as a positive facility filter.
- `wifi, bukan proyektor` keeps the positive wifi filter and ignores projector as a positive filter.
- `saya hanya membutuhkan wifi` may still select wifi as a positive filter.

Important limitation: Stage 2.2 prevents a negated facility from being misinterpreted as a positive requirement. It does not yet implement exclusion semantics that return only rooms *without* that facility. That requires a later, explicitly scoped slot/filter stage.

## 7. Normalization result structure

The typed response model is `AssistantNormalizationResult`:

| Field | Meaning |
|---|---|
| `raw_text` | Original user message, unchanged |
| `normalized_text` | Lowercase, whitespace-normalized text with deterministic corrections and punctuation cleanup |
| `tokens` | Lexical tokens extracted from the original input, case-folded before corrections |
| `normalized_tokens` | Token list after deterministic mappings |
| `filler_tokens` | Filler tokens identified in the normalized token list |
| `corrections` | Traceable correction records |
| `unknown_tokens` | Alphabetic tokens not recognized by the common or current catalogue vocabulary |
| `normalization_applied` | Whether preprocessing, correction, or filler separation changed the parser representation |
| `parser_text` | Normalized text with conversational fillers removed; negation and restrictions remain |

Each correction contains `original_token`, `normalized_token`, `correction_type`, `source`, and optional `confidence`. Confidence remains null unless a future implementation has a real calibrated score.

The `normalization` object is additive in the existing assistant response. Existing fields such as `engine`, `intent`, `slots`, `filters`, `rooms`, `alternative_slots`, `follow_up_questions`, `reservation_action`, and `privacy` remain present.

## 8. Examples

### Informal language

Input:

```text
Bro, cariin ruangn di FTII yg kosong dengan proyektor dong
```

Normalized text:

```text
bro cari ruangan di ftii yang kosong dengan proyektor dong
```

Parser text:

```text
cari ruangan di ftii yang kosong dengan proyektor
```

The current parser can then use the observed FTII catalogue entry and an observed projector alias group, while ignoring the fillers.

### Negation

Input:

```text
Saya tidak ingin ruangan yang ada AC
```

Normalized text:

```text
saya tidak ingin ruangan yang ada ac
```

The negation remains. If AC is present in the active facility catalogue, it is not added as a positive facility filter.

### Room code and date/time

Input:

```text
Ruang RK-FTII-101 pada 2026-11-30 jam 09:00-11:00
```

The code and date/time tokens remain intact for the existing parser. They are not passed through repeated-character reduction or fuzzy correction.

## 9. Limitations

- The slang/typo dictionary is deliberately finite and requires an explicit code change to add entries.
- The abbreviation `lg` expands to `lagi`; the full word `lagi` is preserved because it can mean "currently" or "again" depending on context. It is excluded only from the current ROOM_SEARCH free-text filter tokens, not rewritten in the normalized message.
- Fuzzy correction is one-edit, one-token, and only applies to a unique active-catalogue candidate of at least five characters.
- Ambiguous abbreviations such as a short faculty prefix are left as typed.
- Negated facility wording is preserved and not treated as a positive requirement, but full negative-result semantics are not implemented.
- `normalized_text` is a canonical token sequence; punctuation outside date/time/code tokens is intentionally removed.
- A symbol-only or filler-only message results in no unfiltered room search; the existing response asks for more meaningful criteria.
- The parser still has only the `ROOM_SEARCH` intent and its previous slot capabilities.

## 10. Adding vocabulary safely

1. Add high-certainty student slang/abbreviations to `SLANG_DICTIONARY` using exact tokens only.
2. Add a deterministic spelling correction to `TYPO_DICTIONARY` only when the mapping is unambiguous and meaning-preserving.
3. Do not hard-code faculty, building, room, or facility names. They must be observed in the Assistant Data Catalog.
4. Add a facility alias to the existing catalogue mapping only when it is verified as the same real-world facility; unknown values must remain raw.
5. Add golden cases to `backend/tests/test_indonesian_normalizer.py` and preserve all `backend/tests/test_discovery.py` regressions.
6. Run backend lint, SQLite/API tests, PostgreSQL integration tests, and migration checks before merging.

No new package, external service, database table, migration, intent, memory system, AI provider, or chatbot UI is introduced in Stage 2.2.
