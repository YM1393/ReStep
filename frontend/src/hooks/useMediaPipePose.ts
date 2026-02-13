/**
 * MediaPipe Pose Landmarker 훅
 * - 브라우저에서 PoseLandmarker Heavy 모델 실행
 * - 2D 정규화 랜드마크 + 3D 월드 랜드마크 반환
 * - Canvas에 2D 스켈레톤 오버레이 드로잉 (옵션)
 */
import { useRef, useState, useEffect, useCallback } from 'react';
import { PoseLandmarker, FilesetResolver } from '@mediapipe/tasks-vision';
import type { NormalizedLandmark, Landmark } from '@mediapipe/tasks-vision';

// 바디 랜드마크 연결 (인덱스 11-32, 얼굴 제외)
const BODY_CONNECTIONS = [
  [11, 12], [11, 13], [13, 15], [15, 17], [15, 19], [15, 21],
  [12, 14], [14, 16], [16, 18], [16, 20], [16, 22],
  [11, 23], [12, 24], [23, 24],
  [23, 25], [25, 27], [27, 29], [27, 31], [29, 31],
  [24, 26], [26, 28], [28, 30], [28, 32], [30, 32],
];

const LEFT_INDICES = new Set([11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31]);

interface UseMediaPipePoseOptions {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  enabled: boolean;
  drawSkeleton?: boolean;
  targetFps?: number;
}

interface UseMediaPipePoseResult {
  landmarks: NormalizedLandmark[] | null;
  worldLandmarks: Landmark[] | null;
  isReady: boolean;
  isLoading: boolean;
  fps: number;
  error: string | null;
}

export type { NormalizedLandmark, Landmark };

