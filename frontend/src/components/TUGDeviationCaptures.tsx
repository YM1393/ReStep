import { useState } from 'react';
import type { DeviationCapture } from '../types';

interface TUGDeviationCapturesProps {
  captures: DeviationCapture[];
}

const severityColors: Record<string, { bg: string; text: string; badge: string }> = {
  mild: { bg: 'bg-yellow-50 dark:bg-yellow-900/20', text: 'text-yellow-600', badge: 'bg-yellow-500' },
  moderate: { bg: 'bg-orange-50 dark:bg-orange-900/20', text: 'text-orange-600', badge: 'bg-orange-500' },
  severe: { bg: 'bg-red-50 dark:bg-red-900/20', text: 'text-red-600', badge: 'bg-red-500' },
};

const severityLabels: Record<string, string> = {
  mild: '경미',
  moderate: '보통',
  severe: '심함',
};

const typeLabels: Record<string, string> = {
  shoulder: '어깨',
  hip: '골반',
  both: '어깨+골반',
};

export default function TUGDeviationCaptures({ captures }: TUGDeviationCapturesProps) {
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const [filter, setFilter] = useState<string>('all');

  const filteredCaptures = filter === 'all'
    ? captures
    : captures.filter(c => c.type === filter || (filter === 'both' && c.type === 'both'));

  const selectedCapture = selectedIdx !== null ? filteredCaptures[selectedIdx] : null;

  return (
    <div className="card">
      <h4 className="font-semibold text-gray-800 dark:text-gray-100 mb-3 flex items-center">
        <svg className="w-5 h-5 mr-2 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
        </svg>
        자세 편향 캡처
        <span className="ml-2 text-xs text-gray-400 font-normal">({captures.length}건 감지)</span>
      </h4>

      {/* 필터 */}
      <div className="flex gap-2 mb-3">
        {['all', 'shoulder', 'hip', 'both'].map((f) => (
          <button
            key={f}
            onClick={() => { setFilter(f); setSelectedIdx(null); }}
            className={`px-2.5 py-1 text-xs rounded-lg transition-colors ${
              filter === f
                ? 'bg-orange-500 text-white'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
            }`}
          >
            {f === 'all' ? '전체' : typeLabels[f] || f}
          </button>
        ))}
      </div>

      {/* 캡처 그리드 */}
      <div className="grid grid-cols-5 gap-2">
        {filteredCaptures.map((capture, idx) => {
          const colors = severityColors[capture.severity] || severityColors.mild;
          return (
            <div
              key={idx}
              className="relative cursor-pointer rounded-lg overflow-hidden border-2 border-gray-200 dark:border-gray-600 hover:border-orange-400 hover:shadow-lg transition-all"
              onClick={() => setSelectedIdx(idx)}
            >
              <img
                src={`data:image/jpeg;base64,${capture.frame}`}
                alt={`편향 ${capture.time}s`}
                className="w-full aspect-video object-cover"
              />
              {/* severity 배지 */}
              <div className={`absolute top-1 right-1 px-1.5 py-0.5 ${colors.badge} rounded text-white text-[9px] font-bold`}>
                {severityLabels[capture.severity]}
              </div>
              {/* 시간 */}
              <div className="absolute bottom-0 left-0 right-0 bg-black/60 px-1 py-0.5">
                <p className="text-white text-[10px] text-center">{capture.time}s</p>
              </div>
            </div>
          );
        })}
      </div>

      {filteredCaptures.length === 0 && (
        <p className="text-sm text-gray-400 text-center py-4">해당 유형의 편향이 감지되지 않았습니다.</p>
      )}

      {/* 상세 모달 */}
      {selectedCapture && selectedIdx !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={() => setSelectedIdx(null)}>
          <div
            className="bg-white dark:bg-gray-800 rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* 헤더 */}
            <div className={`p-4 ${severityColors[selectedCapture.severity]?.bg || ''} border-b border-gray-200 dark:border-gray-700`}>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className={`text-lg font-bold ${severityColors[selectedCapture.severity]?.text || ''}`}>
                    자세 편향 - {typeLabels[selectedCapture.type]}
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    시점: {selectedCapture.time}초 | 심각도: {severityLabels[selectedCapture.severity]}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedIdx(null)}
                  className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* 이미지 */}
            <div className="p-4">
              <div className="relative rounded-xl overflow-hidden bg-black mb-4">
                <img
                  src={`data:image/jpeg;base64,${selectedCapture.frame}`}
                  alt={`편향 캡처 ${selectedCapture.time}s`}
                  className="w-full h-auto"
                />
              </div>

              {/* 각도 정보 */}
              <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded-xl">
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">어깨 기울기</p>
                  <p className={`text-xl font-bold ${
                    Math.abs(selectedCapture.shoulder_angle) > 10 ? 'text-red-500' :
                    Math.abs(selectedCapture.shoulder_angle) > 5 ? 'text-orange-500' : 'text-green-500'
                  }`}>
                    {selectedCapture.shoulder_angle > 0 ? '+' : ''}{selectedCapture.shoulder_angle.toFixed(1)}°
                  </p>
                </div>
                <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded-xl">
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">골반 기울기</p>
                  <p className={`text-xl font-bold ${
                    Math.abs(selectedCapture.hip_angle) > 10 ? 'text-red-500' :
                    Math.abs(selectedCapture.hip_angle) > 5 ? 'text-orange-500' : 'text-green-500'
                  }`}>
                    {selectedCapture.hip_angle > 0 ? '+' : ''}{selectedCapture.hip_angle.toFixed(1)}°
                  </p>
                </div>
              </div>

              {/* 이전/다음 버튼 */}
              <div className="flex justify-between">
                <button
                  onClick={() => setSelectedIdx(Math.max(0, selectedIdx - 1))}
                  disabled={selectedIdx === 0}
                  className="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 rounded-lg disabled:opacity-30"
                >
                  이전
                </button>
                <span className="text-sm text-gray-400 self-center">
                  {selectedIdx + 1} / {filteredCaptures.length}
                </span>
                <button
                  onClick={() => setSelectedIdx(Math.min(filteredCaptures.length - 1, selectedIdx + 1))}
                  disabled={selectedIdx === filteredCaptures.length - 1}
                  className="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 rounded-lg disabled:opacity-30"
                >
                  다음
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
