import { useState, useEffect } from 'react';
import { distanceGoalApi } from '../services/api';
import type { DistanceGoal } from '../services/api';

interface GoalProgressProps {
  patientId: string;
  speedMps: number;
  onSetGoal: () => void;
}

const EMOJI_PRESETS = ['🏪', '🏫', '🌳', '🏥', '🛒', '🚌', '🏠', '⛪', '🏢', '🚶', '🚗', '☕'];

function formatTime(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}초`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  if (secs === 0) return `${mins}분`;
  return `${mins}분 ${secs}초`;
}

function formatDistance(meters: number): string {
  if (meters >= 1000) return `${(meters / 1000).toFixed(meters % 1000 === 0 ? 0 : 1)}km`;
  return `${meters}m`;
}

export default function GoalProgressCard({ patientId, speedMps }: GoalProgressProps) {
  const [goals, setGoals] = useState<DistanceGoal[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formEmoji, setFormEmoji] = useState('🏪');
  const [formLabel, setFormLabel] = useState('');
  const [formDistance, setFormDistance] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadGoals();
  }, [patientId]);

  const loadGoals = async () => {
    try {
      const data = await distanceGoalApi.getAll(patientId);
      setGoals(data);
    } catch { /* ignore */ }
    setLoading(false);
  };

  const handleAdd = async () => {
    const dist = parseFloat(formDistance);
    if (!formLabel.trim() || isNaN(dist) || dist <= 0) return;
    setSaving(true);
    try {
      const created = await distanceGoalApi.create(patientId, {
        distance_meters: dist,
        label: formLabel.trim(),
        emoji: formEmoji,
      });
      setGoals(prev => [...prev, created].sort((a, b) => a.distance_meters - b.distance_meters));
      setFormLabel('');
      setFormDistance('');
      setFormEmoji('🏪');
      setShowForm(false);
    } catch { /* ignore */ }
    setSaving(false);
  };

  const handleDelete = async (goalId: string) => {
    try {
      await distanceGoalApi.delete(goalId);
      setGoals(prev => prev.filter(g => g.id !== goalId));
    } catch { /* ignore */ }
  };

  if (loading) return null;

  return (
    <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm">
      <div className="flex justify-between items-center mb-1">
        <h3 className="font-bold text-gray-900 dark:text-gray-100">이 속도라면?</h3>
        <button
          onClick={() => setShowForm(!showForm)}
          className="text-xs px-3 py-1.5 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
        >
          {showForm ? '취소' : '+ 목적지'}
        </button>
      </div>
      {speedMps > 0 && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
          현재 속도 <span className="font-semibold text-gray-700 dark:text-gray-300">{speedMps.toFixed(2)} m/s</span> 기준
        </p>
      )}

      {/* Add Form */}
      {showForm && (
        <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-xl space-y-3">
          {/* Emoji selector */}
          <div>
            <p className="text-xs text-gray-600 dark:text-gray-400 mb-1.5">아이콘</p>
            <div className="flex flex-wrap gap-1.5">
              {EMOJI_PRESETS.map(e => (
                <button
                  key={e}
                  onClick={() => setFormEmoji(e)}
                  className={`w-9 h-9 text-lg rounded-lg transition-all ${
                    formEmoji === e
                      ? 'bg-blue-500 shadow-md scale-110'
                      : 'bg-white dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600'
                  }`}
                >
                  {e}
                </button>
              ))}
              <input
                type="text"
                value={formEmoji}
                onChange={e => {
                  const val = e.target.value;
                  if (val) setFormEmoji(val.slice(-2));
                }}
                className="w-9 h-9 text-center text-lg rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
                title="직접 입력"
              />
            </div>
          </div>

          {/* Label + Distance */}
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="장소명 (예: 앞 편의점)"
              value={formLabel}
              onChange={e => setFormLabel(e.target.value)}
              className="flex-1 px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400"
            />
            <input
              type="number"
              placeholder="거리(m)"
              value={formDistance}
              onChange={e => setFormDistance(e.target.value)}
              className="w-24 px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400"
              min="1"
            />
          </div>

          <button
            onClick={handleAdd}
            disabled={saving || !formLabel.trim() || !formDistance}
            className="w-full py-2 text-sm font-semibold text-white bg-blue-500 rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {saving ? '저장 중...' : '추가'}
          </button>
        </div>
      )}

      {/* Goal List */}
      {goals.length === 0 && !speedMps ? (
        <p className="text-sm text-gray-400 text-center py-4">
          보행 데이터가 필요합니다
        </p>
      ) : goals.length === 0 ? (
        <p className="text-sm text-gray-400 text-center py-6">
          환자 주변 목적지를 추가해보세요
        </p>
      ) : (
        <div className="space-y-2.5">
          {goals.map(goal => {
            const timeSeconds = speedMps > 0 ? goal.distance_meters / speedMps : 0;
            const isCrosswalk = goal.label.includes('횡단보도');
            // 횡단보도 신호시간: 보행진입시간 7초 + 1m당 1초(일반) / 1.5초(보호구역)
            const signalGeneral = isCrosswalk ? 7 + goal.distance_meters * 1 : 0;
            const signalProtected = isCrosswalk ? 7 + goal.distance_meters * 1.5 : 0;
            const canCrossGeneral = isCrosswalk && speedMps > 0 && timeSeconds <= signalGeneral;
            const canCrossProtected = isCrosswalk && speedMps > 0 && timeSeconds <= signalProtected;

            return (
              <div key={goal.id} className="group p-3 bg-gray-50 dark:bg-gray-700/50 rounded-xl">
                <div className="flex items-center gap-3">
                  <span className="text-2xl flex-shrink-0">{goal.emoji}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">
                        {goal.label}
                        <span className="ml-1.5 text-xs font-normal text-gray-400">{formatDistance(goal.distance_meters)}</span>
                      </span>
                      {speedMps > 0 ? (
                        <span className="text-sm font-bold text-blue-600 dark:text-blue-400 flex-shrink-0 ml-2">
                          {formatTime(timeSeconds)}
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400 flex-shrink-0 ml-2">-</span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(goal.id)}
                    className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 text-sm flex-shrink-0 transition-opacity"
                    title="삭제"
                  >
                    &times;
                  </button>
                </div>

                {/* 횡단보도 신호시간 비교 */}
                {isCrosswalk && speedMps > 0 && (
                  <div className="mt-2 ml-11 space-y-1.5">
                    <div className={`flex items-center justify-between text-xs px-2.5 py-1.5 rounded-lg ${
                      canCrossGeneral
                        ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400'
                        : 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400'
                    }`}>
                      <span>일반 신호 <span className="text-gray-400 dark:text-gray-500">(1.0m/s 기준)</span></span>
                      <span className="font-semibold">
                        {formatTime(signalGeneral)} {canCrossGeneral ? '통과 가능' : '시간 부족'}
                      </span>
                    </div>
                    <div className={`flex items-center justify-between text-xs px-2.5 py-1.5 rounded-lg ${
                      canCrossProtected
                        ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400'
                        : 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400'
                    }`}>
                      <span>보호구역 신호 <span className="text-gray-400 dark:text-gray-500">(0.7m/s 기준)</span></span>
                      <span className="font-semibold">
                        {formatTime(signalProtected)} {canCrossProtected ? '통과 가능' : '시간 부족'}
                      </span>
                    </div>
                    <p className="text-[10px] text-gray-400 dark:text-gray-500">
                      신호시간 = 보행진입 7초 + 거리 × {'{'}1초/m | 1.5초/m{'}'}
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
