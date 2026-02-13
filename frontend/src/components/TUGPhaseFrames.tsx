import { useState } from 'react';
import type { PhaseFrames, PhaseClips } from '../types';
import { testApi } from '../services/api';

interface TUGPhaseFramesProps {
  phaseFrames: PhaseFrames;
  phaseClips?: PhaseClips;
  testId?: string;
}

const phaseOrder: (keyof PhaseFrames)[] = ['stand_up', 'walk_out', 'turn', 'walk_back', 'sit_down'];

const phaseColors: Record<string, { bg: string; border: string; text: string; light: string }> = {
  stand_up: { bg: 'bg-purple-500', border: 'border-purple-500', text: 'text-purple-600', light: 'bg-purple-50 dark:bg-purple-900/20' },
  walk_out: { bg: 'bg-blue-500', border: 'border-blue-500', text: 'text-blue-600', light: 'bg-blue-50 dark:bg-blue-900/20' },
  turn: { bg: 'bg-yellow-500', border: 'border-yellow-500', text: 'text-yellow-600', light: 'bg-yellow-50 dark:bg-yellow-900/20' },
  walk_back: { bg: 'bg-green-500', border: 'border-green-500', text: 'text-green-600', light: 'bg-green-50 dark:bg-green-900/20' },
  sit_down: { bg: 'bg-pink-500', border: 'border-pink-500', text: 'text-pink-600', light: 'bg-pink-50 dark:bg-pink-900/20' }
};

export default function TUGPhaseFrames({ phaseFrames, phaseClips, testId }: TUGPhaseFramesProps) {
  const [selectedPhase, setSelectedPhase] = useState<keyof PhaseFrames | null>(null);
  const [showModal, setShowModal] = useState(false);

  const openModal = (phase: keyof PhaseFrames) => {
    setSelectedPhase(phase);
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setSelectedPhase(null);
  };

  const selectedFrame = selectedPhase ? phaseFrames[selectedPhase] : null;

  return (
    <div className="card">
      <h4 className="font-semibold text-gray-800 dark:text-gray-100 mb-4 flex items-center">
        <svg className="w-5 h-5 mr-2 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        단계별 전환 시점 캡처
      </h4>

      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
        {phaseClips && testId
          ? '각 단계 전환 시점의 클립 영상입니다. 클릭하면 상세 정보를 확인할 수 있습니다.'
          : '각 단계 전환 시점의 프레임입니다. 클릭하면 감지 기준과 상세 정보를 확인할 수 있습니다.'}
      </p>

      {/* 단계별 썸네일 그리드 */}
      <div className="grid grid-cols-5 gap-2">
        {phaseOrder.map((phase, index) => {
          const frameInfo = phaseFrames[phase];
          const clipInfo = phaseClips?.[phase];
          const colors = phaseColors[phase];
          const hasClip = clipInfo?.clip_filename && testId;

          if (!frameInfo && !clipInfo) {
            return (
              <div key={phase} className="aspect-video bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center">
                <span className="text-xs text-gray-400">없음</span>
              </div>
            );
          }

          return (
            <div
              key={phase}
              className={`relative cursor-pointer rounded-lg overflow-hidden border-2 ${colors.border} hover:shadow-lg transition-shadow`}
              onClick={() => openModal(phase)}
            >
              {hasClip ? (
                <video
                  src={testApi.getPhaseClipUrl(testId!, phase)}
                  className="w-full aspect-video object-cover"
                  autoPlay
                  loop
                  muted
                  playsInline
                />
              ) : frameInfo ? (
                <img
                  src={`data:image/jpeg;base64,${frameInfo.frame}`}
                  alt={frameInfo?.label || clipInfo?.label || phase}
                  className="w-full aspect-video object-cover"
                />
              ) : clipInfo?.thumbnail ? (
                <img
                  src={`data:image/jpeg;base64,${clipInfo.thumbnail}`}
                  alt={clipInfo.label}
                  className="w-full aspect-video object-cover"
                />
              ) : null}
              {/* 클립 아이콘 */}
              {hasClip && (
                <div className="absolute top-1 right-1 bg-black/50 rounded-full p-0.5">
                  <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                </div>
              )}
              {/* 단계 번호 뱃지 */}
              <div className={`absolute top-1 left-1 w-5 h-5 ${colors.bg} rounded-full flex items-center justify-center`}>
                <span className="text-white text-xs font-bold">{index + 1}</span>
              </div>
              {/* 단계 레이블 */}
              <div className="absolute bottom-0 left-0 right-0 bg-black/60 px-1 py-0.5">
                <p className="text-white text-xs truncate text-center">{frameInfo?.label || clipInfo?.label}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* 범례 */}
      <div className="mt-4 flex flex-wrap gap-2 justify-center">
        {phaseOrder.map((phase) => {
          const frameInfo = phaseFrames[phase];
          const colors = phaseColors[phase];
          if (!frameInfo) return null;

          return (
            <button
              key={phase}
              onClick={() => openModal(phase)}
              className={`flex items-center px-2 py-1 rounded-lg ${colors.light} hover:opacity-80 transition-opacity`}
            >
              <div className={`w-2 h-2 rounded-full ${colors.bg} mr-1.5`} />
              <span className={`text-xs font-medium ${colors.text}`}>{frameInfo.label}</span>
              <span className="text-xs text-gray-400 ml-1">({frameInfo.time}s)</span>
            </button>
          );
        })}
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
                    <span className="text-white font-bold">{phaseOrder.indexOf(selectedPhase) + 1}</span>
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

            {/* 모달 콘텐츠 */}
            <div className="p-4">
              {/* 캡처 이미지 or 클립 영상 */}
              <div className="relative rounded-xl overflow-hidden bg-black mb-4">
                {phaseClips?.[selectedPhase]?.clip_filename && testId ? (
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
                {/* 단계 오버레이 */}
                <div className={`absolute top-4 left-4 px-3 py-1 ${phaseColors[selectedPhase].bg} rounded-lg shadow-lg`}>
                  <span className="text-white font-bold">{selectedFrame.label}</span>
                </div>
                {/* 시간 오버레이 */}
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
