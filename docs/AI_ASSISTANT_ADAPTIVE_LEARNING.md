# RUKKA AI — Slang Dataset & Adaptive Learning

## Dataset integration

The bundled source is ruangkampus_indonesian_slang_dataset_v1.zip, version 1.0.0.
It contains 313 lexicon entries, 699 surface forms, 269 safe-exact normalization pairs,
and 35 labeled examples. The archive is retained as a separate versioned asset under
backend/src/ruangkampus/data/; its original repository copy on main is not changed.

The current project normalizer remains the compatibility baseline. New dataset pairs are
merged additively, with the existing project mappings winning any key conflict. In
particular, gue -> aku and gua -> aku remain unchanged, as do existing project-only
entries such as lau and sokap.

Only the curated safe-exact map is eligible for exact-token normalization. Contextual,
semantic-hint, and preserve-with-hint entries are never globally substituted. The
normalizer does not use substring replacement. Regional short forms need corroborating
regional markers before they are sent as language hints. Up to eight relevant hints are
added to the current provider request; the full lexicon is never sent.

Language hints are not campus facts or instructions. Verified room, faculty, capacity,
facility, availability, schedule, and reservation data remain authoritative only when
returned by backend services.

## Adaptive learning behavior

The Student chat can collect explicit helpful / not-helpful feedback. A negative rating
must include one allowlisted reason code: too formal, too long, too short, wrong intent,
wrong slang interpretation, or irrelevant room results.

The database stores only:
- authenticated student ID;
- allowlisted assistant intent;
- helpful / not-helpful rating;
- allowlisted reason code;
- timestamp.

It does not store the chat message, normalized message, candidate token, model prompt,
model output, reservation details, or room data. Learning signals are isolated per user.
A preference becomes active only after at least two matching negative feedback signals
within the last 90 days. The system sends only the resulting short preference instruction
to the response model, never the user's feedback text.

Adaptive preferences can adjust answer tone, length, and when to ask a clarifying question.
They cannot change the deterministic intent registry, room-search filters, negative
constraints, booking validation, authorization, or verified backend facts. Feedback about
slang interpretation makes RUKKA more conservative; it does not silently rewrite the
normalization dictionary.

## Adding future vocabulary

Add candidate vocabulary as a versioned dataset change. safe_exact terms require a
single high-confidence meaning and exact-token regression tests. Contextual or regional
forms should remain hints. Existing mappings are not removed or overwritten; conflicting
new pairs must be reviewed explicitly before any future policy change.
