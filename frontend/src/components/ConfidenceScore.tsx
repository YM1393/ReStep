import { useState } from 'react';
import type { ConfidenceScore as ConfidenceScoreType } from '../types';

interface ConfidenceScoreProps {
  confidence: ConfidenceScoreType;
  compact?: boolean;
}

export default function ConfidenceScore({ confidence, compact = false }: ConfidenceScoreProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  const { score, level, label } = confidence;
  const { pose_detection_rate, walk_duration_score, walk_time_score, walk_speed_score } = confidence.details;

  // Color based on score
  const getColor = (s: number) => {
    if (s >= 80) return { ring: '#22c55e', bg: 'bg-green-50 dark:bg-green-900/20', text: 'text-green-700 dark:text-green-400', label: 'text-green-600 dark:text-green-400' };
    if (s >= 50) return { ring: '#eab308', bg: 'bg-yellow-50 dark:bg-yellow-900/20', text: 'text-yellow-800 dark:text-yellow-300', label: 'text-yellow-600 dark:text-yellow-400' };
    return { ring: '#ef4444', bg: 'bg-red-50 dark:bg-red-900/20', text: 'text-red-700 dark:text-red-400', label: 'text-red-600 dark:text-red-400' };
  };

  const colors = getColor(score);

  // SVG circular progress
  const size = compact ? 48 : 72;
  const strokeWidth = compact ? 4 : 6;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference - (score / 100) * circumference;

  const levelLabel = level === 'high' ? '높음' : level === 'medium' ? '보통' : level === 'low' ? '낮음' : '매우 낮음';

  if (compact) {
    return (
      <div
        className="relative inline-flex items-center gap-2 cursor-pointer"
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        <svg width={size} height={size} className="transform -rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            className="text-gray-200 dark:text-gray-700"
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={colors.ring}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            strokeLinecap="round"
          />
        </svg>
        <span
          className={`absolute font-bold text-xs ${colors.text}`}
          style={{ left: size / 2, top: size / 2, transform: 'translate(-50%, -50%)' }}
        >
          {score}
        </span>

        {/* Tooltip */}
        {showTooltip && (
          <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-56 p-3 bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 z-50">
            <p className="text-xs font-bold text-gray-900 dark:text-gray-100 mb-2">
              {label} ({levelLabel})
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
              AI 분석의 신뢰도를 나타냅니다. 포즈 감지율, 보행 구간, 시간/속도 합리성을 종합 평가합니다.
            </p>
            <div className="space-y-1.5">
              <DetailBar label="포즈 감지율" value={pose_detection_rate} />
              <DetailBar label="보행 구간" value={walk_duration_score} />
              <DetailBar label="보행 시간" value={walk_time_score} />
              <DetailBar label="보행 속도" value={walk_speed_score} />
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={`${colors.bg} p-4 rounded-xl`}>
      <div className="flex items-center gap-4">
        {/* Ring */}
        <div className="relative flex-shrink-0">
          <svg width={size} height={size} className="transform -rotate-90">
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke="currentColor"
              strokeWidth={strokeWidth}
              className="text-gray-200 dark:text-gray-700"
            />
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke={colors.ring}
              strokeWidth={strokeWidth}
              strokeDasharray={circumference}
              strokeDashoffset={dashOffset}
              strokeLinecap="round"
            />
          </svg>
          <span
            className={`absolute inset-0 flex items-center justify-center font-bold text-lg ${colors.text}`}
          >
            {score}
          </span>
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="font-bold text-gray-900 dark:text-gray-100 text-sm">
              {label}
            </h4>
            <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${colors.text} ${colors.bg}`}>
              {levelLabel}
            </span>
          </div>
          <div className="space-y-1">
            <DetailBar label="포즈 감지율" value={pose_detection_rate} />
            <DetailBar label="보행 구간" value={walk_duration_score} />
            <DetailBar label="보행 시간" value={walk_time_score} />
            <DetailBar label="보행 속도" value={walk_speed_score} />
          </div>
        </div>
      </div>
    </div>
  );
}

function DetailBar({ label, value }: { label: string; value: number }) {
  const barColor =
    value >= 80 ? 'bg-green-500' :
    value >= 50 ? 'bg-yellow-500' :
    'bg-red-500';

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-600 dark:text-gray-400 w-16 flex-shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${barColor}`}
          style={{ width: `${Math.min(100, value)}%` }}
        />
      </div>
      <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 w-6 text-right">{value}</span>
    </div>
  );
}
