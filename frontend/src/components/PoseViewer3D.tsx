import { useState, useCallback, useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Grid, PerspectiveCamera } from '@react-three/drei';
import type { Pose3DFrame } from '../types';
import { AnimatedAnatomicalSkeleton } from './pose3d/AnatomicalSkeleton';

interface PoseViewer3DProps {
  frames: Pose3DFrame[];
}

export default function PoseViewer3D({ frames }: PoseViewer3DProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [viewPreset, setViewPreset] = useState<'front' | 'side' | 'top'>('front');

  const cameraPositions = useMemo(() => ({
    front: [0, 0, 1.8] as [number, number, number],
    side: [1.8, 0, 0] as [number, number, number],
    top: [0, -2, 0.01] as [number, number, number],
  }), []);

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

  if (!frames || frames.length === 0) {
    return (
      <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-8 text-center text-gray-500 dark:text-gray-400">
        <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 10h.01M15 10h.01M9.5 15.5a3.5 3.5 0 015 0" />
        </svg>
        <p className="font-medium">3D 포즈 데이터 없음</p>
        <p className="text-sm mt-1">이 검사는 3D 데이터가 포함되지 않았습니다. 영상을 다시 분석하면 3D 데이터가 생성됩니다.</p>
      </div>
    );
  }

  const currentTime = frames[currentIndex]?.time ?? 0;
  const totalDuration = frames.length > 1 ? frames[frames.length - 1].time - frames[0].time : 0;
  const relativeTime = currentTime - (frames[0]?.time ?? 0);

  return (
    <div className="rounded-lg border overflow-hidden" style={{ backgroundColor: '#0d1117', borderColor: '#1a3a4a' }}>
      {/* 3D Canvas */}
      <div className="h-[450px] relative" style={{ backgroundColor: '#0d1117' }}>
        <Canvas>
          <color attach="background" args={['#0d1117']} />
          <PerspectiveCamera makeDefault position={cameraPositions[viewPreset]} fov={50} />
          <ambientLight intensity={0.15} />
          <AnimatedAnatomicalSkeleton
            frames={frames}
            currentIndex={currentIndex}
            playing={playing}
            speed={speed}
            onFrameChange={handleFrameChange}
            phaseColor="#3B82F6"
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

        {/* Legend */}
        <div className="absolute top-3 left-3 rounded px-3 py-2 text-xs font-medium" style={{ backgroundColor: 'rgba(59,130,246,0.15)', color: '#60a5fa' }}>
          10MWT Gait Analysis
        </div>
      </div>

      {/* Controls */}
      <div className="p-4 space-y-3" style={{ backgroundColor: '#0d1117' }}>
        {/* Playback controls */}
        <div className="flex items-center gap-3">
          <button
            onClick={togglePlay}
            className="w-10 h-10 flex items-center justify-center rounded-full transition-colors"
            style={{ backgroundColor: '#3B82F6', color: '#ffffff' }}
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

          <input
            type="range"
            min={0}
            max={Math.max(0, frames.length - 1)}
            value={currentIndex}
            onChange={handleSliderChange}
            className="flex-1 h-2"
            style={{ accentColor: '#3B82F6' }}
            aria-label="타임라인"
          />

          <span className="text-sm w-24 text-right tabular-nums" style={{ color: '#5a8a9a' }}>
            {relativeTime.toFixed(1)}s / {totalDuration.toFixed(1)}s
          </span>
        </div>

        {/* Speed + Camera controls */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xs" style={{ color: '#5a7a8a' }}>속도:</span>
            {[0.5, 1, 2].map(s => (
              <button
                key={s}
                onClick={() => setSpeed(s)}
                className="px-2 py-1 text-xs rounded transition-colors"
                style={{
                  backgroundColor: speed === s ? '#3B82F6' : '#152030',
                  color: speed === s ? '#ffffff' : '#5a8a9a',
                }}
              >
                {s}x
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs" style={{ color: '#5a7a8a' }}>시점:</span>
            {([
              ['front', '정면'],
              ['side', '측면'],
              ['top', '상단'],
            ] as const).map(([key, label]) => (
              <button
                key={key}
                onClick={() => setViewPreset(key)}
                className="px-2 py-1 text-xs rounded transition-colors"
                style={{
                  backgroundColor: viewPreset === key ? '#3B82F6' : '#152030',
                  color: viewPreset === key ? '#ffffff' : '#5a8a9a',
                }}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Frame info */}
        <div className="text-xs text-center" style={{ color: '#3a5a6a' }}>
          프레임 {currentIndex + 1} / {frames.length} | 마우스 드래그로 회전, 스크롤로 확대/축소
        </div>
      </div>
    </div>
  );
}
