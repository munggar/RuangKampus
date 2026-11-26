# RuangKampus — AI Assistant API Contract (Stages 2.1–2.4 + RUKKA AI)

This document describes the Student-only room assistant, its deterministic backend execution, and the optional OpenRouter/Gemma response-generation layer.

## 1. Endpoint and access

| Property | Value |
|---|---|
| Method | `POST` |
| Path | `/api/v1/assistant/chat` |
| Authentication | Required: `Authorization: Bearer <access_token>` |
| Authorized role | `STUDENT` only |
| Current engine | `RULE_BASED` by default; `HYBRID` when the optional AI provider is used |
| Assistant identity | `RUKKA AI` — Ruang Asisten Kampus |
| Current intent | Allowlisted deterministic intents (see section 11) |
| Conversation persistence | User-owned structured search slots for up to 30 minutes; raw messages and generated answers are not persisted |
| External AI provider | Optional OpenRouter-compatible provider; disabled by default |

The endpoint resolves identity through the existing `require_student` dependency. There is no `user_id` field in the request contract, and the assistant does not accept an identity supplied by the caller as an authorization source.

TU/Admin users receive HTTP 403 from this Student-only endpoint. Schedule administration remains in the separate `/api/v1/admin/*` routes.

## 2. Request schema

The Pydantic request model is `AssistantChatIn` in `backend/src/ruangkampus/schemas.py`.

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `message` | string, 3–1000 chars | Yes | User's current message |
| `conversation_id` | UUID or null | No | Opaque identifier for the authenticated student's short-lived conversation; server rotates it after expiry |
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

