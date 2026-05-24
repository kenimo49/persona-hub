# @persona-hub/core

Pure evaluation engine for [persona-hub](https://github.com/kenimo49/persona-hub). Takes user `answers` and a `ProfileSpec`, returns an `EvalResult`.

**Status**: scaffold only. Real scoring lands in [Issue #3](https://github.com/kenimo49/persona-hub/issues/3).

## Install

_Not yet published to npm._

```bash
pnpm add @persona-hub/core
```

## Usage

```ts
import { evaluate } from '@persona-hub/core'

const result = evaluate(answers, spec)
// → { type: 'citrus', scores: {...}, confidence: 0.78, scoring_version: '0.1.0' }
```

## License

Apache-2.0. See repository [LICENSE](../../LICENSE).
