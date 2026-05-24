import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { evaluate, SCORING_VERSION } from '../evaluate.js'
import type { ProfileSpec } from '../types.js'

const __dirname = dirname(fileURLToPath(import.meta.url))
const FRAGRANCE_PATH = resolve(__dirname, '../../../profiles/src/fragrance.json')

const FRAGRANCE_SPEC = JSON.parse(readFileSync(FRAGRANCE_PATH, 'utf8')) as ProfileSpec

const EXPECTED_TYPE_IDS = ['citrus', 'woody', 'floral', 'oriental', 'aquatic', 'green'] as const
type FragranceTypeId = (typeof EXPECTED_TYPE_IDS)[number]

describe('fragrance.v1 profile pack — spec shape', () => {
  it('declares profile_id, version, and schema_version', () => {
    expect(FRAGRANCE_SPEC.profile_id).toBe('fragrance.v1')
    expect(FRAGRANCE_SPEC.profile_version).toBe('1.0.0')
    expect(FRAGRANCE_SPEC.schema_version).toBe('1')
  })

  it('has exactly 6 types: citrus, woody, floral, oriental, aquatic, green', () => {
    const ids = FRAGRANCE_SPEC.types.map((t) => t.id).sort()
    expect(ids).toEqual([...EXPECTED_TYPE_IDS].sort())
  })

  it('every type carries both EN and JA descriptions', () => {
    for (const t of FRAGRANCE_SPEC.types) {
      expect(typeof t.description).toBe('string')
      expect((t.description ?? '').length).toBeGreaterThan(0)
      const descJa = (t as { description_ja?: unknown }).description_ja
      expect(typeof descJa).toBe('string')
      expect((descJa as string).length).toBeGreaterThan(0)
    }
  })

  it('has exactly 5 questions, each with 5 options', () => {
    expect(FRAGRANCE_SPEC.questions).toHaveLength(5)
    for (const q of FRAGRANCE_SPEC.questions) {
      expect(q.options).toHaveLength(5)
    }
  })

  it('every option weight references a known type id', () => {
    const validIds = new Set(FRAGRANCE_SPEC.types.map((t) => t.id))
    for (const q of FRAGRANCE_SPEC.questions) {
      for (const opt of q.options) {
        for (const typeId of Object.keys(opt.weights)) {
          expect(validIds.has(typeId)).toBe(true)
        }
      }
    }
  })

  it('aggregation method is softmax', () => {
    expect(FRAGRANCE_SPEC.aggregation.method).toBe('softmax')
  })
})

describe('fragrance.v1 — evaluator integration', () => {
  it('passes evaluate() shape validation on any complete answer set', () => {
    const answers: Record<string, string> = {}
    for (const q of FRAGRANCE_SPEC.questions) {
      answers[q.id] = q.options[0]!.id
    }
    const result = evaluate(answers, FRAGRANCE_SPEC)
    expect(result.scoring_version).toBe(SCORING_VERSION)
  })

  it('returns probabilities that sum to 1 under softmax', () => {
    const answers: Record<string, string> = {}
    for (const q of FRAGRANCE_SPEC.questions) {
      answers[q.id] = q.options[2]!.id
    }
    const result = evaluate(answers, FRAGRANCE_SPEC)
    const total = Object.values(result.scores).reduce((acc, s) => acc + s, 0)
    expect(total).toBeCloseTo(1, 5)
  })

  it('is deterministic across repeated calls', () => {
    const answers = { fq_01: 'a', fq_02: 'b', fq_03: 'c', fq_04: 'd', fq_05: 'e' }
    const a = evaluate(answers, FRAGRANCE_SPEC)
    const b = evaluate(answers, FRAGRANCE_SPEC)
    expect(a).toEqual(b)
  })

  it('every type can win at least one answer pattern (no dead types)', () => {
    const witness: Record<FragranceTypeId, string[]> = {
      citrus: ['a', 'a', 'a', 'd', 'a'],
      woody: ['b', 'b', 'd', 'e', 'b'],
      floral: ['c', 'd', 'c', 'd', 'd'],
      oriental: ['e', 'c', 'b', 'c', 'e'],
      aquatic: ['a', 'e', 'e', 'a', 'a'],
      green: ['d', 'b', 'e', 'b', 'c'],
    }
    for (const typeId of EXPECTED_TYPE_IDS) {
      const optionIds = witness[typeId]
      const answers: Record<string, string> = {}
      FRAGRANCE_SPEC.questions.forEach((q, i) => {
        answers[q.id] = optionIds[i]!
      })
      const result = evaluate(answers, FRAGRANCE_SPEC)
      expect(result.type, `expected ${typeId} to win with witness ${optionIds.join(',')}`).toBe(
        typeId
      )
    }
  })

  it('throws on missing answer', () => {
    const partial = { fq_01: 'a', fq_02: 'b', fq_03: 'c', fq_04: 'd' }
    expect(() => evaluate(partial, FRAGRANCE_SPEC)).toThrow(/Missing answer/)
  })

  it('throws on unknown option id', () => {
    const bad = { fq_01: 'z', fq_02: 'b', fq_03: 'c', fq_04: 'd', fq_05: 'e' }
    expect(() => evaluate(bad, FRAGRANCE_SPEC)).toThrow(/Unknown option/)
  })
})

