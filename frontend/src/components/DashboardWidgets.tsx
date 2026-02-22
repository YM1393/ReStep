import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { dashboardApi } from '../services/api';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts';

// ===== Recent Tests Widget =====
export function RecentTestsWidget() {
  const [tests, setTests] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    dashboardApi.getRecentTests(5).then(setTests).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <WidgetSkeleton />;

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">최근 검사</h3>
      {tests.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">검사 기록 없음</p>
      ) : (
        <div className="space-y-2">
          {tests.map(t => (
            <Link
              key={t.id}
              to={`/patients/${t.patient_id}`}
              className="flex items-center justify-between p-2.5 bg-gray-50 dark:bg-gray-700/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              <div className="flex items-center gap-1.5">
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                  (t.test_type || '10MWT') === 'TUG'
                    ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'
                    : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                }`}>
                  {t.test_type || '10MWT'}
                </span>
                <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{t.patient_name}</span>
                <span className="text-xs text-gray-500 dark:text-gray-400">#{t.patient_number}</span>
              </div>
              <div className="text-right">
                <span className="text-sm font-semibold text-blue-600 dark:text-blue-400">{t.walk_speed_mps.toFixed(2)} m/s</span>
                <div className="text-xs text-gray-400">{new Date(t.test_date).toLocaleDateString('ko-KR')}</div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

// ===== Risk Patients Widget =====
interface RiskPatientsProps {
  patients: { id: string; name: string; patient_number: string; speed: number; walkTime: number }[];
}

export function RiskPatientsWidget({ patients }: RiskPatientsProps) {
  const riskPatients = patients.filter(p => p.walkTime > 12.5).slice(0, 5);

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
        주의 필요 환자
        {riskPatients.length > 0 && (
          <span className="ml-2 text-xs px-2 py-0.5 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-full">
            {riskPatients.length}
          </span>
        )}
      </h3>
      {riskPatients.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">주의 필요 환자 없음</p>
      ) : (
        <div className="space-y-2">
          {riskPatients.map(p => (
            <Link
              key={p.id}
              to={`/patients/${p.id}`}
              className="flex items-center justify-between p-2.5 bg-red-50 dark:bg-red-900/10 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/20 transition-colors"
            >
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{p.name}</span>
              <span className="text-sm font-semibold text-red-600 dark:text-red-400">{p.walkTime.toFixed(1)}초</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

// ===== Speed Distribution Widget =====
export function SpeedDistributionWidget() {
  const [data, setData] = useState<{ name: string; value: number; color: string }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    dashboardApi.getSpeedDistribution().then(setData).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <WidgetSkeleton />;

  const total = data.reduce((s, d) => s + d.value, 0);
  if (total === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">속도 분포</h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">데이터 없음</p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">속도 분포</h3>
      <ResponsiveContainer width="100%" height={240}>
        <PieChart margin={{ top: 20, right: 20, bottom: 5, left: 20 }}>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={75}
            dataKey="value"
            label={({ name, value }) => `${name} ${value}`}
          >
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip formatter={(value: number, name: string) => [`${value}명`, name]} />
          <Legend wrapperStyle={{ fontSize: '12px' }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

// ===== Weekly Activity Widget =====
export function WeeklyActivityWidget() {
  const [data, setData] = useState<{ day: string; count: number }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    dashboardApi.getWeeklyActivity().then(setData).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <WidgetSkeleton />;

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">주간 검사 현황</h3>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: -15 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="day" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} allowDecimals={false} />
          <Tooltip formatter={(value: number) => [`${value}건`, '검사 수']} />
          <Bar dataKey="count" fill="#2563EB" radius={[4, 4, 0, 0]} barSize={30} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ===== Widget Skeleton =====
function WidgetSkeleton() {
  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-5 animate-pulse">
      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-24 mb-4"></div>
      <div className="space-y-3">
        <div className="h-10 bg-gray-100 dark:bg-gray-700/50 rounded"></div>
        <div className="h-10 bg-gray-100 dark:bg-gray-700/50 rounded"></div>
        <div className="h-10 bg-gray-100 dark:bg-gray-700/50 rounded"></div>
      </div>
    </div>
  );
}

// ===== Customize Panel =====
interface CustomizePanelProps {
  widgets: { id: string; label: string; visible: boolean; order: number }[];
  onToggle: (id: string) => void;
  onMove: (id: string, direction: 'up' | 'down') => void;
  onReset: () => void;
  onClose: () => void;
}

export function CustomizePanel({ widgets, onToggle, onMove, onReset, onClose }: CustomizePanelProps) {
  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-5 mb-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-semibold text-gray-900 dark:text-gray-100">대시보드 위젯 설정</h3>
        <div className="flex gap-2">
          <button
            onClick={onReset}
            className="text-xs px-3 py-1.5 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
          >
            초기화
          </button>
          <button
            onClick={onClose}
            className="text-xs px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            완료
          </button>
        </div>
      </div>
      <div className="space-y-2">
        {widgets.map((w, idx) => (
          <div
            key={w.id}
            className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
          >
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={w.visible}
                onChange={() => onToggle(w.id)}
                className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-800 dark:text-gray-200">{w.label}</span>
            </label>
            <div className="flex gap-1">
              <button
                onClick={() => onMove(w.id, 'up')}
                disabled={idx === 0}
                className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-30"
                aria-label={`${w.label} 위로 이동`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                </svg>
              </button>
              <button
                onClick={() => onMove(w.id, 'down')}
                disabled={idx === widgets.length - 1}
                className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-30"
                aria-label={`${w.label} 아래로 이동`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
