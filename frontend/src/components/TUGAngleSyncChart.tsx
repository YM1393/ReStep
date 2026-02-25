import { forwardRef, useImperativeHandle, useRef, useMemo } from 'react';
import type { AngleDataPoint } from '../types';

export interface TUGAngleSyncChartHandle {
  updateTime: (time: number) => void;
}

interface TUGAngleSyncChartProps {
  angleData: AngleDataPoint[];
}

const svgW = 340, svgH = 130;
const padL = 30, padR = 10, padT = 15, padB = 22;
const plotW = svgW - padL - padR;
const plotH = svgH - padT - padB;
const maxDeg = 15;

function clamp(v: number, min: number, max: number) {
  return v < min ? min : v > max ? max : v;
}

function toY(deg: number) {
  return padT + plotH / 2 - (clamp(deg, -maxDeg, maxDeg) / maxDeg) * (plotH / 2);
}

const TUGAngleSyncChart = forwardRef<TUGAngleSyncChartHandle, TUGAngleSyncChartProps>(
  ({ angleData }, ref) => {
    const cursorRef = useRef<SVGLineElement>(null);
    const dotShoulderRef = useRef<SVGCircleElement>(null);
    const dotHipRef = useRef<SVGCircleElement>(null);
    const shoulderValRef = useRef<HTMLSpanElement>(null);
    const hipValRef = useRef<HTMLSpanElement>(null);

    const { shoulderPath, hipPath, t0, tEnd } = useMemo(() => {
      if (!angleData.length) return { shoulderPath: '', hipPath: '', t0: 0, tEnd: 0 };

      const t0 = angleData[0].time;
      const tEnd = angleData[angleData.length - 1].time;
      const timeRange = tEnd - t0 || 1;

      // subsample if too many points
      const step = angleData.length > 200 ? Math.floor(angleData.length / 200) : 1;

      let sp = '';
      let hp = '';
      for (let i = 0; i < angleData.length; i += step) {
        const p = angleData[i];
        const x = padL + ((p.time - t0) / timeRange) * plotW;
        const sy = toY(p.shoulder_tilt);
        const hy = toY(p.hip_tilt);
        const cmd = i === 0 ? 'M' : 'L';
        sp += `${cmd}${x.toFixed(1)},${sy.toFixed(1)}`;
        hp += `${cmd}${x.toFixed(1)},${hy.toFixed(1)}`;
      }

      // always include last point
      if (step > 1) {
        const last = angleData[angleData.length - 1];
        const x = padL + ((last.time - t0) / timeRange) * plotW;
        sp += `L${x.toFixed(1)},${toY(last.shoulder_tilt).toFixed(1)}`;
        hp += `L${x.toFixed(1)},${toY(last.hip_tilt).toFixed(1)}`;
      }

      return { shoulderPath: sp, hipPath: hp, t0, tEnd };
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

        const sy = toY(pt.shoulder_tilt);
        const hy = toY(pt.hip_tilt);
        dotShoulderRef.current?.setAttribute('cx', String(cx));
        dotShoulderRef.current?.setAttribute('cy', String(sy));
        dotHipRef.current?.setAttribute('cx', String(cx));
        dotHipRef.current?.setAttribute('cy', String(hy));

        if (shoulderValRef.current) shoulderValRef.current.textContent = `${pt.shoulder_tilt.toFixed(1)}°`;
        if (hipValRef.current) hipValRef.current.textContent = `${pt.hip_tilt.toFixed(1)}°`;
      }
    }), [angleData, t0, tEnd]);

    if (!angleData.length) return null;

    const centerY = padT + plotH / 2;
    const warn5Y = toY(5);
    const warnN5Y = toY(-5);

    return (
      <div>
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 flex items-center">
          <svg className="w-4 h-4 mr-1.5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          어깨/골반 기울기 (정면 영상)
        </p>
        <div className="flex items-center gap-4 mb-1 text-xs">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 bg-blue-500 rounded-full inline-block" />
            <span className="text-gray-600 dark:text-gray-400">어깨</span>
            <span ref={shoulderValRef} className="font-mono font-bold text-blue-600 dark:text-blue-400 ml-0.5">--</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 bg-emerald-500 rounded-full inline-block" />
            <span className="text-gray-600 dark:text-gray-400">골반</span>
            <span ref={hipValRef} className="font-mono font-bold text-emerald-600 dark:text-emerald-400 ml-0.5">--</span>
          </span>
        </div>
        <svg viewBox={`0 0 ${svgW} ${svgH}`} className="w-full" style={{ height: 110 }}>
          {/* Background */}
          <rect x={padL} y={padT} width={plotW} height={plotH} rx="2" fill="currentColor" className="text-gray-50 dark:text-gray-600/30" />
          {/* 0° center line */}
          <line x1={padL} y1={centerY} x2={padL + plotW} y2={centerY}
            stroke="currentColor" strokeWidth="1" className="text-gray-300 dark:text-gray-500" strokeDasharray="6,3" />
          {/* ±5° warning lines */}
          <line x1={padL} y1={warn5Y} x2={padL + plotW} y2={warn5Y}
            stroke="currentColor" strokeWidth="0.5" className="text-amber-300 dark:text-amber-700" strokeDasharray="3,3" />
          <line x1={padL} y1={warnN5Y} x2={padL + plotW} y2={warnN5Y}
            stroke="currentColor" strokeWidth="0.5" className="text-amber-300 dark:text-amber-700" strokeDasharray="3,3" />
          {/* Shoulder path */}
          <path d={shoulderPath} fill="none" stroke="#3b82f6" strokeWidth="1.5" strokeLinejoin="round" />
          {/* Hip path */}
          <path d={hipPath} fill="none" stroke="#10b981" strokeWidth="1.5" strokeLinejoin="round" />
          {/* Cursor line */}
          <line ref={cursorRef} x1={padL} y1={padT} x2={padL} y2={padT + plotH}
            stroke="#ef4444" strokeWidth="1.5" opacity="0.8" />
          {/* Tracking dots */}
          <circle ref={dotShoulderRef} r="3.5" fill="#3b82f6" cx={padL} cy={centerY} />
          <circle ref={dotHipRef} r="3.5" fill="#10b981" cx={padL} cy={centerY} />
          {/* Y-axis labels */}
          <text x={padL - 3} y={padT + 4} textAnchor="end" className="text-[8px] fill-gray-400">+{maxDeg}°</text>
          <text x={padL - 3} y={centerY + 3} textAnchor="end" className="text-[8px] fill-gray-400">0°</text>
          <text x={padL - 3} y={padT + plotH + 3} textAnchor="end" className="text-[8px] fill-gray-400">-{maxDeg}°</text>
          {/* ±5° labels */}
          <text x={padL + plotW + 2} y={warn5Y + 3} textAnchor="start" className="text-[7px] fill-amber-400">5°</text>
          <text x={padL + plotW + 2} y={warnN5Y + 3} textAnchor="start" className="text-[7px] fill-amber-400">-5°</text>
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

TUGAngleSyncChart.displayName = 'TUGAngleSyncChart';
export default TUGAngleSyncChart;
