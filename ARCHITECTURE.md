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

## Component breakdown

### `@persona-hub/core` (SDK)

```ts
import type { Answers, ProfileSpec, EvalResult } from '@persona-hub/core'

export function evaluate(answers: Answers, spec: ProfileSpec): EvalResult
```

Pure function. Takes answers + profile spec, returns typed result with scores per type.

### `@persona-hub/profiles/*` (Profile packs)

JSON specs that define:

- `questions[]`: `{ id, prompt, options[] }`
- `options[]`: `{ id, label, weights: { typeId → number } }`
- `types[]`: `{ id, name, description }`
- `aggregation`: how to convert scores → final type (argmax, softmax, threshold, ...)

Each pack is independently versionable.

### API (persistence + aggregation)

4 endpoints, intentionally minimal:

```
POST /personas
  Body: { source, profile_type, result, answers? }
  Returns: { persona_id }

POST /personas/:id/signals
  Body: { source, profile_type, result }
  Returns: { ok: true }

GET /personas/:id
  Returns: { persona_id, signals[], aggregate? }

GET /personas/:id/aggregate
  Returns: { big_five_estimate, summary, ... }
```

The API does not evaluate. It receives evaluated results from clients and stores them.

### Internal aggregation engine

When `GET /aggregate` is called, the API translates raw signals (e.g., "citrus", "minimal-silent") into a unified Big Five / MBTI / DiSC / Enneagram / Strengths estimate. This is the "translation machine" hidden behind the API — consuming services don't surface a 5-framework UI to users.

## What persona-hub is NOT

- **Not an authentication system**. Use Auth0/Clerk/Stytch for that. persona-hub identifies personas, not users. A `persona_id` is not tied to login; it's tied to the result of a quiz.
- **Not a CDP**. persona-hub doesn't ingest arbitrary events. It aggregates *evaluated* persona signals.
- **Not a quiz builder UI**. The SDK is headless. Each consuming service builds its own UI in its own framework.

## Cross-service persona handoff

```
User completes kaoriq quiz
  → kaoriq calls evaluate() locally → result.type = "citrus"
  → kaoriq optionally POSTs to API → persona_id = "pm_abc123" (stored in localStorage)

User visits mypcrig later
  → mypcrig reads persona_id from localStorage
  → mypcrig completes its own quiz → result.type = "minimal-silent"
  → mypcrig POSTs as a signal to /personas/pm_abc123/signals
  → mypcrig calls GET /personas/pm_abc123/aggregate
  → API responds with cross-domain Big Five estimate, used for personalization
```

## Architectural inspirations

| Tool | What we borrow |
|------|----------------|
| **LaunchDarkly** | Client SDK with in-memory evaluation + persistent data store + streaming sync. Proven architecture for "local fast path + optional remote." |
| **Twilio Segment Engage** | Cross-service profile aggregation, identity resolution, computed traits. |
| **Stripe Elements** | Client SDK + thin server API as a design contract. |
| **Algolia InstantSearch** | Headless SDK pattern where each consumer builds its own UI. |
| **PostHog** | Open source distribution model; self-hosted API with hosted option later. |

## License & commercialization

Apache 2.0 for all OSS code. The maintainer may operate a managed hosted version (`persona-hub.cloud` or similar) under a separate commercial agreement, but the source code in this repo remains Apache 2.0 indefinitely.
