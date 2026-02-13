/**
 * Tests for fallRisk.ts - must match backend fall_risk.py thresholds exactly.
 */
import {
  calculateSpeedScore,
  calculateTimeScore,
  calculateFallRiskScore,
  getRiskLevel,
  getFallRiskAssessment,
} from './fallRisk'

describe('calculateSpeedScore', () => {
  it('returns 50 for normal speed (>= 1.2)', () => {
    expect(calculateSpeedScore(1.2)).toBe(50)
    expect(calculateSpeedScore(1.5)).toBe(50)
  })

  it('returns 40 for mild speed (>= 1.0, < 1.2)', () => {
    expect(calculateSpeedScore(1.0)).toBe(40)
    expect(calculateSpeedScore(1.19)).toBe(40)
  })

  it('returns 25 for caution speed (>= 0.8, < 1.0)', () => {
    expect(calculateSpeedScore(0.8)).toBe(25)
    expect(calculateSpeedScore(0.99)).toBe(25)
  })

  it('returns 10 for danger speed (< 0.8)', () => {
    expect(calculateSpeedScore(0.79)).toBe(10)
    expect(calculateSpeedScore(0.0)).toBe(10)
  })

  it('returns 10 for negative speed', () => {
    expect(calculateSpeedScore(-1.0)).toBe(10)
  })
})

describe('calculateTimeScore', () => {
  it('returns 50 for normal time (<= 8.3)', () => {
    expect(calculateTimeScore(8.3)).toBe(50)
    expect(calculateTimeScore(5.0)).toBe(50)
  })

  it('returns 40 for mild time (> 8.3, <= 10.0)', () => {
    expect(calculateTimeScore(8.31)).toBe(40)
    expect(calculateTimeScore(10.0)).toBe(40)
  })

  it('returns 25 for caution time (> 10.0, <= 12.5)', () => {
    expect(calculateTimeScore(10.01)).toBe(25)
    expect(calculateTimeScore(12.5)).toBe(25)
  })

  it('returns 10 for danger time (> 12.5)', () => {
    expect(calculateTimeScore(12.51)).toBe(10)
    expect(calculateTimeScore(20.0)).toBe(10)
  })
})

describe('calculateFallRiskScore', () => {
  it('returns 100 for perfect score', () => {
    expect(calculateFallRiskScore(1.2, 8.3)).toBe(100)
  })

  it('returns 20 for worst score', () => {
    expect(calculateFallRiskScore(0.5, 15.0)).toBe(20)
  })

  it('returns 65 for mixed score', () => {
    expect(calculateFallRiskScore(1.0, 11.0)).toBe(65)
  })
})

describe('getRiskLevel', () => {
  it('returns normal for score >= 90', () => {
    expect(getRiskLevel(90).level).toBe('normal')
    expect(getRiskLevel(100).level).toBe('normal')
    expect(getRiskLevel(90).labelEn).toBe('Normal')
  })

  it('returns mild for score 70-89', () => {
    expect(getRiskLevel(70).level).toBe('mild')
    expect(getRiskLevel(89).level).toBe('mild')
  })

  it('returns moderate for score 50-69', () => {
    expect(getRiskLevel(50).level).toBe('moderate')
    expect(getRiskLevel(69).level).toBe('moderate')
  })

  it('returns high for score < 50', () => {
    expect(getRiskLevel(49).level).toBe('high')
    expect(getRiskLevel(0).level).toBe('high')
  })
})

describe('getFallRiskAssessment', () => {
  it('returns complete assessment for normal case', () => {
    const result = getFallRiskAssessment(1.2, 8.0)
    expect(result.score).toBe(100)
    expect(result.speedScore).toBe(50)
    expect(result.timeScore).toBe(50)
    expect(result.level.level).toBe('normal')
  })

  it('returns high risk for poor values', () => {
    const result = getFallRiskAssessment(0.5, 15.0)
    expect(result.score).toBe(20)
    expect(result.level.level).toBe('high')
  })
})

describe('Frontend-Backend Parity', () => {
  it.each([
    [0.79, 10],
    [0.8, 25],
    [0.99, 25],
    [1.0, 40],
    [1.19, 40],
    [1.2, 50],
  ])('speed score: %f -> %d', (speed, expected) => {
    expect(calculateSpeedScore(speed)).toBe(expected)
  })

  it.each([
    [8.3, 50],
    [8.31, 40],
    [10.0, 40],
    [10.01, 25],
    [12.5, 25],
    [12.51, 10],
  ])('time score: %f -> %d', (time, expected) => {
    expect(calculateTimeScore(time)).toBe(expected)
  })
})
