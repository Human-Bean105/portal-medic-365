# Security and privacy review

This describes what Medi does with data today. It is a developer review, not a legal or regulatory assessment, and Medi
makes no compliance claims (for example HIPAA or PIPEDA).

## Data flow

| Data | Where it lives | Where it goes |
|---|---|---|
| Conversation (text, optional photo) | Browser memory for the current visit | Sent to Medi's server each turn, which forwards it to OpenAI to produce the answer. Not stored by Medi's server. |
| Health profile (age, conditions, medications, ...) | Browser `localStorage` on the person's device | Sent with each turn only when the visit is "for me"; never used for "someone else" visits. |
| Language and map location | Browser `localStorage` | Language goes with each request; the map location goes to Google Maps only when the map is opened. |
| Voice audio | Streamed directly from the browser to OpenAI's Realtime API (WebRTC) | Medi's server only creates the session; it never receives audio. |
| Developer token | Browser `sessionStorage` (developer dashboard only) | Sent as the `X-Medi-Dev` header. |

**External processing:** OpenAI processes conversation content to generate answers, embeddings, transcription, and speech,
under OpenAI's API data policies. The person is told this in the profile dialog. Medi does not promise confidentiality.

## Storage and retention

- Medi's server keeps no database and no conversation history. Vercel functions are stateless.
- **Logs** contain one JSON line per request: request id, endpoint, timings per stage, token counts, estimated cost, mode,
  language, number of messages, counts of alerts and passages, retrieval scores, and error types. They never contain message
  text, replies, alert labels, source titles, or the level of care. This is enforced by `Trace.summary(redact=True)` and
  covered by a unit test.
- **Session reset:** "New visit" clears the conversation in the browser. Clearing the profile form (or browser storage)
  deletes the profile. There is nothing to delete on the server.

## Access control and secrets

- `OPENAI_API_KEY` is a Vercel environment variable (marked sensitive) and in a local `.env` that is git-ignored and
  excluded from deployments. It is never sent to the browser.
- The developer trace, the analyzer output, and `/inspect` are returned only when the `X-Medi-Dev` header matches
  `MEDI_DEV_TOKEN` (constant-time comparison). Without the variable set, developer access is off.

## Input handling

- Only `user` and `assistant` messages are accepted, so a client can't inject system instructions. Photos must be inline
  image data. Messages, history length, profile fields, and request bodies (15 MB) are size-limited.
- Malformed requests get a 400 with a short reason; unexpected errors return a generic message without internal details.

## Abuse protection

- Best-effort rate limiting per IP and per server instance (40 requests per minute; 10 for voice sessions). Because Vercel
  instances don't share memory, platform-wide protection should be added as a Vercel Firewall rate-limit rule (dashboard
  setting, recommended).
- Requests to OpenAI have timeouts; temporary failures are retried a limited number of times; exhausted credits fail fast.

## Test data

All evaluation data is synthetic (written for this project or machine-translated from it). No real user conversations are
used for development or evaluation.
