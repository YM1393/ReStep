import type { WalkTest, ClinicalNormativeResponse, ClinicalVariables } from '../types';

interface DashboardSummaryProps {
  latestTest: WalkTest;
  previousTest?: WalkTest;
  clinicalNormative?: ClinicalNormativeResponse | null;
}

function getStatusColor(comparison?: string): string {
  switch (comparison) {
    case 'normal': return 'border-green-500';
    case 'below_average':
    case 'above_average': return 'border-yellow-500';
    case 'below_normal':
    case 'above_normal':
    case 'significantly_below':
    case 'significantly_above': return 'border-red-500';
    default: return 'border-gray-300 dark:border-gray-600';
  }
}

function getStatusBg(comparison?: string): string {
  switch (comparison) {
    case 'normal': return 'text-green-600 dark:text-green-400';
    case 'below_average':
    case 'above_average': return 'text-yellow-600 dark:text-yellow-400';
    case 'below_normal':
    case 'above_normal':
    case 'significantly_below':
    case 'significantly_above': return 'text-red-600 dark:text-red-400';
    default: return 'text-gray-500';
  }
}

function getDelta(current: number | undefined, previous: number | undefined, invert = false): { arrow: string; delta: number; color: string } | null {
  if (current == null || previous == null) return null;
  const diff = current - previous;
  if (Math.abs(diff) < 0.001) return { arrow: '→', delta: 0, color: 'text-gray-400' };
  const improved = invert ? diff < 0 : diff > 0;
  return {
    arrow: improved ? '↑' : '↓',
    delta: Math.abs(diff),
    color: improved ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400',
  };
}

function parseCV(test: WalkTest): ClinicalVariables | undefined {
  const ad = test.analysis_data as Record<string, unknown> | undefined;
  return ad?.clinical_variables as ClinicalVariables | undefined;
}

export default function DashboardSummary({ latestTest, previousTest, clinicalNormative }: DashboardSummaryProps) {
  const cv = parseCV(latestTest);
  const prevCv = previousTest ? parseCV(previousTest) : undefined;

  const cards: {
    label: string;
    value: string;
    unit: string;
    delta: ReturnType<typeof getDelta>;
    borderColor: string;
    statusLabel: string;
    statusColor: string;
  }[] = [];

  // 1. 보행 시간 (주요 지표)
  cards.push({
    label: '보행 시간',
    value: latestTest.walk_time_seconds?.toFixed(1) ?? '-',
    unit: '초',
    delta: getDelta(latestTest.walk_time_seconds, previousTest?.walk_time_seconds, true),
    borderColor: (latestTest.walk_time_seconds ?? 99) <= 10 ? 'border-green-500' : 'border-yellow-500',
    statusLabel: (latestTest.walk_time_seconds ?? 99) <= 10 ? '정상' : '느림',
    statusColor: (latestTest.walk_time_seconds ?? 99) <= 10 ? 'text-green-600' : 'text-yellow-600',
  });

  // 2. 보행 속도
  const speedNorm = clinicalNormative as Record<string, { comparison?: string; comparison_label?: string }> | undefined;
  cards.push({
    label: '보행 속도',
    value: latestTest.walk_speed_mps?.toFixed(2) ?? '-',
    unit: 'm/s',
    delta: getDelta(latestTest.walk_speed_mps, previousTest?.walk_speed_mps),
    borderColor: speedNorm ? 'border-blue-500' : 'border-gray-300 dark:border-gray-600',
    statusLabel: '',
    statusColor: '',
  });

  // 3. 보폭 (측면 촬영에서만)
  if (cv?.stride_length && (latestTest.test_type || '10MWT') !== '10MWT') {
    const norm = clinicalNormative?.stride_length;
    cards.push({
      label: '보폭',
      value: String(cv.stride_length.value),
      unit: 'm',
      delta: getDelta(cv.stride_length.value, prevCv?.stride_length?.value),
      borderColor: getStatusColor(norm?.comparison),
      statusLabel: norm?.comparison_label ?? '',
      statusColor: getStatusBg(norm?.comparison),
    });
  }

  // 4. 케이던스
  if (cv?.cadence) {
    const norm = clinicalNormative?.cadence;
    cards.push({
      label: '분당 걸음수',
      value: String(cv.cadence.value),
      unit: 'steps/min',
      delta: getDelta(cv.cadence.value, prevCv?.cadence?.value),
      borderColor: getStatusColor(norm?.comparison),
      statusLabel: norm?.comparison_label ?? '',
      statusColor: getStatusBg(norm?.comparison),
    });
  }

  if (cards.length === 0) return null;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      {cards.map((card, i) => (
        <div key={i} className={`bg-white dark:bg-gray-800 p-3 rounded-xl shadow-sm border-l-4 ${card.borderColor}`}>
          <p className="text-[11px] text-gray-500 dark:text-gray-400 truncate">{card.label}</p>
          <p className="text-xl font-bold text-gray-900 dark:text-gray-100 mt-0.5">
            {card.value}
            <span className="text-[10px] font-normal text-gray-400 ml-1">{card.unit}</span>
          </p>
          <div className="flex items-center justify-between mt-1">
            {card.delta && card.delta.delta > 0 ? (
              <span className={`text-[11px] font-semibold ${card.delta.color}`}>
                {card.delta.arrow} {card.delta.delta.toFixed(2)}
              </span>
            ) : (
              <span className="text-[11px] text-gray-300">-</span>
            )}
            {card.statusLabel && (
              <span className={`text-[10px] ${card.statusColor}`}>{card.statusLabel}</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
