# persona-hub

> Lightweight persona evaluation SDK + thin persistence API. Build domain-specific personality quizzes that share a single persona profile across services.

**Status**: Phase 0 — architecture design. Not yet ready for production use.

## Why persona-hub

Existing tools cover one piece at a time:

- **CDPs** (Segment, PostHog, RudderStack) aggregate events across services but don't evaluate quiz responses.
- **Personality APIs** (Crystal Knows, Truity, Big 5 Assessments) evaluate but don't share a profile across multiple services or domains.
- **Quiz SaaS** (Outgrow, Typeform, Riddle) embed widgets but each service stays siloed.
- **Feature flag SDKs** (LaunchDarkly) have the right architecture but the wrong domain.

persona-hub combines all three: domain-specific quiz evaluation in a client SDK, with optional persistence to a thin API for cross-service persona aggregation.

## Architecture

```
[your service]                    [persona-hub API — optional]

  Quiz UI                         POST /personas          (anonymous OK)
    +                             POST /personas/:id/signals
  @persona-hub/core (SDK)         GET  /personas/:id
    +                             GET  /personas/:id/aggregate
  @persona-hub/profiles/*.json
```

Each service evaluates locally (0ms, no network, GDPR-friendly). Persistence is opt-in — services POST results to mint a `persona_id` that other services can read later.

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full design.

## Quick start

_Phase 1 deliverable; not yet published to npm._

```ts
import { evaluate } from '@persona-hub/core'
import fragranceProfile from '@persona-hub/profiles/fragrance.json'

const result = evaluate(answers, fragranceProfile)
// → { type: 'citrus', scores: {...}, confidence: 0.78 }
```

## Profile packs

- `@persona-hub/profiles/fragrance` — perfume / home fragrance taste (kaoriq.com)
- `@persona-hub/profiles/pc` — PC build preferences (mypcrig.com, planned)
- `@persona-hub/profiles/whisky` — whisky taste profile (legacydram.com, planned)

Profiles are JSON specs that define questions, options, types, and scoring weights. Anyone can publish a profile pack.

## Architectural inspirations

- **LaunchDarkly** — client SDK with in-memory evaluation + persistent data store + streaming sync. persona-hub borrows this pattern for the persona domain.
- **Twilio Segment Engage** — cross-service profile aggregation with computed traits. persona-hub aims for similar aggregation in a self-hostable, SDK-first form.
- **Stripe Elements / Algolia InstantSearch** — SDK + thin API duality as a design contract.

## What persona-hub is NOT

- Not an authentication system (use Auth0 / Clerk / Stytch).
- Not a CDP (use Segment / PostHog for arbitrary event ingestion).
- Not a quiz builder UI (the SDK is headless; each service builds its own UI).

## License

Apache 2.0. The maintainer may offer a managed hosted service in the future; the OSS code will remain Apache 2.0.

## Status & roadmap

See [Issue #1: Architecture](../../issues/1) for the design decision, and subsequent issues for implementation tasks.