export function useMediaPipePose({
  videoRef,
  canvasRef,
  enabled,
  drawSkeleton = true,
  targetFps = 15,
}: UseMediaPipePoseOptions): UseMediaPipePoseResult {
  const [landmarks, setLandmarks] = useState<NormalizedLandmark[] | null>(null);
  const [worldLandmarks, setWorldLandmarks] = useState<Landmark[] | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [fps, setFps] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const poseLandmarkerRef = useRef<PoseLandmarker | null>(null);
  const rafRef = useRef<number>(0);
  const lastTimeRef = useRef(0);
  const frameCountRef = useRef(0);
  const fpsTimerRef = useRef(performance.now());
  const minInterval = 1000 / targetFps;

  // 모델 초기화
  useEffect(() => {
    let cancelled = false;

    async function init() {
      if (poseLandmarkerRef.current) return;
      setIsLoading(true);
      setError(null);

      try {
        const vision = await FilesetResolver.forVisionTasks(
          'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm'
        );

        if (cancelled) return;

        // Use full model on mobile (lighter), heavy on desktop
        const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
        const modelPath = isMobile
          ? 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task'
          : 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task';

        let landmarker: PoseLandmarker;
        try {
          // Try GPU first
          landmarker = await PoseLandmarker.createFromOptions(vision, {
            baseOptions: { modelAssetPath: modelPath, delegate: 'GPU' },
            runningMode: 'VIDEO',
            numPoses: 1,
          });
          console.log('[MediaPipe] Initialized with GPU delegate');
        } catch {
          // Fallback to CPU
          console.warn('[MediaPipe] GPU failed, falling back to CPU');
          landmarker = await PoseLandmarker.createFromOptions(vision, {
            baseOptions: { modelAssetPath: modelPath, delegate: 'CPU' },
            runningMode: 'VIDEO',
            numPoses: 1,
          });
          console.log('[MediaPipe] Initialized with CPU delegate');
        }

        if (cancelled) {
          landmarker.close();
          return;
        }

        poseLandmarkerRef.current = landmarker;
        setIsReady(true);
        setIsLoading(false);
      } catch (err) {
        if (!cancelled) {
          console.error('[MediaPipe] Init error:', err);
          setError(err instanceof Error ? err.message : 'MediaPipe 초기화 실패');
          setIsLoading(false);
        }
      }
    }

    init();
    return () => { cancelled = true; };
  }, []);

  // 스켈레톤 드로잉
  const drawOverlay = useCallback((lms: NormalizedLandmark[], canvas: HTMLCanvasElement, video: HTMLVideoElement) => {
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // 캔버스 해상도에 비례하는 스케일 (모바일에서 오버레이가 작게 보이는 문제 방지)
    const scale = Math.max(canvas.width, canvas.height) / 500;
    const lineW = Math.max(2, Math.round(3 * scale));
    const pointR = Math.max(3, Math.round(5 * scale));
    const outlineW = Math.max(1, Math.round(1.5 * scale));

    // 바디 연결선만 그리기
    for (const [a, b] of BODY_CONNECTIONS) {
      if (a >= lms.length || b >= lms.length) continue;
      const la = lms[a];
      const lb = lms[b];
      if (la.visibility !== undefined && la.visibility < 0.5) continue;
      if (lb.visibility !== undefined && lb.visibility < 0.5) continue;

      const isLeft = LEFT_INDICES.has(a) || LEFT_INDICES.has(b);
      const color = isLeft ? '#00e5b0' : '#4fc3f7';

      ctx.beginPath();
      ctx.moveTo(la.x * canvas.width, la.y * canvas.height);
      ctx.lineTo(lb.x * canvas.width, lb.y * canvas.height);
      ctx.strokeStyle = color;
      ctx.lineWidth = lineW;
      ctx.stroke();
    }

    // 바디 랜드마크 점
    for (let i = 11; i < Math.min(33, lms.length); i++) {
      const lm = lms[i];
      if (lm.visibility !== undefined && lm.visibility < 0.5) continue;
      const isLeft = LEFT_INDICES.has(i);
      ctx.beginPath();
      ctx.arc(lm.x * canvas.width, lm.y * canvas.height, pointR, 0, 2 * Math.PI);
      ctx.fillStyle = isLeft ? '#00e5b0' : '#4fc3f7';
      ctx.fill();
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = outlineW;
      ctx.stroke();
    }
  }, []);

  // 프레임 처리 루프
  useEffect(() => {
    if (!enabled || !isReady || !poseLandmarkerRef.current) {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      return;
    }

    const detect = (now: number) => {
      rafRef.current = requestAnimationFrame(detect);

      // FPS 제한
      if (now - lastTimeRef.current < minInterval) return;
      lastTimeRef.current = now;

      const video = videoRef.current;
      const canvas = canvasRef.current;
      const landmarker = poseLandmarkerRef.current;
      if (!video || !landmarker || video.readyState < 2) return;

      try {
        const result = landmarker.detectForVideo(video, now);

        if (result.landmarks && result.landmarks.length > 0) {
          const lms = result.landmarks[0];
          setLandmarks(lms);

          if (result.worldLandmarks && result.worldLandmarks.length > 0) {
            setWorldLandmarks(result.worldLandmarks[0]);
          }

          // 스켈레톤 오버레이
          if (drawSkeleton && canvas) {
            drawOverlay(lms, canvas, video);
          }
        }

        // FPS 계산
        frameCountRef.current++;
        const elapsed = now - fpsTimerRef.current;
        if (elapsed >= 1000) {
          setFps(Math.round(frameCountRef.current * 1000 / elapsed));
          frameCountRef.current = 0;
          fpsTimerRef.current = now;
        }
      } catch {
        // detectForVideo 에러 무시 (간헐적)
      }
    };

    rafRef.current = requestAnimationFrame(detect);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [enabled, isReady, drawSkeleton, targetFps, videoRef, canvasRef, drawOverlay, minInterval]);

  // 클린업
  useEffect(() => {
    return () => {
      if (poseLandmarkerRef.current) {
        poseLandmarkerRef.current.close();
        poseLandmarkerRef.current = null;
      }
    };
  }, []);

  return { landmarks, worldLandmarks, isReady, isLoading, fps, error };
}