The supplied identifier is scoped to the authenticated Student. The backend persists only bounded structured search slots and last intent for up to 30 minutes of inactivity; raw messages and generated replies are not stored. An ID owned by another user returns 404.

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
| `assistant_name` | string | `RUKKA AI` — stable display name for the assistant |
| `message` | string | Deterministic response when AI is disabled; otherwise a grounded natural-language response based on backend facts |
| `conversation_id` | UUID or null | Opaque ID for the current short-lived user-owned conversation |
| `intent` | allowlisted intent string | Determined by the Rule-Based Intent Engine; see section 11 |
| `slots` | object | Search filters extracted by the current parser |
| `confidence` | number 0–1 or null | Deterministic rule-strength score or accepted AI fallback score; not a calibrated probability |
| `normalization` | object | Stage 2.2 raw/normalized text, tokens, fillers, corrections, unknown tokens, and parser text; additive and optional |
| `missing_fields` | string array | Existing search details requested by follow-up logic |
| `requires_clarification` | boolean | True when the current engine asks follow-up questions |
| `clarification_message` | string or null | First current follow-up question, if any |
| `result_type` | enum | `ROOMS_FOUND`, `ALTERNATIVE_SLOTS`, `ROOM_DETAILS`, `RESERVATIONS_FOUND`, or `NO_RESULTS` |
| `requires_confirmation` | boolean | Always false; no transaction intent is implemented |
| `confidence_basis` | enum or null | `RULE_HEURISTIC` or `AI_FALLBACK` when a score is present |
| `data` | object | Structured backend result: `rooms`, `alternative_slots`, `reservations`, and `filters` |

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
    "conversation_id": "d58d925b-64a4-4d9d-99be-2d2a6f6a8d2a",
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
    "confidence": 0.82,
    "confidence_basis": "RULE_HEURISTIC",
    "missing_fields": ["date", "start_time", "end_time", "min_capacity"],
    "requires_clarification": true,
    "clarification_message": "Untuk mengecek ketersediaan, kirim tanggal, jam mulai, dan jam selesai.",
    "result_type": "NO_RESULTS",
    "requires_confirmation": false,
    "data": {
      "rooms": [],
      "alternative_slots": [],
      "reservations": [],
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
    "privacy": "Pesan asli tidak disimpan. Slot pencarian terstruktur disimpan sementara selama maksimal 30 menit."
  }
}
```

The confidence field is a deterministic rule-strength score, not a calibrated probability. confidence_basis identifies RULE_HEURISTIC or AI_FALLBACK. Conversation state stores bounded structured slots with a 30-minute inactivity TTL; raw message text is not persisted.

## 4. Result and clarification semantics

- `ROOMS_FOUND`: the current room query returned one or more room records. When a date/time range was provided, the existing availability service also filtered the records for that interval.
- `ROOM_DETAILS`: one active room was resolved from an exact observed room name/code match in the Assistant Data Catalog.
- `RESERVATIONS_FOUND`: one or more reservation summaries belonging only to the authenticated Student were returned.
- `ALTERNATIVE_SLOTS`: the existing alternative-slot function returned candidates after checking the requested criteria.
- `NO_RESULTS`: no matching rooms, reservation summaries, or alternative slots were returned.
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
- Raw chat messages are not stored as conversation history. With `ASSISTANT_AI_ENABLED=false`, no message is sent to an external provider. When enabled, the provider receives only a sanitized current message and, for response generation, a small whitelist of public room facts returned by backend search. It never receives user identity, conversation history/state, private reservation records, or database access.

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

The Stage 2.2 normalizer preserves negative wording and prevents a negated facility from becoming a positive facility filter. It does not yet implement full negative-filter semantics such as returning only rooms without AC or a projector. At the Stage 2.2 baseline, the endpoint supported only `ROOM_SEARCH`. Stage 2.3 adds deterministic intent classification; it still does not execute reservation actions, persist memory, calculate confidence, call an LLM adapter, or change the frontend chatbot.

## 11. Rule-Based Intent Detection (Stage 2.3)

The Student assistant now classifies normalized messages into an allowlisted set of deterministic intents before selecting an execution path.

Supported intent names:
- ROOM_SEARCH
- ROOM_AVAILABILITY
- ALTERNATIVE_SLOTS
- ROOM_DETAIL
- RESERVATION_HELP
- MY_RESERVATIONS
- RESERVATION_STATUS
- RESERVATION_CREATE_PREVIEW
- RESERVATION_CANCEL_PREVIEW
- FAQ
- SMALLTALK
- OUT_OF_SCOPE

The intent engine consumes normalized text and the current active-room catalogue. It uses exact phrase boundaries and context-aware checks for cancellation wording. It does not call a language model and does not assign a numeric confidence score; confidence calibration is a separate stage.

Execution boundaries in this stage:
- ROOM_SEARCH reuses the existing deterministic room parser and room query.
- ROOM_AVAILABILITY requires a complete date, start time, and end time before the availability engine is queried. Missing values produce a clarification instead of a broad query.
- ALTERNATIVE_SLOTS requires a complete date/time window and reuses the existing alternative-slot service.
- Informational, reservation-related, small-talk, and out-of-scope intents receive deterministic text responses and do not query the room catalogue.
- Reservation creation and cancellation are not performed by intent classification. Their existing application endpoints and confirmation/authorization rules remain authoritative.
- Private reservation data is not returned by the assistant at this stage. Read-only reservation intents are recognized but explicitly report that chat retrieval is not yet enabled.

The intent value is an expanded response field; legacy fields, Student-only authorization, room availability logic, and the reservation workflow remain in place.

## 11. Conversation state, intent confidence, and AI fallback

### Conversation state (Stage 2.4)

- A Student-only conversation is identified by an opaque UUID and owned by the authenticated user.
- Conversation state expires after 30 minutes of inactivity.
- Only structured slots and the last intent are stored. Raw or normalized user messages, provider prompts, model output, and generated response content are not stored.
- Missing slots in a follow-up may be carried forward from the same active conversation. New explicit values override older values. Reset phrases discard prior search criteria. Negated faculty/building/facility mentions do not re-add the old positive filter.
- An identifier owned by another student is not accessible and returns 404.
- Alembic revision f7c2a91d6e40 creates the conversation-state table.

### Function registry and backend execution

The rule engine and optional AI fallback can select only registered Student capabilities. The AI provider cannot name Python functions, provide SQL, access the database, view another user's records, or execute mutations. Room search, availability and alternative slots continue to call existing backend services. Room detail is resolved against the active-room catalogue. Reservation list/status reads are filtered by the authenticated user's ID.

Reservation create/cancel intents remain previews; the assistant does not create or cancel a reservation. The user must continue through the existing reservation workflow, where the backend rechecks availability and authorization.

### Confidence and analytics

confidence represents deterministic rule strength when confidence_basis is RULE_HEURISTIC; it is not a probability. When an enabled external AI provider supplies an accepted interpretation, the basis is AI_FALLBACK. Aggregate telemetry records intent, rule, confidence basis, result type, clarification and whether the fallback was used. It excludes raw message text, user IDs and reservation contents.

### Optional AI provider and RUKKA AI response generation

AI remains disabled by default. When enabled, the same OpenAI-compatible chat-completions endpoint supports two bounded uses:

1. **Intent fallback:** only when the deterministic intent engine returns `OUT_OF_SCOPE`. It receives the current sanitized message plus bounded observed faculty/building/facility vocabulary, then must return strict JSON for `ROOM_SEARCH`, `ROOM_AVAILABILITY`, or `ALTERNATIVE_SLOTS`. All returned campus labels are checked against the active Assistant Data Catalog before backend execution.
2. **Grounded response writing:** after backend search/availability functions have completed, RUKKA AI can turn the deterministic summary and a small whitelist of public room facts into a more natural Indonesian answer. It cannot run tools, issue SQL, change records, or override the backend result. It is not called for personal reservation-list/status intents or reservation create/cancel previews. When intent fallback already used the provider, response generation is skipped to avoid a second request in the same turn.

Recommended OpenRouter setup:
- `ASSISTANT_AI_ENABLED=false` until the API key is installed and verified.
- `ASSISTANT_AI_ENDPOINT_URL=https://openrouter.ai/api/v1/chat/completions`.
- `ASSISTANT_AI_MODEL=google/gemma-4-26b-a4b-it:free`.
- `ASSISTANT_AI_API_KEY`: the OpenRouter secret; store only in the backend environment/secret manager.
- `ASSISTANT_AI_TIMEOUT_SECONDS=6` (maximum 8 seconds).

The current response layer sends only a redacted current message, whitelisted room metadata (name/code, faculty, building, floor, capacity, facilities and location description), bounded filter values, result counts and one optional next-step question. Room database IDs are omitted. It does not send chat history, conversation state/ID, account identity, personal reservations, reservation purposes, private notes, or administrative schedule source records. Email addresses, phone numbers and long numeric identifiers in the current message are redacted before the response-writing request. Private reservation intents are answered by the deterministic backend without sending their contents to the model.

The assistant is named **RUKKA AI — asisten virtual RuangKampus**. Its response style is direct, warm and solution-oriented: present available results first, do not ask a stack of questions, and ask at most one necessary follow-up. If the backend has not checked a complete date/time range, RUKKA AI must say that availability is not yet verified. It may never invent room details, claim a room is free without a backend check, or claim a reservation has been created/cancelled.

The `engine` field becomes `HYBRID` when AI response writing or intent fallback is used. `confidence_basis` still describes intent classification strength (`RULE_HEURISTIC` or `AI_FALLBACK`); it is not a rating of generated prose. With no provider configured or when a provider request fails validation/times out, the deterministic response is returned. Provider use may be subject to OpenRouter rate limits and privacy/retention terms; review the institution's requirements before enabling it.