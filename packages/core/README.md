# @persona-hub/core

Pure evaluation engine for [persona-hub](https://github.com/kenimo49/persona-hub). Takes user `answers` and a `ProfileSpec`, returns an `EvalResult`.

**Status**: MVP — `evaluate()` implemented with argmax and softmax aggregation. `threshold` method is not yet supported.

## Install

### From npm (planned)

`@persona-hub/core` is not yet published to npm. Once it is:

```bash
pnpm add @persona-hub/core
```

### From this workspace (today)

This package is part of the persona-hub monorepo. To use it from another workspace package, depend on it as `"@persona-hub/core": "workspace:*"` and let pnpm link the local source.

## Usage

```ts
import { evaluate } from '@persona-hub/core'

const result = evaluate(answers, spec)
// → { type: 'citrus', scores: {...}, confidence: 0.78, scoring_version: '0.1.0' }
```

## License

Apache-2.0. See repository [LICENSE](../../LICENSE).
