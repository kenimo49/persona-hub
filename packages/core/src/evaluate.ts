import type { Answers, EvalResult, OptionSpec, ProfileSpec } from './types.js'

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
  const typeIds = new Set<string>()
  for (const t of spec.types) {
    if (!isPlainObject(t) || typeof t.id !== 'string' || typeof t.name !== 'string') {
      throw new TypeError('each type must have string id and name')
    }
    if (typeIds.has(t.id)) {
      throw new TypeError(`duplicate type id "${t.id}"`)
    }
    typeIds.add(t.id)
  }
  if (!Array.isArray(spec.questions) || spec.questions.length === 0) {
    throw new TypeError('questions must be a non-empty array')
  }
  const questionIds = new Set<string>()
  for (const q of spec.questions) {
    if (!isPlainObject(q) || typeof q.id !== 'string' || typeof q.prompt !== 'string') {
      throw new TypeError('each question must have string id and prompt')
    }
    if (questionIds.has(q.id)) {
      throw new TypeError(`duplicate question id "${q.id}"`)
    }
    questionIds.add(q.id)
    if (!Array.isArray(q.options) || q.options.length === 0) {
      throw new TypeError(`question "${q.id}" must have a non-empty options array`)
    }
    const optionIds = new Set<string>()
    for (const opt of q.options) {
      if (!isPlainObject(opt) || typeof opt.id !== 'string' || typeof opt.label !== 'string') {
        throw new TypeError(`each option in question "${q.id}" must have string id and label`)
      }
      if (optionIds.has(opt.id)) {
        throw new TypeError(`duplicate option id "${opt.id}" in question "${q.id}"`)
      }
      optionIds.add(opt.id)
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

/** Per-spec index: question id → (option id → option), built once and cached.
 *
 * Avoids the `O(questions * options)` linear scans that `Array.prototype.find`
 * would do on every evaluate() call. The cache is keyed by the spec object
 * itself via WeakMap.
 *
 * Cache safety: `evaluate()` treats `spec` as immutable. Profile packs are
 * loaded from JSON and not mutated between calls in any normal usage. If a
 * caller mutates `spec.questions` or any nested option array in place, the
 * cached index will not reflect the change — pass a freshly constructed spec
 * object instead. `validateProfileSpec` enforces that `type.id`, `question.id`,
 * and `option.id` within a question are unique, so the cached index can never
 * silently lose entries to last-write-wins overwrites.
 */
const SPEC_INDEX_CACHE = new WeakMap<ProfileSpec, Map<string, Map<string, OptionSpec>>>()

function buildSpecIndex(spec: ProfileSpec): Map<string, Map<string, OptionSpec>> {
  const cached = SPEC_INDEX_CACHE.get(spec)
  if (cached !== undefined) return cached
  const index = new Map<string, Map<string, OptionSpec>>()
  for (const q of spec.questions) {
    const optionMap = new Map<string, OptionSpec>()
    for (const opt of q.options) optionMap.set(opt.id, opt)
    index.set(q.id, optionMap)
  }
  SPEC_INDEX_CACHE.set(spec, index)
  return index
}

function accumulateRawScores(answers: Answers, spec: ProfileSpec): Record<string, number> {
  const scores: Record<string, number> = {}
  for (const t of spec.types) {
    scores[t.id] = 0
  }
  const specIndex = buildSpecIndex(spec)
  const missing: string[] = []
  for (const q of spec.questions) {
    if (answers[q.id] === undefined) missing.push(q.id)
  }
  if (missing.length > 0) {
    const expected = spec.questions.map((q) => q.id).join(', ')
    throw new Error(
      `Missing answers for question(s): ${missing.join(', ')}. ` +
        `Expected one entry per question id: ${expected}.`
    )
  }
  for (const q of spec.questions) {
    const selectedOptionId = answers[q.id]!
    const optionMap = specIndex.get(q.id)!
    const option = optionMap.get(selectedOptionId)
    if (option === undefined) {
      const validOptions = Array.from(optionMap.keys()).join(', ')
      throw new Error(
        `Unknown option "${selectedOptionId}" for question "${q.id}". ` +
          `Valid options: ${validOptions}.`
      )
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
 * throws on missing answers or unknown options. The first call against a
 * given spec object builds a one-time index of `(question, option) → option`
 * which is cached for subsequent calls via WeakMap.
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
