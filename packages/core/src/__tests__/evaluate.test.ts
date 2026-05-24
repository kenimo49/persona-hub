import { describe, expect, it } from 'vitest'
import { evaluate } from '../evaluate.js'

describe('evaluate', () => {
  it('throws until implemented (tracked in Issue #3)', () => {
    expect(() => evaluate({}, {} as never)).toThrow(/not yet implemented/)
  })
})
