/** A user's answers to a quiz. Keys are question IDs; values are option IDs. */
export type Answers = Record<string, string>

/** A type a user can be classified into (e.g., "citrus", "woody"). */
export interface TypeSpec {
  id: string
  name: string
  description?: string
}

/** A single quiz question and its options. */
export interface QuestionSpec {
  id: string
  prompt: string
  options: Array<{
    id: string
    label: string
    /** Per-type weight contributed when this option is selected. */
    weights: Record<string, number>
  }>
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

/** The result of evaluating a user's answers against a profile spec. */
export interface EvalResult {
  /** The winning type id. */
  type: string
  /** Per-type scores. */
  scores: Record<string, number>
  /** Confidence in the winning type, 0-1. */
  confidence: number
  /** The scoring engine version that produced this result. */
  scoring_version: string
}
