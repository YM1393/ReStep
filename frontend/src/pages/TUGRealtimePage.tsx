/**
 * 실시간 TUG 검사 페이지
 * - 카메라로 실시간 측면 촬영
 * - MediaPipe JS로 2D/3D 랜드마크 추출
 * - 2D 스켈레톤 오버레이 + 3D 본 모델 + 단계 감지
 */
import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, Grid } from '@react-three/drei';
import { patientApi, authApi } from '../services/api';
import { useMediaPipePose } from '../hooks/useMediaPipePose';
import { useTUGRealtimeWebSocket } from '../hooks/useTUGRealtimeWebSocket';
import { SkeletonBody } from '../components/pose3d/AnatomicalSkeleton';
import type { Patient, TUGPose3DFrame } from '../types';

const PHASE_COLORS: Record<string, string> = {
  stand_up: '#A855F7',
  walk_out: '#3B82F6',
  turn: '#EAB308',
  walk_back: '#22C55E',
  sit_down: '#EC4899',
  unknown: '#6B7280',
};

const PHASE_LABELS: Record<string, string> = {
  stand_up: '기립',
  walk_out: '보행',
  turn: '회전',
  walk_back: '복귀',
  sit_down: '착석',
  unknown: '대기',
};

const PHASE_ORDER = ['stand_up', 'walk_out', 'turn', 'walk_back', 'sit_down'];

