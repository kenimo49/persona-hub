# @persona-hub/profiles

Profile packs for [`@persona-hub/core`](../core). Each pack is a JSON spec defining questions, options, types, and scoring weights for a specific domain.

## Available packs

| Pack | Domain | Status |
|------|--------|--------|
| `fragrance` | perfume / home fragrance taste | available ([fragrance.json](./src/fragrance.json)) |
| `pc` | PC build preferences | planned |
| `whisky` | whisky taste profile | planned |

## Using a pack

```ts
import { evaluate } from '@persona-hub/core'
// Bundlers (Vite, esbuild, webpack) accept the import directly:
import fragrance from '@persona-hub/profiles/fragrance.json'
// Native Node ESM needs the import attribute:
// import fragrance from '@persona-hub/profiles/fragrance.json' with { type: 'json' }

const answers = { fq_01: 'a', fq_02: 'a', fq_03: 'a', fq_04: 'd', fq_05: 'a' }
const result = evaluate(answers, fragrance)
// → { type: 'citrus', scores: { citrus: 0.996, aquatic: 0.002, ... }, confidence: 0.996, ... }
```

The pack ships as plain JSON; consumers re-validate it through `@persona-hub/core`'s `evaluate()`.

## Contributing a pack

See [CONTRIBUTING.md](../../CONTRIBUTING.md#profile-pack-contribution-standards) at the repo root for the standards a profile pack must meet (evidence-based descriptions, licensing, tests, etc.).

## License

Apache-2.0. Each JSON spec inherits the repository [LICENSE](../../LICENSE).
