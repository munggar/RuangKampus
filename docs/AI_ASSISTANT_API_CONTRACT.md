# RuangKampus — AI Assistant API Contract (Stage 2.1)

This document describes the contract implemented by the current backend. It does not describe a generative AI service.

## 1. Endpoint and access

| Property | Value |
|---|---|
| Method | `POST` |
| Path | `/api/v1/assistant/chat` |
| Authentication | Required: `Authorization: Bearer <access_token>` |
| Authorized role | `STUDENT` only |
| Current engine | `RULE_BASED` |
| Current intent | `ROOM_SEARCH` |
| Conversation persistence | Not implemented |
| External AI provider | None |

The endpoint resolves identity through the existing `require_student` dependency. There is no `user_id` field in the request contract, and the assistant does not accept an identity supplied by the caller as an authorization source.

Staff Sekretariat users receive HTTP 403 from this Student-only endpoint. Schedule administration remains in the separate `/api/v1/admin/*` routes.

## 2. Request schema

The Pydantic request model is `AssistantChatIn` in `backend/src/ruangkampus/schemas.py`.

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `message` | string, 3–1000 chars | Yes | User's current message |
| `conversation_id` | UUID or null | No | Reserved for future conversation support; currently accepted but not stored or used |
| `faculty` | string or null, max 160 | No | Explicit faculty text filter |
| `building` | string or null, max 160 | No | Explicit building text filter |
| `min_capacity` | integer 1–10000 or null | No | Minimum room capacity filter |
| `facilities` | string array, max 25 values | No | Explicit facility filters |
| `date` | ISO date or null | No | Requested campus-local date |
| `start_time` | time or null | No | Requested start time |
| `end_time` | time or null | No | Requested end time |
| `participant_count` | integer 1–10000 | No | Participant count for availability evaluation; defaults to 1 |

The `date`, `start_time`, and `end_time` fields must be supplied together. `end_time` must be later than `start_time`; overnight periods are unsupported.

The existing frontend request `discoveryApi.chat({ message })` remains valid. The current backend also retains the earlier optional filter fields.

### Request example (legacy-compatible)

```json
{
  "message": "Carikan ruangan untuk 20 orang di FTII dengan proyektor"
}
```

### Request example with reserved conversation identifier

```json
{
  "message": "Carikan ruangan rapat",
  "conversation_id": "d58d925b-64a4-4d9d-99be-2d2a6f6a8d2a"
}
```

The supplied identifier is accepted for forward compatibility, but the current implementation does not persist conversation state and returns `conversation_id: null`. It must not be interpreted as a working conversation session.

## 3. Response schema

FastAPI returns the standard business response envelope:

```json
{
  "success": true,
  "message": "Room assistant response generated",
  "data": {}
}
```

The inner Pydantic response model is `AssistantChatResponseData`. The response contains additive structured fields and preserves the fields consumed by the existing frontend.

### Structured fields

| Field | Type | Current behavior |
|---|---|---|
| `message` | string | Existing rule-based response text |
| `conversation_id` | UUID or null | Always null; no backend conversation store exists |
| `intent` | literal `ROOM_SEARCH` | The only current assistant intent |
| `slots` | object | Search filters extracted by the current parser |
| `confidence` | number 0–1 or null | Always null; no confidence model is implemented |
| `normalization` | object | Stage 2.2 raw/normalized text, tokens, fillers, corrections, unknown tokens, and parser text; additive and optional |
| `missing_fields` | string array | Existing search details requested by follow-up logic |
| `requires_clarification` | boolean | True when the current engine asks follow-up questions |
| `clarification_message` | string or null | First current follow-up question, if any |
| `result_type` | enum | `ROOMS_FOUND`, `ALTERNATIVE_SLOTS`, or `NO_RESULTS` |
| `requires_confirmation` | boolean | Always false; no transaction intent is implemented |
| `data` | object | Structured backend result: `rooms`, `alternative_slots`, and `filters` |

The `slots` object contains `faculty`, `building`, `min_capacity`, `facilities`, `date`, `start_time`, `end_time`, `participant_count`, and `search_terms`.

### Backward-compatible fields

The following existing inner response keys remain available:

- `engine`
- `intent`
- `message`
- `filters`
- `rooms`
- `alternative_slots`
- `follow_up_questions`
- `reservation_action`
- `privacy`

The duplicated `data.rooms`, `data.alternative_slots`, and `data.filters` fields provide a typed grouping for future backend consumers. The legacy top-level inner fields are intentionally retained for the current React page.

