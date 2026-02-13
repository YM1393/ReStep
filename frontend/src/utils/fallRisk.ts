/**
 * 낙상 위험도 점수 계산 유틸리티
 *
 * 점수 계산 기준:
 * - 보행 속도와 시간을 각각 50점씩 배점
 * - 총점 0-100점으로 종합 위험도 산출
 */

export interface FallRiskLevel {
  level: 'normal' | 'mild' | 'moderate' | 'high';
  label: string;
  labelEn: string;
  color: string;
  bgColor: string;
  description: string;
}

export interface FallRiskAssessment {
  score: number;
  speedScore: number;
  timeScore: number;
  level: FallRiskLevel;
}

/**
 * 보행 속도 기반 점수 (0-50점)
 */
export function calculateSpeedScore(speedMps: number): number {
  if (speedMps >= 1.2) return 50;  // 정상
  if (speedMps >= 1.0) return 40;  // 경도
  if (speedMps >= 0.8) return 25;  // 주의
  return 10;  // 위험
}

/**
 * 보행 시간 기반 점수 (0-50점)
 */
export function calculateTimeScore(timeSeconds: number): number {
  if (timeSeconds <= 8.3) return 50;   // 정상
  if (timeSeconds <= 10.0) return 40;  // 경도
  if (timeSeconds <= 12.5) return 25;  // 주의
  return 10;  // 위험
}

/**
 * 종합 낙상 위험 점수 계산 (0-100점)
 */
export function calculateFallRiskScore(speedMps: number, timeSeconds: number): number {
  return calculateSpeedScore(speedMps) + calculateTimeScore(timeSeconds);
}

/**
 * 점수에 따른 위험도 등급 반환
 */
export function getRiskLevel(score: number): FallRiskLevel {
  if (score >= 90) {
    return {
      level: 'normal',
      label: '정상',
      labelEn: 'Normal',
      color: 'text-green-600 dark:text-green-400',
      bgColor: 'bg-green-100 dark:bg-green-900/30',
      description: '낙상 위험이 낮습니다.'
    };
  }
  if (score >= 70) {
    return {
      level: 'mild',
      label: '경도 위험',
      labelEn: 'Mild Risk',
      color: 'text-blue-600 dark:text-blue-400',
      bgColor: 'bg-blue-100 dark:bg-blue-900/30',
      description: '경미한 낙상 위험이 있습니다.'
    };
  }
  if (score >= 50) {
    return {
      level: 'moderate',
      label: '중등도 위험',
      labelEn: 'Moderate Risk',
      color: 'text-orange-600 dark:text-orange-400',
      bgColor: 'bg-orange-100 dark:bg-orange-900/30',
      description: '낙상 위험이 있습니다. 예방 조치가 필요합니다.'
    };
  }
  return {
    level: 'high',
    label: '고위험',
    labelEn: 'High Risk',
    color: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-100 dark:bg-red-900/30',
    description: '낙상 위험이 높습니다. 즉각적인 개입이 필요합니다.'
  };
}

/**
 * 종합 낙상 위험 평가 결과 반환
 */
export function getFallRiskAssessment(speedMps: number, timeSeconds: number): FallRiskAssessment {
  const speedScore = calculateSpeedScore(speedMps);
  const timeScore = calculateTimeScore(timeSeconds);
  const score = speedScore + timeScore;
  const level = getRiskLevel(score);

  return {
    score,
    speedScore,
    timeScore,
    level
  };
}
