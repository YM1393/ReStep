import { forwardRef, useImperativeHandle, useRef, useMemo } from 'react';
import type { SideAngleDataPoint } from '../types';

export interface TUGSideAngleSyncChartHandle {
  updateTime: (time: number) => void;
}

interface TUGSideAngleSyncChartProps {
  angleData: SideAngleDataPoint[];
}

const svgW = 340, svgH = 130;
const padL = 36, padR = 10, padT = 15, padB = 22;
const plotW = svgW - padL - padR;
const plotH = svgH - padT - padB;
const minDeg = 60, maxDeg = 180;
const range = maxDeg - minDeg;

function clamp(v: number, min: number, max: number) {
  return v < min ? min : v > max ? max : v;
}

// Higher angle (180° = straight) maps to lower Y (top)
function toY(deg: number) {
  return padT + plotH - ((clamp(deg, minDeg, maxDeg) - minDeg) / range) * plotH;
}

const TUGSideAngleSyncChart = forwardRef<TUGSideAngleSyncChartHandle, TUGSideAngleSyncChartProps>(
  ({ angleData }, ref) => {
    const cursorRef = useRef<SVGLineElement>(null);
    const dotKneeRef = useRef<SVGCircleElement>(null);
    const dotHipRef = useRef<SVGCircleElement>(null);
    const kneeValRef = useRef<HTMLSpanElement>(null);
    const hipValRef = useRef<HTMLSpanElement>(null);

    const { kneePath, hipPath, t0, tEnd } = useMemo(() => {
      if (!angleData.length) return { kneePath: '', hipPath: '', t0: 0, tEnd: 0 };

      const t0 = angleData[0].time;
      const tEnd = angleData[angleData.length - 1].time;
      const timeRange = tEnd - t0 || 1;

      const step = angleData.length > 200 ? Math.floor(angleData.length / 200) : 1;

      let kp = '';
      let hp = '';
      for (let i = 0; i < angleData.length; i += step) {
        const p = angleData[i];
        const x = padL + ((p.time - t0) / timeRange) * plotW;
        const ky = toY(p.knee_angle);
        const hy = toY(p.hip_angle);
        const cmd = i === 0 ? 'M' : 'L';
        kp += `${cmd}${x.toFixed(1)},${ky.toFixed(1)}`;
        hp += `${cmd}${x.toFixed(1)},${hy.toFixed(1)}`;
      }

      if (step > 1) {
        const last = angleData[angleData.length - 1];
        const x = padL + ((last.time - t0) / timeRange) * plotW;
        kp += `L${x.toFixed(1)},${toY(last.knee_angle).toFixed(1)}`;
        hp += `L${x.toFixed(1)},${toY(last.hip_angle).toFixed(1)}`;
      }

      return { kneePath: kp, hipPath: hp, t0, tEnd };
    }, [angleData]);

    useImperativeHandle(ref, () => ({
      updateTime(t: number) {
        if (!angleData.length || !cursorRef.current) return;
        const timeRange = tEnd - t0 || 1;
        const x = padL + ((t - t0) / timeRange) * plotW;
        const cx = Math.max(padL, Math.min(padL + plotW, x));

        cursorRef.current.setAttribute('x1', String(cx));
        cursorRef.current.setAttribute('x2', String(cx));

        // binary search
        let lo = 0, hi = angleData.length - 1;
        while (lo < hi) {
          const mid = (lo + hi) >> 1;
          if (angleData[mid].time < t) lo = mid + 1;
          else hi = mid;
        }
        const idx = lo > 0 && Math.abs(angleData[lo - 1].time - t) < Math.abs(angleData[lo].time - t) ? lo - 1 : lo;
        const pt = angleData[idx];

        const ky = toY(pt.knee_angle);
        const hy = toY(pt.hip_angle);
        dotKneeRef.current?.setAttribute('cx', String(cx));
        dotKneeRef.current?.setAttribute('cy', String(ky));
        dotHipRef.current?.setAttribute('cx', String(cx));
        dotHipRef.current?.setAttribute('cy', String(hy));

        if (kneeValRef.current) kneeValRef.current.textContent = `${pt.knee_angle.toFixed(0)}°`;
        if (hipValRef.current) hipValRef.current.textContent = `${pt.hip_angle.toFixed(0)}°`;
      }
    }), [angleData, t0, tEnd]);

    if (!angleData.length) return null;

    const y90 = toY(90);
    const y120 = toY(120);
    const y180 = toY(180);

    return (
      <div>
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 flex items-center">
          <svg className="w-4 h-4 mr-1.5 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          무릎/골반 관절 각도 (측면 영상)
        </p>
        <div className="flex items-center gap-4 mb-1 text-xs">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 bg-blue-500 rounded-full inline-block" />
            <span className="text-gray-600 dark:text-gray-400">무릎</span>
            <span ref={kneeValRef} className="font-mono font-bold text-blue-600 dark:text-blue-400 ml-0.5">--</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 bg-orange-500 rounded-full inline-block" />
            <span className="text-gray-600 dark:text-gray-400">골반</span>
            <span ref={hipValRef} className="font-mono font-bold text-orange-600 dark:text-orange-400 ml-0.5">--</span>
          </span>
        </div>
        <svg viewBox={`0 0 ${svgW} ${svgH}`} className="w-full" style={{ height: 110 }}>
          {/* Background */}
          <rect x={padL} y={padT} width={plotW} height={plotH} rx="2" fill="currentColor" className="text-gray-50 dark:text-gray-600/30" />
          {/* 180° line (full extension) */}
          <line x1={padL} y1={y180} x2={padL + plotW} y2={y180}
            stroke="currentColor" strokeWidth="0.5" className="text-green-300 dark:text-green-700" strokeDasharray="3,3" />
          {/* 120° line */}
          <line x1={padL} y1={y120} x2={padL + plotW} y2={y120}
            stroke="currentColor" strokeWidth="0.5" className="text-gray-200 dark:text-gray-600" strokeDasharray="3,3" />
          {/* 90° reference line (right angle) */}
          <line x1={padL} y1={y90} x2={padL + plotW} y2={y90}
            stroke="currentColor" strokeWidth="1" className="text-amber-300 dark:text-amber-600" strokeDasharray="6,3" />
          {/* Knee path */}
          <path d={kneePath} fill="none" stroke="#3b82f6" strokeWidth="1.5" strokeLinejoin="round" />
          {/* Hip path */}
          <path d={hipPath} fill="none" stroke="#f97316" strokeWidth="1.5" strokeLinejoin="round" />
          {/* Cursor line */}
          <line ref={cursorRef} x1={padL} y1={padT} x2={padL} y2={padT + plotH}
            stroke="#ef4444" strokeWidth="1.5" opacity="0.8" />
          {/* Tracking dots */}
          <circle ref={dotKneeRef} r="3.5" fill="#3b82f6" cx={padL} cy={y180} />
          <circle ref={dotHipRef} r="3.5" fill="#f97316" cx={padL} cy={y180} />
          {/* Y-axis labels */}
          <text x={padL - 3} y={y180 + 3} textAnchor="end" className="text-[8px] fill-gray-400">180°</text>
          <text x={padL - 3} y={y120 + 3} textAnchor="end" className="text-[8px] fill-gray-400">120°</text>
          <text x={padL - 3} y={y90 + 3} textAnchor="end" className="text-[8px] fill-gray-400">90°</text>
          <text x={padL - 3} y={padT + plotH + 3} textAnchor="end" className="text-[8px] fill-gray-400">{minDeg}°</text>
        </svg>
        <div className="flex justify-between text-[10px] text-gray-400 mt-0.5" style={{ paddingLeft: padL, paddingRight: padR }}>
          <span>0s</span>
          <span>시간</span>
          <span>{(tEnd - t0).toFixed(1)}s</span>
        </div>
      </div>
    );
  }
);

TUGSideAngleSyncChart.displayName = 'TUGSideAngleSyncChart';
export default TUGSideAngleSyncChart;