describe('fragrance.v1 — matrix fairness (brute-force over all 5^5 patterns)', () => {
  function allPatterns(): Array<Record<string, string>> {
    const optionIdsPerQ = FRAGRANCE_SPEC.questions.map((q) => q.options.map((o) => o.id))
    const patterns: Array<Record<string, string>> = []
    for (const a of optionIdsPerQ[0]!) {
      for (const b of optionIdsPerQ[1]!) {
        for (const c of optionIdsPerQ[2]!) {
          for (const d of optionIdsPerQ[3]!) {
            for (const e of optionIdsPerQ[4]!) {
              patterns.push({
                [FRAGRANCE_SPEC.questions[0]!.id]: a,
                [FRAGRANCE_SPEC.questions[1]!.id]: b,
                [FRAGRANCE_SPEC.questions[2]!.id]: c,
                [FRAGRANCE_SPEC.questions[3]!.id]: d,
                [FRAGRANCE_SPEC.questions[4]!.id]: e,
              })
            }
          }
        }
      }
    }
    return patterns
  }

  // Sum raw weights for an answer pattern — bypasses softmax to compare on the same scale.
  function rawScores(answers: Record<string, string>): Record<string, number> {
    const scores: Record<string, number> = {}
    for (const t of FRAGRANCE_SPEC.types) scores[t.id] = 0
    for (const q of FRAGRANCE_SPEC.questions) {
      const opt = q.options.find((o) => o.id === answers[q.id])!
      for (const [tid, w] of Object.entries(opt.weights)) {
        scores[tid] = (scores[tid] ?? 0) + w
      }
    }
    return scores
  }

  it('no type dominates more than ~2.5x the least-winning type (strict-argmax patterns)', () => {
    const patterns = allPatterns()
    const wins: Record<string, number> = {}
    for (const t of FRAGRANCE_SPEC.types) wins[t.id] = 0
    for (const ans of patterns) {
      const raw = rawScores(ans)
      const max = Math.max(...Object.values(raw))
      const winners = Object.entries(raw).filter(([, s]) => s === max)
      if (winners.length === 1) {
        wins[winners[0]![0]] = (wins[winners[0]![0]] ?? 0) + 1
      }
    }
    const counts = Object.values(wins)
    const ratio = Math.max(...counts) / Math.min(...counts)
    // Hard ceiling; current matrix sits around 2.1x. If a future edit pushes past 3x,
    // the matrix has drifted toward an obvious bias and should be re-balanced.
    expect(ratio).toBeLessThan(3.0)
  })

  it('every option is part of at least one strict-argmax winning pattern (no orphan options)', () => {
    const patterns = allPatterns()
    const seenPerQ: Record<string, Set<string>> = {}
    for (const q of FRAGRANCE_SPEC.questions) seenPerQ[q.id] = new Set()
    for (const ans of patterns) {
      const raw = rawScores(ans)
      const max = Math.max(...Object.values(raw))
      const winners = Object.entries(raw).filter(([, s]) => s === max)
      if (winners.length === 1) {
        for (const q of FRAGRANCE_SPEC.questions) seenPerQ[q.id]!.add(ans[q.id]!)
      }
    }
    for (const q of FRAGRANCE_SPEC.questions) {
      const expected = new Set(q.options.map((o) => o.id))
      expect(seenPerQ[q.id], `question ${q.id} orphan options`).toEqual(expected)
    }
  })

  it('every type can be the strict-argmax winner under at least one answer pattern', () => {
    const patterns = allPatterns()
    const ever = new Set<string>()
    for (const ans of patterns) {
      const raw = rawScores(ans)
      const max = Math.max(...Object.values(raw))
      const winners = Object.entries(raw).filter(([, s]) => s === max)
      if (winners.length === 1) ever.add(winners[0]![0])
    }
    const all = new Set(FRAGRANCE_SPEC.types.map((t) => t.id))
    expect(ever).toEqual(all)
  })

  it('documents tie-break behavior: ties resolve by spec.types insertion order', () => {
    // This documents the current core/evaluate.ts contract for downstream consumers.
    // The matrix has 846/3125 (~27%) tie patterns, so the behavior is observable
    // in production. If the core tie-break policy changes (e.g., random or
    // alphabetical), this test will fail and force an explicit decision.
    //
    // Pattern below produces raw { citrus: 4, woody: 4, ... } — a real 2-way tie
    // at the top, verified by brute-force over all 5^5 patterns.
    const tiePattern = { fq_01: 'a', fq_02: 'a', fq_03: 'b', fq_04: 'a', fq_05: 'b' }
    const raw: Record<string, number> = {}
    for (const t of FRAGRANCE_SPEC.types) raw[t.id] = 0
    for (const q of FRAGRANCE_SPEC.questions) {
      const opt = q.options.find((o) => o.id === tiePattern[q.id as keyof typeof tiePattern])!
      for (const [tid, w] of Object.entries(opt.weights)) raw[tid] = (raw[tid] ?? 0) + w
    }
    const max = Math.max(...Object.values(raw))
    const tied = FRAGRANCE_SPEC.types.map((t) => t.id).filter((id) => raw[id] === max)
    // Sanity: guarantee this pattern actually ties at the top.
    expect(tied.length).toBeGreaterThanOrEqual(2)
    expect(tied).toContain('citrus')
    expect(tied).toContain('woody')

    const result = evaluate(tiePattern, FRAGRANCE_SPEC)
    // For softmax, equal raw scores normalise to equal probabilities, and
    // argmaxOf in core/evaluate.ts uses strict `>` so it returns the first
    // tied id in the spec.types iteration order. citrus precedes woody.
    expect(result.type).toBe(tied[0])
    expect(result.type).toBe('citrus')
  })
})

describe('fragrance.v1 — package export wiring', () => {
  it('packages/profiles/package.json exports ./fragrance.json pointing at the same file', async () => {
    // Guards against accidental drift between the docs/README import path and the
    // package.json exports map. Loads both ends and asserts identical content.
    const profilesPkgPath = resolve(__dirname, '../../../profiles/package.json')
    const profilesPkg = JSON.parse(readFileSync(profilesPkgPath, 'utf8')) as {
      exports?: Record<string, string>
    }
    expect(profilesPkg.exports?.['./fragrance.json']).toBe('./src/fragrance.json')

    const exportedTarget = resolve(
      __dirname,
      '../../../profiles',
      profilesPkg.exports!['./fragrance.json']!
    )
    const exportedJson = JSON.parse(readFileSync(exportedTarget, 'utf8'))
    expect(exportedJson.profile_id).toBe('fragrance.v1')
    // Same file the integration tests use — pin equality so a future move of the
    // source file is caught immediately.
    expect(exportedTarget).toBe(FRAGRANCE_PATH)
  })
})
