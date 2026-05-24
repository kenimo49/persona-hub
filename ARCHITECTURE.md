# persona-hub Architecture

## Overview

persona-hub is a two-part system:

1. **Client SDK** (`@persona-hub/core` + `@persona-hub/profiles/*`)
   Evaluates quiz answers against a profile spec, locally and synchronously. Zero network, zero auth, zero infrastructure dependency.

2. **Persistence API** (FastAPI service, self-hostable)
   Optional. Persists results, accepts signals from multiple services, returns aggregated profiles.

The split lets services use persona-hub at any depth: from "embed a quiz that posts to nowhere" to "full cross-service persona aggregation with internal MBTI/BigFive translation".

## Design principles

1. **No SPOF**: If the persistence API is unavailable, quizzes still work because evaluation is local.
2. **Privacy first**: Anonymous evaluation by default. PII persists only when the user opts in.
3. **Single source of truth**: The API persistence layer uses the same `@persona-hub/core` SDK internally. No logic divergence between client-side and server-side scoring.
4. **Domain-agnostic core, domain-specific profiles**: The SDK doesn't know about fragrance, PCs, or whisky. Profiles are JSON specs anyone can author and publish.
5. **Versioned signals**: Every stored signal records the profile spec version and scoring engine version, so future changes don't silently corrupt aggregation comparability.

## Component breakdown

### `@persona-hub/core` (SDK)

```ts
import type { Answers, ProfileSpec, EvalResult } from '@persona-hub/core'

export function evaluate(answers: Answers, spec: ProfileSpec): EvalResult
```

Pure function. Takes answers + profile spec, returns typed result with scores per type. The return value carries `scoring_version` so downstream consumers know which evaluator produced it.

### `@persona-hub/profiles/*` (Profile packs)

JSON specs that define:

- `schema_version`: spec format version (currently `'1'`)
- `profile_id`: stable identifier (e.g., `fragrance.v1`)
- `profile_version`: semver of this specific pack
- `questions[]`: `{ id, prompt, options[] }`
- `options[]`: `{ id, label, weights: { typeId → number } }`
- `types[]`: `{ id, name, description }`
- `aggregation`: how to convert scores → final type (argmax, softmax, threshold, ...)

Each pack is independently versionable.

### API (persistence + aggregation)

5 endpoints, intentionally minimal:

```
POST /personas
  Auth:    API key (source service)
  Body:    { source, profile_id, profile_version, scoring_version,
             result, answers? }
  Returns: { persona_id }

POST /personas/:id/signals
  Auth:    X-API-Key (source service) that already has access, OR
           X-API-Key + Authorization: Bearer <handoff_token>
           for the first cross-source write
  Body:    { source, profile_id, profile_version, scoring_version,
             result, answers? }
  Returns: { ok: true }

GET /personas/:id
  Auth:    Same as POST /personas/:id/signals
  Returns: { persona_id, signals[], aggregate? }

GET /personas/:id/aggregate
  Auth:    Same as GET /personas/:id
  Returns: { persona_id, big_five_estimate, source_signals[],
             scoring_version, placeholder }

POST /personas/:id/handoff_token
  Auth:    X-API-Key with existing persona access
  Returns: { token, persona_id, expires_in }
```

The API does not evaluate by default. It receives evaluated results from clients and stores them. For higher integrity, source services may instead submit raw `answers`, in which case the API re-runs `evaluate()` server-side using the same `@persona-hub/core` SDK (see "Optional server-side re-evaluation" below).

### Internal aggregation engine

When `GET /aggregate` is called, the API translates raw signals (e.g., "citrus", "minimal-silent") into a unified Big Five / MBTI / DiSC / Enneagram / StrengthsFinder-style estimate. This is the "translation machine" hidden behind the API — consuming services don't surface a 5-framework UI to users.

## Cross-service persona handoff

Because browsers scope `localStorage` and cookies per origin, `persona_id` cannot be shared automatically across different domains (e.g., `kaoriq.com` and `mypcrig.com`). persona-hub uses an explicit handoff mechanism instead.

### Same-origin path (simplest)

If your services share a root domain (e.g., `kaoriq.example.com` and `pc.example.com`), set the persona cookie on the shared parent domain. No handoff needed.

### Cross-origin path: signed handoff token (recommended)

