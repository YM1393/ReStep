import { useState } from 'react';
import { testApi } from '../services/api';

interface AIReportProps {
  testId: string;
}

interface ReportSection {
  title: string;
  content: React.ReactNode;
}

export default function AIReport({ testId }: AIReportProps) {
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const loadReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await testApi.getAIReport(testId);
      setReport(data);
    } catch {
      setError('AI 리포트 생성에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const toggleSection = (key: string) => {
    setCollapsed(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const getReportText = (): string => {
    if (!report) return '';
    const ps = report.patient_summary;
    const tr = report.test_results;
    const risk = report.risk_assessment;
    const lines: string[] = [];

    lines.push(`=== AI 임상 리포트 ===`);
    lines.push(`환자: ${ps.name} (${ps.patient_number}) | ${ps.gender} ${ps.age}세 | ${ps.height_cm}cm`);
    if (ps.diagnosis) lines.push(`진단명: ${ps.diagnosis}`);
    lines.push(`검사일: ${ps.test_date}`);
    lines.push('');
    lines.push(`[검사 결과] ${tr.test_type_label}`);
    lines.push(`보행 속도: ${tr.walk_speed_mps} m/s | 보행 시간: ${tr.walk_time_seconds}초`);
    lines.push(`위험도: ${risk.label} (${risk.score}/100)`);
    risk.interpretations?.forEach((i: string) => lines.push(`  - ${i}`));
    lines.push('');

    if (report.gait_analysis?.clinical_findings?.length > 0) {
      lines.push('[보행 분석]');
      report.gait_analysis.clinical_findings.forEach((f: any) => {
        lines.push(`  ${f.variable}: ${f.value} - ${f.assessment}`);
      });
      lines.push('');
    }

    if (report.progress?.comparison?.summary) {
      lines.push('[경과]');
      lines.push(report.progress.comparison.summary);
      lines.push('');
    }

    if (report.recommendations?.length > 0) {
      lines.push('[재활 추천]');
      report.recommendations.forEach((r: any) => {
        lines.push(`  [${r.priority === 'high' ? '높음' : r.priority === 'medium' ? '보통' : '낮음'}] ${r.title}`);
        lines.push(`    ${r.description}`);
      });
    }

    return lines.join('\n');
  };

  const handleCopy = async () => {
    const text = getReportText();
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!report && !loading) {
    return (
      <button
        onClick={loadReport}
        className="w-full px-4 py-3 text-center bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400 rounded-lg font-semibold text-sm hover:bg-purple-100 dark:hover:bg-purple-900/40 transition-colors flex items-center justify-center gap-2"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
        AI 리포트 생성
      </button>
    );
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center py-6" role="status">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-purple-500"></div>
        <span className="ml-2 text-sm text-gray-500 dark:text-gray-400">AI 리포트 생성 중...</span>
        <span className="sr-only">AI 리포트 생성 중</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-4" role="alert">
        <p className="text-sm text-red-500 mb-2">{error}</p>
        <button onClick={loadReport} className="text-sm text-blue-600 dark:text-blue-400 hover:underline">다시 시도</button>
      </div>
    );
  }

  if (!report) return null;

  const ps = report.patient_summary;
  const tr = report.test_results;
  const ga = report.gait_analysis;
  const prog = report.progress;
  const risk = report.risk_assessment;
  const recs = report.recommendations || [];

  const sections: ReportSection[] = [
    {
      title: '환자 정보',
      content: (
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div><span className="text-gray-500 dark:text-gray-400">이름:</span> <span className="font-medium text-gray-900 dark:text-gray-100">{ps.name}</span></div>
          <div><span className="text-gray-500 dark:text-gray-400">번호:</span> <span className="font-medium text-gray-900 dark:text-gray-100">#{ps.patient_number}</span></div>
          <div><span className="text-gray-500 dark:text-gray-400">성별/나이:</span> <span className="font-medium text-gray-900 dark:text-gray-100">{ps.gender} {ps.age}세</span></div>
          <div><span className="text-gray-500 dark:text-gray-400">키:</span> <span className="font-medium text-gray-900 dark:text-gray-100">{ps.height_cm}cm</span></div>
          {ps.diagnosis && <div className="col-span-2"><span className="text-gray-500 dark:text-gray-400">진단명:</span> <span className="font-medium text-gray-900 dark:text-gray-100">{ps.diagnosis}</span></div>}
        </div>
      ),
    },
    {
      title: '검사 결과',
      content: (
        <div>
          <div className="flex items-center gap-3 mb-3">
            <span className="px-2.5 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded-full text-xs font-medium">{tr.test_type_label}</span>
            <span className="text-xs text-gray-500 dark:text-gray-400">{ps.test_date}</span>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
              <div className="text-xs text-gray-500 dark:text-gray-400">보행 속도</div>
              <div className="text-xl font-bold text-blue-600 dark:text-blue-400">{tr.walk_speed_mps} <span className="text-sm font-normal">m/s</span></div>
            </div>
            <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
              <div className="text-xs text-gray-500 dark:text-gray-400">보행 시간</div>
              <div className="text-xl font-bold text-blue-600 dark:text-blue-400">{tr.walk_time_seconds} <span className="text-sm font-normal">초</span></div>
            </div>
          </div>
        </div>
      ),
    },
    {
      title: '보행 분석',
      content: (
        <div className="space-y-3">
          {ga.gait_pattern && (
            <div className="text-sm">
              <div className="text-gray-500 dark:text-gray-400 mb-1">자세 분석</div>
              <div className="text-gray-800 dark:text-gray-200">어깨: {ga.gait_pattern.shoulder_tilt}</div>
              <div className="text-gray-800 dark:text-gray-200">골반: {ga.gait_pattern.hip_tilt}</div>
              <div className="mt-1 text-gray-700 dark:text-gray-300 font-medium">{ga.gait_pattern.assessment}</div>
            </div>
          )}
          {ga.clinical_findings?.length > 0 && (
            <div>
              <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">임상 소견</div>
              {ga.clinical_findings.map((f: any, i: number) => (
                <div key={i} className="flex justify-between items-start p-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg mb-1.5 text-sm">
                  <div>
                    <span className="font-medium text-gray-800 dark:text-gray-200">{f.variable}</span>
                    <span className="text-gray-500 dark:text-gray-400 ml-2">{f.value}</span>
                  </div>
                  <span className="text-xs text-gray-600 dark:text-gray-400 text-right ml-2 max-w-[50%]">{f.assessment}</span>
                </div>
              ))}
            </div>
          )}
          {ga.asymmetry_warnings?.length > 0 && (
            <div>
              <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">비대칭 경고</div>
              {ga.asymmetry_warnings.map((w: any, i: number) => (
                <div key={i} className="flex items-start gap-2 p-2 bg-orange-50 dark:bg-orange-900/10 rounded-lg mb-1.5 text-sm">
                  <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                    w.severity === 'severe' ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
                    : w.severity === 'moderate' ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400'
                    : 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400'
                  }`}>{w.severity === 'severe' ? '심함' : w.severity === 'moderate' ? '중등' : '경미'}</span>
                  <div>
                    <span className="font-medium text-gray-800 dark:text-gray-200">{w.type}</span>
                    <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5">{w.description}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
          {ga.confidence && (
            <div className="text-xs text-gray-500 dark:text-gray-400">
              분석 신뢰도: <span className="font-medium">{ga.confidence.label} ({ga.confidence.score}점)</span>
            </div>
          )}
        </div>
      ),
    },
    {
      title: '위험도 평가',
      content: (
        <div>
          <div className="flex items-center gap-3 mb-3">
            <div className={`px-3 py-1.5 rounded-full text-sm font-semibold ${
              risk.level === 'normal' ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
              : risk.level === 'mild' ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400'
              : risk.level === 'moderate' ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400'
              : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
            }`}>{risk.label}</div>
            <span className="text-lg font-bold text-gray-900 dark:text-gray-100">{risk.score}/100</span>
          </div>
          <ul className="space-y-1">
            {risk.interpretations?.map((interp: string, i: number) => (
              <li key={i} className="text-sm text-gray-700 dark:text-gray-300 flex items-start gap-2">
                <span className="text-gray-400 mt-0.5">-</span>
                {interp}
              </li>
            ))}
          </ul>
        </div>
      ),
    },
  ];

  // Add progress section if data exists
  if (prog?.comparison || prog?.trend) {
    sections.splice(3, 0, {
      title: '경과',
      content: (
        <div className="space-y-3">
          {prog.comparison && (
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  prog.comparison.is_improved
                    ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                    : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
                }`}>{prog.comparison.is_improved ? '개선' : '주의'}</span>
                <span className="text-sm text-gray-600 dark:text-gray-400">{prog.comparison.improvement_pct > 0 ? '+' : ''}{prog.comparison.improvement_pct}%</span>
              </div>
            </div>
          )}
          {prog.trend && (
            <div className="text-sm">
              <span className="text-gray-500 dark:text-gray-400">추세:</span>
              <span className="font-medium text-gray-800 dark:text-gray-200 ml-1">{prog.trend.direction_label}</span>
              {prog.trend.goal_eta && (
                <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">목표 도달 예상: {prog.trend.goal_eta}</div>
              )}
            </div>
          )}
          {prog.goal_status && (
            <div className="text-sm">
              <span className="text-gray-500 dark:text-gray-400">목표 달성률:</span>
              <span className="font-medium text-gray-800 dark:text-gray-200 ml-1">{prog.goal_status.achievement_pct}%</span>
              <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2 mt-1">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all"
                  style={{ width: `${Math.min(100, prog.goal_status.achievement_pct)}%` }}
                />
              </div>
            </div>
          )}
        </div>
      ),
    });
  }

  // Add recommendations section
  if (recs.length > 0) {
    sections.push({
      title: '재활 추천',
      content: (
        <div className="space-y-2">
          {recs.slice(0, 5).map((r: any, i: number) => (
            <div key={i} className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                  r.priority === 'high' ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
                  : r.priority === 'medium' ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400'
                  : 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                }`}>{r.priority === 'high' ? '높음' : r.priority === 'medium' ? '보통' : '낮음'}</span>
                <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{r.title}</span>
              </div>
              <p className="text-xs text-gray-600 dark:text-gray-400">{r.description}</p>
              {r.frequency && <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">{r.frequency}</p>}
            </div>
          ))}
        </div>
      ),
    });
  }

  return (
    <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm">
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
          <svg className="w-5 h-5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          AI 임상 리포트
        </h3>
        <div className="flex gap-2">
          <button
            onClick={handleCopy}
            className="text-xs px-3 py-1.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 flex items-center gap-1"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
            </svg>
            {copied ? '복사됨!' : '복사'}
          </button>
          <button
            onClick={() => window.print()}
            className="text-xs px-3 py-1.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 flex items-center gap-1"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
            </svg>
            인쇄
          </button>
        </div>
      </div>

      {/* Sections */}
      <div className="space-y-3">
        {sections.map((section, idx) => {
          const key = `section-${idx}`;
          const isCollapsed = collapsed[key];
          return (
            <div key={key} className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
              <button
                onClick={() => toggleSection(key)}
                className="w-full flex justify-between items-center px-4 py-3 bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">{section.title}</span>
                <svg
                  className={`w-4 h-4 text-gray-400 transition-transform ${isCollapsed ? '' : 'rotate-180'}`}
                  fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {!isCollapsed && (
                <div className="px-4 py-3">
                  {section.content}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-3 text-xs text-gray-400 dark:text-gray-500 text-right">
        생성일: {new Date(report.generated_at).toLocaleString('ko-KR')}
      </div>
    </div>
  );
}