### Example response shape

This is an illustrative no-result response shape, not a claim about current production room data:

```json
{
  "success": true,
  "message": "Room assistant response generated",
  "data": {
    "message": "Belum ada ruangan yang cocok. Coba ubah fakultas, gedung, kapasitas, fasilitas, atau waktu.",
    "conversation_id": null,
    "intent": "ROOM_SEARCH",
    "slots": {
      "faculty": null,
      "building": null,
      "min_capacity": null,
      "facilities": [],
      "date": null,
      "start_time": null,
      "end_time": null,
      "participant_count": 1,
      "search_terms": []
    },
    "confidence": null,
    "missing_fields": ["date", "start_time", "end_time", "min_capacity"],
    "requires_clarification": true,
    "clarification_message": "Untuk mengecek ketersediaan, kirim tanggal, jam mulai, dan jam selesai.",
    "result_type": "NO_RESULTS",
    "requires_confirmation": false,
    "data": {
      "rooms": [],
      "alternative_slots": [],
      "filters": {
        "faculty": null,
        "building": null,
        "min_capacity": null,
        "facilities": [],
        "date": null,
        "start_time": null,
        "end_time": null,
        "participant_count": 1,
        "search_terms": []
      }
    },
    "engine": "RULE_BASED",
    "filters": {
      "faculty": null,
      "building": null,
      "min_capacity": null,
      "facilities": [],
      "date": null,
      "start_time": null,
      "end_time": null,
      "participant_count": 1
    },
    "rooms": [],
    "alternative_slots": [],
    "follow_up_questions": [
      "Untuk mengecek ketersediaan, kirim tanggal, jam mulai, dan jam selesai.",
      "Berapa jumlah peserta yang akan menggunakan ruangan?"
    ],
    "reservation_action": "NOT_CREATED",
    "privacy": "Pesan tidak disimpan sebagai riwayat percakapan dan tidak dikirim ke penyedia AI eksternal."
  }
}
```

The `confidence` and `conversation_id` null values are deliberate. The system must not fabricate a confidence score or imply that conversation memory is available.

## 4. Result and clarification semantics

- `ROOMS_FOUND`: the current room query returned one or more room records. When a date/time range was provided, the existing availability service also filtered the records for that interval.
- `ALTERNATIVE_SLOTS`: no exact room match was returned for the requested date/time, but the existing alternative-slot function returned candidates.
- `NO_RESULTS`: neither room results nor alternative slots were returned.
- `missing_fields`: fields the existing follow-up logic requests to refine an availability/capacity search. They are not a new reservation-validation contract.
- `requires_confirmation`: false because the current endpoint only searches and recommends. It does not create or cancel reservations.

The endpoint continues to return availability-derived results from existing backend functions. It does not return academic course names, schedule import source metadata, administrator activity, or another user's reservation records.

## 5. Assistant data catalogue

The internal service is implemented in `backend/src/ruangkampus/services/assistant_catalog.py`. It reads active, non-deleted rows from `rooms` and builds an in-memory catalogue. It does not create or update database records and is not exposed as a public endpoint.

### Faculty and building metadata

- Source: `Room.faculty` and `Room.building`.
- Empty values and exact configured placeholder labels (including `Belum ditentukan`, `N/A`, `unknown`, and `-`) are excluded from selectable catalogue values.
- Distinct labels are grouped after trimming whitespace and comparing case-insensitively.
- `source_values` retains the exact original text values found in the database.
- No official UHAMKA faculty list or inferred faculty aliases are created.

### Facility metadata

- Source: `Room.facilities` JSON array.
- The only canonical facility aliases are the terms already present in the original `FACILITY_TERMS` dictionary used by the previous assistant parser.
- The catalogue includes a known mapping group only when at least one matching source value is observed in active room records.
- Unrecognized source values remain searchable using their observed text, have `canonical_name: null`, and are not mapped to a different facility.
- Original values are returned in `source_values`; no database value is rewritten.

### Room metadata

Catalogue room entries are derived from stored room IDs, names, codes, faculty, building, floor, location description, capacity, facilities, and operating hours. Placeholder building/location values are not considered valid metadata.

## 6. Read-only data-quality assessment

Run the report using the database selected by `DATABASE_URL`:

```bash
cd backend
PYTHONPATH=src python -m ruangkampus.cli assistant-data-quality
```

The CLI reads active, non-deleted `rooms` records and prints JSON. It does not commit changes, update source labels, or run migrations.

The report includes:

