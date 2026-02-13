import { useRef, useEffect, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import type { Pose3DFrame } from '../../types';

// ═══════════════════════════════════════════════════════════
// Clinical Gait Analysis Visualization
// ═══════════════════════════════════════════════════════════

// Color palette
const COL_LEFT = new THREE.Color('#00e5b0');   // cyan-green (left)
const COL_RIGHT = new THREE.Color('#4fc3f7');  // medical blue (right)
const COL_TRUNK = new THREE.Color('#00c8d4');  // trunk/spine
const COL_JOINT = new THREE.Color('#ffffff');   // joints
const COL_ANGLE = new THREE.Color('#ff7043');   // angle arcs
const COL_REF = new THREE.Color('#ffffff');     // reference lines
const COL_TRAJ = new THREE.Color('#7c4dff');   // trajectory
const COL_COM = new THREE.Color('#ffab40');     // center of mass

// Shared materials
const matLeft = new THREE.MeshBasicMaterial({ color: COL_LEFT, transparent: true, opacity: 0.95 });
const matRight = new THREE.MeshBasicMaterial({ color: COL_RIGHT, transparent: true, opacity: 0.95 });
const matTrunk = new THREE.MeshBasicMaterial({ color: COL_TRUNK, transparent: true, opacity: 0.9 });
const matJoint = new THREE.MeshBasicMaterial({ color: COL_JOINT });
const matGlowLeft = new THREE.MeshBasicMaterial({ color: COL_LEFT, transparent: true, opacity: 0.12, blending: THREE.AdditiveBlending, depthWrite: false });
const matGlowRight = new THREE.MeshBasicMaterial({ color: COL_RIGHT, transparent: true, opacity: 0.12, blending: THREE.AdditiveBlending, depthWrite: false });
const matGlowTrunk = new THREE.MeshBasicMaterial({ color: COL_TRUNK, transparent: true, opacity: 0.1, blending: THREE.AdditiveBlending, depthWrite: false });
const matGlowJoint = new THREE.MeshBasicMaterial({ color: COL_JOINT, transparent: true, opacity: 0.2, blending: THREE.AdditiveBlending, depthWrite: false });
const matAngle = new THREE.MeshBasicMaterial({ color: COL_ANGLE, transparent: true, opacity: 0.6, side: THREE.DoubleSide });
const matAngleLine = new THREE.MeshBasicMaterial({ color: COL_ANGLE, transparent: true, opacity: 0.9 });
const matRef = new THREE.MeshBasicMaterial({ color: COL_REF, transparent: true, opacity: 0.15 });
const matTraj = new THREE.MeshBasicMaterial({ color: COL_TRAJ, transparent: true, opacity: 0.4, blending: THREE.AdditiveBlending, depthWrite: false });
const matCom = new THREE.MeshBasicMaterial({ color: COL_COM, transparent: true, opacity: 0.5 });

// ─── Helpers ───
function v(lm: number[]): THREE.Vector3 { return new THREE.Vector3(lm[0], -lm[1], -lm[2]); }
function midV(a: THREE.Vector3, b: THREE.Vector3): THREE.Vector3 { return new THREE.Vector3().addVectors(a, b).multiplyScalar(0.5); }
function lerpV(a: THREE.Vector3, b: THREE.Vector3, t: number): THREE.Vector3 { return new THREE.Vector3().lerpVectors(a, b, t); }

function angleBetween(a: THREE.Vector3, b: THREE.Vector3): number {
  const dot = a.dot(b) / (a.length() * b.length());
  return Math.acos(Math.max(-1, Math.min(1, dot)));
}

// ─── Tapered Bone (thick in middle, thin at ends) ───
function TaperedBone({ a, b, mat, glowMat, thickness = 0.006 }: {
  a: THREE.Vector3; b: THREE.Vector3; mat: THREE.Material; glowMat: THREE.Material; thickness?: number;
}) {
  const geo = useMemo(() => {
    const len = a.distanceTo(b);
    if (len < 0.001) return null;
    const t = thickness;
    // Tapered profile: thin at ends, wider at ~30-70%
    const profile: THREE.Vector2[] = [
      new THREE.Vector2(t * 0.3, 0),
      new THREE.Vector2(t * 0.5, len * 0.05),
      new THREE.Vector2(t * 0.85, len * 0.15),
      new THREE.Vector2(t * 1.0, len * 0.3),
      new THREE.Vector2(t * 1.0, len * 0.7),
      new THREE.Vector2(t * 0.85, len * 0.85),
      new THREE.Vector2(t * 0.5, len * 0.95),
      new THREE.Vector2(t * 0.3, len),
    ];
    return new THREE.LatheGeometry(profile, 8);
  }, [a, b, thickness]);

  const glowGeo = useMemo(() => {
    const len = a.distanceTo(b);
    if (len < 0.001) return null;
    const t = thickness * 2.5;
    const profile: THREE.Vector2[] = [
      new THREE.Vector2(t * 0.3, 0),
      new THREE.Vector2(t * 0.7, len * 0.15),
      new THREE.Vector2(t * 1.0, len * 0.35),
      new THREE.Vector2(t * 1.0, len * 0.65),
      new THREE.Vector2(t * 0.7, len * 0.85),
      new THREE.Vector2(t * 0.3, len),
    ];
    return new THREE.LatheGeometry(profile, 6);
  }, [a, b, thickness]);

  const q = useMemo(() => {
    const d = new THREE.Vector3().subVectors(b, a).normalize();
    return new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), d);
  }, [a, b]);

  useEffect(() => () => { geo?.dispose(); glowGeo?.dispose(); }, [geo, glowGeo]);
  if (!geo || !glowGeo) return null;

  return (
    <group>
      <mesh geometry={geo} position={a} quaternion={q} material={mat} />
      <mesh geometry={glowGeo} position={a} quaternion={q} material={glowMat} />
    </group>
  );
}

