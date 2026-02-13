import { useState, useCallback } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Grid, PerspectiveCamera } from '@react-three/drei';
import type { TUGPose3DFrame, TUGPhases } from '../types';
import { AnimatedAnatomicalSkeleton } from './pose3d/AnatomicalSkeleton';

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
  unknown: '-',
};

const PHASE_ORDER = ['stand_up', 'walk_out', 'turn', 'walk_back', 'sit_down'] as const;

interface PhaseTimelineBarProps {
  phases: TUGPhases;
  totalTime: number;
  currentTime: number;
  onSeek: (time: number) => void;
}

function PhaseTimelineBar({ phases, totalTime, currentTime, onSeek }: PhaseTimelineBarProps) {
  if (totalTime <= 0) return null;

  return (
    <div className="relative h-8 rounded-lg overflow-hidden flex cursor-pointer" role="progressbar">
      {PHASE_ORDER.map(phaseName => {
        const phase = phases[phaseName];
        if (!phase) return null;
        const widthPct = (phase.duration / totalTime) * 100;
        return (
          <div
            key={phaseName}
            className="relative h-full flex items-center justify-center text-xs font-medium text-white/90 hover:brightness-110 transition-all"
            style={{
              width: `${widthPct}%`,
              backgroundColor: PHASE_COLORS[phaseName],
              minWidth: widthPct > 5 ? undefined : '2px',
            }}
            onClick={() => onSeek(phase.start_time)}
            title={`${PHASE_LABELS[phaseName]} (${(phase.duration ?? 0).toFixed(1)}s)`}
          >
            {widthPct > 10 && PHASE_LABELS[phaseName]}
          </div>
        );
      })}
      {/* Current position indicator */}
      <div
        className="absolute top-0 bottom-0 w-0.5 bg-white shadow-lg z-10 pointer-events-none"
        style={{ left: `${Math.min(100, (currentTime / totalTime) * 100)}%` }}
      />
    </div>
  );
}

interface TUGPoseViewer3DProps {
  sideFrames: TUGPose3DFrame[];
  frontFrames?: TUGPose3DFrame[];
  phases: TUGPhases;
  totalTime: number;
}

