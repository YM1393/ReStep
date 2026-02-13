/**
 * 실시간 TUG 검사 WebSocket 훅
 * - /ws/tug-realtime/{clientId} 엔드포인트와 통신
 * - 랜드마크 전송, 단계 감지 결과 수신
 */
import { useRef, useState, useCallback, useEffect } from 'react';
import type { NormalizedLandmark, Landmark } from '@mediapipe/tasks-vision';
import type { RealtimeTUGTestResult } from '../types';

interface TUGRealtimeState {
  currentPhase: string;
  phaseLabel: string;
  elapsedTime: number;
  legAngle: number;
  hipHeight: number;
  transitions: Array<{ phase: string; start: number; end?: number }>;
  isTestRunning: boolean;
  testResult: RealtimeTUGTestResult | null;
}

interface UseTUGRealtimeWSOptions {
  patientId: string;
  userId: string;
  enabled: boolean;
}

const INITIAL_STATE: TUGRealtimeState = {
  currentPhase: 'unknown',
  phaseLabel: '-',
  elapsedTime: 0,
  legAngle: 0,
  hipHeight: 0,
  transitions: [],
  isTestRunning: false,
  testResult: null,
};

export function useTUGRealtimeWebSocket({ patientId, userId, enabled }: UseTUGRealtimeWSOptions) {
  const [state, setState] = useState<TUGRealtimeState>(INITIAL_STATE);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const lastSendRef = useRef(0);
  const clientIdRef = useRef(`tug-rt-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`);

  // WebSocket 연결
  useEffect(() => {
    if (!enabled) return;

    const apiBase = import.meta.env.VITE_API_URL as string;
    let url: string;
    if (apiBase) {
      // Production: use backend URL (e.g. https://xxx.ngrok-free.dev -> wss://xxx.ngrok-free.dev)
      const wsBase = apiBase.replace(/^http/, 'ws');
      url = `${wsBase}/ws/tug-realtime/${clientIdRef.current}`;
    } else {
      // Dev: same host
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      url = `${protocol}//${window.location.host}/ws/tug-realtime/${clientIdRef.current}`;
    }

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setError(null);
      console.log('[TUG WS] Connected');
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        handleMessage(msg);
      } catch {
        // 파싱 에러 무시
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      console.log('[TUG WS] Disconnected');
    };

    ws.onerror = () => {
      setError('WebSocket 연결 오류');
    };

    // 핑 간격
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 15000);

    return () => {
      clearInterval(pingInterval);
      ws.close();
      wsRef.current = null;
    };
  }, [enabled]);

  const handleMessage = useCallback((msg: Record<string, unknown>) => {
    const type = msg.type as string;

    if (type === 'test_started') {
      setState(prev => ({ ...prev, isTestRunning: true }));
    } else if (type === 'phase_update') {
      setState(prev => ({
        ...prev,
        currentPhase: msg.current_phase as string || prev.currentPhase,
        phaseLabel: msg.phase_label as string || prev.phaseLabel,
        elapsedTime: msg.elapsed_time as number ?? prev.elapsedTime,
        legAngle: msg.leg_angle as number ?? prev.legAngle,
        hipHeight: msg.hip_height as number ?? prev.hipHeight,
      }));
    } else if (type === 'phase_transition') {
      setState(prev => ({
        ...prev,
        currentPhase: msg.current_phase as string || prev.currentPhase,
        phaseLabel: msg.phase_label as string || prev.phaseLabel,
        elapsedTime: msg.elapsed_time as number ?? prev.elapsedTime,
        transitions: (msg.transitions as TUGRealtimeState['transitions']) || prev.transitions,
      }));
    } else if (type === 'test_completed') {
      setState(prev => ({
        ...prev,
        isTestRunning: false,
        testResult: msg as unknown as RealtimeTUGTestResult,
      }));
    }
  }, []);

  const startTest = useCallback(() => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    ws.send(JSON.stringify({
      type: 'start_test',
      patient_id: patientId,
      user_id: userId,
    }));

    setState({ ...INITIAL_STATE, isTestRunning: true });
  }, [patientId, userId]);

  const stopTest = useCallback(() => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    ws.send(JSON.stringify({ type: 'stop_test' }));
  }, []);

  const sendFrame = useCallback((
    lms: NormalizedLandmark[],
    timestamp: number,
    worldLms?: Landmark[] | null,
  ) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    // 쓰로틀링: 최대 20fps
    const now = performance.now();
    if (now - lastSendRef.current < 50) return;
    lastSendRef.current = now;

    const payload: Record<string, unknown> = {
      type: 'frame_data',
      timestamp,
      landmarks: lms.map(l => [l.x, l.y, l.z]),
    };

    if (worldLms) {
      payload.world_landmarks = worldLms.map(l => [l.x, l.y, l.z]);
    }

    ws.send(JSON.stringify(payload));
  }, []);

  return { state, startTest, stopTest, sendFrame, isConnected, error };
}
