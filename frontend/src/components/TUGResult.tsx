import { useState } from 'react';
import type { TUGAnalysisData, TUGAssessment, PhaseFrames, PhaseClips } from '../types';
import { testApi } from '../services/api';
import TUGWeightShift from './TUGWeightShift';

interface TUGResultProps {
  data: TUGAnalysisData;
  testId?: string;
}

// 기립/착석 속도에 따른 색상
const getSpeedColor = (assessment: string): string => {
  if (assessment.includes('빠름')) return 'text-orange-500';
  if (assessment.includes('보통')) return 'text-green-500';
  if (assessment.includes('느림')) return 'text-blue-500';
  return 'text-gray-500';
};

const assessmentLabels: Record<TUGAssessment, string> = {
  normal: '정상',
  good: '양호',
  caution: '주의',
  risk: '낙상위험'
};

const assessmentColors: Record<TUGAssessment, { bg: string; text: string; border: string }> = {
  normal: {
    bg: 'bg-green-100 dark:bg-green-900/30',
    text: 'text-green-700 dark:text-green-300',
    border: 'border-green-200 dark:border-green-800'
  },
  good: {
    bg: 'bg-blue-100 dark:bg-blue-900/30',
    text: 'text-blue-700 dark:text-blue-300',
    border: 'border-blue-200 dark:border-blue-800'
  },
  caution: {
    bg: 'bg-yellow-100 dark:bg-yellow-900/30',
    text: 'text-yellow-700 dark:text-yellow-300',
    border: 'border-yellow-200 dark:border-yellow-800'
  },
  risk: {
    bg: 'bg-red-100 dark:bg-red-900/30',
    text: 'text-red-700 dark:text-red-300',
    border: 'border-red-200 dark:border-red-800'
  }
};

const phaseLabels: Record<string, string> = {
  stand_up: '일어서기',
  walk_out: '걷기 (나감)',
  turn: '돌아서기',
  walk_back: '걷기 (돌아옴)',
  sit_down: '앉기'
};

const phaseColors: Record<string, { bg: string; border: string; text: string; light: string }> = {
  stand_up: { bg: 'bg-purple-500', border: 'border-purple-500', text: 'text-purple-600', light: 'bg-purple-50 dark:bg-purple-900/20' },
  walk_out: { bg: 'bg-blue-500', border: 'border-blue-500', text: 'text-blue-600', light: 'bg-blue-50 dark:bg-blue-900/20' },
  turn: { bg: 'bg-yellow-500', border: 'border-yellow-500', text: 'text-yellow-600', light: 'bg-yellow-50 dark:bg-yellow-900/20' },
  walk_back: { bg: 'bg-green-500', border: 'border-green-500', text: 'text-green-600', light: 'bg-green-50 dark:bg-green-900/20' },
  sit_down: { bg: 'bg-pink-500', border: 'border-pink-500', text: 'text-pink-600', light: 'bg-pink-50 dark:bg-pink-900/20' }
};

const phaseOrder = ['stand_up', 'walk_out', 'turn', 'walk_back', 'sit_down'] as const;

