import { useState, useEffect } from 'react';
import {
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  ComposedChart,
} from 'recharts';
import { testApi } from '../services/api';
import type { TrendAnalysisResponse, TestType } from '../types';

interface Props {
  patientId: string;
  testType?: TestType;
}

const TREND_LABELS: Record<string, { label: string; color: string }> = {
  improving: { label: '개선 중', color: 'text-green-600 dark:text-green-400' },
  stable: { label: '안정', color: 'text-blue-600 dark:text-blue-400' },
  declining: { label: '저하 중', color: 'text-red-600 dark:text-red-400' },
};

export default function TrendChart({ patientId, testType = '10MWT' }: Props) {
  const [data, setData] = useState<TrendAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTrends();
  }, [patientId, testType]);

  const loadTrends = async () => {
    try {
      setLoading(true);
      const result = await testApi.getTrends(patientId, testType);
      setData(result);
    } catch {
      // Trends are optional
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm">
        <h3 className="font-bold text-gray-900 dark:text-gray-100 mb-3">추세 분석</h3>
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
        </div>
      </div>
    );
  }

  if (!data) return null;

  if (!data.sufficient_data) {
    return (
      <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm">
        <h3 className="font-bold text-gray-900 dark:text-gray-100 mb-3">추세 분석</h3>
        <div className="text-center py-6">
          <svg className="w-10 h-10 text-gray-300 dark:text-gray-600 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
          </svg>
          <p className="text-sm text-gray-500 dark:text-gray-400">{data.message}</p>
        </div>
      </div>
    );
  }

  const trendConfig = TREND_LABELS[data.trend_direction || 'stable'];

  // Build chart data: actual + predictions
  const chartData: any[] = [];

  // Actual data points
  for (const dp of data.data_points || []) {
    chartData.push({
      date: dp.date.substring(5), // MM-DD
      fullDate: dp.date,
      value: dp.value,
      trendLine: dp.trend_value,
      type: 'actual',
    });
  }

  // Prediction data points
  for (const pred of data.predictions || []) {
    chartData.push({
      date: pred.date.substring(5),
      fullDate: pred.date,
      prediction: pred.value,
      predLower: pred.lower,
      predUpper: pred.upper,
      trendLine: pred.value,
      type: 'prediction',
    });
  }

  // Goal line value
  const goalValue = data.goal_info?.target_value;

  const gridColor = '#e5e7eb';
  const tickColor = '#6b7280';

  return (
    <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-bold text-gray-900 dark:text-gray-100">추세 분석</h3>
        <div className="flex items-center gap-2">
          <span className={`text-sm font-semibold ${trendConfig.color}`}>
            {trendConfig.label}
          </span>
          {data.r_squared != null && (
            <span className="text-xs text-gray-400 dark:text-gray-400">
              R²={data.r_squared}
            </span>
          )}
        </div>
      </div>

      {/* Stats summary */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        <div className="p-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400">현재</p>
          <p className="text-sm font-bold text-gray-900 dark:text-gray-100">
            {data.latest_value} {data.value_unit}
          </p>
        </div>
        <div className="p-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400">주당 변화</p>
          <p className={`text-sm font-bold ${
            data.slope_per_week && data.slope_per_week > 0
              ? (testType === 'TUG' ? 'text-red-600' : 'text-green-600')
              : data.slope_per_week && data.slope_per_week < 0
              ? (testType === 'TUG' ? 'text-green-600' : 'text-red-600')
              : 'text-gray-600'
          }`}>
            {data.slope_per_week && data.slope_per_week > 0 ? '+' : ''}{data.slope_per_week}
          </p>
        </div>
        <div className="p-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400">측정 횟수</p>
          <p className="text-sm font-bold text-gray-900 dark:text-gray-100">
            {data.total_measurements}회
          </p>
        </div>
      </div>

      {/* Chart */}
      <div className="h-52">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 5, right: 15, left: 5, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 9, fill: tickColor }}
              stroke={gridColor}
            />
            <YAxis
              tick={{ fontSize: 9, fill: tickColor }}
              stroke={gridColor}
              domain={['auto', 'auto']}
              tickFormatter={(v) => `${v}`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'white',
                border: 'none',
                borderRadius: '12px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                fontSize: '12px',
              }}
              formatter={(value: number, name: string) => {
                const unit = data.value_unit || '';
                if (name === 'trendLine') return [`${value?.toFixed(3)} ${unit}`, '추세선'];
                if (name === 'prediction') return [`${value?.toFixed(3)} ${unit}`, '예측'];
                if (name === 'value') return [`${value?.toFixed(3)} ${unit}`, data.value_label || '값'];
                return [value, name];
              }}
              labelFormatter={(label) => `${label}`}
            />

            {/* Confidence band for predictions */}
            <Area
              dataKey="predUpper"
              stroke="none"
              fill="#3b82f6"
              fillOpacity={0.08}
            />
            <Area
              dataKey="predLower"
              stroke="none"
              fill="white"
              fillOpacity={1}
            />

            {/* Goal line */}
            {goalValue != null && (
              <ReferenceLine
                y={goalValue}
                stroke="#f59e0b"
                strokeDasharray="5 5"
                label={{ value: `목표 ${goalValue}`, position: 'right', fontSize: 9, fill: '#f59e0b' }}
              />
            )}

            {/* Trend line (dashed, extends into predictions) */}
            <Line
              type="monotone"
              dataKey="trendLine"
              stroke="#94a3b8"
              strokeWidth={1.5}
              strokeDasharray="6 4"
              dot={false}
              connectNulls
            />

            {/* Actual data points */}
            <Line
              type="monotone"
              dataKey="value"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={{ fill: '#3b82f6', r: 4 }}
              activeDot={{ r: 6, fill: '#2563eb' }}
              connectNulls
            />

            {/* Prediction points */}
            <Line
              type="monotone"
              dataKey="prediction"
              stroke="#3b82f6"
              strokeWidth={1.5}
              strokeDasharray="4 4"
              dot={{ fill: '#93c5fd', stroke: '#3b82f6', strokeWidth: 1, r: 3 }}
              connectNulls
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap justify-center gap-4 mt-3 text-xs">
        <div className="flex items-center gap-1">
          <div className="w-3 h-0.5 bg-blue-500 rounded" />
          <span className="text-gray-500 dark:text-gray-400">측정값</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-0.5 border-t-2 border-dashed border-gray-400" />
          <span className="text-gray-500 dark:text-gray-400">추세선</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-0.5 border-t-2 border-dashed border-blue-400" />
          <span className="text-gray-500 dark:text-gray-400">예측</span>
        </div>
        {goalValue != null && (
          <div className="flex items-center gap-1">
            <div className="w-3 h-0.5 border-t-2 border-dashed border-amber-400" />
            <span className="text-gray-500 dark:text-gray-400">목표</span>
          </div>
        )}
      </div>

      {/* Goal ETA */}
      {data.goal_eta && (
        <div className="mt-3 p-2 bg-amber-50 dark:bg-amber-900/20 rounded-lg text-center">
          <p className="text-xs text-amber-700 dark:text-amber-400">
            <span className="font-semibold">목표 도달 예상일: </span>
            {data.goal_eta}
            {data.goal_info?.weeks_remaining && (
              <span className="ml-1">(약 {data.goal_info.weeks_remaining}주 후)</span>
            )}
          </p>
        </div>
      )}
      {data.goal_info?.message && !data.goal_eta && (
        <div className="mt-3 p-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400">{data.goal_info.message}</p>
        </div>
      )}

      {/* Predictions table */}
      {data.predictions && data.predictions.length > 0 && (
        <div className="mt-3">
          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">예측값</p>
          <div className="grid grid-cols-3 gap-1 text-xs">
            {data.predictions.map((pred, i) => (
              <div key={i} className="p-1.5 bg-gray-50 dark:bg-gray-700/50 rounded text-center">
                <p className="text-gray-400 dark:text-gray-400">{pred.label}</p>
                <p className="font-semibold text-gray-900 dark:text-gray-100">
                  {pred.value} {data.value_unit}
                </p>
                <p className="text-gray-400 dark:text-gray-400">
                  {pred.lower}~{pred.upper}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
