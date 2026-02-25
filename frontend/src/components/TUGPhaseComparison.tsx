import { useState, useCallback } from 'react';
import type { WalkTest, TUGAnalysisData, TUGPhaseComparisonResponse, PhaseFrames } from '../types';
import { testApi } from '../services/api';

interface TUGPhaseComparisonProps {
  patientId: string;
  tests: WalkTest[];
}

const phaseOrder = ['stand_up', 'walk_out', 'turn', 'walk_back', 'sit_down'] as const;

const phaseLabels: Record<string, string> = {
  stand_up: '일어서기',
  walk_out: '걷기(나감)',
  turn: '돌아서기',
  walk_back: '걷기(돌아옴)',
  sit_down: '앉기'
};

const phaseColors: Record<string, { bg: string; border: string; text: string; light: string }> = {
  stand_up: { bg: 'bg-purple-500', border: 'border-purple-500', text: 'text-purple-600', light: 'bg-purple-50 dark:bg-purple-900/20' },
  walk_out: { bg: 'bg-blue-500', border: 'border-blue-500', text: 'text-blue-600', light: 'bg-blue-50 dark:bg-blue-900/20' },
  turn: { bg: 'bg-yellow-500', border: 'border-yellow-500', text: 'text-yellow-600', light: 'bg-yellow-50 dark:bg-yellow-900/20' },
  walk_back: { bg: 'bg-green-500', border: 'border-green-500', text: 'text-green-600', light: 'bg-green-50 dark:bg-green-900/20' },
  sit_down: { bg: 'bg-pink-500', border: 'border-pink-500', text: 'text-pink-600', light: 'bg-pink-50 dark:bg-pink-900/20' }
};