- Active room count.
- Faculty, building, location, and facility completeness counts.
- Distinct observed metadata values and spelling-variation groups.
- Operating-hours counts: valid, missing, and inconsistent.
- Per-room status: `VALID`, `INCOMPLETE`, or `INCONSISTENT`.
- Report-level `UNABLE_TO_VERIFY` and reason code if the database query fails.

A successful query sets `verification_status: VERIFIED`. This indicates only that the configured database query succeeded. It does not establish that the database is an authoritative UHAMKA source or that every imported room value has been campus-verified.

## 7. Errors

The standard error envelope is:

```json
{
  "success": false,
  "message": "Request validation failed",
  "errors": []
}
```

| HTTP status | Meaning |
|---:|---|
| 401 | Missing, invalid, or expired authentication |
| 403 | Authenticated caller is not Student |
| 422 | Invalid request, including incomplete date/time group or invalid period |
| 429 | Existing assistant per-process rate limit exceeded |
| 500 | Unexpected application/database failure |

## 8. Security and scope

- Student authentication is mandatory.
- User identity is obtained from the backend access token and active session.
- The endpoint has no administrative function registry or administrative intent.
- It does not expose full academic schedules.
- It does not query or return reservation ownership/history.
- It does not create, cancel, approve, reject, or modify reservations.
- Reservation creation and cancellation continue to use their existing APIs and authorization rules.
- Chat messages are not stored as conversation history and are not sent to an AI provider.

## 9. Historical non-goals in the Stage 2.1 baseline

The following items were not implemented at the Stage 2.1 merge point. Stage 2.2 has since added the Indonesian Chat Normalizer described in section 10.

Other items still outside scope:

- New multi-intent Rule-Based Engine.
- Confidence scoring.
- Conversation memory or session ownership.
- LLM intent fallback or provider adapter.
- Generative answers.
- Reservation transaction intents or confirmation state.
- Chat analytics or feedback persistence.
- A new faculty master table, facility master table, database migration, or bulk metadata correction.

The frontend TypeScript interfaces have additive optional fields only. No chatbot UI behavior is changed.

## 10. Indonesian Chat Normalizer (Stage 2.2)

The existing Student-only `POST /api/v1/assistant/chat` flow now runs deterministic Indonesian text normalization before the existing `ROOM_SEARCH` filter parser.

### Processing and compatibility

- The original `message` is retained as `normalization.raw_text`.
- `normalized_text` and `normalized_tokens` contain lowercase tokens, deterministic spelling/slang corrections, and punctuation cleanup.
- `filler_tokens` records conversational fillers; `parser_text` removes those fillers only.
- Negation and restriction words (including `tidak`, `bukan`, `jangan`, `tanpa`, `kecuali`, and `hanya`) remain in the normalized representation.
- The current parser receives `parser_text`; it remains the same `ROOM_SEARCH` intent and uses the same candidate/availability functions.
- The response has an additive `normalization` object. Existing legacy response keys and the existing `AssistantChatIn` request shape remain supported.
- Raw chat messages are not persisted. The normalizer does not call an external AI provider.

### Catalogue and ambiguity rules

The normalizer reads the existing Assistant Data Catalog built from active, non-deleted room records. It uses observed room names/codes, faculty, building, floor, location descriptions, and facilities. Faculty/building labels are not invented or hard-coded.

Known facility aliases are selected only when their canonical alias group is present in the current catalogue. An unmapped facility may be matched using its exact observed source label but is never assigned a different canonical facility. A locally negated facility/faculty/building mention is not promoted to a positive filter. A later contrast word (`tetapi`, `melainkan`, or `namun`) starts a new context. Ambiguous catalogue candidates are not arbitrarily selected.

### Correction policy

- Exact token-level slang and typo dictionaries are used; substring replacement is not used.
- Repeated runs of three or more letters are reduced for ordinary alphabetic tokens.
- Date, time, numeric, and alphanumeric room-code tokens are protected.
- Catalogue typo matching uses at most one edit and requires one unique candidate of at least five characters.
- Correction records provide original/normalized token, correction type, source, and optional confidence. Confidence remains null because no calibrated score exists.

### Scope limitation

The Stage 2.2 normalizer preserves negative wording and prevents a negated facility from becoming a positive facility filter. It does not yet implement full negative-filter semantics such as returning only rooms without AC or a projector. The endpoint still supports only `ROOM_SEARCH`; no additional intent, reservation action, confidence engine, memory, LLM adapter, or frontend chatbot change is introduced.

