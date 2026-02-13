import { useState, useEffect } from 'react';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { testApi } from '../services/api';
import type { ClinicalCorrelationsResponse, TestType } from '../types';

interface CorrelationAnalysisProps {
  patientId: string;
  testType?: TestType;
}

function getCorrColor(r: number): string {
  const abs = Math.abs(r);
  if (abs >= 0.7) return r > 0 ? 'bg-blue-500 text-white' : 'bg-red-500 text-white';
  if (abs >= 0.3) return r > 0 ? 'bg-blue-200 text-blue-900 dark:bg-blue-800 dark:text-blue-200' : 'bg-red-200 text-red-900 dark:bg-red-800 dark:text-red-200';
  return 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400';
}

function getCorrBarWidth(r: number): string {
  return `${Math.min(100, Math.abs(r) * 100)}%`;
}

export default function CorrelationAnalysis({ patientId, testType = '10MWT' }: CorrelationAnalysisProps) {
  const [data, setData] = useState<ClinicalCorrelationsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<'matrix' | 'scatter'>('matrix');
  const [selectedPair, setSelectedPair] = useState(0);

  useEffect(() => {
    testApi.getClinicalCorrelations(patientId, testType)
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

  if (!data || !data.sufficient_data) {
    if (data?.message) {
      return (
        <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm">
          <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100 mb-2">상관관계 분석</h3>
          <p className="text-xs text-gray-400">{data.message}</p>
        </div>
      );
    }
    return null;
  }

  const { variables, variable_labels, correlation_matrix, significant_correlations, scatter_data, speed_correlations } = data;

  const scatterKeys = Object.keys(scatter_data);
  const currentScatter = scatterKeys[selectedPair] ? scatter_data[scatterKeys[selectedPair]] : [];
  const currentPair = significant_correlations[selectedPair];

  return (
    <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100">상관관계 분석</h3>
        <div className="flex gap-1">
          <button
            onClick={() => setMode('matrix')}
            className={`px-2 py-1 text-[10px] rounded ${mode === 'matrix' ? 'bg-blue-500 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-500'}`}
          >
            행렬
          </button>
          <button
            onClick={() => setMode('scatter')}
            className={`px-2 py-1 text-[10px] rounded ${mode === 'scatter' ? 'bg-blue-500 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-500'}`}
          >
            산점도
          </button>
        </div>
      </div>

      {/* 속도-변수 상관 순위 */}
      {speed_correlations.length > 0 && (
        <div>
          <p className="text-[11px] text-gray-500 dark:text-gray-400 mb-2">속도와의 상관관계</p>
          <div className="space-y-1.5">
            {speed_correlations.map(sc => (
              <div key={sc.variable} className="flex items-center gap-2">
                <span className="text-[10px] text-gray-600 dark:text-gray-400 w-20 truncate">{sc.label}</span>
                <div className="flex-1 h-3 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${sc.r >= 0 ? 'bg-blue-400' : 'bg-red-400'}`}
                    style={{ width: getCorrBarWidth(sc.r) }}
                  />
                </div>
                <span className="text-[10px] font-mono w-10 text-right text-gray-600 dark:text-gray-400">
                  {sc.r > 0 ? '+' : ''}{sc.r.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 모드 1: 상관행렬 */}
      {mode === 'matrix' && (
        <div className="overflow-x-auto">
          <div className="inline-grid gap-px" style={{ gridTemplateColumns: `60px repeat(${variables.length}, 40px)` }}>
            {/* 헤더 */}
            <div />
            {variables.map(v => (
              <div key={v} className="text-[8px] text-gray-500 text-center truncate px-0.5">
                {(variable_labels[v] || v).slice(0, 4)}
              </div>
            ))}
            {/* 행 */}
            {variables.map((vi, i) => (
              <>
                <div key={`label-${vi}`} className="text-[9px] text-gray-600 dark:text-gray-400 truncate pr-1 flex items-center">
                  {(variable_labels[vi] || vi).slice(0, 6)}
                </div>
                {variables.map((_, j) => (
                  <div
                    key={`${i}-${j}`}
                    className={`w-10 h-8 flex items-center justify-center text-[9px] font-mono rounded-sm ${getCorrColor(correlation_matrix[i][j])}`}
                  >
                    {i === j ? '-' : correlation_matrix[i][j].toFixed(1)}
                  </div>
                ))}
              </>
            ))}
          </div>
        </div>
      )}

      {/* 모드 2: 산점도 */}
      {mode === 'scatter' && significant_correlations.length > 0 && (
        <div>
          <select
            value={selectedPair}
            onChange={e => setSelectedPair(Number(e.target.value))}
            className="w-full text-xs p-1.5 rounded border dark:bg-gray-700 dark:border-gray-600 mb-2"
          >
            {significant_correlations.map((sc, i) => (
              <option key={i} value={i}>{sc.label} (r={sc.r.toFixed(2)})</option>
            ))}
          </select>

          {currentScatter.length > 0 && (
            <ResponsiveContainer width="100%" height={180}>
              <ScatterChart margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="x"
                  type="number"
                  tick={{ fontSize: 10 }}
                  stroke="#9ca3af"
                  name={currentPair ? variable_labels[currentPair.var1] : ''}
                />
                <YAxis
                  dataKey="y"
                  type="number"
                  tick={{ fontSize: 10 }}
                  stroke="#9ca3af"
                  name={currentPair ? variable_labels[currentPair.var2] : ''}
                />
                <Tooltip
                  cursor={{ strokeDasharray: '3 3' }}
                  contentStyle={{ fontSize: 11, borderRadius: 8 }}
                />
                <Scatter data={currentScatter} fill="#3B82F6" r={4} />
              </ScatterChart>
            </ResponsiveContainer>
          )}

          {currentPair && (
            <p className="text-[10px] text-center text-gray-400 mt-1">
              r = {currentPair.r.toFixed(3)}, p = {currentPair.p_value?.toFixed(4)}
            </p>
          )}
        </div>
      )}

      <p className="text-[10px] text-gray-400 text-center">
        {data.n_tests}개 검사 기반 분석
      </p>
    </div>
  );
}
