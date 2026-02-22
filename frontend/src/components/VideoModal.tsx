import { useState, useRef, useEffect } from 'react';
import { testApi } from '../services/api';
import type { WalkTest, VideoInfo, TUGAnalysisData, AnalysisData } from '../types';
import TUGPhaseFrames from './TUGPhaseFrames';
import { useFocusTrap } from '../hooks/useFocusTrap';

interface VideoModalProps {
  test: WalkTest;
  onClose: () => void;
}

type OverlayVideoType = 'side' | 'front';

export default function VideoModal({ test, onClose }: VideoModalProps) {
  const focusTrapRef = useFocusTrap(true);
  const videoRef = useRef<HTMLVideoElement>(null);
  const overlayVideoRef = useRef<HTMLVideoElement>(null);
  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showPoseOverlay, setShowPoseOverlay] = useState(true);  // 포즈 오버레이 기본 ON
  const [overlayType, setOverlayType] = useState<OverlayVideoType>('side'); // TUG는 기본 측면
  const [sequentialMode, setSequentialMode] = useState(false); // 순차재생 모드
  const [seqPlaying, setSeqPlaying] = useState<'side' | 'front'>('side'); // 현재 순차재생 중인 영상

  const videoUrl = testApi.getVideoUrl(test);

  // TUG 검사인지 확인
  const isTUG = test.test_type === 'TUG';

  // 오버레이 영상 URL 가져오기
  const getOverlayVideoUrls = () => {
    const analysisData = test.analysis_data as (TUGAnalysisData | AnalysisData | null);

    if (!analysisData) return { side: null, front: null, default: null };

    // TUG 검사: 측면/정면 오버레이 (레거시 overlay_video_filename도 측면으로 처리)
    if (isTUG) {
      const tugData = analysisData as TUGAnalysisData;
      const sideUrl = tugData.side_overlay_video_filename
        ? `/uploads/${tugData.side_overlay_video_filename}`
        : (tugData.overlay_video_filename ? `/uploads/${tugData.overlay_video_filename}` : null);
      const frontUrl = tugData.front_overlay_video_filename
        ? `/uploads/${tugData.front_overlay_video_filename}`
        : null;
      return {
        side: sideUrl,
        front: frontUrl,
        default: sideUrl || frontUrl
      };
    }

    // 10MWT 또는 기존 방식
    if ('overlay_video_filename' in analysisData && analysisData.overlay_video_filename) {
      const url = `/uploads/${analysisData.overlay_video_filename}`;
      return { side: url, front: null, default: url };
    }

    return { side: null, front: null, default: null };
  };

  const overlayUrls = getOverlayVideoUrls();

  // TUG 원본 영상 URL (측면/정면)
  const tugOriginalUrls = (() => {
    if (!isTUG) return null;
    const tugData = test.analysis_data as TUGAnalysisData | null;
    const frontFilename = tugData?.front_video_filename;
    const frontUrl = frontFilename ? `/uploads/${frontFilename}` : null;
    return { side: videoUrl, front: frontUrl };
  })();

  // 순차재생 모드에서 현재 영상 타입 결정
  const activeViewType = sequentialMode ? seqPlaying : overlayType;

  const currentOverlayUrl = isTUG
    ? (activeViewType === 'front' ? (overlayUrls.front || overlayUrls.side) : (overlayUrls.side || overlayUrls.front))
    : overlayUrls.default;

  // 순차재생 모드에서 원본 영상 URL 결정
  const currentVideoUrl = isTUG && tugOriginalUrls
    ? (activeViewType === 'front' ? (tugOriginalUrls.front || tugOriginalUrls.side) : tugOriginalUrls.side)
    : videoUrl;

  // 순차재생: 정면 영상 가능 여부
  const hasFrontVideo = !!(tugOriginalUrls?.front || overlayUrls.front);

  useEffect(() => {
    const loadVideoInfo = async () => {
      try {
        const info = await testApi.getVideoInfo(test.id);
        setVideoInfo(info);
      } catch (err) {
        console.error('Failed to load video info:', err);
      } finally {
        setLoading(false);
      }
    };
    loadVideoInfo();
  }, [test.id]);

  // ESC 키로 닫기
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  // 모달 열릴 때 스크롤 방지
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, []);

  const handleDownload = () => {
    const downloadUrl = testApi.downloadVideo(test.id);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `walk_test_${test.id}.mp4`;
    link.click();
  };

  const togglePoseOverlay = () => {
    setShowPoseOverlay(!showPoseOverlay);
  };

  // 순차재생: 측면 끝나면 정면 자동 전환
  const handleSequentialEnded = () => {
    if (sequentialMode && seqPlaying === 'side') {
      setSeqPlaying('front');
    }
  };

  // 순차재생 모드 토글
  const toggleSequentialMode = () => {
    if (!sequentialMode) {
      setSequentialMode(true);
      setSeqPlaying('side');
    } else {
      setSequentialMode(false);
    }
  };

  if (!videoUrl) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="video-modal-title"
    >
      <div
        ref={focusTrapRef}
        className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto animate-fadeIn"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 헤더 */}
        <div className="p-4 border-b dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <h3 id="video-modal-title" className="font-semibold text-gray-800 dark:text-gray-100">검사 동영상</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {new Date(test.test_date).toLocaleDateString('ko-KR')} · {test.walk_time_seconds.toFixed(2)}초 · {test.walk_speed_mps.toFixed(2)}m/s
              </p>
            </div>
            <div className="flex items-center space-x-2">
              {/* 포즈 오버레이 토글 버튼 - 오버레이 영상이 있을 때만 표시 */}
              {currentOverlayUrl && (
                <button
                  onClick={togglePoseOverlay}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    showPoseOverlay
                      ? 'bg-green-500 text-white'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }`}
                  aria-label={showPoseOverlay ? '원본 영상 보기' : '포즈 오버레이 보기'}
                  aria-pressed={showPoseOverlay}
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                  <span>{showPoseOverlay ? '포즈' : '원본'}</span>
                </button>
              )}
              <button
                onClick={onClose}
                className="p-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
                aria-label="닫기"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* TUG 검사: 측면/정면 선택 + 순차재생 버튼 */}
          {isTUG && hasFrontVideo && (
            <div className="flex items-center gap-2 mt-3 pt-3 border-t dark:border-gray-600">
              <span className="text-sm text-gray-600 dark:text-gray-300 mr-1">
                {sequentialMode ? `순차 재생: ${seqPlaying === 'side' ? '측면' : '정면'}` : '영상 선택:'}
              </span>
              {!sequentialMode && (
                <>
                  <button
                    onClick={() => setOverlayType('side')}
                    disabled={!overlayUrls.side && !tugOriginalUrls?.side}
                    aria-pressed={overlayType === 'side'}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      overlayType === 'side'
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-100 dark:bg-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-500'
                    }`}
                  >
                    측면
                  </button>
                  <button
                    onClick={() => setOverlayType('front')}
                    aria-pressed={overlayType === 'front'}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      overlayType === 'front'
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-100 dark:bg-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-500'
                    }`}
                  >
                    정면
                  </button>
                </>
              )}
              <button
                onClick={toggleSequentialMode}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  sequentialMode
                    ? 'bg-green-500 text-white'
                    : 'bg-gray-100 dark:bg-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-500'
                }`}
              >
                순차재생
              </button>
            </div>
          )}
        </div>

        {/* 비디오 플레이어 */}
        <div className="bg-black relative">
          {showPoseOverlay && currentOverlayUrl ? (
            <div className="relative">
              <video
                ref={overlayVideoRef}
                key={currentOverlayUrl}
                src={currentOverlayUrl}
                controls
                autoPlay
                className="w-full max-h-[60vh]"
                onError={() => {
                  console.warn('포즈 오버레이 영상 로딩 실패, 원본 영상으로 전환');
                  setShowPoseOverlay(false);
                }}
                onEnded={sequentialMode ? handleSequentialEnded : undefined}
              >
                브라우저가 동영상 재생을 지원하지 않습니다.
              </video>
              {/* 포즈 오버레이 안내 배지 */}
              <div className="absolute top-4 left-4 px-3 py-1 bg-green-500 text-white text-sm font-medium rounded-lg shadow-lg flex items-center space-x-2">
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="4" />
                </svg>
                <span>
                  {isTUG
                    ? (activeViewType === 'front' && overlayUrls.front ? '정면 포즈 오버레이' : '측면 포즈 오버레이')
                    : 'MediaPipe 포즈 오버레이'
                  }
                  {sequentialMode && ' (순차재생)'}
                </span>
              </div>
            </div>
          ) : (
            <video
              ref={videoRef}
              key={currentVideoUrl}
              src={currentVideoUrl || undefined}
              controls
              autoPlay
              className="w-full max-h-[60vh]"
              onError={() => setError('동영상을 불러올 수 없습니다.')}
              onEnded={sequentialMode ? handleSequentialEnded : undefined}
            >
              브라우저가 동영상 재생을 지원하지 않습니다.
            </video>
          )}
        </div>

        {/* 포즈 오버레이 설명 */}
        {showPoseOverlay && currentOverlayUrl && (
          <div className="p-3 bg-green-50 dark:bg-green-900/30 border-t border-green-200 dark:border-green-800">
            <div className="flex items-start space-x-3">
              <svg className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="text-sm text-green-700 dark:text-green-300">
                <p className="font-medium">MediaPipe 포즈 분석 영상</p>
                <p className="text-green-600 dark:text-green-400 mt-1">
                  {isTUG && overlayType === 'front' && overlayUrls.front
                    ? '정면 영상: 어깨와 골반의 기울기 분석에 적합합니다. 좌/우 균형을 확인하세요.'
                    : isTUG && overlayType === 'side' && overlayUrls.side
                    ? '측면 영상: 기립/착석 동작과 보행 패턴 분석에 적합합니다.'
                    : '검사 분석 시 녹화된 관절 포인트와 스켈레톤 연결선이 표시됩니다.'
                  }
                </p>
              </div>
            </div>
          </div>
        )}

        {/* 오버레이 영상이 없는 경우 안내 */}
        {!currentOverlayUrl && (
          <div className="p-3 bg-yellow-50 dark:bg-yellow-900/30 border-t border-yellow-200 dark:border-yellow-800">
            <div className="flex items-start space-x-3">
              <svg className="w-5 h-5 text-yellow-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <div className="text-sm text-yellow-700 dark:text-yellow-300">
                <p className="font-medium">포즈 오버레이 영상 없음</p>
                <p className="text-yellow-600 dark:text-yellow-400 mt-1">
                  이 검사는 포즈 오버레이 기능이 추가되기 전에 분석된 영상입니다.
                  새로 분석한 영상에서는 포즈 오버레이를 볼 수 있습니다.
                </p>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div role="alert" className="p-4 bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* TUG 검사 단계별 전환 시점 캡처 */}
        {test.test_type === 'TUG' && test.analysis_data && (test.analysis_data as TUGAnalysisData).phase_frames && (
          <div className="p-4 border-t dark:border-gray-700">
            <TUGPhaseFrames
              phaseFrames={(test.analysis_data as TUGAnalysisData).phase_frames!}
              phaseClips={(test.analysis_data as TUGAnalysisData).phase_clips}
              testId={test.id}
            />
          </div>
        )}

        {/* 푸터 - 정보 및 다운로드 */}
        <div className="p-4 bg-gray-50 dark:bg-gray-700/50 flex items-center justify-between">
          <div className="text-sm text-gray-500 dark:text-gray-400">
            {loading ? (
              <span>파일 정보 로딩 중...</span>
            ) : videoInfo ? (
              <span>파일 크기: {videoInfo.size_mb} MB</span>
            ) : null}
          </div>
          <button
            onClick={handleDownload}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            aria-label="동영상 다운로드"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            <span>다운로드</span>
          </button>
        </div>
      </div>
    </div>
  );
}
