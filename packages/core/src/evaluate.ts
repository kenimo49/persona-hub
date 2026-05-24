import type { Answers, EvalResult, ProfileSpec } from './types.js'

export const SCORING_VERSION = '0.1.0'

type AggregationMethod = ProfileSpec['aggregation']['method']

const VALID_METHODS: ReadonlySet<AggregationMethod> = new Set(['argmax', 'softmax', 'threshold'])

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function validateProfileSpec(spec: unknown): asserts spec is ProfileSpec {
  if (!isPlainObject(spec)) {
    throw new TypeError('ProfileSpec must be an object')
  }
  if (spec.schema_version !== '1') {
    throw new TypeError(`Unsupported schema_version: ${String(spec.schema_version)} (expected "1")`)
  }
  if (typeof spec.profile_id !== 'string') {
    throw new TypeError('profile_id must be a string')
  }
  if (typeof spec.profile_version !== 'string') {
    throw new TypeError('profile_version must be a string')
  }
  if (!Array.isArray(spec.types) || spec.types.length === 0) {
    throw new TypeError('types must be a non-empty array')
  }
  for (const t of spec.types) {
    if (!isPlainObject(t) || typeof t.id !== 'string' || typeof t.name !== 'string') {
      throw new TypeError('each type must have string id and name')
    }
  }
  if (!Array.isArray(spec.questions) || spec.questions.length === 0) {
    throw new TypeError('questions must be a non-empty array')
  }
  for (const q of spec.questions) {
    if (!isPlainObject(q) || typeof q.id !== 'string' || typeof q.prompt !== 'string') {
      throw new TypeError('each question must have string id and prompt')
    }
    if (!Array.isArray(q.options) || q.options.length === 0) {
      throw new TypeError(`question "${q.id}" must have a non-empty options array`)
    }
    for (const opt of q.options) {
      if (!isPlainObject(opt) || typeof opt.id !== 'string' || typeof opt.label !== 'string') {
        throw new TypeError(`each option in question "${q.id}" must have string id and label`)
      }
      if (!isPlainObject(opt.weights)) {
        throw new TypeError(`option "${opt.id}" must have a weights object`)
      }
      for (const [typeId, w] of Object.entries(opt.weights)) {
        if (typeof w !== 'number' || Number.isNaN(w)) {
          throw new TypeError(`option "${opt.id}" weight for type "${typeId}" must be a finite number`)
        }
      }
    }
  }
  if (!isPlainObject(spec.aggregation) || !VALID_METHODS.has(spec.aggregation.method as AggregationMethod)) {
    throw new TypeError('aggregation.method must be one of: argmax, softmax, threshold')
  }
}

function assertWeightTypeIdsExist(spec: ProfileSpec): void {
  const validTypeIds = new Set(spec.types.map((t) => t.id))
  for (const q of spec.questions) {
    for (const opt of q.options) {
      for (const typeId of Object.keys(opt.weights)) {
        if (!validTypeIds.has(typeId)) {
          throw new Error(
            `Invalid weight reference: option "${opt.id}" in question "${q.id}" references unknown type "${typeId}"`
          )
        }
      }
    }
  }
}

function accumulateRawScores(answers: Answers, spec: ProfileSpec): Record<string, number> {
  const scores: Record<string, number> = {}
  for (const t of spec.types) {
    scores[t.id] = 0
  }
  for (const q of spec.questions) {
    const selectedOptionId = answers[q.id]
    if (selectedOptionId === undefined) {
      throw new Error(`Missing answer for question "${q.id}"`)
    }
    const option = q.options.find((o) => o.id === selectedOptionId)
    if (option === undefined) {
      throw new Error(`Unknown option "${selectedOptionId}" for question "${q.id}"`)
    }
    for (const [typeId, weight] of Object.entries(option.weights)) {
      scores[typeId] = (scores[typeId] ?? 0) + weight
    }
  }
  return scores
}

function argmaxOf(scores: Record<string, number>): string {
  const entries = Object.entries(scores)
  let winner = entries[0]![0]
  let max = entries[0]![1]
  for (let i = 1; i < entries.length; i++) {
    if (entries[i]![1] > max) {
      winner = entries[i]![0]
      max = entries[i]![1]
    }
  }
  return winner
}

function softmaxNormalize(scores: Record<string, number>): Record<string, number> {
  const entries = Object.entries(scores)
  const maxScore = entries.reduce((m, [, s]) => Math.max(m, s), -Infinity)
  const exps = entries.map(([id, s]) => [id, Math.exp(s - maxScore)] as const)
  const sum = exps.reduce((acc, [, e]) => acc + e, 0)
  return Object.fromEntries(exps.map(([id, e]) => [id, e / sum]))
}

function argmaxConfidence(scores: Record<string, number>): number {
  const sorted = Object.values(scores).sort((a, b) => b - a)
  const top = sorted[0] ?? 0
  const second = sorted[1] ?? 0
  if (top <= 0) {
    return 0
  }
  return Math.max(0, Math.min(1, (top - second) / top))
}

function aggregate(rawScores: Record<string, number>, method: AggregationMethod): EvalResult {
  if (method === 'threshold') {
    throw new Error(
      "Aggregation method 'threshold' is not yet implemented. Use 'argmax' or 'softmax' for now."
    )
  }
  if (method === 'softmax') {
    const normalized = softmaxNormalize(rawScores)
    const winner = argmaxOf(normalized)
    return {
      type: winner,
      scores: normalized,
      confidence: normalized[winner] ?? 0,
      scoring_version: SCORING_VERSION,
    }
  }
  const winner = argmaxOf(rawScores)
  return {
    type: winner,
    scores: { ...rawScores },
    confidence: argmaxConfidence(rawScores),
    scoring_version: SCORING_VERSION,
  }
}

/**
 * Evaluate a user's answers against a profile spec.
 *
 * Pure, deterministic. Validates the spec and cross-references at runtime;
 * throws on missing answers or unknown options.
 *
 * @param answers - questionId -> optionId
 * @param spec - the profile pack (validated at runtime)
 * @returns winning type, per-type scores, and confidence in [0, 1]
 */
export function evaluate(answers: Answers, spec: ProfileSpec): EvalResult {
  validateProfileSpec(spec)
  assertWeightTypeIdsExist(spec)
  const rawScores = accumulateRawScores(answers, spec)
  return aggregate(rawScores, spec.aggregation.method)
}
