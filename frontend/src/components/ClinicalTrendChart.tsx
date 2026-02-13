import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { testApi } from '../services/api';
import type { ClinicalTrendsResponse, ClinicalNormativeResponse, TestType } from '../types';

interface ClinicalTrendChartProps {
  patientId: string;
  testType?: TestType;
  clinicalNormative?: ClinicalNormativeResponse | null;
}

const VAR_OPTIONS: { key: string; label: string; unit: string; color: string }[] = [
  { key: 'stride_length', label: '보폭', unit: 'm', color: '#3B82F6' },
  { key: 'cadence', label: '분당 걸음수', unit: 'steps/min', color: '#8B5CF6' },
  { key: 'double_support', label: '이중지지기', unit: '%', color: '#EF4444' },
  { key: 'walk_time', label: '보행 시간', unit: '초', color: '#06B6D4' },
];

export default function ClinicalTrendChart({ patientId, testType = '10MWT', clinicalNormative }: ClinicalTrendChartProps) {
  const [data, setData] = useState<ClinicalTrendsResponse | null>(null);
  const [selectedVar, setSelectedVar] = useState(testType === '10MWT' ? 'cadence' : 'stride_length');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    testApi.getClinicalTrends(patientId, testType)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [patientId, testType]);

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm">
        <div className="animate-pulse h-48 bg-gray-100 dark:bg-gray-700 rounded-lg" />
      </div>
    );
  }

  if (!data || data.data_points.length < 2) return null;

  const filteredOptions = testType === '10MWT'
    ? VAR_OPTIONS.filter(v => v.key !== 'stride_length')
    : VAR_OPTIONS;
  const varInfo = filteredOptions.find(v => v.key === selectedVar) || filteredOptions[0];
  const availableVars = filteredOptions.filter(v =>
    data.data_points.some(p => (p as unknown as Record<string, unknown>)[v.key] != null)
  );

  // 정상 범위 참조선
  const normData = clinicalNormative?.[selectedVar === 'walk_time' ? 'step_time' : selectedVar];
  const normLow = normData?.normative?.range_low;
  const normHigh = normData?.normative?.range_high;

  const chartData = data.data_points.map(p => ({
    date: p.date?.slice(5) || '',
    value: (p as unknown as Record<string, unknown>)[selectedVar] as number | undefined,
  })).filter(d => d.value != null);

  return (
    <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100">임상 변수 추이</h3>
      </div>

      <div className="flex flex-wrap gap-1 mb-3">
        {availableVars.map(v => (
          <button
            key={v.key}
            onClick={() => setSelectedVar(v.key)}
            className={`px-2 py-1 text-[11px] rounded-full transition-colors ${
              selectedVar === v.key
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
            }`}
          >
            {v.label}
          </button>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="date" tick={{ fontSize: 10 }} stroke="#9ca3af" />
          <YAxis tick={{ fontSize: 10 }} stroke="#9ca3af" domain={['auto', 'auto']} />
          <Tooltip
            formatter={(val: number) => [`${val} ${varInfo.unit}`, varInfo.label]}
            contentStyle={{ fontSize: 12, borderRadius: 8 }}
          />
          {normLow != null && (
            <ReferenceLine y={normLow} stroke="#22c55e" strokeDasharray="4 4" label={{ value: '하한', fontSize: 9, fill: '#22c55e' }} />
          )}
          {normHigh != null && (
            <ReferenceLine y={normHigh} stroke="#22c55e" strokeDasharray="4 4" label={{ value: '상한', fontSize: 9, fill: '#22c55e' }} />
          )}
          <Line
            type="monotone"
            dataKey="value"
            stroke={varInfo.color}
            strokeWidth={2}
            dot={{ r: 3, fill: varInfo.color }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>

      <p className="text-[10px] text-gray-400 text-center mt-1">
        {data.tests_with_clinical_data}개 검사 데이터
      </p>
    </div>
  );
}
