import type { WalkTest } from '../types';

interface NotesAnalysisSummaryProps {
  tests: WalkTest[];
}

type AnalysisResult = {
  status: 'improving' | 'worsening' | 'mixed' | 'neutral';
  label: string;
  description: string;
  positiveCount: number;
  negativeCount: number;
  totalNotesCount: number;
  recentTrend: string;
  keywords: { positive: string[]; negative: string[] };
};

// 긍정적 키워드 (호전)
const positiveKeywords = [
  '좋아졌', '좋아짐', '호전', '개선', '나아졌', '향상', '안정',
  '회복', '편해졌', '편해짐', '잘 걸', '잘걸', '통증 감소', '통증감소',
  '덜 아', '덜아', '나아', '좋아', '개선됨', '호전됨', '감소',
  '수월', '편안', '양호', '좋은', '더 좋', '빨라', '빨라졌',
  '정상', '안심', '괜찮'
];

// 부정적 키워드 (악화)
const negativeKeywords = [
  '악화', '나빠졌', '나빠짐', '안좋아', '안 좋아', '힘들어', '힘들',
  '불안정', '어려워', '통증 증가', '통증증가', '떨어졌', '떨어짐',
  '더 아', '아프', '힘듬', '악화됨', '증가', '느려', '느려졌',
  '불편', '위험', '걱정', '주의', '심해', '심해졌', '안좋', '나쁨'
];

// 단일 메모 분석
function analyzeNote(note: string): { positive: string[]; negative: string[] } {
  const text = note.toLowerCase();
  const foundPositive: string[] = [];
  const foundNegative: string[] = [];

  positiveKeywords.forEach(keyword => {
    if (text.includes(keyword) && !foundPositive.includes(keyword)) {
      foundPositive.push(keyword);
    }
  });

  negativeKeywords.forEach(keyword => {
    if (text.includes(keyword) && !foundNegative.includes(keyword)) {
      foundNegative.push(keyword);
    }
  });

  return { positive: foundPositive, negative: foundNegative };
}

// 모든 검사 메모 종합 분석
function analyzeAllNotes(tests: WalkTest[]): AnalysisResult {
  const testsWithNotes = tests.filter(t => t.notes && t.notes.trim().length > 0);

  if (testsWithNotes.length === 0) {
    return {
      status: 'neutral',
      label: '',
      description: '',
      positiveCount: 0,
      negativeCount: 0,
      totalNotesCount: 0,
      recentTrend: '',
      keywords: { positive: [], negative: [] }
    };
  }

  let totalPositive = 0;
  let totalNegative = 0;
  const allPositiveKeywords: string[] = [];
  const allNegativeKeywords: string[] = [];

  // 시간순 정렬 (오래된 것부터)
  const sortedTests = [...testsWithNotes].sort(
    (a, b) => new Date(a.test_date).getTime() - new Date(b.test_date).getTime()
  );

  // 각 메모 분석
  sortedTests.forEach(test => {
    if (test.notes) {
      const result = analyzeNote(test.notes);
      totalPositive += result.positive.length;
      totalNegative += result.negative.length;

      result.positive.forEach(k => {
        if (!allPositiveKeywords.includes(k)) allPositiveKeywords.push(k);
      });
      result.negative.forEach(k => {
        if (!allNegativeKeywords.includes(k)) allNegativeKeywords.push(k);
      });
    }
  });

  // 최근 3개 검사의 추세 분석
  const recentTests = sortedTests.slice(-3);
  let recentPositive = 0;
  let recentNegative = 0;

  recentTests.forEach(test => {
    if (test.notes) {
      const result = analyzeNote(test.notes);
      recentPositive += result.positive.length;
      recentNegative += result.negative.length;
    }
  });

  // 전체 추세 결정
  let status: AnalysisResult['status'];
  let label: string;
  let description: string;

  if (totalPositive > totalNegative * 1.5) {
    status = 'improving';
    label = '전반적 호전';
    description = '치료사 메모를 분석한 결과, 환자 상태가 전반적으로 호전되고 있는 것으로 보입니다.';
  } else if (totalNegative > totalPositive * 1.5) {
    status = 'worsening';
    label = '주의 관찰 필요';
    description = '치료사 메모를 분석한 결과, 환자 상태에 주의가 필요한 것으로 보입니다.';
  } else if (totalPositive > 0 || totalNegative > 0) {
    status = 'mixed';
    label = '변동 있음';
    description = '치료사 메모를 분석한 결과, 환자 상태에 변동이 있는 것으로 보입니다.';
  } else {
    status = 'neutral';
    label = '';
    description = '';
  }

  // 최근 추세
  let recentTrend = '';
  if (recentTests.length >= 2) {
    if (recentPositive > recentNegative) {
      recentTrend = '최근 검사에서 호전 경향이 나타나고 있습니다.';
    } else if (recentNegative > recentPositive) {
      recentTrend = '최근 검사에서 주의가 필요한 소견이 있습니다.';
    }
  }

  return {
    status,
    label,
    description,
    positiveCount: totalPositive,
    negativeCount: totalNegative,
    totalNotesCount: testsWithNotes.length,
    recentTrend,
    keywords: { positive: allPositiveKeywords, negative: allNegativeKeywords }
  };
}

