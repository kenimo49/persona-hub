/** A user's answers to a quiz. Keys are question IDs; values are option IDs. */
export type Answers = Record<string, string>

/** A type a user can be classified into (e.g., "citrus", "woody"). */
export interface TypeSpec {
  id: string
  name: string
  description?: string
  /** Optional localized description, keyed `description_<bcp47>` (e.g., `description_ja`). */
  [localizedDescription: `description_${string}`]: string | undefined
}

/** A single option a user can pick for a question. */
export interface OptionSpec {
  id: string
  label: string
  /** Per-type weight contributed when this option is selected. */
  weights: Record<string, number>
  /** Optional localized label, keyed `label_<bcp47>` (e.g., `label_ja`). */
  [localizedLabel: `label_${string}`]: string | undefined
}

/** A single quiz question and its options. */
export interface QuestionSpec {
  id: string
  prompt: string
  options: OptionSpec[]
  /** Optional localized prompt, keyed `prompt_<bcp47>` (e.g., `prompt_ja`). */
  [localizedPrompt: `prompt_${string}`]: string | undefined
}

/** A full profile pack: questions, types, and aggregation rules. */
export interface ProfileSpec {
  schema_version: '1'
  profile_id: string
  profile_version: string
  types: TypeSpec[]
  questions: QuestionSpec[]
  aggregation: {
    method: 'argmax' | 'softmax' | 'threshold'
  }
}

/** The result of evaluating a user's answers against a profile spec.
 *
 * `scores` semantics depend on `spec.aggregation.method`:
 *   - `argmax`:  raw cumulative weights per type (unbounded; integer when all
 *                weights are integers).
 *   - `softmax`: probabilities per type (each in [0, 1], summing to 1).
 *   - `threshold`: not yet implemented.
 *
 * `confidence` semantics:
 *   - `argmax`:  margin between top and second score, normalised by top; in [0, 1].
 *   - `softmax`: the winning type's probability; in [0, 1].
 */
export interface EvalResult {
  /** The winning type id. */
  type: string
  /** Per-type scores. Semantics depend on aggregation method — see interface docs. */
  scores: Record<string, number>
  /** Confidence in the winning type, in [0, 1]. Semantics depend on aggregation method. */
  confidence: number
  /** The scoring engine version that produced this result. */
  scoring_version: string
}