```
User completes kaoriq quiz
  → kaoriq calls evaluate() locally → result.type = "citrus"
  → kaoriq POSTs to API → persona_id = "pm_abc123"
                          (stored in kaoriq.com localStorage only)

User clicks "Continue at mypcrig" on the kaoriq result page
  → kaoriq calls POST /personas/pm_abc123/handoff_token
                  → returns { token: "ht_xxx", expires_in: 300 }
  → kaoriq redirects user to https://mypcrig.com/?ph_token=ht_xxx

mypcrig page loads, reads ph_token from URL
  → mypcrig knows persona_id = "pm_abc123" from a prior query string,
    a backend handshake, or by decoding the unsigned JWT body
  → mypcrig calls evaluate() on its own quiz → result.type = "minimal-silent"
  → mypcrig POSTs as a signal with the token attached:
        POST /personas/pm_abc123/signals
        X-API-Key:     <mypcrig key>
        Authorization: Bearer ht_xxx
    On success, the API marks the token consumed (single-use) and
    persists mypcrig's key on the persona's access list, so future
    requests from mypcrig need only X-API-Key.
  → mypcrig calls GET /personas/pm_abc123/aggregate
       → API responds with cross-domain Big Five estimate
```

The handoff token is short-lived (≤5 minutes), single-use, and bound to the originating source. This is the same pattern OAuth uses for cross-origin identity, scoped down to persona linking. There is no separate `GET /personas/by_token/...` step — the token rides on the next real persona request as a Bearer credential.

### Privacy-first path: recovery code

For users who want no implicit cross-origin links, the SDK can display a 6-digit recovery code at the end of a quiz. The user types it into another service later to retrieve the same `persona_id`. Trade-off: extra UX friction, no automated tracking surface.

## Security & privacy model

### Threat model

The hub exposes a persistence API consumed by trusted source services (e.g., `kaoriq.com`) and a `persona_id` that survives across services. Attackers may try to:

1. Spoof writes as a legitimate source service (fake "kaoriq" signals)
2. Enumerate `persona_id`s and read other users' profiles
3. Inject fabricated quiz results that bypass `evaluate()` entirely
4. Replay handoff tokens after they've been consumed

### Required defenses

| Defense | Where | Notes |
|---------|-------|-------|
| **High-entropy `persona_id`** | API | 128-bit random (ULID or UUIDv4). Never sequential. |
| **API key per source service** | API | Each consuming service (kaoriq, mypcrig) gets a key. No anonymous public writes. |
| **Signed handoff tokens** | API | Short-lived (≤5 min), single-use, JWT or signed nonce. |
| **Rate limiting** | API | Per IP + per API key. |
| **Read access control** | API | `GET /personas/:id` requires either (a) the API key that originally wrote it, or (b) a valid handoff/read token. |
| **Source whitelist per signal** | API | A signal's `profile_id` must match the source service's registered domain. |
| **Optional server-side re-evaluation** | API | When integrity matters more than client-side speed, source services submit raw `answers`; the API re-runs `evaluate()` using the same `@persona-hub/core`. |

### Privacy posture

- Anonymous evaluation always supported (no PII required to score a quiz)
- `persona_id` is opaque — does not encode user identity
- No third-party tracking, no cookies on the hub itself
- PII (e.g., raw `answers`) only persists when explicitly POSTed; consuming services should default to omitting it

### Out-of-scope (for now)

- End-to-end encryption of persona contents (signals are stored in plaintext in the API DB)
- Compliance certifications (GDPR/CCPA processor agreements, SOC2) — self-hosters are responsible

## Architectural inspirations

| Tool | What we borrow | What we explicitly don't |
|------|----------------|--------------------------|
| **LaunchDarkly** | Client SDK with in-memory evaluation against a versioned ruleset + optional persistent store. The "local fast path, optional remote" shape. | Streaming SSE transport. Phase 0 is REST-only; persona signals don't change often enough to need sub-second push. |
| **Twilio Segment Engage** | Cross-service profile aggregation, computed traits. | Generic event ingestion. persona-hub only accepts *evaluated* signals, not arbitrary events. |
| **Stripe Elements** | SDK + thin server API as a design contract. | Hosted-only model. persona-hub is self-hostable. |
| **Algolia InstantSearch** | Headless SDK pattern where each consumer builds its own UI. | Search-as-a-service hosting model. |
| **PostHog** | Open-source distribution; self-hosted API with optional managed hosting later. | Generic product analytics scope. |

## What persona-hub is NOT

- **Not an authentication system**. Use Auth0/Clerk/Stytch. persona-hub identifies *personas*, not users. A `persona_id` is not tied to login; it's tied to the result of a quiz (or set of quizzes).
- **Not a CDP**. persona-hub doesn't ingest arbitrary events. It aggregates *evaluated* persona signals.
- **Not a quiz builder UI**. The SDK is headless. Each consuming service builds its own UI in its own framework.

## License & commercialization

Apache 2.0 for all OSS code. The maintainer may operate a managed hosted version (`persona-hub.cloud` or similar) under a separate commercial agreement, but the source code in this repo remains Apache 2.0 indefinitely.

Trademarks: MBTI is a registered trademark of The Myers-Briggs Foundation; DiSC is a trademark of Wiley; StrengthsFinder is a trademark of Gallup. References to these frameworks in persona-hub describe conceptual aggregation only and do not imply endorsement.