export default function NotesAnalysisSummary({ tests }: NotesAnalysisSummaryProps) {
  const analysis = analyzeAllNotes(tests);

  // 메모가 없는 경우
  if (analysis.totalNotesCount === 0) {
    return (
      <div className="card border-2 border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800/50">
        <div className="flex items-start space-x-3">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 bg-gray-400 dark:bg-gray-600">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </div>
          <div className="flex-1">
            <h3 className="font-bold text-lg text-gray-700 dark:text-gray-300">
              치료사 메모 분석
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              작성된 메모가 없습니다.
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-300 mt-2">
              각 검사 기록에 메모를 작성하시면 환자 상태의 변화 추이를 자동으로 분석해 드립니다.
            </p>
            <div className="mt-3 p-2 bg-blue-50 dark:bg-blue-900/30 rounded-lg border border-blue-200 dark:border-blue-800">
              <p className="text-xs text-blue-600 dark:text-blue-400">
                💡 팁: 메모에 "호전", "좋아졌", "악화", "힘들어" 등의 표현을 사용하면 더 정확한 분석이 가능합니다.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // 메모는 있지만 분석할 키워드가 없는 경우
  if (analysis.status === 'neutral') {
    return (
      <div className="card border-2 border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800/50">
        <div className="flex items-start space-x-3">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 bg-gray-400 dark:bg-gray-600">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="flex-1">
            <h3 className="font-bold text-lg text-gray-700 dark:text-gray-300">
              치료사 메모 분석
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              메모 {analysis.totalNotesCount}개가 있지만 분석 가능한 키워드를 찾지 못했습니다.
            </p>
            <div className="mt-3 p-2 bg-blue-50 dark:bg-blue-900/30 rounded-lg border border-blue-200 dark:border-blue-800">
              <p className="text-xs text-blue-600 dark:text-blue-400">
                💡 팁: "호전됨", "좋아졌다", "악화", "힘들어함" 등 환자 상태를 나타내는 표현을 사용해 주세요.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`card border-2 ${
      analysis.status === 'improving'
        ? 'border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/30'
        : analysis.status === 'worsening'
        ? 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/30'
        : 'border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-900/30'
    }`}>
      <div className="flex items-start space-x-3">
        {/* 아이콘 */}
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 ${
          analysis.status === 'improving'
            ? 'bg-green-500'
            : analysis.status === 'worsening'
            ? 'bg-red-500'
            : 'bg-yellow-500'
        }`}>
          {analysis.status === 'improving' && (
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
          )}
          {analysis.status === 'worsening' && (
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
            </svg>
          )}
          {analysis.status === 'mixed' && (
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          )}
        </div>

        {/* 내용 */}
        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-1">
            <h3 className={`font-bold text-lg ${
              analysis.status === 'improving'
                ? 'text-green-700 dark:text-green-300'
                : analysis.status === 'worsening'
                ? 'text-red-700 dark:text-red-300'
                : 'text-yellow-700 dark:text-yellow-300'
            }`}>
              {analysis.label}
            </h3>
            <span className="text-xs text-gray-500 dark:text-gray-400 bg-white/50 dark:bg-gray-800/50 px-2 py-0.5 rounded-full">
              메모 {analysis.totalNotesCount}개 분석
            </span>
          </div>

          <p className={`text-sm ${
            analysis.status === 'improving'
              ? 'text-green-600 dark:text-green-400'
              : analysis.status === 'worsening'
              ? 'text-red-600 dark:text-red-400'
              : 'text-yellow-600 dark:text-yellow-400'
          }`}>
            {analysis.description}
          </p>

          {analysis.recentTrend && (
            <p className="text-sm text-gray-600 dark:text-gray-300 mt-2">
              {analysis.recentTrend}
            </p>
          )}

          {/* 키워드 요약 */}
          <div className="mt-3 flex flex-wrap gap-2">
            {analysis.keywords.positive.slice(0, 5).map((keyword, i) => (
              <span key={`pos-${i}`} className="text-xs px-2 py-1 bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300 rounded-full">
                {keyword}
              </span>
            ))}
            {analysis.keywords.negative.slice(0, 5).map((keyword, i) => (
              <span key={`neg-${i}`} className="text-xs px-2 py-1 bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300 rounded-full">
                {keyword}
              </span>
            ))}
          </div>

          {/* 통계 */}
          <div className="mt-3 pt-3 border-t border-gray-200/50 dark:border-gray-600/50 flex items-center space-x-4 text-xs">
            <div className="flex items-center space-x-1">
              <span className="w-2 h-2 bg-green-500 rounded-full"></span>
              <span className="text-gray-600 dark:text-gray-300">호전 키워드: {analysis.positiveCount}회</span>
            </div>
            <div className="flex items-center space-x-1">
              <span className="w-2 h-2 bg-red-500 rounded-full"></span>
              <span className="text-gray-600 dark:text-gray-300">주의 키워드: {analysis.negativeCount}회</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
