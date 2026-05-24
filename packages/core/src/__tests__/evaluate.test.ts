import { describe, expect, it } from 'vitest'
import { evaluate, SCORING_VERSION } from '../evaluate.js'
import type { ProfileSpec } from '../types.js'

const SIMPLE_SPEC: ProfileSpec = {
  schema_version: '1',
  profile_id: 'test.simple',
  profile_version: '1.0.0',
  types: [
    { id: 'red', name: 'Red' },
    { id: 'blue', name: 'Blue' },
    { id: 'green', name: 'Green' },
  ],
  questions: [
    {
      id: 'q1',
      prompt: 'Pick one',
      options: [
        { id: 'a', label: 'A', weights: { red: 2, blue: 0, green: 0 } },
        { id: 'b', label: 'B', weights: { red: 0, blue: 2, green: 0 } },
      ],
    },
    {
      id: 'q2',
      prompt: 'Pick again',
      options: [
        { id: 'a', label: 'A', weights: { red: 1, blue: 0, green: 0 } },
        { id: 'b', label: 'B', weights: { red: 0, blue: 0, green: 3 } },
      ],
    },
  ],
  aggregation: { method: 'argmax' },
}

describe('evaluate — argmax happy path', () => {
  it('returns the type with the highest cumulative score', () => {
    const result = evaluate({ q1: 'a', q2: 'a' }, SIMPLE_SPEC)
    expect(result.type).toBe('red')
    expect(result.scores).toEqual({ red: 3, blue: 0, green: 0 })
  })

  it('emits the current scoring_version', () => {
    const result = evaluate({ q1: 'a', q2: 'a' }, SIMPLE_SPEC)
    expect(result.scoring_version).toBe(SCORING_VERSION)
  })

  it('is deterministic across repeated calls', () => {
    const a = evaluate({ q1: 'a', q2: 'b' }, SIMPLE_SPEC)
    const b = evaluate({ q1: 'a', q2: 'b' }, SIMPLE_SPEC)
    expect(a).toEqual(b)
  })

  it('confidence is 1 when the winner shuts out other types', () => {
    const result = evaluate({ q1: 'a', q2: 'a' }, SIMPLE_SPEC)
    expect(result.confidence).toBe(1)
  })

  it('confidence reflects the margin between top and second', () => {
    // q1=a → red+2; q2=b → green+3. Scores: red=2, blue=0, green=3.
    // Winner=green, margin=(3-2)/3 = 1/3.
    const result = evaluate({ q1: 'a', q2: 'b' }, SIMPLE_SPEC)
    expect(result.type).toBe('green')
    expect(result.confidence).toBeCloseTo(1 / 3, 5)
  })

  it('confidence is 0 when no option contributes any weight', () => {
    const zeroSpec: ProfileSpec = {
      ...SIMPLE_SPEC,
      questions: [
        {
          id: 'q1',
          prompt: 'p',
          options: [{ id: 'a', label: 'A', weights: { red: 0, blue: 0, green: 0 } }],
        },
      ],
    }
    const result = evaluate({ q1: 'a' }, zeroSpec)
    expect(result.confidence).toBe(0)
  })
})

describe('evaluate — softmax', () => {
  const softmaxSpec: ProfileSpec = { ...SIMPLE_SPEC, aggregation: { method: 'softmax' } }

  it('returns probabilities that sum to 1', () => {
    const result = evaluate({ q1: 'a', q2: 'a' }, softmaxSpec)
    const total = Object.values(result.scores).reduce((acc, s) => acc + s, 0)
    expect(total).toBeCloseTo(1, 5)
  })

  it('confidence equals the winning probability', () => {
    const result = evaluate({ q1: 'a', q2: 'a' }, softmaxSpec)
    expect(result.type).toBe('red')
    expect(result.confidence).toBeCloseTo(result.scores.red!, 5)
  })

  it('all probabilities are in [0, 1]', () => {
    const result = evaluate({ q1: 'a', q2: 'b' }, softmaxSpec)
    for (const p of Object.values(result.scores)) {
      expect(p).toBeGreaterThanOrEqual(0)
      expect(p).toBeLessThanOrEqual(1)
    }
  })
})

describe('evaluate — spec validation', () => {
  it('rejects an unsupported schema_version', () => {
    const bad = { ...SIMPLE_SPEC, schema_version: '2' as never }
    expect(() => evaluate({ q1: 'a', q2: 'a' }, bad)).toThrow(/schema_version/)
  })

  it('rejects a missing types array', () => {
    const bad = { ...SIMPLE_SPEC, types: undefined } as unknown as ProfileSpec
    expect(() => evaluate({ q1: 'a', q2: 'a' }, bad)).toThrow(/types/)
  })

  it('rejects a missing questions array', () => {
    const bad = { ...SIMPLE_SPEC, questions: [] } as unknown as ProfileSpec
    expect(() => evaluate({}, bad)).toThrow(/questions/)
  })

  it('rejects an unknown aggregation method', () => {
    const bad = { ...SIMPLE_SPEC, aggregation: { method: 'magic' } } as unknown as ProfileSpec
    expect(() => evaluate({ q1: 'a', q2: 'a' }, bad)).toThrow(/aggregation.method/)
  })

  it('rejects weights with a non-numeric value', () => {
    const bad: ProfileSpec = {
      ...SIMPLE_SPEC,
      questions: [
        {
          id: 'q1',
          prompt: 'p',
          options: [{ id: 'a', label: 'A', weights: { red: 'oops' as unknown as number } }],
        },
      ],
    }
    expect(() => evaluate({ q1: 'a' }, bad)).toThrow(/weight/)
  })

  it('rejects weights that reference an unknown type', () => {
    const bad: ProfileSpec = {
      ...SIMPLE_SPEC,
      questions: [
        {
          id: 'q1',
          prompt: 'p',
          options: [{ id: 'a', label: 'A', weights: { not_a_real_type: 5 } }],
        },
      ],
    }
    expect(() => evaluate({ q1: 'a' }, bad)).toThrow(/unknown type/)
  })
})

describe('evaluate — answer errors', () => {
  it('throws when an answer is missing for a question', () => {
    expect(() => evaluate({ q1: 'a' }, SIMPLE_SPEC)).toThrow(/Missing answer.*"q2"/)
  })

  it('throws when an answer references an option that does not exist', () => {
    expect(() => evaluate({ q1: 'z', q2: 'a' }, SIMPLE_SPEC)).toThrow(/Unknown option "z"/)
  })
})

describe('evaluate — threshold is not yet implemented', () => {
  it('throws a clear not-implemented error', () => {
    const spec: ProfileSpec = { ...SIMPLE_SPEC, aggregation: { method: 'threshold' } }
    expect(() => evaluate({ q1: 'a', q2: 'a' }, spec)).toThrow(/not yet implemented/)
  })
})