// ─── Joint Point (small diamond with glow) ───
function Joint({ pos, size = 0.007, isPrimary = false }: {
  pos: THREE.Vector3; size?: number; isPrimary?: boolean;
}) {
  return (
    <group position={pos}>
      {/* Core */}
      <mesh material={matJoint} rotation={[Math.PI / 4, 0, Math.PI / 4]}>
        <octahedronGeometry args={[size, 0]} />
      </mesh>
      {/* Glow halo */}
      <mesh material={matGlowJoint}>
        <sphereGeometry args={[size * (isPrimary ? 3.5 : 2.5), 12, 12]} />
      </mesh>
      {isPrimary && (
        <mesh material={matGlowJoint}>
          <ringGeometry args={[size * 2.0, size * 2.5, 16]} />
        </mesh>
      )}
    </group>
  );
}

// ─── Angle Arc ───
function AngleArc({ vertex, a, b, radius = 0.04 }: {
  vertex: THREE.Vector3; a: THREE.Vector3; b: THREE.Vector3; radius?: number;
}) {
  const data = useMemo(() => {
    const va = new THREE.Vector3().subVectors(a, vertex).normalize();
    const vb = new THREE.Vector3().subVectors(b, vertex).normalize();
    const angle = angleBetween(va, vb);
    const degrees = Math.round(angle * 180 / Math.PI);

    // Create arc geometry
    const normal = new THREE.Vector3().crossVectors(va, vb).normalize();
    if (normal.length() < 0.001) return null;

    const steps = 16;
    const pts: THREE.Vector3[] = [];
    for (let i = 0; i <= steps; i++) {
      const t = i / steps;
      const q = new THREE.Quaternion().setFromAxisAngle(normal, angle * t);
      const p = va.clone().applyQuaternion(q).multiplyScalar(radius).add(vertex);
      pts.push(p);
    }

    // Extension lines
    const lineA = [vertex.clone(), vertex.clone().add(va.clone().multiplyScalar(radius * 1.3))];
    const lineB = [vertex.clone(), vertex.clone().add(vb.clone().multiplyScalar(radius * 1.3))];

    // Label position
    const midDir = va.clone().add(vb).normalize();
    const labelPos = vertex.clone().add(midDir.multiplyScalar(radius * 1.6));

    return { pts, lineA, lineB, degrees, labelPos };
  }, [vertex, a, b, radius]);

  if (!data) return null;

  return (
    <group>
      {/* Arc curve */}
      <ArcLine points={data.pts} />
      {/* Extension lines */}
      <ThinLine a={data.lineA[0]} b={data.lineA[1]} mat={matAngleLine} />
      <ThinLine a={data.lineB[0]} b={data.lineB[1]} mat={matAngleLine} />
      {/* Degree indicator sphere */}
      <mesh position={data.labelPos} material={matAngle}>
        <sphereGeometry args={[0.006, 8, 8]} />
      </mesh>
    </group>
  );
}

