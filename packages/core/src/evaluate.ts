import type { Answers, EvalResult, ProfileSpec } from './types.js'

export const SCORING_VERSION = '0.0.0'

/**
 * Evaluate a user's answers against a profile spec.
 *
 * Scaffold stub. Real scoring logic lands in Issue #3.
 *
 * @see https://github.com/kenimo49/persona-hub/issues/3
 */
export function evaluate(_answers: Answers, _spec: ProfileSpec): EvalResult {
  throw new Error('@persona-hub/core: evaluate() is not yet implemented. See Issue #3.')
}
