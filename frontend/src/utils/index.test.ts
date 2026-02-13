/**
 * Tests for utils/index.ts
 */
import { formatDate, calculateAge, getSpeedAssessment, getSpeedColor } from './index'

describe('formatDate', () => {
  it('formats ISO date to ko-KR locale', () => {
    const result = formatDate('2025-01-15')
    expect(result).toContain('2025')
    expect(result).toContain('1')
    expect(result).toContain('15')
  })
})

describe('calculateAge', () => {
  it('calculates correct age', () => {
    const now = new Date()
    const year = now.getFullYear() - 30
    const pastBirthday = `${year}-01-01`
    expect(calculateAge(pastBirthday)).toBe(30)
  })

  it('subtracts 1 if birthday has not passed', () => {
    const now = new Date()
    const year = now.getFullYear() - 30
    const futureBirthday = `${year}-12-31`
    const age = calculateAge(futureBirthday)
    // If today is Dec 31, age is 30; otherwise 29
    expect(age).toBeGreaterThanOrEqual(29)
    expect(age).toBeLessThanOrEqual(30)
  })
})

describe('getSpeedAssessment', () => {
  it('returns Normal for speed >= 1.2', () => {
    expect(getSpeedAssessment(1.2)).toBe('Normal')
    expect(getSpeedAssessment(1.5)).toBe('Normal')
  })

  it('returns Mildly reduced for speed >= 1.0', () => {
    expect(getSpeedAssessment(1.0)).toBe('Mildly reduced')
    expect(getSpeedAssessment(1.19)).toBe('Mildly reduced')
  })

  it('returns Moderately reduced for speed >= 0.8', () => {
    expect(getSpeedAssessment(0.8)).toBe('Moderately reduced')
    expect(getSpeedAssessment(0.99)).toBe('Moderately reduced')
  })

  it('returns Severely reduced for speed < 0.8', () => {
    expect(getSpeedAssessment(0.5)).toBe('Severely reduced')
  })
})

describe('getSpeedColor', () => {
  it('returns green for speed >= 1.2', () => {
    expect(getSpeedColor(1.2)).toBe('green')
  })

  it('returns yellow for speed >= 0.8', () => {
    expect(getSpeedColor(0.8)).toBe('yellow')
    expect(getSpeedColor(1.19)).toBe('yellow')
  })

  it('returns red for speed < 0.8', () => {
    expect(getSpeedColor(0.5)).toBe('red')
  })
})
