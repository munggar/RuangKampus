# Brevo transactional email setup

RuangKampus already creates in-app notifications and attempts email delivery after reservation transactions commit. This provider uses Brevo's transactional email API; it does not change reservation endpoints or frontend behavior.

## Brevo account preparation

1. Create or sign in to a Brevo account.
2. Verify a sender address in the Brevo dashboard. The sender must be authorized by Brevo before it can send.
3. Generate an API key from Brevo SMTP & API settings. Use an API v3 key, not the SMTP relay password.
4. Keep the API key private. Do not put it in the frontend, repository, screenshots, or chat.

## Railway API service variables

Set these variables on the `ruangkampus-api` service in the production environment:

| Variable | Value |
|---|---|
| `EMAIL_BACKEND` | `brevo` |
| `BREVO_API_KEY` | The Brevo API v3 key |
| `BREVO_SENDER_EMAIL` | The exact verified sender email address |
| `BREVO_SENDER_NAME` | `RuangKampus` |

The existing `SMTP_TIMEOUT_SECONDS` value is also used as the Brevo HTTP request timeout. Do not set the Brevo key in `ruangkampus-web`; it belongs only in `ruangkampus-api`.

After setting the variables, Railway redeploys the API. Production configuration validation refuses to start with `EMAIL_BACKEND=brevo` when the key or sender address is missing.

## Events already connected to the mail service

- New reservation request: email to active TU/Admin accounts.
- Reservation approved: email to the student who submitted it.
- Reservation rejected: email to the student, including the rejection reason.
- Reservation cancelled by TU/Admin: email to the student.
- Reservation cancelled by student: email to active TU/Admin accounts.
- Password reset: email to the account address.

In-app notifications remain persisted in PostgreSQL and the existing API responses do not change. Email is an additional delivery channel.

## Delivery semantics and troubleshooting

The API records one email attempt per notification and intentionally does not automatically retry an ambiguous provider timeout, preventing duplicate messages. A successful Brevo API response means Brevo accepted the message for processing; it does not prove final inbox delivery. Check Brevo transactional logs for delivery, bounce, or block events.

If a message is not sent, verify that:
- `EMAIL_BACKEND=brevo` is set on `ruangkampus-api`.
- The API key is valid and has permission to send transactional emails.
- `BREVO_SENDER_EMAIL` exactly matches a sender verified in Brevo.
- The recipient address is valid and the Brevo account is permitted to send transactional email.

Local development should continue using `EMAIL_BACKEND=console`; it writes messages to `.local_mailbox/` and does not send real email.
