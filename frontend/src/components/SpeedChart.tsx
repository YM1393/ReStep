import { useState, useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceArea,
} from 'recharts';
import type { WalkTest, TestType, NormativeRange } from '../types';

interface SpeedChartProps {
  tests: WalkTest[];
  testType?: TestType | 'ALL';
  normativeRange?: NormativeRange;
}

type DateRange = '3m' | '6m' | '1y' | 'all';

const PAGE_SIZE = 20;

export default function SpeedChart({ tests, testType = 'ALL', normativeRange }: SpeedChartProps) {
  const isTUG = testType === 'TUG';
  const gridColor = '#e5e7eb';
  const tickColor = '#6b7280';

  const [dateRange, setDateRange] = useState<DateRange>('all');
  const [page, setPage] = useState(0);

  // Sort by date ascending
  const sortedTests = useMemo(() =>
    [...tests].sort(
      (a, b) => new Date(a.test_date).getTime() - new Date(b.test_date).getTime()
    ),
    [tests]
  );

  // Apply date range filter
  const filteredTests = useMemo(() => {
    if (dateRange === 'all') return sortedTests;
    const now = new Date();
    const cutoff = new Date();
    if (dateRange === '3m') cutoff.setMonth(now.getMonth() - 3);
    else if (dateRange === '6m') cutoff.setMonth(now.getMonth() - 6);
    else if (dateRange === '1y') cutoff.setFullYear(now.getFullYear() - 1);
    return sortedTests.filter(t => new Date(t.test_date) >= cutoff);
  }, [sortedTests, dateRange]);

  // Pagination
  const totalPages = Math.max(1, Math.ceil(filteredTests.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages - 1);
  const needsPagination = filteredTests.length > PAGE_SIZE;

  const pagedTests = useMemo(() => {
    if (!needsPagination) return filteredTests;
    const start = currentPage * PAGE_SIZE;
    return filteredTests.slice(start, start + PAGE_SIZE);
  }, [filteredTests, currentPage, needsPagination]);

  // Moving average (3-point)
  const calcMovingAvg = (values: number[], window = 3): (number | null)[] => {
    return values.map((_, i) => {
      if (i < window - 1) return null;
      const slice = values.slice(i - window + 1, i + 1);
      return parseFloat((slice.reduce((a, b) => a + b, 0) / slice.length).toFixed(2));
    });
  };

  const speeds = pagedTests.map(t => t.walk_speed_mps);
  const times = pagedTests.map(t => t.walk_time_seconds);
  const speedTrend = calcMovingAvg(speeds);
  const timeTrend = calcMovingAvg(times);

  // Calculate the global index offset for display
  const globalOffset = needsPagination ? currentPage * PAGE_SIZE : 0;

  const data = pagedTests.map((test, index) => ({
    name: `${globalOffset + index + 1}회`,
    date: new Date(test.test_date).toLocaleDateString('ko-KR'),
    speed: test.walk_speed_mps,
    time: test.walk_time_seconds,
    speedTrend: speedTrend[index],
    timeTrend: timeTrend[index],
  }));

  const chartTitle = isTUG ? 'TUG 검사 변화 추이' : '보행 변화 추이';

  const dateRangeOptions: { key: DateRange; label: string }[] = [
    { key: '3m', label: '3개월' },
    { key: '6m', label: '6개월' },
    { key: '1y', label: '1년' },
    { key: 'all', label: '전체' },
  ];

  if (tests.length < 2) {
    return (
      <div className="card">
        <h3 className="font-semibold text-gray-800 dark:text-gray-100 mb-4">{chartTitle}</h3>
        <div className="h-64 flex flex-col items-center justify-center text-gray-400">
          <svg className="w-12 h-12 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <p className="text-sm">그래프를 보려면 2회 이상의 검사가 필요합니다</p>
        </div>
      </div>
    );
  }

  // Filter bar + pagination controls
  const FilterBar = () => (
    <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
      <div className="flex gap-1">
        {dateRangeOptions.map(opt => (
          <button
            key={opt.key}
            onClick={() => { setDateRange(opt.key); setPage(0); }}
            className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors ${
              dateRange === opt.key
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>
      <span className="text-xs text-gray-500 dark:text-gray-400">
        {filteredTests.length}회 검사
      </span>
    </div>
  );

  const PaginationControls = () => {
    if (!needsPagination) return null;
    return (
      <div className="flex items-center justify-center gap-2 mt-3">
        <button
          onClick={() => setPage(p => Math.max(0, p - 1))}
          disabled={currentPage === 0}
          className="px-2 py-1 rounded text-xs font-semibold bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          &lt; 이전
        </button>
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {currentPage + 1} / {totalPages}
        </span>
        <button
          onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
          disabled={currentPage >= totalPages - 1}
          className="px-2 py-1 rounded text-xs font-semibold bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          다음 &gt;
        </button>
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {/* Speed chart (not for TUG) */}
      {!isTUG && (
      <div className="card">
        <div className="flex items-center mb-4">
          <div className="w-3 h-3 bg-blue-500 rounded-full mr-2" />
          <h3 className="font-semibold text-gray-800 dark:text-gray-100">보행 속도 변화 추이</h3>
          <span className="ml-2 text-sm text-gray-500 dark:text-gray-400">(m/s)</span>
        </div>
        <FilterBar />
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10, fill: tickColor }}
                stroke={gridColor}
              />
              <YAxis
                domain={[0, 2]}
                tick={{ fontSize: 10, fill: tickColor }}
                stroke={gridColor}
                tickFormatter={(value) => `${value}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'white',
                  border: 'none',
                  borderRadius: '12px',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                }}
                formatter={(value: number, name: string) => {
                  if (name === 'speedTrend') return [`${value.toFixed(2)} m/s`, '추세'];
                  return [`${value.toFixed(2)} m/s`, '보행 속도'];
                }}
                labelFormatter={(label) => `날짜: ${label}`}
              />
              {normativeRange && (
                <ReferenceArea
                  y1={normativeRange.range_low}
                  y2={normativeRange.range_high}
                  fill="#22c55e"
                  fillOpacity={0.08}
                  label={{ value: `정상 ${normativeRange.range_low}-${normativeRange.range_high}`, position: 'insideTopRight', fontSize: 8, fill: '#22c55e' }}
                />
              )}
              <ReferenceLine
                y={1.2}
                stroke="#22c55e"
                strokeDasharray="5 5"
                label={{ value: '정상 (≤8.3초)', position: 'right', fontSize: 9, fill: '#22c55e' }}
              />
              <ReferenceLine
                y={0.8}
                stroke="#ef4444"
                strokeDasharray="5 5"
                label={{ value: '위험 (>12.5초)', position: 'right', fontSize: 9, fill: '#ef4444' }}
              />
              <Line
                type="monotone"
                dataKey="speed"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={{ fill: '#3b82f6', strokeWidth: 1, r: 4 }}
                activeDot={{ r: 6, fill: '#2563eb' }}
              />
              {data.length >= 3 && (
                <Line
                  type="monotone"
                  dataKey="speedTrend"
                  stroke="#3b82f6"
                  strokeWidth={1.5}
                  strokeDasharray="4 4"
                  dot={false}
                  connectNulls
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="flex justify-center gap-6 mt-3 text-xs">
          <div className="flex items-center">
            <div className="w-3 h-0.5 mr-1.5" style={{ borderTop: '2px dashed #22c55e' }} />
            <span className="text-green-600 dark:text-green-400">정상 (≤8.3초)</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-0.5 mr-1.5" style={{ borderTop: '2px dashed #ef4444' }} />
            <span className="text-red-500 dark:text-red-400">위험 ({'>'}12.5초)</span>
          </div>
        </div>
        <PaginationControls />
      </div>
      )}

      {/* Time chart */}
      <div className="card">
        <div className="flex items-center mb-4">
          <div className={`w-3 h-3 rounded-full mr-2 ${isTUG ? 'bg-green-500' : 'bg-purple-500'}`} />
          <h3 className="font-semibold text-gray-800 dark:text-gray-100">
            {isTUG ? 'TUG 시간 변화 추이' : '보행 시간 변화 추이'}
          </h3>
          <span className="ml-2 text-sm text-gray-500 dark:text-gray-400">(초)</span>
        </div>
        {/* Show filter only for TUG (speed chart already has it for non-TUG) */}
        {isTUG && <FilterBar />}
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10, fill: tickColor }}
                stroke={gridColor}
              />
              <YAxis
                domain={isTUG ? [0, 40] : [0, 20]}
                tick={{ fontSize: 10, fill: tickColor }}
                stroke={gridColor}
                tickFormatter={(value) => `${value}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'white',
                  border: 'none',
                  borderRadius: '12px',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                }}
                formatter={(value: number, name: string) => {
                  if (name === 'timeTrend') return [`${value.toFixed(2)} 초`, '추세'];
                  return [`${value.toFixed(2)} 초`, isTUG ? 'TUG 시간' : '보행 시간'];
                }}
                labelFormatter={(label) => `날짜: ${label}`}
              />
              {isTUG ? (
                <>
                  <ReferenceLine
                    y={10}
                    stroke="#22c55e"
                    strokeDasharray="5 5"
                    label={{ value: '정상 10', position: 'right', fontSize: 9, fill: '#22c55e' }}
                  />
                  <ReferenceLine
                    y={20}
                    stroke="#3b82f6"
                    strokeDasharray="5 5"
                    label={{ value: '양호 20', position: 'right', fontSize: 9, fill: '#3b82f6' }}
                  />
                  <ReferenceLine
                    y={30}
                    stroke="#ef4444"
                    strokeDasharray="5 5"
                    label={{ value: '위험 30', position: 'right', fontSize: 9, fill: '#ef4444' }}
                  />
                </>
              ) : (
                <>
                  <ReferenceLine
                    y={8.3}
                    stroke="#22c55e"
                    strokeDasharray="5 5"
                    label={{ value: '정상 8.3', position: 'right', fontSize: 9, fill: '#22c55e' }}
                  />
                  <ReferenceLine
                    y={12.5}
                    stroke="#ef4444"
                    strokeDasharray="5 5"
                    label={{ value: '위험 12.5', position: 'right', fontSize: 9, fill: '#ef4444' }}
                  />
                </>
              )}
              <Line
                type="monotone"
                dataKey="time"
                stroke={isTUG ? '#22c55e' : '#8b5cf6'}
                strokeWidth={2}
                dot={{ fill: isTUG ? '#22c55e' : '#8b5cf6', strokeWidth: 1, r: 4 }}
                activeDot={{ r: 6, fill: isTUG ? '#16a34a' : '#7c3aed' }}
              />
              {data.length >= 3 && (
                <Line
                  type="monotone"
                  dataKey="timeTrend"
                  stroke={isTUG ? '#22c55e' : '#8b5cf6'}
                  strokeWidth={1.5}
                  strokeDasharray="4 4"
                  dot={false}
                  connectNulls
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="flex justify-center gap-6 mt-3 text-xs">
          {isTUG ? (
            <>
              <div className="flex items-center">
                <div className="w-3 h-0.5 mr-1.5" style={{ borderTop: '2px dashed #22c55e' }} />
                <span className="text-green-600 dark:text-green-400">정상 (&lt;10초)</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-0.5 mr-1.5" style={{ borderTop: '2px dashed #3b82f6' }} />
                <span className="text-blue-600 dark:text-blue-400">양호 (10-20초)</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-0.5 mr-1.5" style={{ borderTop: '2px dashed #ef4444' }} />
                <span className="text-red-500 dark:text-red-400">위험 ({'>='}30초)</span>
              </div>
            </>
          ) : (
            <>
              <div className="flex items-center">
                <div className="w-3 h-0.5 mr-1.5" style={{ borderTop: '2px dashed #22c55e' }} />
                <span className="text-green-600 dark:text-green-400">정상 ({'<='}8.3초)</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-0.5 mr-1.5" style={{ borderTop: '2px dashed #ef4444' }} />
                <span className="text-red-500 dark:text-red-400">위험 ({'>='}12.5초)</span>
              </div>
            </>
          )}
        </div>
        <PaginationControls />
      </div>
    </div>
  );
}
