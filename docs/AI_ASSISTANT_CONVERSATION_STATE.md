# Assistant Conversation State and Confidence (Stage 2.4)

## Scope

This stage adds short-lived conversational state for the authenticated Student assistant and a transparent deterministic intent confidence score. It does not persist raw chat messages, grant an LLM database access, or execute reservation transactions.

## Conversation state

- Conversations are owned by the authenticated Student user.
- A conversation expires after 30 minutes of inactivity; each valid turn refreshes the expiry.
- The database stores only structured search slots (faculty, building, capacity, facilities, date/time, participant count, and bounded search terms) plus the last intent.
- Raw input, normalized text, generated response text, and private reservation content are not stored in conversation state.
- A requested conversation ID owned by another user returns 404 without revealing whether it exists.
- Missing slots can be continued from the same active conversation. New explicit criteria override old criteria. Negation does not re-add previous faculty/building/facility requirements. Reset phrases start a new search context.
- Unknown or expired conversation IDs result in a new conversation identifier.

## Confidence

The response confidence is a deterministic rule-strength score based on the exact matched rule and supporting structured evidence. It is not a calibrated probability and must not be presented as an ML confidence probability. The response confidence_basis is RULE_HEURISTIC.

## Security

- All conversation reads and writes happen after require_student.
- Every conversation query is scoped to its UUID and owner.
- State is bounded and allowlisted.
- No chat text is included in analytics or persistent state.
- Reservation reads, when implemented by the assistant, must always filter by authenticated user.id.
- Reservation creation/cancellation continue to use their existing confirmation and validation workflow outside the assistant.

## Migration

Alembic revision f7c2a91d6e40 creates the conversation-state table and owner/expiry index. It has a reversible downgrade. The migration must be exercised against SQLite and PostgreSQL in CI before deployment.