export default function TUGResult({ data, testId }: TUGResultProps) {
  const assessment = data.assessment;
  const colors = assessmentColors[assessment];
  const [hoveredPhase, setHoveredPhase] = useState<string | null>(null);
  const [selectedPhase, setSelectedPhase] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);

  const totalPhaseTime = Object.values(data.phases).reduce(
    (sum, phase) => sum + phase.duration, 0
  );

  const hasFrames = data.phase_frames && Object.keys(data.phase_frames).length > 0;

  const handlePhaseClick = (key: string) => {
    if (!hasFrames) return;
    setSelectedPhase(selectedPhase === key ? null : key);
  };

  const openModal = (phase: string) => {
    setSelectedPhase(phase);
    setShowModal(true);
  };

  const closeModal = () => setShowModal(false);

  const selectedFrame = selectedPhase && data.phase_frames
    ? data.phase_frames[selectedPhase as keyof PhaseFrames]
    : null;

  return (
    <div className={`card border-2 ${colors.border} ${colors.bg}`}>
      <h3 className="font-semibold text-gray-800 dark:text-gray-100 mb-4 flex items-center">
        <svg className="w-5 h-5 mr-2 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        TUG 검사 결과
      </h3>

      {/* 총 시간 및 평가 */}
      <div className="flex items-center justify-between mb-6">
        <div className="text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">총 소요 시간</p>
          <p className="text-4xl font-bold text-gray-800 dark:text-gray-100">
            {data.total_time_seconds.toFixed(1)}
            <span className="text-lg text-gray-500 dark:text-gray-400 ml-1">초</span>
          </p>
        </div>
        <div className={`px-6 py-3 rounded-xl ${colors.bg} ${colors.border} border`}>
          <p className={`text-2xl font-bold ${colors.text}`}>
            {assessmentLabels[assessment]}
          </p>
        </div>
      </div>

      {/* 평가 기준 안내 */}
      <div className="mb-6 p-3 bg-gray-50 dark:bg-gray-800 rounded-xl">
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-2 font-medium">TUG 평가 기준</p>
        <div className="flex items-center justify-between text-xs">
          <span className="text-green-600 dark:text-green-400">&lt;10초: 정상</span>
          <span className="text-blue-600 dark:text-blue-400">10-20초: 양호</span>
          <span className="text-yellow-600 dark:text-yellow-400">20-30초: 주의</span>
          <span className="text-red-600 dark:text-red-400">&gt;30초: 위험</span>
        </div>
      </div>

      {/* 단계별 소요 시간 - 인터랙티브 바 */}
      <div className="mb-4">
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">단계별 소요 시간</p>
        {hasFrames && (
          <p className="text-xs text-gray-400 dark:text-gray-400 mb-2">클릭하여 캡처 보기</p>
        )}

        {/* 시간 바 */}
        <div className="h-10 rounded-lg overflow-visible flex mb-2 relative">
          {Object.entries(data.phases).map(([key, phase]) => {
            const percentage = (phase.duration / totalPhaseTime) * 100;
            const isHovered = hoveredPhase === key;
            const isSelected = selectedPhase === key;
            const pc = phaseColors[key];

            return (
              <div
                key={key}
                className={`${pc.bg} flex items-center justify-center transition-all duration-200 ${
                  hasFrames ? 'cursor-pointer' : ''
                } ${isHovered ? 'z-20' : isSelected ? 'z-10' : 'z-0'}`}
                style={{
                  width: `${percentage}%`,
                  transform: isHovered ? 'scaleY(1.25)' : isSelected ? 'scaleY(1.12)' : 'scaleY(1)',
                  transformOrigin: 'center',
                  boxShadow: isHovered
                    ? '0 4px 12px rgba(0,0,0,0.3)'
                    : isSelected
                    ? '0 2px 8px rgba(0,0,0,0.2)'
                    : 'none',
                  filter: isHovered ? 'brightness(1.2)' : isSelected ? 'brightness(1.1)' : 'brightness(1)',
                  borderRadius: isHovered || isSelected ? '4px' : '0',
                  opacity: isHovered ? 1 : isSelected ? 1 : 0.85,
                }}
                title={`${phaseLabels[key]}: ${phase.duration.toFixed(1)}초${hasFrames ? ' (클릭하여 캡처 보기)' : ''}`}
                onMouseEnter={() => setHoveredPhase(key)}
                onMouseLeave={() => setHoveredPhase(null)}
                onClick={() => handlePhaseClick(key)}
              >
                {percentage > 15 && (
                  <span className={`text-white text-xs font-medium truncate px-1 transition-all duration-200 ${
                    isHovered ? 'font-bold' : ''
                  }`}>
                    {isHovered ? phaseLabels[key] : `${phase.duration.toFixed(1)}s`}
                  </span>
                )}
              </div>
            );
          })}
        </div>

        {/* 범례 */}
        <div className="flex flex-wrap gap-3 mt-3">
          {Object.entries(data.phases).map(([key, phase]) => {
            const isSelected = selectedPhase === key;
            return (
              <div
                key={key}
                className={`flex items-center ${hasFrames ? 'cursor-pointer' : ''} ${
                  isSelected ? 'font-semibold' : ''
                }`}
                onClick={() => handlePhaseClick(key)}
              >
                <div className={`w-3 h-3 rounded-full ${phaseColors[key].bg} mr-1.5 ${
                  isSelected ? 'ring-2 ring-offset-1 ring-gray-400' : ''
                }`}></div>
                <span className={`text-xs ${isSelected ? 'text-gray-800 dark:text-gray-200' : 'text-gray-600 dark:text-gray-400'}`}>
                  {phaseLabels[key]}: {phase.duration.toFixed(1)}초
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* 선택된 단계의 캡처 프레임 (인라인) */}
      {selectedPhase && selectedFrame && (
        <div className={`mb-4 p-3 rounded-xl border-2 ${phaseColors[selectedPhase].border} ${phaseColors[selectedPhase].light}`}>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center">
              <div className={`w-6 h-6 ${phaseColors[selectedPhase].bg} rounded-full flex items-center justify-center mr-2`}>
                <span className="text-white text-xs font-bold">{phaseOrder.indexOf(selectedPhase as typeof phaseOrder[number]) + 1}</span>
              </div>
              <span className={`font-bold text-sm ${phaseColors[selectedPhase].text}`}>
                {selectedFrame.label}
              </span>
              <span className="text-xs text-gray-500 dark:text-gray-400 ml-2">
                {data.phases[selectedPhase as keyof typeof data.phases].duration.toFixed(2)}초
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => openModal(selectedPhase)}
                className="text-xs px-2.5 py-1 bg-white dark:bg-gray-700 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors border border-gray-200 dark:border-gray-600"
              >
                상세
              </button>
              <button
                onClick={() => setSelectedPhase(null)}
                className="p-0.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          <div className="relative rounded-lg overflow-hidden bg-black cursor-pointer" onClick={() => openModal(selectedPhase)}>
            {data.phase_clips?.[selectedPhase as keyof PhaseClips]?.clip_filename && testId ? (
              <video
                src={testApi.getPhaseClipUrl(testId, selectedPhase)}
                className="w-full h-auto max-h-52 object-contain"
                autoPlay loop muted playsInline
              />
            ) : (
              <img
                src={`data:image/jpeg;base64,${selectedFrame.frame}`}
                alt={selectedFrame.label}
                className="w-full h-auto max-h-52 object-contain"
              />
            )}
          </div>

          {selectedFrame.criteria && (
            <p className="mt-2 text-xs text-gray-600 dark:text-gray-300">
              <span className="font-medium">감지 기준:</span> {selectedFrame.criteria}
            </p>
          )}
        </div>
      )}

      {/* 기립/착석 분석 (있는 경우) */}
      {(data.stand_up || data.sit_down) && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-600">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">기립/착석 분석</p>
          <div className="grid grid-cols-2 gap-3">
            {data.stand_up && (
              <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                <div className="flex items-center mb-2">
                  <svg className="w-4 h-4 text-purple-500 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                  </svg>
                  <p className="text-xs font-medium text-purple-700 dark:text-purple-300">기립</p>
                </div>
                <p className="text-lg font-bold text-gray-800 dark:text-gray-100">
                  {data.stand_up.duration.toFixed(1)}<span className="text-sm text-gray-500">초</span>
                </p>
                <p className={`text-xs font-medium ${getSpeedColor(data.stand_up.assessment)}`}>
                  {data.stand_up.assessment}
                </p>
                {data.stand_up.used_hand_support && (
                  <div className="mt-2 flex items-center text-xs text-amber-600 dark:text-amber-400">
                    <svg className="w-3.5 h-3.5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 11.5V14m0-2.5v-6a1.5 1.5 0 113 0m-3 6a1.5 1.5 0 00-3 0v2a7.5 7.5 0 0015 0v-5a1.5 1.5 0 00-3 0m-6-3V11m0-5.5v-1a1.5 1.5 0 013 0v1m0 0V11m0-5.5a1.5 1.5 0 013 0v3m0 0V11" />
                    </svg>
                    손으로 짚고 일어남
                  </div>
                )}
              </div>
            )}
            {data.sit_down && (
              <div className="p-3 bg-pink-50 dark:bg-pink-900/20 rounded-lg">
                <div className="flex items-center mb-2">
                  <svg className="w-4 h-4 text-pink-500 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                  </svg>
                  <p className="text-xs font-medium text-pink-700 dark:text-pink-300">착석</p>
                </div>
                <p className="text-lg font-bold text-gray-800 dark:text-gray-100">
                  {data.sit_down.duration.toFixed(1)}<span className="text-sm text-gray-500">초</span>
                </p>
                <p className={`text-xs font-medium ${getSpeedColor(data.sit_down.assessment)}`}>
                  {data.sit_down.assessment}
                </p>
                {data.sit_down.used_hand_support && (
                  <div className="mt-2 flex items-center text-xs text-amber-600 dark:text-amber-400">
                    <svg className="w-3.5 h-3.5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 11.5V14m0-2.5v-6a1.5 1.5 0 113 0m-3 6a1.5 1.5 0 00-3 0v2a7.5 7.5 0 0015 0v-5a1.5 1.5 0 00-3 0m-6-3V11m0-5.5v-1a1.5 1.5 0 013 0v1m0 0V11m0-5.5a1.5 1.5 0 013 0v3m0 0V11" />
                    </svg>
                    손으로 짚고 앉음
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 운동 반응 분석 */}
      {(data.reaction_time || data.first_step_time) && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-600">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">운동 반응 분석</p>
          <div className="grid grid-cols-2 gap-3">
            {data.reaction_time && data.reaction_time.reaction_time > 0 && (
              <div className="p-3 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg">
                <div className="flex items-center mb-2">
                  <svg className="w-4 h-4 text-indigo-500 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  <p className="text-xs font-medium text-indigo-700 dark:text-indigo-300">반응 시간</p>
                </div>
                <p className="text-lg font-bold text-gray-800 dark:text-gray-100">
                  {data.reaction_time.reaction_time.toFixed(2)}<span className="text-sm text-gray-500">초</span>
                </p>
                <p className="text-xs text-gray-400 dark:text-gray-400">첫 움직임까지 소요 시간</p>
              </div>
            )}
            {data.first_step_time && data.first_step_time.time_to_first_step > 0 && (
              <div className="p-3 bg-cyan-50 dark:bg-cyan-900/20 rounded-lg">
                <div className="flex items-center mb-2">
                  <svg className="w-4 h-4 text-cyan-500 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                  <p className="text-xs font-medium text-cyan-700 dark:text-cyan-300">첫 걸음 시간</p>
                </div>
                <p className="text-lg font-bold text-gray-800 dark:text-gray-100">
                  {data.first_step_time.time_to_first_step.toFixed(2)}<span className="text-sm text-gray-500">초</span>
                </p>
                {data.first_step_time.hesitation_detected && (
                  <div className="mt-1 flex items-center text-xs text-orange-600 dark:text-orange-400">
                    <svg className="w-3.5 h-3.5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                    </svg>
                    보행 개시 지연 감지
                  </div>
                )}
                <p className="text-xs text-gray-400 dark:text-gray-400 mt-0.5">기립 완료 후 첫 발걸음</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 기울기 분석 */}
      {data.tilt_analysis && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-600">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">기울기 분석 (정면 영상)</p>
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-white dark:bg-gray-700 rounded-lg">
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">어깨 기울기</p>
              <p className={`font-bold ${
                Math.abs(data.tilt_analysis.shoulder_tilt_avg) >= 5 ? 'text-orange-500'
                : Math.abs(data.tilt_analysis.shoulder_tilt_avg) >= 2 ? 'text-yellow-500'
                : 'text-green-500'
              }`}>
                평균 {data.tilt_analysis.shoulder_tilt_avg > 0 ? '+' : ''}{data.tilt_analysis.shoulder_tilt_avg}°
              </p>
              <p className="text-xs text-gray-400 dark:text-gray-400">
                최대 {data.tilt_analysis.shoulder_tilt_max}° | {data.tilt_analysis.shoulder_tilt_direction}
              </p>
            </div>
            <div className="p-3 bg-white dark:bg-gray-700 rounded-lg">
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">골반 기울기</p>
              <p className={`font-bold ${
                Math.abs(data.tilt_analysis.hip_tilt_avg) >= 5 ? 'text-orange-500'
                : Math.abs(data.tilt_analysis.hip_tilt_avg) >= 2 ? 'text-yellow-500'
                : 'text-green-500'
              }`}>
                평균 {data.tilt_analysis.hip_tilt_avg > 0 ? '+' : ''}{data.tilt_analysis.hip_tilt_avg}°
              </p>
              <p className="text-xs text-gray-400 dark:text-gray-400">
                최대 {data.tilt_analysis.hip_tilt_max}° | {data.tilt_analysis.hip_tilt_direction}
              </p>
            </div>
          </div>
          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">{data.tilt_analysis.assessment}</p>
        </div>
      )}

      {/* 보행 패턴 (기존 단일 영상 TUG 호환) */}
      {!data.tilt_analysis && data.gait_pattern && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-600">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">보행 패턴 분석</p>
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-white dark:bg-gray-700 rounded-lg">
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">어깨 기울기</p>
              <p className={`font-bold ${
                Math.abs(data.gait_pattern.shoulder_tilt_avg) >= 5 ? 'text-orange-500'
                : Math.abs(data.gait_pattern.shoulder_tilt_avg) >= 2 ? 'text-yellow-500'
                : 'text-green-500'
              }`}>
                평균 {data.gait_pattern.shoulder_tilt_avg > 0 ? '+' : ''}{data.gait_pattern.shoulder_tilt_avg}°
              </p>
              <p className="text-xs text-gray-400 dark:text-gray-400">최대 {data.gait_pattern.shoulder_tilt_max}°</p>
            </div>
            <div className="p-3 bg-white dark:bg-gray-700 rounded-lg">
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">골반 기울기</p>
              <p className={`font-bold ${
                Math.abs(data.gait_pattern.hip_tilt_avg) >= 5 ? 'text-orange-500'
                : Math.abs(data.gait_pattern.hip_tilt_avg) >= 2 ? 'text-yellow-500'
                : 'text-green-500'
              }`}>
                평균 {data.gait_pattern.hip_tilt_avg > 0 ? '+' : ''}{data.gait_pattern.hip_tilt_avg}°
              </p>
              <p className="text-xs text-gray-400 dark:text-gray-400">최대 {data.gait_pattern.hip_tilt_max}°</p>
            </div>
          </div>
          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">{data.gait_pattern.assessment}</p>
        </div>
      )}

      {/* 체중이동 분석 */}
      {data.weight_shift && data.weight_shift.lateral_sway_amplitude > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-600">
          <TUGWeightShift data={data.weight_shift} />
        </div>
      )}

      {/* 상세 모달 */}
      {showModal && selectedFrame && selectedPhase && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={closeModal}>
          <div
            className="bg-white dark:bg-gray-800 rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className={`p-4 ${phaseColors[selectedPhase].light} border-b border-gray-200 dark:border-gray-700`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <div className={`w-8 h-8 ${phaseColors[selectedPhase].bg} rounded-full flex items-center justify-center mr-3`}>
                    <span className="text-white font-bold">{phaseOrder.indexOf(selectedPhase as typeof phaseOrder[number]) + 1}</span>
                  </div>
                  <div>
                    <h3 className={`text-lg font-bold ${phaseColors[selectedPhase].text}`}>{selectedFrame.label}</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      시작: {selectedFrame.time}초 | 지속: {selectedFrame.duration}초
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {phaseOrder.indexOf(selectedPhase as typeof phaseOrder[number]) > 0 && (
                    <button onClick={() => setSelectedPhase(phaseOrder[phaseOrder.indexOf(selectedPhase as typeof phaseOrder[number]) - 1])}
                      className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700" title="이전">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
                    </button>
                  )}
                  {phaseOrder.indexOf(selectedPhase as typeof phaseOrder[number]) < phaseOrder.length - 1 && (
                    <button onClick={() => setSelectedPhase(phaseOrder[phaseOrder.indexOf(selectedPhase as typeof phaseOrder[number]) + 1])}
                      className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700" title="다음">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                    </button>
                  )}
                  <button onClick={closeModal} className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                  </button>
                </div>
              </div>
            </div>
            <div className="p-4">
              <div className="relative rounded-xl overflow-hidden bg-black mb-4">
                {data.phase_clips?.[selectedPhase as keyof PhaseClips]?.clip_filename && testId ? (
                  <video src={testApi.getPhaseClipUrl(testId, selectedPhase)} className="w-full h-auto" controls autoPlay loop muted playsInline />
                ) : (
                  <img src={`data:image/jpeg;base64,${selectedFrame.frame}`} alt={selectedFrame.label} className="w-full h-auto" />
                )}
                <div className={`absolute top-4 left-4 px-3 py-1 ${phaseColors[selectedPhase].bg} rounded-lg shadow-lg`}>
                  <span className="text-white font-bold">{selectedFrame.label}</span>
                </div>
              </div>
              {selectedFrame.criteria && (
                <div className={`p-4 rounded-xl ${phaseColors[selectedPhase].light} mb-4`}>
                  <h4 className={`font-semibold ${phaseColors[selectedPhase].text} mb-2`}>감지 기준</h4>
                  <p className="text-gray-700 dark:text-gray-300 font-medium">{selectedFrame.criteria}</p>
                </div>
              )}
              {selectedFrame.description && (
                <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-xl mb-4">
                  <h4 className="font-semibold text-gray-700 dark:text-gray-300 mb-2">상세 설명</h4>
                  <p className="text-gray-600 dark:text-gray-400">{selectedFrame.description}</p>
                </div>
              )}
              {selectedFrame.key_points && selectedFrame.key_points.length > 0 && (
                <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-xl mb-4">
                  <h4 className="font-semibold text-gray-700 dark:text-gray-300 mb-3">주요 감지 포인트</h4>
                  <ul className="space-y-2">
                    {selectedFrame.key_points.map((point, idx) => (
                      <li key={idx} className="flex items-center text-gray-600 dark:text-gray-400">
                        <div className={`w-2 h-2 rounded-full ${phaseColors[selectedPhase].bg} mr-2`} />
                        {point}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="flex justify-end">
                <a href={`data:image/jpeg;base64,${selectedFrame.frame}`} download={`TUG_${selectedPhase}_${selectedFrame.time}s.jpg`}
                  className="inline-flex items-center px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors">
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                  이미지 다운로드
                </a>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
