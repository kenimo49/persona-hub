# persona-hub

**English** · [日本語](./README.ja.md)

> Lightweight persona evaluation SDK + thin persistence API. Build domain-specific personality quizzes that share a single persona profile across services.

**Status**: Phase 0 — architecture design. Not yet ready for production use.

## What it looks like

You add a 5-question quiz to your site. The SDK scores it instantly in the browser. Optionally, you post the result to a persona-hub server so the same user can carry that profile to a related site.

```ts
import { evaluate } from '@persona-hub/core'
import fragranceProfile from '@persona-hub/profiles/fragrance.json'

// answers: { q1: 'a', q2: 'c', ... }
const result = evaluate(answers, fragranceProfile)
// → { type: 'citrus', scores: { citrus: 0.83, woody: 0.41, ... }, confidence: 0.78 }
```

That's the SDK side. The API side is four endpoints (`POST /personas`, `POST /personas/:id/signals`, `GET /personas/:id`, `GET /personas/:id/aggregate`) and is entirely optional — your quiz works without it.

## Why persona-hub

Existing tools cover one piece at a time:

- **CDPs** (Segment, PostHog, RudderStack) aggregate events across services but don't evaluate quiz responses.
- **Personality APIs** (Crystal Knows, Truity, Big 5 Assessments) evaluate but don't share a profile across multiple services or domains.
- **Quiz SaaS** (Outgrow, Typeform, Riddle) embed widgets but each service stays siloed.
- **Feature flag SDKs** (LaunchDarkly) have the right SDK-plus-store architecture but the wrong domain.

persona-hub combines these patterns: domain-specific quiz evaluation in a client SDK, with optional persistence to a thin API for cross-service persona aggregation.

## Architecture

```
[your service]                    [persona-hub API — optional]

  Quiz UI                         POST /personas          (signed by source service)
    +                             POST /personas/:id/signals
  @persona-hub/core (SDK)         GET  /personas/:id
    +                             GET  /personas/:id/aggregate
  @persona-hub/profiles/*.json
```

Each service evaluates locally (0ms, no network, GDPR-friendly by default). Persistence is opt-in — services POST results to mint a `persona_id` that other services can read later (via an explicit signed handoff, since browsers scope storage per origin).

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full design, including the security and privacy model.

## Profile packs

- `@persona-hub/profiles/fragrance` — perfume / home fragrance taste (kaoriq.com)
- `@persona-hub/profiles/pc` — PC build preferences (mypcrig.com, planned)
- `@persona-hub/profiles/whisky` — whisky taste profile (legacydram.com, planned)

Profiles are JSON specs that define questions, options, types, and scoring weights. Anyone can publish a profile pack — see [CONTRIBUTING.md](./CONTRIBUTING.md).

## Architectural inspirations

- **LaunchDarkly** — client SDK with in-memory evaluation against a versioned ruleset + optional persistent data store. persona-hub borrows the "local fast path, optional remote" shape (not the streaming transport, at least not in Phase 0).
- **Twilio Segment Engage** — cross-service profile aggregation with computed traits. persona-hub aims for similar aggregation in a self-hostable, SDK-first form.
- **Stripe Elements / Algolia InstantSearch** — SDK + thin API duality as a design contract.

## What persona-hub is NOT

- Not an authentication system (use Auth0 / Clerk / Stytch).
- Not a CDP (use Segment / PostHog for arbitrary event ingestion).
- Not a quiz builder UI (the SDK is headless; each service builds its own UI).

## Trademarks & disclaimers

References to MBTI, DiSC, Big Five, Enneagram, and StrengthsFinder describe the conceptual frameworks for internal aggregation. persona-hub is not affiliated with, endorsed by, or sponsored by any of the trademark holders (The Myers-Briggs Foundation, Wiley, Gallup, etc.). The internal aggregation engine uses publicly available item pools (e.g., IPIP for Big Five) where applicable.

## License

Apache 2.0. The maintainer may offer a managed hosted service in the future; the OSS code will remain Apache 2.0.

## Contributing & security

- Design discussion: open an [Issue](https://github.com/kenimo49/persona-hub/issues)
- Code contributions: see [CONTRIBUTING.md](./CONTRIBUTING.md)
- Security reports: see [SECURITY.md](./SECURITY.md)
- Community standards: see [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md)

## Status & roadmap

See [Issue #1: Architecture](https://github.com/kenimo49/persona-hub/issues/1) for the design decision, and the open issues list for the implementation plan.
