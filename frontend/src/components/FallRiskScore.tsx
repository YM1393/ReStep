import { getFallRiskAssessment, type FallRiskAssessment } from '../utils/fallRisk';

interface FallRiskScoreProps {
  speedMps: number;
  timeSeconds: number;
  compact?: boolean;
}

export default function FallRiskScore({ speedMps, timeSeconds, compact = false }: FallRiskScoreProps) {
  const assessment: FallRiskAssessment = getFallRiskAssessment(speedMps, timeSeconds);

  // 점수에 따른 색상
  const getScoreColor = () => {
    if (assessment.score >= 90) return 'text-green-500';
    if (assessment.score >= 70) return 'text-blue-500';
    if (assessment.score >= 50) return 'text-orange-500';
    return 'text-red-500';
  };

  // 원형 게이지용 stroke dash 계산
  const circumference = 2 * Math.PI * 45; // r=45
  const strokeDashoffset = circumference - (assessment.score / 100) * circumference;

  // 게이지 색상
  const getGaugeColor = () => {
    if (assessment.score >= 90) return '#22c55e'; // green-500
    if (assessment.score >= 70) return '#3b82f6'; // blue-500
    if (assessment.score >= 50) return '#f97316'; // orange-500
    return '#ef4444'; // red-500
  };

  if (compact) {
    return (
      <div className={`inline-flex items-center space-x-2 px-3 py-1.5 rounded-full ${assessment.level.bgColor}`}>
        <span className={`text-lg font-bold ${assessment.level.color}`}>{assessment.score}</span>
        <span className={`text-sm font-medium ${assessment.level.color}`}>{assessment.level.label}</span>
      </div>
    );
  }

  return (
    <div className="card">
      <h3 className="font-semibold text-gray-800 dark:text-gray-100 mb-4">낙상 위험 점수</h3>

      <div className="flex items-center justify-center mb-4">
        {/* 원형 게이지 */}
        <div className="relative">
          <svg className="w-32 h-32 transform -rotate-90">
            {/* 배경 원 */}
            <circle
              cx="64"
              cy="64"
              r="45"
              className="stroke-gray-200 dark:stroke-gray-600"
              strokeWidth="10"
              fill="none"
            />
            {/* 진행 원 */}
            <circle
              cx="64"
              cy="64"
              r="45"
              stroke={getGaugeColor()}
              strokeWidth="10"
              fill="none"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              className="transition-all duration-500"
            />
          </svg>
          {/* 중앙 점수 */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={`text-3xl font-bold ${getScoreColor()}`}>{assessment.score}</span>
            <span className="text-xs text-gray-500 dark:text-gray-400">/ 100</span>
          </div>
        </div>
      </div>

      {/* 등급 및 설명 */}
      <div className={`text-center p-3 rounded-xl ${assessment.level.bgColor}`}>
        <p className={`text-lg font-bold ${assessment.level.color}`}>
          {assessment.level.label}
        </p>
        <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">{assessment.level.description}</p>
      </div>

      {/* 점수 상세 */}
      <div className="grid grid-cols-2 gap-3 mt-4">
        <div className="text-center p-3 bg-blue-50 dark:bg-blue-900/30 rounded-xl">
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">속도 점수</p>
          <p className="text-xl font-bold text-blue-600 dark:text-blue-400">{assessment.speedScore}<span className="text-sm text-gray-400">/50</span></p>
        </div>
        <div className="text-center p-3 bg-purple-50 dark:bg-purple-900/30 rounded-xl">
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">시간 점수</p>
          <p className="text-xl font-bold text-purple-600 dark:text-purple-400">{assessment.timeScore}<span className="text-sm text-gray-400">/50</span></p>
        </div>
      </div>

      {/* 점수 기준 */}
      <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-700">
        <p className="text-xs text-gray-400 dark:text-gray-400 mb-2">점수 기준</p>
        <div className="grid grid-cols-4 gap-1 text-center text-xs">
          <div className="p-1.5 bg-green-50 dark:bg-green-900/30 rounded">
            <p className="font-medium text-green-600 dark:text-green-400">90+</p>
            <p className="text-gray-500 dark:text-gray-400">정상</p>
          </div>
          <div className="p-1.5 bg-blue-50 dark:bg-blue-900/30 rounded">
            <p className="font-medium text-blue-600 dark:text-blue-400">70-89</p>
            <p className="text-gray-500 dark:text-gray-400">경도</p>
          </div>
          <div className="p-1.5 bg-orange-50 dark:bg-orange-900/30 rounded">
            <p className="font-medium text-orange-600 dark:text-orange-400">50-69</p>
            <p className="text-gray-500 dark:text-gray-400">중등도</p>
          </div>
          <div className="p-1.5 bg-red-50 dark:bg-red-900/30 rounded">
            <p className="font-medium text-red-600 dark:text-red-400">0-49</p>
            <p className="text-gray-500 dark:text-gray-400">고위험</p>
          </div>
        </div>
      </div>
    </div>
  );
}
