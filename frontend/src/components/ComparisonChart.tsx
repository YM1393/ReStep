import { useMemo } from 'react';
import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  Radar, Legend, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
} from 'recharts';
import type { WalkTest, AnalysisData, ClinicalVariables } from '../types';

interface ComparisonChartProps {
  currentTest: WalkTest;
  previousTest: WalkTest;
}

// Normalize a value to 0-100 scale given min/max range
function normalize(value: number, min: number, max: number): number {
  if (max === min) return 50;
  return Math.max(0, Math.min(100, ((value - min) / (max - min)) * 100));
}

// Extract metrics for radar chart from clinical variables
function extractRadarMetrics(test: WalkTest): Record<string, number> {
  const ad = test.analysis_data as AnalysisData | undefined;
  const cv: ClinicalVariables | undefined = ad?.clinical_variables;

  return {
    speed: test.walk_speed_mps,
    cadence: cv?.cadence?.value ?? 0,
    trunkStability: cv?.trunk_inclination
      ? Math.max(0, 100 - cv.trunk_inclination.std * 10)
      : 0,
  };
}

export default function ComparisonChart({ currentTest, previousTest }: ComparisonChartProps) {
  const radarData = useMemo(() => {
    const curr = extractRadarMetrics(currentTest);
    const prev = extractRadarMetrics(previousTest);

    // Only show radar if at least some clinical variables exist
    const hasClinical = curr.cadence > 0 || prev.cadence > 0;

    if (!hasClinical) return null;

    return [
      {
        metric: '보행 속도',
        current: normalize(curr.speed, 0, 2.0),
        previous: normalize(prev.speed, 0, 2.0),
      },
      {
        metric: '분당 보수',
        current: normalize(curr.cadence, 0, 160),
        previous: normalize(prev.cadence, 0, 160),
      },
      {
        metric: '체간 안정성',
        current: curr.trunkStability,
        previous: prev.trunkStability,
      },
    ];
  }, [currentTest, previousTest]);

  const barData = useMemo(() => {
    const speedDiff = currentTest.walk_speed_mps - previousTest.walk_speed_mps;
    const timeDiff = currentTest.walk_time_seconds - previousTest.walk_time_seconds;

    return [
      {
        name: '보행 속도 (m/s)',
        current: Number(currentTest.walk_speed_mps.toFixed(2)),
        previous: Number(previousTest.walk_speed_mps.toFixed(2)),
        delta: Number(speedDiff.toFixed(2)),
        unit: 'm/s',
        higherIsBetter: true,
      },
      {
        name: '보행 시간 (초)',
        current: Number(currentTest.walk_time_seconds.toFixed(2)),
        previous: Number(previousTest.walk_time_seconds.toFixed(2)),
        delta: Number(timeDiff.toFixed(2)),
        unit: '초',
        higherIsBetter: false,
      },
    ];
  }, [currentTest, previousTest]);

  return (
    <div className="space-y-6">
      {/* Bar Chart - Speed & Time Comparison */}
      <div>
        <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
          주요 지표 비교
        </h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {barData.map((item) => {
            const improved = item.higherIsBetter
              ? item.delta > 0
              : item.delta < 0;
            const deltaText = `${item.delta > 0 ? '+' : ''}${item.delta} ${item.unit}`;

            return (
              <div
                key={item.name}
                className="bg-gray-50 dark:bg-gray-700/50 rounded-xl p-4"
              >
                <div className="flex justify-between items-center mb-2">
                  <span className="text-xs text-gray-500 dark:text-gray-400">{item.name}</span>
                  <span
                    className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                      improved
                        ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                        : item.delta === 0
                        ? 'bg-gray-100 dark:bg-gray-600 text-gray-600 dark:text-gray-300'
                        : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
                    }`}
                  >
                    {deltaText}
                  </span>
                </div>
                <ResponsiveContainer width="100%" height={100}>
                  <BarChart
                    data={[item]}
                    layout="vertical"
                    margin={{ top: 0, right: 30, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" hide />
                    <YAxis type="category" dataKey="name" hide />
                    <Tooltip
                      formatter={(value: number, name: string) => [
                        `${value} ${item.unit}`,
                        name === 'previous' ? '이전' : '현재',
                      ]}
                      contentStyle={{
                        borderRadius: '8px',
                        border: 'none',
                        boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                      }}
                    />
                    <Bar dataKey="previous" fill="#9CA3AF" name="이전" radius={[4, 4, 4, 4]} barSize={20} />
                    <Bar dataKey="current" fill="#2563EB" name="현재" radius={[4, 4, 4, 4]} barSize={20} />
                  </BarChart>
                </ResponsiveContainer>
                <div className="flex justify-between text-xs mt-1">
                  <span className="text-gray-400">
                    이전: <span className="text-gray-600 dark:text-gray-300 font-medium">{item.previous} {item.unit}</span>
                  </span>
                  <span className="text-gray-400">
                    현재: <span className="text-blue-600 dark:text-blue-400 font-medium">{item.current} {item.unit}</span>
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Radar Chart - Multi-metric comparison */}
      {radarData && (
        <div>
          <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
            종합 보행 지표
          </h4>
          <div className="bg-gray-50 dark:bg-gray-700/50 rounded-xl p-4">
            <ResponsiveContainer width="100%" height={300}>
              <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="70%">
                <PolarGrid stroke="#d1d5db" />
                <PolarAngleAxis
                  dataKey="metric"
                  tick={{ fontSize: 12, fill: '#6b7280' }}
                />
                <PolarRadiusAxis
                  angle={90}
                  domain={[0, 100]}
                  tick={false}
                  axisLine={false}
                />
                <Radar
                  name="이전"
                  dataKey="previous"
                  stroke="#9CA3AF"
                  fill="#9CA3AF"
                  fillOpacity={0.2}
                  strokeWidth={2}
                />
                <Radar
                  name="현재"
                  dataKey="current"
                  stroke="#2563EB"
                  fill="#2563EB"
                  fillOpacity={0.3}
                  strokeWidth={2}
                />
                <Legend
                  wrapperStyle={{ fontSize: '12px' }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