export default function TUGRealtimePage() {
  const { id: patientId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const user = authApi.getCurrentUser();

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const startTimeRef = useRef<number>(0);
  const streamRef = useRef<MediaStream | null>(null);

  const [patient, setPatient] = useState<Patient | null>(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [testPhase, setTestPhase] = useState<'idle' | 'ready' | 'testing' | 'completed'>('idle');
  const [localTimer, setLocalTimer] = useState(0);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [debugMsg, setDebugMsg] = useState<string>('');

  // MediaPipe 훅
  const { landmarks, worldLandmarks, isReady: mpReady, isLoading: mpLoading, fps, error: mpError } = useMediaPipePose({
    videoRef,
    canvasRef,
    enabled: cameraActive,
    drawSkeleton: true,
    targetFps: 15,
  });

  // WebSocket 훅
  const { state: wsState, startTest, stopTest, sendFrame, isConnected } = useTUGRealtimeWebSocket({
    patientId: patientId || '',
    userId: user?.id || '',
    enabled: testPhase !== 'idle',
  });

  // 환자 정보 로드
  useEffect(() => {
    if (patientId) {
      patientApi.getById(patientId).then(setPatient).catch(console.error);
    }
  }, [patientId]);

  // Ref callback: video 마운트 시 즉시 stream 연결
  const videoRefCallback = useCallback((el: HTMLVideoElement | null) => {
    videoRef.current = el;
    if (el && streamRef.current && !el.srcObject) {
      el.srcObject = streamRef.current;
      el.play().then(() => {
        setDebugMsg(`카메라 OK (${el.videoWidth}x${el.videoHeight})`);
      }).catch((e) => {
        setDebugMsg(`play() 실패: ${e.message}`);
      });
    }
  }, []);

  // 카메라 시작
  const startCamera = useCallback(async () => {
    setCameraError(null);
    setDebugMsg('카메라 요청중...');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' },
        audio: false,
      });
      streamRef.current = stream;
      setDebugMsg('스트림 획득, 연결중...');
      setTestPhase('ready');
      setCameraActive(true);
    } catch (err) {
      console.error('[Camera]', err);
      const msg = err instanceof Error ? err.message : String(err);
      setCameraError(`카메라 오류: ${msg}`);
      setDebugMsg(`실패: ${msg}`);
    }
  }, []);

  // 카메라 중지
  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current?.srcObject) {
      videoRef.current.srcObject = null;
    }
    setCameraActive(false);
  }, []);

  // 검사 시작
  const handleStartTest = useCallback(() => {
    startTest();
    startTimeRef.current = performance.now() / 1000;
    setTestPhase('testing');
    setLocalTimer(0);
  }, [startTest]);

  // 검사 중지
  const handleStopTest = useCallback(() => {
    stopTest();
    setTestPhase('completed');
  }, [stopTest]);

  // 프레임 전송 (랜드마크 변경 시)
  useEffect(() => {
    if (testPhase !== 'testing' || !landmarks || !wsState.isTestRunning) return;
    const ts = performance.now() / 1000;
    sendFrame(landmarks, ts, worldLandmarks);
  }, [landmarks, testPhase, wsState.isTestRunning, sendFrame, worldLandmarks]);

  // 로컬 타이머
  useEffect(() => {
    if (testPhase !== 'testing') return;
    const interval = setInterval(() => {
      setLocalTimer((performance.now() / 1000) - startTimeRef.current);
    }, 100);
    return () => clearInterval(interval);
  }, [testPhase]);

  // 검사 완료 감지
  useEffect(() => {
    if (wsState.testResult && testPhase === 'testing') {
      setTestPhase('completed');
    }
  }, [wsState.testResult, testPhase]);

  // 3D 모델용 프레임 생성
  const currentPose3DFrame: TUGPose3DFrame | null = useMemo(() => {
    if (!worldLandmarks || worldLandmarks.length < 33) return null;
    return {
      time: localTimer,
      phase: wsState.currentPhase || 'unknown',
      landmarks: worldLandmarks.slice(11, 33).map(lm => [lm.x, lm.y, lm.z]),
    };
  }, [worldLandmarks, localTimer, wsState.currentPhase]);

  // 현재 표시할 경과 시간
  const elapsed = testPhase === 'testing' ? (wsState.elapsedTime || localTimer) : (wsState.testResult?.total_time_seconds || localTimer);

  // 페이지 나갈 때 카메라 정리
  useEffect(() => {
    return () => stopCamera();
  }, [stopCamera]);

  const phaseColor = PHASE_COLORS[wsState.currentPhase] || PHASE_COLORS.unknown;

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-4">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate(`/patients/${patientId}`)} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
          </button>
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">실시간 TUG 검사</h1>
            {patient && <p className="text-sm text-gray-500 dark:text-gray-400">{patient.name}</p>}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* 연결 상태 */}
          {testPhase !== 'idle' && (
            <span className={`text-xs px-2 py-1 rounded-full ${isConnected ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' : 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'}`}>
              {isConnected ? '연결됨' : '연결 끊김'}
            </span>
          )}

          {/* 검사 컨트롤 */}
          {testPhase === 'idle' && (
            <button onClick={startCamera} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium">
              카메라 시작
            </button>
          )}
          {testPhase === 'ready' && (
            <button
              onClick={handleStartTest}
              disabled={!mpReady || !isConnected}
              className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {mpLoading ? '모델 로딩중...' : mpError ? '모델 오류' : !isConnected ? '서버 연결중...' : !mpReady ? '모델 준비중...' : '검사 시작'}
            </button>
          )}
          {testPhase === 'testing' && (
            <button onClick={handleStopTest} className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium">
              검사 중지
            </button>
          )}
          {testPhase === 'completed' && (
            <button
              onClick={() => navigate(`/patients/${patientId}`)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
            >
              결과 보기
            </button>
          )}
        </div>
      </div>

      {/* 에러 표시 */}
      {(cameraError || mpError) && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 text-red-700 dark:text-red-300 text-sm">
          {cameraError || mpError}
        </div>
      )}

      {/* 안내 텍스트 (idle 상태) */}
      {testPhase === 'idle' && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6 text-center">
          <svg className="w-16 h-16 mx-auto mb-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          <h3 className="text-lg font-bold text-blue-800 dark:text-blue-200 mb-2">카메라를 환자 측면에 배치하세요</h3>
          <p className="text-blue-600 dark:text-blue-300 text-sm">
            환자가 의자에서 일어나 3m 걸은 뒤 돌아오는 전체 과정이 촬영되도록 카메라를 배치합니다.
          </p>
        </div>
      )}

      {/* 메인 뷰 (카메라 + 3D 모델) */}
      {testPhase !== 'idle' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* 카메라 뷰 */}
          <div className="relative rounded-lg overflow-hidden bg-black aspect-video">
            <video
              ref={videoRefCallback}
              autoPlay
              playsInline
              muted
              className="w-full h-full object-cover"
            />
            <canvas
              ref={canvasRef}
              className="absolute inset-0 w-full h-full"
              style={{ pointerEvents: 'none' }}
            />

            {/* FPS + 디버그 */}
            <div className="absolute top-2 left-2 bg-black/60 text-white text-xs px-2 py-1 rounded">
              {fps} FPS | {debugMsg}
            </div>

            {/* 단계 배지 (카메라 위) */}
            {testPhase === 'testing' && (
              <div
                className="absolute top-2 right-2 px-3 py-1.5 rounded-full text-sm font-bold text-white shadow-lg"
                style={{ backgroundColor: phaseColor }}
              >
                {PHASE_LABELS[wsState.currentPhase] || '대기'}
              </div>
            )}

            {/* 모델 로딩 표시 */}
            {mpLoading && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/50">
                <div className="text-center text-white">
                  <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-white mx-auto mb-2" />
                  <p className="text-sm">MediaPipe 모델 로딩중...</p>
                </div>
              </div>
            )}
          </div>

          {/* 3D 본 모델 */}
          <div className="rounded-lg overflow-hidden" style={{ backgroundColor: '#0d1117', aspectRatio: '16/9' }}>
            <Canvas>
              <color attach="background" args={['#0d1117']} />
              <PerspectiveCamera makeDefault position={[0, 0, 1.8]} fov={50} />
              <ambientLight intensity={0.15} />
              {currentPose3DFrame && (
                <SkeletonBody
                  frame={currentPose3DFrame}
                  phaseColor={phaseColor}
                />
              )}
              <Grid
                args={[4, 4]}
                position={[0, -0.45, 0]}
                cellSize={0.2}
                cellColor="#1a3a4a"
                sectionSize={1}
                sectionColor="#1e5060"
                fadeDistance={5}
              />
              <OrbitControls enableDamping dampingFactor={0.1} target={[0, 0, 0]} />
            </Canvas>

            {/* 3D 모델 안내 */}
            {!currentPose3DFrame && (
              <div className="absolute inset-0 flex items-center justify-center">
                <p className="text-sm" style={{ color: '#5a8a9a' }}>
                  {mpReady ? '환자가 카메라에 보이면 3D 모델이 표시됩니다' : '모델 로딩중...'}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 타이머 + 단계 표시 */}
      {(testPhase === 'testing' || testPhase === 'completed') && (
        <div className="rounded-lg border dark:border-gray-700 p-4 space-y-3" style={{ backgroundColor: testPhase === 'completed' ? undefined : '#0d1117', borderColor: testPhase === 'completed' ? undefined : '#1a3a4a' }}>
          {/* 타이머 */}
          <div className="flex items-center justify-center gap-4">
            <div
              className="px-4 py-2 rounded-full text-lg font-bold text-white"
              style={{ backgroundColor: phaseColor }}
            >
              {PHASE_LABELS[wsState.currentPhase] || '대기'}
            </div>
            <div className="text-3xl font-mono font-bold tabular-nums" style={{ color: testPhase === 'completed' ? undefined : '#00e5b0' }}>
              {elapsed.toFixed(1)}s
            </div>
          </div>

          {/* 단계 타임라인 바 */}
          {wsState.transitions.length > 0 && (
            <div className="relative h-8 rounded-lg overflow-hidden flex">
              {wsState.transitions.map((t, i) => {
                const totalElapsed = elapsed || 1;
                const start = t.start;
                const end = t.end ?? totalElapsed;
                const widthPct = ((end - start) / totalElapsed) * 100;
                return (
                  <div
                    key={i}
                    className="h-full flex items-center justify-center text-xs font-medium text-white/90"
                    style={{
                      width: `${Math.max(widthPct, 1)}%`,
                      backgroundColor: PHASE_COLORS[t.phase] || PHASE_COLORS.unknown,
                    }}
                  >
                    {widthPct > 10 && PHASE_LABELS[t.phase]}
                  </div>
                );
              })}
            </div>
          )}

          {/* 단계 범례 */}
          <div className="flex items-center justify-center gap-3 flex-wrap">
            {PHASE_ORDER.map(p => (
              <div key={p} className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-sm inline-block" style={{ backgroundColor: PHASE_COLORS[p] }} />
                <span className="text-xs" style={{ color: testPhase === 'completed' ? undefined : '#5a8a9a' }}>{PHASE_LABELS[p]}</span>
              </div>
            ))}
          </div>

          {/* 검사 완료 결과 요약 */}
          {testPhase === 'completed' && wsState.testResult && (
            <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <h3 className="font-bold text-lg mb-2 text-gray-900 dark:text-white">검사 결과</h3>
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">총 소요시간</p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">{wsState.testResult.total_time_seconds?.toFixed(1)}s</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">보행 속도</p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">{wsState.testResult.walk_speed_mps?.toFixed(2)} m/s</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">평가</p>
                  <p className={`text-2xl font-bold ${
                    wsState.testResult.assessment === 'normal' ? 'text-green-600' :
                    wsState.testResult.assessment === 'good' ? 'text-blue-600' :
                    wsState.testResult.assessment === 'caution' ? 'text-yellow-600' :
                    'text-red-600'
                  }`}>
                    {wsState.testResult.assessment === 'normal' ? '정상' :
                     wsState.testResult.assessment === 'good' ? '양호' :
                     wsState.testResult.assessment === 'caution' ? '주의' : '위험'}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 안내 텍스트 */}
      {testPhase === 'ready' && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 text-center">
          <p className="text-sm text-yellow-700 dark:text-yellow-300">
            카메라에 환자가 보이는지 확인 후 <strong>"검사 시작"</strong> 버튼을 누르세요.
            {!mpReady && <span className="block mt-1">MediaPipe 모델을 로딩하고 있습니다...</span>}
          </p>
        </div>
      )}
    </div>
  );
}