function ArcLine({ points }: { points: THREE.Vector3[] }) {
  const geo = useMemo(() => {
    if (points.length < 2) return null;
    const curve = new THREE.CatmullRomCurve3(points);
    return new THREE.TubeGeometry(curve, 16, 0.002, 4, false);
  }, [points]);
  useEffect(() => () => { geo?.dispose(); }, [geo]);
  if (!geo) return null;
  return <mesh geometry={geo} material={matAngleLine} />;
}

function ThinLine({ a, b, mat, r = 0.001 }: { a: THREE.Vector3; b: THREE.Vector3; mat: THREE.Material; r?: number }) {
  const geo = useMemo(() => {
    const len = a.distanceTo(b);
    if (len < 0.0005) return null;
    return new THREE.CylinderGeometry(r, r, len, 4);
  }, [a, b, r]);
  const { pos, q } = useMemo(() => {
    const d = new THREE.Vector3().subVectors(b, a).normalize();
    return { pos: midV(a, b), q: new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), d) };
  }, [a, b]);
  useEffect(() => () => { geo?.dispose(); }, [geo]);
  if (!geo) return null;
  return <mesh geometry={geo} position={pos} quaternion={q} material={mat} />;
}

// ─── Spine Curve (smooth) ───
function SpineCurve({ points, mat, glowMat, r = 0.005 }: {
  points: THREE.Vector3[]; mat: THREE.Material; glowMat: THREE.Material; r?: number;
}) {
  const geo = useMemo(() => {
    if (points.length < 2) return null;
    return new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points), 20, r, 6, false);
  }, [points, r]);
  const glowGeo = useMemo(() => {
    if (points.length < 2) return null;
    return new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points), 16, r * 2.5, 6, false);
  }, [points, r]);
  useEffect(() => () => { geo?.dispose(); glowGeo?.dispose(); }, [geo, glowGeo]);
  if (!geo || !glowGeo) return null;
  return (
    <group>
      <mesh geometry={geo} material={mat} />
      <mesh geometry={glowGeo} material={glowMat} />
    </group>
  );
}

// ─── Trajectory Trail ───
function Trajectory({ frames, currentIndex, landmarkIdx, mat }: {
  frames: Pose3DFrame[]; currentIndex: number; landmarkIdx: number; mat: THREE.Material;
}) {
  const geo = useMemo(() => {
    const windowSize = 40;
    const start = Math.max(0, currentIndex - windowSize);
    const end = Math.min(frames.length, currentIndex + 1);
    // Get current frame bounding box center for centering
    const curLm = frames[currentIndex]?.landmarks;
    if (!curLm) return null;
    const curRaw = curLm.map(l => v(l));
    let mnX = Infinity, mxX = -Infinity, mnY = Infinity, mxY = -Infinity, mnZ = Infinity, mxZ = -Infinity;
    for (const pt of curRaw) {
      if (pt.x < mnX) mnX = pt.x; if (pt.x > mxX) mxX = pt.x;
      if (pt.y < mnY) mnY = pt.y; if (pt.y > mxY) mxY = pt.y;
      if (pt.z < mnZ) mnZ = pt.z; if (pt.z > mxZ) mxZ = pt.z;
    }
    const cx = (mnX + mxX) / 2, cy = (mnY + mxY) / 2, cz = (mnZ + mxZ) / 2;
    const pts: THREE.Vector3[] = [];
    for (let i = start; i < end; i += 2) {
      const lm = frames[i].landmarks;
      if (lm && lm[landmarkIdx]) {
        const pt = v(lm[landmarkIdx]);
        pts.push(new THREE.Vector3(pt.x - cx, pt.y - cy, pt.z - cz));
      }
    }
    if (pts.length < 2) return null;
    return new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), pts.length * 2, 0.003, 4, false);
  }, [frames, currentIndex, landmarkIdx]);
  useEffect(() => () => { geo?.dispose(); }, [geo]);
  if (!geo) return null;
  return <mesh geometry={geo} material={mat} />;
}

// ─── Vertical Reference Line ───
function VerticalRef({ top, groundY }: { top: THREE.Vector3; groundY: number }) {
  const segments = 20;
  return (
    <group>
      {Array.from({ length: segments }, (_, i) => {
        const t0 = i / segments;
        const t1 = (i + 0.4) / segments;
        const y0 = top.y + (groundY - top.y) * t0;
        const y1 = top.y + (groundY - top.y) * t1;
        return (
          <ThinLine key={i} a={new THREE.Vector3(top.x, y0, top.z)} b={new THREE.Vector3(top.x, y1, top.z)} mat={matRef} r={0.0008} />
        );
      })}
      {/* Ground projection marker */}
      <mesh position={new THREE.Vector3(top.x, groundY, top.z)} rotation={[-Math.PI / 2, 0, 0]} material={matRef}>
        <ringGeometry args={[0.01, 0.015, 16]} />
      </mesh>
    </group>
  );
}

