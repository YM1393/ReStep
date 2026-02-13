import { useRef, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import type { Pose3DFrame } from '../../types';

// Body landmark indices 11-32 mapped to 0-21 (our array indices)
// 11: left_shoulder, 12: right_shoulder, 13: left_elbow, 14: right_elbow,
// 15: left_wrist, 16: right_wrist, 17: left_pinky, 18: right_pinky,
// 19: left_index, 20: right_index, 21: left_thumb, 22: right_thumb,
// 23: left_hip, 24: right_hip, 25: left_knee, 26: right_knee,
// 27: left_ankle, 28: right_ankle, 29: left_heel, 30: right_heel,
// 31: left_foot_index, 32: right_foot_index

export const BONE_CONNECTIONS: [number, number][] = [
  // Torso
  [0, 1],   // left_shoulder - right_shoulder
  [0, 12],  // left_shoulder - left_hip
  [1, 13],  // right_shoulder - right_hip
  [12, 13], // left_hip - right_hip
  // Left arm
  [0, 2],   // left_shoulder - left_elbow
  [2, 4],   // left_elbow - left_wrist
  // Right arm
  [1, 3],   // right_shoulder - right_elbow
  [3, 5],   // right_elbow - right_wrist
  // Left leg
  [12, 14], // left_hip - left_knee
  [14, 16], // left_knee - left_ankle
  [16, 18], // left_ankle - left_heel
  [16, 20], // left_ankle - left_foot_index
  // Right leg
  [13, 15], // right_hip - right_knee
  [15, 17], // right_knee - right_ankle
  [17, 19], // right_ankle - right_heel
  [17, 21], // right_ankle - right_foot_index
];

// Left side indices (0-indexed from our 11-32 mapping)
export const LEFT_INDICES = new Set([0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20]);
export const RIGHT_INDICES = new Set([1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21]);

export const LEFT_COLOR = '#3B82F6';   // blue
export const RIGHT_COLOR = '#F97316';  // orange
export const TORSO_COLOR = '#8B5CF6';  // purple

export function getBoneColor(i1: number, i2: number): string {
  if (LEFT_INDICES.has(i1) && LEFT_INDICES.has(i2)) return LEFT_COLOR;
  if (RIGHT_INDICES.has(i1) && RIGHT_INDICES.has(i2)) return RIGHT_COLOR;
  return TORSO_COLOR;
}

export function getJointColor(idx: number): string {
  if (LEFT_INDICES.has(idx)) return LEFT_COLOR;
  if (RIGHT_INDICES.has(idx)) return RIGHT_COLOR;
  return TORSO_COLOR;
}

interface SkeletonProps {
  frame: Pose3DFrame;
}

export function Skeleton({ frame }: SkeletonProps) {
  const landmarks = frame.landmarks;

  return (
    <group>
      {/* Joints */}
      {landmarks.map((lm, idx) => (
        <mesh key={idx} position={[lm[0], -lm[1], -lm[2]]}>
          <sphereGeometry args={[0.015, 8, 8]} />
          <meshStandardMaterial color={getJointColor(idx)} />
        </mesh>
      ))}

      {/* Bones */}
      {BONE_CONNECTIONS.map(([i1, i2], idx) => {
        if (i1 >= landmarks.length || i2 >= landmarks.length) return null;
        const p1 = new THREE.Vector3(landmarks[i1][0], -landmarks[i1][1], -landmarks[i1][2]);
        const p2 = new THREE.Vector3(landmarks[i2][0], -landmarks[i2][1], -landmarks[i2][2]);
        const mid = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5);
        const dir = new THREE.Vector3().subVectors(p2, p1);
        const length = dir.length();
        dir.normalize();

        const quaternion = new THREE.Quaternion();
        quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);

        return (
          <mesh key={idx} position={mid} quaternion={quaternion}>
            <cylinderGeometry args={[0.008, 0.008, length, 6]} />
            <meshStandardMaterial color={getBoneColor(i1, i2)} />
          </mesh>
        );
      })}
    </group>
  );
}

interface AnimatedSkeletonProps {
  frames: Pose3DFrame[];
  currentIndex: number;
  playing: boolean;
  speed: number;
  onFrameChange: (idx: number) => void;
}

export function AnimatedSkeleton({ frames, currentIndex, playing, speed, onFrameChange }: AnimatedSkeletonProps) {
  const timeRef = useRef(0);
  const lastIdxRef = useRef(currentIndex);

  useEffect(() => {
    lastIdxRef.current = currentIndex;
  }, [currentIndex]);

  useFrame((_, delta) => {
    if (!playing || frames.length === 0) return;
    timeRef.current += delta * speed;
    const frameDuration = frames.length > 1 ? (frames[frames.length - 1].time - frames[0].time) : 1;
    const elapsed = timeRef.current % frameDuration;
    const targetTime = frames[0].time + elapsed;

    let newIdx = 0;
    for (let i = 0; i < frames.length; i++) {
      if (frames[i].time <= targetTime) newIdx = i;
      else break;
    }

    if (newIdx !== lastIdxRef.current) {
      lastIdxRef.current = newIdx;
      onFrameChange(newIdx);
    }
  });

  if (frames.length === 0) return null;
  return <Skeleton frame={frames[currentIndex]} />;
}
