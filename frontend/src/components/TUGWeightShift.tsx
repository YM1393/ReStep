import type { WeightShiftData } from '../types';

interface TUGWeightShiftProps {
  data: WeightShiftData;
}

const getShiftColor = (shift: string): string => {
  if (shift.includes('편향')) return 'text-orange-500';
  if (shift === '균형') return 'text-green-500';
  return 'text-gray-500';
};

export default function TUGWeightShift({ data }: TUGWeightShiftProps) {
  // CoP 궤적 시각화를 위한 SVG 경로 생성
  const trajectory = data.cop_trajectory || [];
  const hasTrajectory = trajectory.length > 2;

  // 궤적 SVG 범위 계산
  let svgPath = '';
  let minX = 0, maxX = 0;
  if (hasTrajectory) {
    const xValues = trajectory.map(p => p.x);
    minX = Math.min(...xValues) - 5;
    maxX = Math.max(...xValues) + 5;
    const range = maxX - minX || 1;
    const timeRange = trajectory[trajectory.length - 1].time - trajectory[0].time || 1;

    const points = trajectory.map((p, i) => {
      const x = ((p.x - minX) / range) * 280 + 10;
      const y = ((p.time - trajectory[0].time) / timeRange) * 80 + 10;
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
    });
    svgPath = points.join(' ');
  }

  return (
    <div>
      <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3 flex items-center">
        <svg className="w-4 h-4 mr-1.5 text-teal-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
        </svg>
        체중이동 분석 (정면 영상)
      </p>

      {/* 통계 카드 */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="p-2.5 bg-teal-50 dark:bg-teal-900/20 rounded-lg text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">좌우 흔들림</p>
          <p className="text-lg font-bold text-gray-800 dark:text-gray-100">
            {data.lateral_sway_amplitude.toFixed(1)}<span className="text-xs text-gray-500">%</span>
          </p>
        </div>
        <div className="p-2.5 bg-teal-50 dark:bg-teal-900/20 rounded-lg text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">최대 편향</p>
          <p className="text-lg font-bold text-gray-800 dark:text-gray-100">
            {data.lateral_sway_max.toFixed(1)}<span className="text-xs text-gray-500">%</span>
          </p>
        </div>
        <div className="p-2.5 bg-teal-50 dark:bg-teal-900/20 rounded-lg text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">진동 주파수</p>
          <p className="text-lg font-bold text-gray-800 dark:text-gray-100">
            {data.sway_frequency.toFixed(1)}<span className="text-xs text-gray-500">Hz</span>
          </p>
        </div>
      </div>

      {/* 기립 시 체중이동 방향 */}
      <div className="p-2.5 bg-white dark:bg-gray-700 rounded-lg mb-3">
        <div className="flex items-center justify-between">
          <p className="text-xs text-gray-500 dark:text-gray-400">기립 시 체중이동</p>
          <p className={`text-sm font-bold ${getShiftColor(data.standup_weight_shift)}`}>
            {data.standup_weight_shift}
          </p>
        </div>
        {/* 방향 시각화 바 */}
        <div className="mt-2 relative h-3 bg-gray-100 dark:bg-gray-600 rounded-full overflow-hidden">
          <div className="absolute inset-y-0 left-1/2 w-px bg-gray-300 dark:bg-gray-500" />
          <div className="absolute top-0 left-0 text-[8px] text-gray-400 ml-0.5">L</div>
          <div className="absolute top-0 right-0 text-[8px] text-gray-400 mr-0.5">R</div>
        </div>
      </div>

      {/* CoP 궤적 시각화 */}
      {hasTrajectory && (
        <div className="p-2.5 bg-white dark:bg-gray-700 rounded-lg mb-3">
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">좌우 이동 궤적</p>
          <svg viewBox="0 0 300 100" className="w-full h-16">
            {/* 중앙선 */}
            <line x1="150" y1="5" x2="150" y2="95" stroke="currentColor" strokeWidth="0.5" className="text-gray-300 dark:text-gray-600" strokeDasharray="4,4" />
            {/* 궤적 */}
            <path d={svgPath} fill="none" stroke="currentColor" strokeWidth="1.5" className="text-teal-500" />
          </svg>
          <div className="flex justify-between text-[10px] text-gray-400">
            <span>왼쪽</span>
            <span>중앙</span>
            <span>오른쪽</span>
          </div>
        </div>
      )}

      {/* 종합 평가 */}
      <p className="text-xs text-gray-500 dark:text-gray-400">{data.assessment}</p>
    </div>
  );
}