// ─── Center of Mass indicator ───
function CoMIndicator({ pos, groundY }: { pos: THREE.Vector3; groundY: number }) {
  return (
    <group>
      <mesh position={pos} material={matCom}>
        <sphereGeometry args={[0.012, 12, 12]} />
      </mesh>
      <mesh position={pos} material={new THREE.MeshBasicMaterial({ color: COL_COM, transparent: true, opacity: 0.08, blending: THREE.AdditiveBlending, depthWrite: false })}>
        <sphereGeometry args={[0.03, 12, 12]} />
      </mesh>
      {/* Projection to ground */}
      <ThinLine a={pos} b={new THREE.Vector3(pos.x, groundY, pos.z)} mat={matCom} r={0.001} />
      <mesh position={new THREE.Vector3(pos.x, groundY, pos.z)} rotation={[-Math.PI / 2, 0, 0]} material={matCom}>
        <ringGeometry args={[0.008, 0.012, 8]} />
      </mesh>
    </group>
  );
}

// ═══════════════════════════════════════════════════════════
// Main Clinical Skeleton Visualization
// ═══════════════════════════════════════════════════════════
export function SkeletonBody({ frame, frames, currentIndex, phaseColor }: {
  frame: Pose3DFrame; frames?: Pose3DFrame[]; currentIndex?: number; phaseColor?: string;
}) {
  const lm = frame.landmarks;
  if (!lm || lm.length < 22) return null;

  // Phase-based dynamic materials
  const phaseMats = useMemo(() => {
    if (!phaseColor) return null;
    const base = new THREE.Color(phaseColor);
    const left = base.clone().lerp(new THREE.Color('#ffffff'), 0.15);
    const right = base.clone().lerp(new THREE.Color('#000000'), 0.1);
    const trunk = base.clone();
    return {
      left: new THREE.MeshBasicMaterial({ color: left, transparent: true, opacity: 0.95 }),
      right: new THREE.MeshBasicMaterial({ color: right, transparent: true, opacity: 0.95 }),
      trunk: new THREE.MeshBasicMaterial({ color: trunk, transparent: true, opacity: 0.9 }),
      glowLeft: new THREE.MeshBasicMaterial({ color: left, transparent: true, opacity: 0.12, blending: THREE.AdditiveBlending, depthWrite: false }),
      glowRight: new THREE.MeshBasicMaterial({ color: right, transparent: true, opacity: 0.12, blending: THREE.AdditiveBlending, depthWrite: false }),
      glowTrunk: new THREE.MeshBasicMaterial({ color: trunk, transparent: true, opacity: 0.1, blending: THREE.AdditiveBlending, depthWrite: false }),
    };
  }, [phaseColor]);

  const mL = phaseMats?.left ?? matLeft;
  const mR = phaseMats?.right ?? matRight;
  const mT = phaseMats?.trunk ?? matTrunk;
  const gL = phaseMats?.glowLeft ?? matGlowLeft;
  const gR = phaseMats?.glowRight ?? matGlowRight;
  const gT = phaseMats?.glowTrunk ?? matGlowTrunk;

  // Center skeleton: use bounding box center so it stays perfectly centered
  const p = useMemo(() => {
    const raw = lm.map(l => v(l));
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity, minZ = Infinity, maxZ = -Infinity;
    for (const pt of raw) {
      if (pt.x < minX) minX = pt.x; if (pt.x > maxX) maxX = pt.x;
      if (pt.y < minY) minY = pt.y; if (pt.y > maxY) maxY = pt.y;
      if (pt.z < minZ) minZ = pt.z; if (pt.z > maxZ) maxZ = pt.z;
    }
    const cx = (minX + maxX) / 2, cy = (minY + maxY) / 2, cz = (minZ + maxZ) / 2;
    return raw.map(pt => new THREE.Vector3(pt.x - cx, pt.y - cy, pt.z - cz));
  }, [lm]);
  const neck = useMemo(() => midV(p[0], p[1]), [p]);
  const hipCenter = useMemo(() => midV(p[12], p[13]), [p]);

  const { up, fwd } = useMemo(() => {
    const r = new THREE.Vector3().subVectors(p[1], p[0]);
    if (r.length() < 0.001) r.set(1, 0, 0); r.normalize();
    const u = new THREE.Vector3().subVectors(neck, hipCenter);
    if (u.length() < 0.001) u.set(0, 1, 0); u.normalize();
    const f = new THREE.Vector3().crossVectors(u, r);
    if (f.length() < 0.001) f.set(0, 0, -1); f.normalize();
    return { up: u, fwd: f };
  }, [p, neck, hipCenter]);

  const sw = useMemo(() => p[0].distanceTo(p[1]), [p]);

  // Head position
  const head = useMemo(() => neck.clone().addScaledVector(up, Math.max(sw * 0.55, 0.12)), [neck, sw, up]);

  // Approximate CoM (weighted center: ~55% from feet toward head)
  const com = useMemo(() => lerpV(hipCenter, neck, 0.15), [hipCenter, neck]);

  // Ground level (lowest ankle)
  const groundY = useMemo(() => Math.max(p[16].y, p[17].y) + 0.03, [p]);

  // Spine curve points
  const spinePts = useMemo(() => [
    head.clone().addScaledVector(up, -0.05),
    neck.clone().addScaledVector(fwd, 0.004),
    lerpV(neck, hipCenter, 0.4).addScaledVector(fwd, -0.006),
    lerpV(neck, hipCenter, 0.75).addScaledVector(fwd, 0.004),
    hipCenter.clone(),
  ], [head, neck, hipCenter, up, fwd]);

  // Thickness ratios
  const TH = { hip: 0.018, knee: 0.016, ankle: 0.013, shoulder: 0.015, elbow: 0.011, wrist: 0.009, finger: 0.006 };

  return (
    <group>
      {/* ═══ HEAD ═══ */}
      <mesh position={head} material={mT}>
        <sphereGeometry args={[0.07, 20, 16]} />
      </mesh>
      <mesh position={head} material={gT}>
        <sphereGeometry args={[0.095, 16, 12]} />
      </mesh>

      {/* ═══ SPINE ═══ */}
      <SpineCurve points={spinePts} mat={mT} glowMat={gT} r={0.011} />

      {/* ═══ SHOULDER LINE ═══ */}
      <TaperedBone a={p[0]} b={p[1]} mat={mT} glowMat={gT} thickness={0.01} />

      {/* ═══ HIP LINE ═══ */}
      <TaperedBone a={p[12]} b={p[13]} mat={mT} glowMat={gT} thickness={0.01} />

      {/* ═══ LEFT SIDE (brighter) ═══ */}
      {/* Left arm */}
      <TaperedBone a={p[0]} b={p[2]} mat={mL} glowMat={gL} thickness={TH.shoulder} />
      <TaperedBone a={p[2]} b={p[4]} mat={mL} glowMat={gL} thickness={TH.elbow} />
      {/* Left hand rays */}
      {[6, 8, 10].map(i => lm[i] && (
        <TaperedBone key={`lh-${i}`} a={p[4]} b={p[i]} mat={mL} glowMat={gL} thickness={TH.finger} />
      ))}
      {/* Left leg */}
      <TaperedBone a={p[12]} b={p[14]} mat={mL} glowMat={gL} thickness={TH.hip} />
      <TaperedBone a={p[14]} b={p[16]} mat={mL} glowMat={gL} thickness={TH.knee} />
      {/* Left foot */}
      <TaperedBone a={p[16]} b={p[18]} mat={mL} glowMat={gL} thickness={TH.ankle} />
      <TaperedBone a={p[18]} b={p[20]} mat={mL} glowMat={gL} thickness={TH.finger} />
      <TaperedBone a={p[16]} b={p[20]} mat={mL} glowMat={gL} thickness={TH.finger} />

      {/* ═══ RIGHT SIDE (slightly darker) ═══ */}
      {/* Right arm */}
      <TaperedBone a={p[1]} b={p[3]} mat={mR} glowMat={gR} thickness={TH.shoulder} />
      <TaperedBone a={p[3]} b={p[5]} mat={mR} glowMat={gR} thickness={TH.elbow} />
      {/* Right hand rays */}
      {[7, 9, 11].map(i => lm[i] && (
        <TaperedBone key={`rh-${i}`} a={p[5]} b={p[i]} mat={mR} glowMat={gR} thickness={TH.finger} />
      ))}
      {/* Right leg */}
      <TaperedBone a={p[13]} b={p[15]} mat={mR} glowMat={gR} thickness={TH.hip} />
      <TaperedBone a={p[15]} b={p[17]} mat={mR} glowMat={gR} thickness={TH.knee} />
      {/* Right foot */}
      <TaperedBone a={p[17]} b={p[19]} mat={mR} glowMat={gR} thickness={TH.ankle} />
      <TaperedBone a={p[19]} b={p[21]} mat={mR} glowMat={gR} thickness={TH.finger} />
      <TaperedBone a={p[17]} b={p[21]} mat={mR} glowMat={gR} thickness={TH.finger} />

      {/* ═══ JOINTS ═══ */}
      {/* Primary joints (larger) */}
      <Joint pos={p[0]} size={0.008} isPrimary />
      <Joint pos={p[1]} size={0.008} isPrimary />
      <Joint pos={p[12]} size={0.009} isPrimary />
      <Joint pos={p[13]} size={0.009} isPrimary />
      {/* Secondary joints */}
      <Joint pos={p[2]} size={0.006} />
      <Joint pos={p[3]} size={0.006} />
      <Joint pos={p[4]} size={0.005} />
      <Joint pos={p[5]} size={0.005} />
      <Joint pos={p[14]} size={0.008} />
      <Joint pos={p[15]} size={0.008} />
      <Joint pos={p[16]} size={0.006} />
      <Joint pos={p[17]} size={0.006} />
      {/* Neck */}
      <Joint pos={neck} size={0.006} />
      {/* Hip center */}
      <Joint pos={hipCenter} size={0.007} isPrimary />

      {/* ═══ JOINT ANGLES ═══ */}
      {/* Left knee flexion */}
      <AngleArc vertex={p[14]} a={p[12]} b={p[16]} radius={0.05} />
      {/* Right knee flexion */}
      <AngleArc vertex={p[15]} a={p[13]} b={p[17]} radius={0.05} />
      {/* Left hip flexion */}
      <AngleArc vertex={p[12]} a={neck} b={p[14]} radius={0.045} />
      {/* Right hip flexion */}
      <AngleArc vertex={p[13]} a={neck} b={p[15]} radius={0.045} />

      {/* ═══ VERTICAL REFERENCE LINE ═══ */}
      <VerticalRef top={head.clone().addScaledVector(up, 0.05)} groundY={groundY} />

      {/* ═══ CENTER OF MASS ═══ */}
      <CoMIndicator pos={com} groundY={groundY} />

      {/* ═══ ANKLE TRAJECTORY ═══ */}
      {frames && currentIndex != null && (
        <>
          <Trajectory frames={frames} currentIndex={currentIndex} landmarkIdx={16} mat={matTraj} />
          <Trajectory frames={frames} currentIndex={currentIndex} landmarkIdx={17} mat={new THREE.MeshBasicMaterial({ color: '#b388ff', transparent: true, opacity: 0.35, blending: THREE.AdditiveBlending, depthWrite: false })} />
        </>
      )}
    </group>
  );
}

