import { useState } from 'react';
import { testApi } from '../services/api';

interface WalkingHighlightProps {
  testId: string;
}

export default function WalkingHighlight({ testId }: WalkingHighlightProps) {
  const [showClip, setShowClip] = useState(false);
  const [error, setError] = useState(false);

  const clipUrl = testApi.getWalkingClipUrl(testId);

  if (error) return null;

  return (
    <div>
      {!showClip ? (
        <button
          onClick={() => setShowClip(true)}
          className="w-full px-4 py-2.5 text-center bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400 rounded-lg font-semibold text-sm hover:bg-purple-100 dark:hover:bg-purple-900/40 transition-colors flex items-center justify-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          보행 구간 하이라이트 클립
        </button>
      ) : (
        <div className="bg-gray-900 rounded-xl overflow-hidden">
          <video
            src={clipUrl}
            controls
            autoPlay
            className="w-full aspect-video"
            onError={() => { setError(true); setShowClip(false); }}
          />
          <div className="bg-gray-800 px-4 py-2 flex justify-between items-center">
            <span className="text-white text-xs">보행 구간 클립</span>
            <button
              onClick={() => setShowClip(false)}
              className="text-gray-400 hover:text-white text-xs"
            >
              닫기
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