export default function TUGPoseViewer3D({ sideFrames, frontFrames, phases, totalTime }: TUGPoseViewer3DProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [source, setSource] = useState<'side' | 'front'>('side');

  const activeFrames = source === 'front' && frontFrames?.length ? frontFrames : sideFrames;

  const currentFrame = activeFrames[currentIndex];
  const currentTime = currentFrame?.time ?? 0;
  const currentPhase = (currentFrame as TUGPose3DFrame)?.phase ?? 'unknown';

  const handleFrameChange = useCallback((idx: number) => {
    setCurrentIndex(idx);
  }, []);

  const handleSliderChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setCurrentIndex(Number(e.target.value));
    setPlaying(false);
  }, []);

  const togglePlay = useCallback(() => {
    setPlaying(prev => !prev);
  }, []);

  const seekToTime = useCallback((time: number) => {
    const idx = activeFrames.findIndex(f => f.time >= time);
    if (idx >= 0) {
      setCurrentIndex(idx);
      setPlaying(false);
    }
  }, [activeFrames]);

  const skipPhase = useCallback((direction: 1 | -1) => {
    const currentPhaseIdx = PHASE_ORDER.indexOf(currentPhase as typeof PHASE_ORDER[number]);
    const nextPhaseIdx = currentPhaseIdx + direction;
    if (nextPhaseIdx >= 0 && nextPhaseIdx < PHASE_ORDER.length) {
      const nextPhaseName = PHASE_ORDER[nextPhaseIdx];
      const phase = phases[nextPhaseName];
      if (phase) seekToTime(phase.start_time);
    }
  }, [currentPhase, phases, seekToTime]);

  if (!sideFrames || sideFrames.length === 0) {
    return (
      <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-8 text-center text-gray-500 dark:text-gray-400">
        <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
        <p className="font-medium">3D 포즈 데이터 없음</p>
        <p className="text-sm mt-1">TUG 영상을 다시 분석하면 3D 본 모델이 생성됩니다.</p>
      </div>
    );
  }

  const relativeTime = currentTime - (activeFrames[0]?.time ?? 0);
  const totalDuration = activeFrames.length > 1 ? activeFrames[activeFrames.length - 1].time - activeFrames[0].time : 0;

  return (
    <div className="rounded-lg border overflow-hidden" style={{ backgroundColor: '#0d1117', borderColor: '#1a3a4a' }}>
      {/* Source toggle */}
      {frontFrames && frontFrames.length > 0 && (
        <div className="flex items-center gap-2 px-4 pt-3">
          <span className="text-xs" style={{ color: '#5a7a8a' }}>영상 소스:</span>
          {([['side', '측면'], ['front', '정면']] as const).map(([key, label]) => (
            <button
              key={key}
              onClick={() => { setSource(key); setCurrentIndex(0); setPlaying(false); }}
              className="px-3 py-1 text-xs rounded-full transition-colors"
              style={{
                backgroundColor: source === key ? '#00e5b0' : '#152030',
                color: source === key ? '#0d1117' : '#5a8a9a',
              }}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {/* 3D Canvas */}
      <div className="h-[450px] relative" style={{ backgroundColor: '#0d1117' }}>
        <Canvas>
          <color attach="background" args={['#0d1117']} />
          <PerspectiveCamera makeDefault position={[0, 0, 1.8]} fov={50} />
          <ambientLight intensity={0.15} />
          <AnimatedAnatomicalSkeleton
            frames={activeFrames}
            currentIndex={currentIndex}
            playing={playing}
            speed={speed}
            onFrameChange={handleFrameChange}
            phaseColor={PHASE_COLORS[currentPhase] || PHASE_COLORS.unknown}
          />
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

        {/* Phase badge */}
        <div
          className="absolute top-3 right-3 px-3 py-1.5 rounded-full text-sm font-bold text-white shadow-lg transition-colors"
          style={{ backgroundColor: PHASE_COLORS[currentPhase] || PHASE_COLORS.unknown }}
        >
          {PHASE_LABELS[currentPhase] || '-'}
        </div>

        {/* Legend */}
        <div className="absolute top-3 left-3 rounded px-3 py-2 text-xs font-medium" style={{ backgroundColor: 'rgba(0,229,176,0.12)', color: '#00e5b0' }}>
          Clinical Gait Analysis
        </div>
      </div>

      {/* Controls */}
      <div className="p-4 space-y-3" style={{ backgroundColor: '#0d1117' }}>
        {/* Phase timeline bar */}
        <PhaseTimelineBar
          phases={phases}
          totalTime={totalTime}
          currentTime={relativeTime}
          onSeek={(t) => seekToTime(t + (activeFrames[0]?.time ?? 0))}
        />

        {/* Playback controls */}
        <div className="flex items-center gap-3">
          {/* Skip prev phase */}
          <button
            onClick={() => skipPhase(-1)}
            className="w-8 h-8 flex items-center justify-center rounded-full transition-colors"
            style={{ backgroundColor: '#152030', color: '#5a8a9a' }}
            aria-label="이전 단계"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M6 6h2v12H6zm3.5 6l8.5 6V6z" />
            </svg>
          </button>

          {/* Play/Pause */}
          <button
            onClick={togglePlay}
            className="w-10 h-10 flex items-center justify-center rounded-full transition-colors"
            style={{ backgroundColor: '#00e5b0', color: '#0d1117' }}
            aria-label={playing ? '일시정지' : '재생'}
          >
            {playing ? (
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M6 4h4v16H6zM14 4h4v16h-4z" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
            )}
          </button>

          {/* Skip next phase */}
          <button
            onClick={() => skipPhase(1)}
            className="w-8 h-8 flex items-center justify-center rounded-full transition-colors"
            style={{ backgroundColor: '#152030', color: '#5a8a9a' }}
            aria-label="다음 단계"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z" />
            </svg>
          </button>

          {/* Timeline slider */}
          <input
            type="range"
            min={0}
            max={Math.max(0, activeFrames.length - 1)}
            value={currentIndex}
            onChange={handleSliderChange}
            className="flex-1 h-2"
            style={{ accentColor: '#00e5b0' }}
            aria-label="타임라인"
          />

          <span className="text-sm w-24 text-right tabular-nums" style={{ color: '#5a8a9a' }}>
            {relativeTime.toFixed(1)}s / {totalDuration.toFixed(1)}s
          </span>
        </div>

        {/* Speed controls */}
        <div className="flex items-center gap-2">
          <span className="text-xs" style={{ color: '#5a7a8a' }}>속도:</span>
          {[0.5, 1, 2].map(s => (
            <button
              key={s}
              onClick={() => setSpeed(s)}
              className="px-2 py-1 text-xs rounded transition-colors"
              style={{
                backgroundColor: speed === s ? '#00e5b0' : '#152030',
                color: speed === s ? '#0d1117' : '#5a8a9a',
              }}
            >
              {s}x
            </button>
          ))}
        </div>

        {/* Phase legend */}
        <div className="flex items-center justify-center gap-3 flex-wrap">
          {PHASE_ORDER.map(p => (
            <div key={p} className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm inline-block" style={{ backgroundColor: PHASE_COLORS[p] }} />
              <span className="text-xs" style={{ color: '#5a8a9a' }}>{PHASE_LABELS[p]}</span>
            </div>
          ))}
        </div>

        {/* Frame info */}
        <div className="text-xs text-center" style={{ color: '#3a5a6a' }}>
          프레임 {currentIndex + 1} / {activeFrames.length} | 마우스 드래그로 회전, 스크롤로 확대/축소
        </div>
      </div>
    </div>
  );
}