// ═══════════════════════════════════════════════════════════
// Animated wrapper
// ═══════════════════════════════════════════════════════════
export function AnimatedAnatomicalSkeleton({
  frames, currentIndex, playing, speed, onFrameChange, phaseColor,
}: {
  frames: Pose3DFrame[];
  currentIndex: number;
  playing: boolean;
  speed: number;
  onFrameChange: (idx: number) => void;
  phaseColor?: string;
}) {
  const timeRef = useRef(0);
  const lastIdxRef = useRef(currentIndex);
  useEffect(() => { lastIdxRef.current = currentIndex; }, [currentIndex]);

  useFrame((_, delta) => {
    if (!playing || frames.length === 0) return;
    timeRef.current += delta * speed;
    const dur = frames.length > 1 ? frames[frames.length - 1].time - frames[0].time : 1;
    const elapsed = timeRef.current % dur;
    const target = frames[0].time + elapsed;
    let idx = 0;
    for (let i = 0; i < frames.length; i++) {
      if (frames[i].time <= target) idx = i; else break;
    }
    if (idx !== lastIdxRef.current) {
      lastIdxRef.current = idx;
      onFrameChange(idx);
    }
  });

  if (frames.length === 0) return null;
  return <SkeletonBody frame={frames[currentIndex]} frames={frames} currentIndex={currentIndex} phaseColor={phaseColor} />;
}
