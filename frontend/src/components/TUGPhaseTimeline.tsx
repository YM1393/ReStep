import { useState } from 'react';
import type { TUGPhases, PhaseFrames, PhaseClips } from '../types';
import { testApi } from '../services/api';

interface TUGPhaseTimelineProps {
  phases: TUGPhases;
  totalTime: number;
  showDetectionInfo?: boolean;
  phaseFrames?: PhaseFrames;
  phaseClips?: PhaseClips;
  testId?: string;
}

const phaseLabels: Record<string, string> = {
  stand_up: '일어서기',
  walk_out: '걷기(나감)',
  turn: '돌아서기',
  walk_back: '걷기(돌아옴)',
  sit_down: '앉기'
};

const phaseColors: Record<string, { bg: string; border: string; text: string; light: string; hoverBg: string }> = {
  stand_up: { bg: 'bg-purple-500', border: 'border-purple-500', text: 'text-purple-600', light: 'bg-purple-50 dark:bg-purple-900/20', hoverBg: 'bg-purple-400' },
  walk_out: { bg: 'bg-blue-500', border: 'border-blue-500', text: 'text-blue-600', light: 'bg-blue-50 dark:bg-blue-900/20', hoverBg: 'bg-blue-400' },
  turn: { bg: 'bg-yellow-500', border: 'border-yellow-500', text: 'text-yellow-600', light: 'bg-yellow-50 dark:bg-yellow-900/20', hoverBg: 'bg-yellow-400' },
  walk_back: { bg: 'bg-green-500', border: 'border-green-500', text: 'text-green-600', light: 'bg-green-50 dark:bg-green-900/20', hoverBg: 'bg-green-400' },
  sit_down: { bg: 'bg-pink-500', border: 'border-pink-500', text: 'text-pink-600', light: 'bg-pink-50 dark:bg-pink-900/20', hoverBg: 'bg-pink-400' }
};

const detectionCriteria: Record<string, string> = {
  stand_up: '엉덩이-무릎-발목 각도가 120° 이하에서 160° 이상으로 변화',
  walk_out: '기립 완료 후 발이 전방으로 이동 시작',
  turn: '어깨 방향 변화가 최대인 지점 감지',
  walk_back: '회전 완료 후 반대 방향 이동 시작',
  sit_down: '다리 각도가 160° 이상에서 120° 이하로 변화'
};

const phaseOrder = ['stand_up', 'walk_out', 'turn', 'walk_back', 'sit_down'] as const;