export default function TUGPhaseComparison({ patientId, tests }: TUGPhaseComparisonProps) {
  const [comparison, setComparison] = useState<TUGPhaseComparisonResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  const fetchComparison = useCallback(async (testId?: string, prevId?: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await testApi.getTUGPhaseComparison(patientId, testId, prevId);
      setComparison(data);
      setExpanded(true);
    } catch {
      setError('비교 데이터를 불러오는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  }, [patientId]);

  const handleTestChange = (type: 'current' | 'previous', id: string) => {
    if (!comparison) return;
    if (type === 'current') {
      fetchComparison(id, comparison.previous_test?.id);
    } else {
      fetchComparison(comparison.current_test.id, id);
    }
  };

  // 테스트 ID로 WalkTest 찾아서 phase_frames 가져오기
  const getPhaseFrames = (testId: string): PhaseFrames | undefined => {
    const test = tests.find(t => t.id === testId);
    if (!test?.analysis_data) return undefined;
    return (test.analysis_data as TUGAnalysisData).phase_frames;
  };

  const getPhaseClipAvailable = (testId: string, phase: string): boolean => {
    const test = tests.find(t => t.id === testId);
    if (!test?.analysis_data) return false;
    const clips = (test.analysis_data as TUGAnalysisData).phase_clips;
    return !!(clips?.[phase as keyof typeof clips]?.clip_filename);
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString('ko-KR', {
        year: 'numeric', month: 'short', day: 'numeric'
      });
    } catch {
      return dateStr;
    }
  };

  // 아직 로드하지 않은 상태: 버튼 표시
  if (!expanded && !comparison) {
    return (
      <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm">
        <button
          onClick={() => fetchComparison()}
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 rounded-xl font-semibold text-sm hover:bg-indigo-100 dark:hover:bg-indigo-900/40 transition-colors disabled:opacity-50"
        >
          {loading ? (
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-500" />
          ) : (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          )}
          TUG 단계별 비교
        </button>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm">
        <p className="text-red-500 text-sm text-center">{error}</p>
        <button
          onClick={() => fetchComparison()}
          className="mt-2 w-full text-sm text-blue-500 hover:underline"
        >
          다시 시도
        </button>
      </div>
    );
  }

  if (loading || !comparison) {
    return (
      <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm">
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-500" />
        </div>
      </div>
    );
  }

  const { current_test, previous_test, phase_deltas, available_tug_tests } = comparison;
  const currentFrames = getPhaseFrames(current_test.id);
  const previousFrames = previous_test ? getPhaseFrames(previous_test.id) : undefined;

  return (
    <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
          <svg className="w-5 h-5 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          TUG 단계별 비교
        </h3>
        <button
          onClick={() => { setExpanded(false); setComparison(null); }}
          className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* 테스트 선택 드롭다운 */}
      {available_tug_tests.length > 2 && (
        <div className="grid grid-cols-2 gap-2 mb-4">
          <div>
            <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">현재 검사</label>
            <select
              value={current_test.id}
              onChange={(e) => handleTestChange('current', e.target.value)}
              className="w-full text-xs p-1.5 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            >
              {available_tug_tests.map(t => (
                <option key={t.id} value={t.id} disabled={t.id === previous_test?.id}>
                  {formatDate(t.test_date)} ({t.total_time.toFixed(1)}s)
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">이전 검사</label>
            <select
              value={previous_test?.id || ''}
              onChange={(e) => handleTestChange('previous', e.target.value)}
              className="w-full text-xs p-1.5 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            >
              {available_tug_tests.map(t => (
                <option key={t.id} value={t.id} disabled={t.id === current_test.id}>
                  {formatDate(t.test_date)} ({t.total_time.toFixed(1)}s)
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      {/* 총 시간 비교 */}
      <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-xl mb-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-600 dark:text-gray-400">총 시간</span>
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-gray-900 dark:text-gray-100">
              {current_test.total_time.toFixed(2)}s
            </span>
            {comparison.total_time_diff != null && (
              <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-semibold ${
                comparison.total_time_diff < 0
                  ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                  : comparison.total_time_diff > 0
                  ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                  : 'bg-gray-100 text-gray-600 dark:bg-gray-600 dark:text-gray-300'
              }`}>
                {comparison.total_time_diff < 0 ? '↓' : comparison.total_time_diff > 0 ? '↑' : '='}{' '}
                {Math.abs(comparison.total_time_diff).toFixed(2)}s
                {comparison.total_time_pct_change != null && (
                  <span className="ml-0.5">({Math.abs(comparison.total_time_pct_change).toFixed(0)}%)</span>
                )}
              </span>
            )}
          </div>
        </div>
        {previous_test && (
          <p className="text-xs text-gray-500 dark:text-gray-400 text-right mt-1">
            이전: {previous_test.total_time.toFixed(2)}s ({formatDate(previous_test.test_date)})
          </p>
        )}
      </div>

      {/* 단계별 시간 비교 테이블 */}
      <div className="space-y-1.5 mb-4">
        <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">단계별 소요시간</p>
        {phaseOrder.map((phase) => {
          const colors = phaseColors[phase];
          const curDur = current_test.phases?.[phase]?.duration;
          const prevDur = previous_test?.phases?.[phase]?.duration;
          const delta = phase_deltas?.[phase];

          return (
            <div key={phase} className="flex items-center gap-2 py-1.5 px-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors">
              <div className={`w-2.5 h-2.5 rounded-full ${colors.bg} flex-shrink-0`} />
              <span className="text-xs font-medium text-gray-700 dark:text-gray-300 w-20 flex-shrink-0">
                {phaseLabels[phase]}
              </span>
              <span className="text-xs font-bold text-gray-900 dark:text-gray-100 w-12 text-right">
                {curDur != null ? `${curDur.toFixed(2)}s` : '-'}
              </span>
              {previous_test && (
                <>
                  <span className="text-xs text-gray-400 w-12 text-right">
                    {prevDur != null ? `${prevDur.toFixed(2)}s` : '-'}
                  </span>
                  {delta?.duration_diff != null && (
                    <span className={`text-xs font-semibold w-16 text-right ${
                      delta.duration_diff < 0
                        ? 'text-green-600 dark:text-green-400'
                        : delta.duration_diff > 0
                        ? 'text-red-600 dark:text-red-400'
                        : 'text-gray-500'
                    }`}>
                      {delta.duration_diff < 0 ? '↓' : delta.duration_diff > 0 ? '↑' : '='}
                      {Math.abs(delta.duration_diff).toFixed(2)}s
                    </span>
                  )}
                </>
              )}
            </div>
          );
        })}
      </div>

      {/* 나란히 단계 캡처 비교 */}
      {(currentFrames || previousFrames) && (
        <div className="space-y-3">
          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">단계별 전환 캡처 비교</p>

          {/* 레이블 헤더 */}
          <div className="grid grid-cols-2 gap-2">
            <p className="text-xs text-center text-indigo-600 dark:text-indigo-400 font-semibold">
              현재 ({formatDate(current_test.test_date)})
            </p>
            {previous_test && (
              <p className="text-xs text-center text-gray-500 dark:text-gray-400 font-semibold">
                이전 ({formatDate(previous_test.test_date)})
              </p>
            )}
          </div>

          {phaseOrder.map((phase, index) => {
            const colors = phaseColors[phase];
            const curFrame = currentFrames?.[phase];
            const prevFrame = previousFrames?.[phase];
            const curHasClip = getPhaseClipAvailable(current_test.id, phase);
            const prevHasClip = previous_test ? getPhaseClipAvailable(previous_test.id, phase) : false;
            const delta = phase_deltas?.[phase];

            if (!curFrame && !prevFrame) return null;

            return (
              <div key={phase} className={`rounded-xl overflow-hidden border ${colors.border}`}>
                {/* 단계 헤더 */}
                <div className={`px-3 py-1.5 ${colors.light} flex items-center justify-between`}>
                  <div className="flex items-center gap-2">
                    <div className={`w-5 h-5 ${colors.bg} rounded-full flex items-center justify-center`}>
                      <span className="text-white text-xs font-bold">{index + 1}</span>
                    </div>
                    <span className={`text-sm font-semibold ${colors.text}`}>{phaseLabels[phase]}</span>
                  </div>
                  {delta?.duration_diff != null && (
                    <span className={`text-xs font-semibold ${
                      delta.duration_diff < 0
                        ? 'text-green-600 dark:text-green-400'
                        : delta.duration_diff > 0
                        ? 'text-red-600 dark:text-red-400'
                        : 'text-gray-500'
                    }`}>
                      {delta.duration_diff < 0 ? '↓' : delta.duration_diff > 0 ? '↑' : '='}
                      {Math.abs(delta.duration_diff).toFixed(2)}s
                      {delta.pct_change != null && ` (${Math.abs(delta.pct_change).toFixed(0)}%)`}
                    </span>
                  )}
                </div>

                {/* 나란히 이미지 */}
                <div className="grid grid-cols-2 gap-px bg-gray-200 dark:bg-gray-600">
                  {/* 현재 */}
                  <div className="bg-white dark:bg-gray-800 relative">
                    {curHasClip ? (
                      <video
                        src={testApi.getPhaseClipUrl(current_test.id, phase)}
                        className="w-full aspect-video object-cover"
                        autoPlay loop muted playsInline
                      />
                    ) : curFrame ? (
                      <img
                        src={`data:image/jpeg;base64,${curFrame.frame}`}
                        alt={curFrame.label}
                        className="w-full aspect-video object-cover"
                      />
                    ) : (
                      <div className="w-full aspect-video bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
                        <span className="text-xs text-gray-400">없음</span>
                      </div>
                    )}
                    {curFrame && (
                      <div className="absolute bottom-0 left-0 right-0 bg-black/50 px-1.5 py-0.5">
                        <span className="text-white text-xs">{curFrame.duration.toFixed(2)}s</span>
                      </div>
                    )}
                  </div>

                  {/* 이전 */}
                  <div className="bg-white dark:bg-gray-800 relative">
                    {prevHasClip && previous_test ? (
                      <video
                        src={testApi.getPhaseClipUrl(previous_test.id, phase)}
                        className="w-full aspect-video object-cover"
                        autoPlay loop muted playsInline
                      />
                    ) : prevFrame ? (
                      <img
                        src={`data:image/jpeg;base64,${prevFrame.frame}`}
                        alt={prevFrame.label}
                        className="w-full aspect-video object-cover"
                      />
                    ) : (
                      <div className="w-full aspect-video bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
                        <span className="text-xs text-gray-400">없음</span>
                      </div>
                    )}
                    {prevFrame && (
                      <div className="absolute bottom-0 left-0 right-0 bg-black/50 px-1.5 py-0.5">
                        <span className="text-white text-xs">{prevFrame.duration.toFixed(2)}s</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 기립/착석 세부 비교 */}
      {previous_test && (current_test.stand_up_metrics || current_test.sit_down_metrics) && (
        <div className="mt-4 space-y-2">
          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">기립/착석 세부</p>

          {current_test.stand_up_metrics && previous_test.stand_up_metrics && (
            <div className="p-2.5 bg-purple-50 dark:bg-purple-900/10 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-purple-600 dark:text-purple-400">일어서기</span>
                <div className="flex items-center gap-2 text-xs">
                  <span className="font-bold text-gray-900 dark:text-gray-100">
                    {current_test.stand_up_metrics.duration.toFixed(2)}s
                  </span>
                  <span className="text-gray-400">vs</span>
                  <span className="text-gray-500">{previous_test.stand_up_metrics.duration.toFixed(2)}s</span>
                  {(() => {
                    const diff = current_test.stand_up_metrics!.duration - previous_test.stand_up_metrics!.duration;
                    return diff !== 0 ? (
                      <span className={diff < 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}>
                        {diff < 0 ? '↓' : '↑'}{Math.abs(diff).toFixed(2)}s
                      </span>
                    ) : null;
                  })()}
                </div>
              </div>
              <div className="flex gap-2 mt-1">
                <span className="text-xs text-gray-500">{current_test.stand_up_metrics.assessment}</span>
                {current_test.stand_up_metrics.used_hand_support && (
                  <span className="text-xs text-orange-500">손 지지 사용</span>
                )}
              </div>
            </div>
          )}

          {current_test.sit_down_metrics && previous_test.sit_down_metrics && (
            <div className="p-2.5 bg-pink-50 dark:bg-pink-900/10 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-pink-600 dark:text-pink-400">앉기</span>
                <div className="flex items-center gap-2 text-xs">
                  <span className="font-bold text-gray-900 dark:text-gray-100">
                    {current_test.sit_down_metrics.duration.toFixed(2)}s
                  </span>
                  <span className="text-gray-400">vs</span>
                  <span className="text-gray-500">{previous_test.sit_down_metrics.duration.toFixed(2)}s</span>
                  {(() => {
                    const diff = current_test.sit_down_metrics!.duration - previous_test.sit_down_metrics!.duration;
                    return diff !== 0 ? (
                      <span className={diff < 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}>
                        {diff < 0 ? '↓' : '↑'}{Math.abs(diff).toFixed(2)}s
                      </span>
                    ) : null;
                  })()}
                </div>
              </div>
              <div className="flex gap-2 mt-1">
                <span className="text-xs text-gray-500">{current_test.sit_down_metrics.assessment}</span>
                {current_test.sit_down_metrics.used_hand_support && (
                  <span className="text-xs text-orange-500">손 지지 사용</span>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 반응 시간 / 첫 걸음 비교 */}
      {previous_test && (current_test.reaction_time != null || current_test.first_step_time != null) && (
        <div className="mt-3 grid grid-cols-2 gap-2">
          {current_test.reaction_time != null && previous_test.reaction_time != null && (
            <div className="p-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-0.5">반응 시간</p>
              <p className="text-sm font-bold text-gray-900 dark:text-gray-100">
                {current_test.reaction_time.toFixed(3)}s
              </p>
              {(() => {
                const diff = current_test.reaction_time! - previous_test.reaction_time!;
                return (
                  <p className={`text-xs ${diff < 0 ? 'text-green-600 dark:text-green-400' : diff > 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-500'}`}>
                    이전: {previous_test.reaction_time!.toFixed(3)}s
                    {diff !== 0 && ` (${diff < 0 ? '↓' : '↑'}${Math.abs(diff).toFixed(3)}s)`}
                  </p>
                );
              })()}
            </div>
          )}
          {current_test.first_step_time != null && previous_test.first_step_time != null && (
            <div className="p-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-0.5">첫 걸음</p>
              <p className="text-sm font-bold text-gray-900 dark:text-gray-100">
                {current_test.first_step_time.toFixed(3)}s
              </p>
              {(() => {
                const diff = current_test.first_step_time! - previous_test.first_step_time!;
                return (
                  <p className={`text-xs ${diff < 0 ? 'text-green-600 dark:text-green-400' : diff > 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-500'}`}>
                    이전: {previous_test.first_step_time!.toFixed(3)}s
                    {diff !== 0 && ` (${diff < 0 ? '↓' : '↑'}${Math.abs(diff).toFixed(3)}s)`}
                  </p>
                );
              })()}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
