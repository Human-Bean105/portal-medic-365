# Medi API

All endpoints are `POST` with a JSON body. Locally they are served by `server.py`; on Vercel by `api/*.py`.

## Common request fields

| Field | Type | Notes |
|---|---|---|
| `messages` | list | `{"role": "user" or "assistant", "content": string or parts}`. Other roles are dropped. Parts: `{"type": "text", "text": ...}` or `{"type": "image_url", "image_url": {"url": "data:image/..."}}`. |
| `mode` | `"health"` or `"wellbeing"` | Default `health`. |
| `lang` | one of `en fr es zh-Hans zh-Hant pa hi tl ko vi fa ar` | App language; Medi still replies in the language the person writes in. |
| `patient` | `"self"` or `"other"` | The profile is used only for `self`. |
| `profile` | object | Optional self-reported health profile (strings). |

Add the header `X-Medi-Dev: <MEDI_DEV_TOKEN>` to receive the pipeline trace.

## `/stream`

Server-sent events, in order:

1. `{"type": "alerts", "alerts": [{"label", "advice"}]}`: sent first, before retrieval or generation.
2. `{"type": "delta", "text": ...}`: pieces of the JSON answer as the model writes it (the `reply` field comes first).
3. `{"type": "done", "result": {...}}`: the finished answer (see `/consult`), or `{"type": "error", "error": ...}`.

## `/consult`

The same answer in one response. Health mode result:

```json
{
  "reply": "...",
  "stage": "gathering | assessment",
  "triage": {"level": "emergency | urgent_care | clinic | home_care | unknown", "headline": "...", "reasons": []},
  "conditions": [{"name": "...", "status": "probable explanation | possibility | important to rule out",
                  "explanation": "...", "supporting": [], "against": []}],
  "important_unknowns": [], "next_steps": [], "red_flags_to_watch": [], "quick_replies": [],
  "citations": [1, 3],
  "safety_alerts": [{"label": "...", "advice": "..."}],
  "sources": [{"title": "...", "source": "...", "url": "..."}],
  "evidence_status": "sufficient | partial | insufficient | none | not_checked | not_needed | not_used",
  "limitations": ["Medi's reference library doesn't cover this question well, so this is general guidance."]
}
```

Wellbeing mode replaces `stage`, `triage`, and the lists with `"risk": {"level": "none | elevated | crisis", "reason": "..."}`.
The model's output is constrained by strict JSON schemas (`medi/prompts.py`); `sources` always come from retrieved records.

## Other endpoints

| Endpoint | Body | Returns |
|---|---|---|
| `/screen` | `{"text", "lang"}` | `{"alerts": [...]}` from the deterministic screener (used during voice calls). |
| `/retrieve` | `{"messages", "mode", "lang", "hint"}` | `{"passages": [{"t", "s", "u", "x"}]}` (hybrid retrieval, no analyzer or reranker, for fast voice replies). |
| `/summary` | conversation fields | `{"summary": markdown}` printable visit summary. |
| `/speak` | `{"text"}` | MP3 audio (read aloud). |
| `/voice` | `{"sdp", ...}` | `{"sdp"}` answer to start a Realtime voice call. |
| `/inspect` | `{"text", "mode"}` + developer header | Retrieval comparison: vector only, hybrid, hybrid + reranker, with all scores. 403 without the token. |

## Errors

`400` invalid request (with a short reason), `413` body too large, `429` rate limited, `502` AI service unavailable
(generic message; details only in the server log), `500` unexpected error (generic message).