export default function TUGPhaseTimeline({ phases, totalTime, showDetectionInfo = true, phaseFrames, phaseClips, testId }: TUGPhaseTimelineProps) {
  const [hoveredPhase, setHoveredPhase] = useState<string | null>(null);
  const [selectedPhase, setSelectedPhase] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);

  const startTime = phases.stand_up.start_time;
  const hasFrames = phaseFrames && Object.keys(phaseFrames).length > 0;

  const handlePhaseClick = (key: string) => {
    if (selectedPhase === key) {
      setSelectedPhase(null);
    } else {
      setSelectedPhase(key);
    }
  };

  const openModal = (phase: string) => {
    setSelectedPhase(phase);
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
  };

  const selectedFrame = selectedPhase && phaseFrames ? phaseFrames[selectedPhase as keyof PhaseFrames] : null;

  return (
    <div className="card">
      <h4 className="font-semibold text-gray-800 dark:text-gray-100 mb-4 flex items-center">
        <svg className="w-5 h-5 mr-2 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
        단계별 전환 시점
        {hasFrames && (
          <span className="ml-2 text-xs text-gray-400 dark:text-gray-400 font-normal">
            클릭하여 캡처 보기
          </span>
        )}
      </h4>

      {/* 타임라인 바 - 인터랙티브 */}
      <div className="relative mb-6">
        <div className="h-14 bg-gray-100 dark:bg-gray-700 rounded-lg relative overflow-hidden">
          {phaseOrder.map((key) => {
            const phase = phases[key];
            const startPercent = ((phase.start_time - startTime) / totalTime) * 100;
            const widthPercent = (phase.duration / totalTime) * 100;
            const colors = phaseColors[key];
            const isHovered = hoveredPhase === key;
            const isSelected = selectedPhase === key;
            const hasFrame = phaseFrames?.[key as keyof PhaseFrames];

            return (
              <div
                key={key}
                className={`absolute h-full flex items-center justify-center transition-all duration-200 ${
                  hasFrame || hasFrames ? 'cursor-pointer' : ''
                } ${colors.bg} ${
                  isHovered ? 'opacity-100 brightness-110 z-20' : isSelected ? 'opacity-100 z-20' : 'opacity-80'
                }`}
                style={{
                  left: `${startPercent}%`,
                  width: `${widthPercent}%`,
                  transform: isHovered ? 'scaleY(1.15)' : isSelected ? 'scaleY(1.08)' : 'scaleY(1)',
                  transformOrigin: 'center',
                  boxShadow: isHovered
                    ? '0 4px 12px rgba(0,0,0,0.25)'
                    : isSelected
                    ? '0 2px 8px rgba(0,0,0,0.2)'
                    : 'none',
                  filter: isHovered ? 'brightness(1.15)' : 'brightness(1)',
                  borderRadius: isHovered || isSelected ? '4px' : '0',
                }}
                title={`${phaseLabels[key]}: ${phase.duration.toFixed(1)}초${hasFrame ? ' (클릭하여 캡처 보기)' : ''}`}
                onMouseEnter={() => setHoveredPhase(key)}
                onMouseLeave={() => setHoveredPhase(null)}
                onClick={() => hasFrames && handlePhaseClick(key)}
              >
                {widthPercent > 12 && (
                  <span className={`text-white text-xs font-medium truncate px-1 transition-all duration-200 ${
                    isHovered ? 'text-sm font-bold' : ''
                  }`}>
                    {isHovered ? phaseLabels[key] : `${phase.duration.toFixed(1)}s`}
                  </span>
                )}
                {/* 선택 표시 화살표 */}
                {isSelected && (
                  <div className="absolute -bottom-2 left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-[6px] border-r-[6px] border-t-[6px] border-l-transparent border-r-transparent border-t-current z-30"
                    style={{ color: 'var(--tw-shadow-color, #6b7280)' }}
                  />
                )}
              </div>
            );
          })}

          {/* 단계 전환 마커 */}
          {phaseOrder.map((key, index) => {
            if (index === 0) return null;
            const phase = phases[key];
            const position = ((phase.start_time - startTime) / totalTime) * 100;
            return (
              <div
                key={`marker-${key}`}
                className="absolute top-0 bottom-0 w-0.5 bg-white/60 dark:bg-gray-900/60 z-10 pointer-events-none"
                style={{ left: `${position}%` }}
              />
            );
          })}
        </div>

        {/* 시간 눈금 */}
        <div className="flex justify-between mt-1 text-xs text-gray-400 dark:text-gray-400">
          <span>0초</span>
          <span>{(totalTime / 4).toFixed(1)}초</span>
          <span>{(totalTime / 2).toFixed(1)}초</span>
          <span>{(totalTime * 3 / 4).toFixed(1)}초</span>
          <span>{totalTime.toFixed(1)}초</span>
        </div>
      </div>

      {/* 선택된 단계의 캡처 프레임 (인라인) */}
      {selectedPhase && selectedFrame && (
        <div className={`mb-4 p-4 rounded-xl border-2 ${phaseColors[selectedPhase].border} ${phaseColors[selectedPhase].light} animate-fadeIn`}>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center">
              <div className={`w-7 h-7 ${phaseColors[selectedPhase].bg} rounded-full flex items-center justify-center mr-2`}>
                <span className="text-white text-xs font-bold">{phaseOrder.indexOf(selectedPhase as typeof phaseOrder[number]) + 1}</span>
              </div>
              <div>
                <span className={`font-bold ${phaseColors[selectedPhase].text}`}>
                  {selectedFrame.label}
                </span>
                <span className="text-xs text-gray-500 dark:text-gray-400 ml-2">
                  {phases[selectedPhase as keyof typeof phases].duration.toFixed(2)}초
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => openModal(selectedPhase)}
                className="text-xs px-3 py-1.5 bg-white dark:bg-gray-700 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors border border-gray-200 dark:border-gray-600"
              >
                상세보기
              </button>
              <button
                onClick={() => setSelectedPhase(null)}
                className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* 캡처 이미지/클립 */}
          <div className="relative rounded-lg overflow-hidden bg-black cursor-pointer" onClick={() => openModal(selectedPhase)}>
            {phaseClips?.[selectedPhase as keyof PhaseClips]?.clip_filename && testId ? (
              <video
                src={testApi.getPhaseClipUrl(testId, selectedPhase)}
                className="w-full h-auto max-h-64 object-contain"
                autoPlay
                loop
                muted
                playsInline
              />
            ) : (
              <img
                src={`data:image/jpeg;base64,${selectedFrame.frame}`}
                alt={selectedFrame.label}
                className="w-full h-auto max-h-64 object-contain"
              />
            )}
          </div>

          {/* 감지 기준 */}
          {selectedFrame.criteria && (
            <div className="mt-3 p-2 bg-white/60 dark:bg-gray-700/60 rounded-lg">
              <p className="text-xs text-gray-600 dark:text-gray-300">
                <span className="font-medium text-gray-700 dark:text-gray-200">감지 기준: </span>
                {selectedFrame.criteria}
              </p>
            </div>
          )}
        </div>
      )}

      {/* 단계별 상세 정보 */}
      <div className="space-y-2">
        {phaseOrder.map((key, index) => {
          const phase = phases[key];
          const colors = phaseColors[key];
          const prevPhase = index > 0 ? phases[phaseOrder[index - 1]] : null;
          const isSelected = selectedPhase === key;
          const hasFrame = phaseFrames?.[key as keyof PhaseFrames];

          return (
            <div
              key={key}
              className={`p-3 rounded-lg border-l-4 ${colors.border} bg-gray-50 dark:bg-gray-800 transition-all duration-200 ${
                hasFrames ? 'cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-750' : ''
              } ${isSelected ? 'ring-2 ring-offset-1 ring-gray-300 dark:ring-gray-500' : ''}`}
              onClick={() => hasFrames && handlePhaseClick(key)}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center">
                  <span className={`w-6 h-6 rounded-full ${colors.bg} text-white text-xs flex items-center justify-center mr-2`}>
                    {index + 1}
                  </span>
                  <span className={`font-medium ${colors.text} dark:opacity-80`}>
                    {phaseLabels[key]}
                  </span>
                  {hasFrame && (
                    <svg className="w-3.5 h-3.5 ml-1.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                  )}
                </div>
                <div className="text-right">
                  <span className="font-bold text-gray-800 dark:text-gray-100">
                    {phase.duration.toFixed(2)}초
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 ml-8">
                <span>
                  시작: {(phase.start_time - startTime).toFixed(2)}초
                  {prevPhase && (
                    <span className="ml-2 text-gray-400">
                      (이전 단계 종료: {(prevPhase.end_time - startTime).toFixed(2)}초)
                    </span>
                  )}
                </span>
                <span>종료: {(phase.end_time - startTime).toFixed(2)}초</span>
              </div>

              {showDetectionInfo && (
                <div className="mt-2 ml-8 p-2 bg-white dark:bg-gray-700 rounded text-xs text-gray-600 dark:text-gray-300">
                  <span className="font-medium text-gray-700 dark:text-gray-200">감지 기준: </span>
                  {detectionCriteria[key]}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* 범례 */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-600">
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">단계 구분</p>
        <div className="flex flex-wrap gap-2">
          {phaseOrder.map((key) => (
            <div key={key} className="flex items-center">
              <div className={`w-3 h-3 rounded ${phaseColors[key].bg} mr-1`} />
              <span className="text-xs text-gray-600 dark:text-gray-400">{phaseLabels[key]}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 상세 모달 */}
      {showModal && selectedFrame && selectedPhase && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={closeModal}>
          <div
            className="bg-white dark:bg-gray-800 rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* 모달 헤더 */}
            <div className={`p-4 ${phaseColors[selectedPhase].light} border-b border-gray-200 dark:border-gray-700`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <div className={`w-8 h-8 ${phaseColors[selectedPhase].bg} rounded-full flex items-center justify-center mr-3`}>
                    <span className="text-white font-bold">{phaseOrder.indexOf(selectedPhase as typeof phaseOrder[number]) + 1}</span>
                  </div>
                  <div>
                    <h3 className={`text-lg font-bold ${phaseColors[selectedPhase].text}`}>
                      {selectedFrame.label}
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      시작 시점: {selectedFrame.time}초 | 지속 시간: {selectedFrame.duration}초
                    </p>
                  </div>
                </div>
                {/* 이전/다음 네비게이션 */}
                <div className="flex items-center gap-2">
                  {phaseOrder.indexOf(selectedPhase as typeof phaseOrder[number]) > 0 && (
                    <button
                      onClick={() => {
                        const idx = phaseOrder.indexOf(selectedPhase as typeof phaseOrder[number]);
                        setSelectedPhase(phaseOrder[idx - 1]);
                      }}
                      className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
                      title="이전 단계"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                      </svg>
                    </button>
                  )}
                  {phaseOrder.indexOf(selectedPhase as typeof phaseOrder[number]) < phaseOrder.length - 1 && (
                    <button
                      onClick={() => {
                        const idx = phaseOrder.indexOf(selectedPhase as typeof phaseOrder[number]);
                        setSelectedPhase(phaseOrder[idx + 1]);
                      }}
                      className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
                      title="다음 단계"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </button>
                  )}
                  <button
                    onClick={closeModal}
                    className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>

            {/* 모달 콘텐츠 */}
            <div className="p-4">
              <div className="relative rounded-xl overflow-hidden bg-black mb-4">
                {phaseClips?.[selectedPhase as keyof PhaseClips]?.clip_filename && testId ? (
                  <video
                    src={testApi.getPhaseClipUrl(testId, selectedPhase)}
                    className="w-full h-auto"
                    controls
                    autoPlay
                    loop
                    muted
                    playsInline
                  />
                ) : (
                  <img
                    src={`data:image/jpeg;base64,${selectedFrame.frame}`}
                    alt={selectedFrame.label}
                    className="w-full h-auto"
                  />
                )}
                <div className={`absolute top-4 left-4 px-3 py-1 ${phaseColors[selectedPhase].bg} rounded-lg shadow-lg`}>
                  <span className="text-white font-bold">{selectedFrame.label}</span>
                </div>
                <div className="absolute bottom-4 right-4 px-3 py-1 bg-black/70 rounded-lg">
                  <span className="text-white text-sm">{selectedFrame.time}s</span>
                </div>
              </div>

              {/* 감지 기준 */}
              <div className={`p-4 rounded-xl ${phaseColors[selectedPhase].light} mb-4`}>
                <h4 className={`font-semibold ${phaseColors[selectedPhase].text} mb-2 flex items-center`}>
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  감지 기준
                </h4>
                <p className="text-gray-700 dark:text-gray-300 font-medium">
                  {selectedFrame.criteria}
                </p>
              </div>

              {/* 상세 설명 */}
              {selectedFrame.description && (
                <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-xl mb-4">
                  <h4 className="font-semibold text-gray-700 dark:text-gray-300 mb-2 flex items-center">
                    <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    상세 설명
                  </h4>
                  <p className="text-gray-600 dark:text-gray-400">
                    {selectedFrame.description}
                  </p>
                </div>
              )}

              {/* 주요 감지 포인트 */}
              {selectedFrame.key_points && selectedFrame.key_points.length > 0 && (
                <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-xl">
                  <h4 className="font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center">
                    <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                    </svg>
                    주요 감지 포인트
                  </h4>
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

              {/* 이미지 다운로드 버튼 */}
              <div className="mt-4 flex justify-end">
                <a
                  href={`data:image/jpeg;base64,${selectedFrame.frame}`}
                  download={`TUG_${selectedPhase}_${selectedFrame.time}s.jpg`}
                  className="inline-flex items-center px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
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
