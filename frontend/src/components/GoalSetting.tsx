import { useState, useEffect } from 'react';
import { goalApi } from '../services/api';
import type { TestType } from '../types';
import { useFocusTrap } from '../hooks/useFocusTrap';

interface GoalSettingProps {
  patientId: string;
  onClose: () => void;
  onCreated: () => void;
}

export default function GoalSetting({ patientId, onClose, onCreated }: GoalSettingProps) {
  const focusTrapRef = useFocusTrap(true);
  const [testType, setTestType] = useState<TestType>('10MWT');
  const [targetTime, setTargetTime] = useState('');
  const [targetScore, setTargetScore] = useState('');
  const [targetDate, setTargetDate] = useState('');
  const [saving, setSaving] = useState(false);

  // ESC 키로 닫기
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  const handleSubmit = async () => {
    setSaving(true);
    try {
      const data: Record<string, unknown> = { test_type: testType };
      if (testType === '10MWT' && targetTime) data.target_time_seconds = parseFloat(targetTime);
      if (testType === 'TUG' && targetTime) data.target_time_seconds = parseFloat(targetTime);
      if (testType === 'BBS' && targetScore) data.target_score = parseInt(targetScore);
      if (targetDate) data.target_date = targetDate;

      await goalApi.create(patientId, data);
      onCreated();
      onClose();
    } catch {
      alert('목표 생성에 실패했습니다.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="goal-modal-title">
      <div ref={focusTrapRef} className="bg-white dark:bg-gray-800 rounded-xl p-6 w-full max-w-md shadow-xl" onClick={e => e.stopPropagation()}>
        <h3 id="goal-modal-title" className="text-lg font-bold mb-4 dark:text-white">목표 설정</h3>

        <div className="space-y-4">
          <div>
            <label className="text-sm text-gray-600 dark:text-gray-400 block mb-1">검사 유형</label>
            <div className="flex gap-2">
              {(['10MWT', 'TUG', 'BBS'] as TestType[]).map(t => (
                <button
                  key={t}
                  onClick={() => setTestType(t)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium ${
                    testType === t
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          {testType === '10MWT' && (
            <div>
              <label className="text-sm text-gray-600 dark:text-gray-400 block mb-1">목표 보행 시간 (초)</label>
              <input
                type="number"
                step="0.1"
                value={targetTime}
                onChange={e => setTargetTime(e.target.value)}
                placeholder="예: 8.0"
                className="w-full border rounded-lg px-3 py-2 dark:bg-gray-700 dark:border-gray-600"
              />
              <p className="text-xs text-gray-400 mt-1">정상 기준: 10초 이내 (10m 보행)</p>
            </div>
          )}

          {testType === 'TUG' && (
            <div>
              <label className="text-sm text-gray-600 dark:text-gray-400 block mb-1">목표 TUG 시간 (초)</label>
              <input
                type="number"
                step="0.1"
                value={targetTime}
                onChange={e => setTargetTime(e.target.value)}
                placeholder="예: 10.0"
                className="w-full border rounded-lg px-3 py-2 dark:bg-gray-700 dark:border-gray-600"
              />
              <p className="text-xs text-gray-400 mt-1">정상 기준: 10초 이내</p>
            </div>
          )}

          {testType === 'BBS' && (
            <div>
              <label className="text-sm text-gray-600 dark:text-gray-400 block mb-1">목표 BBS 점수 (/56)</label>
              <input
                type="number"
                min="0"
                max="56"
                value={targetScore}
                onChange={e => setTargetScore(e.target.value)}
                placeholder="예: 45"
                className="w-full border rounded-lg px-3 py-2 dark:bg-gray-700 dark:border-gray-600"
              />
            </div>
          )}

          <div>
            <label className="text-sm text-gray-600 dark:text-gray-400 block mb-1">목표 달성일 (선택)</label>
            <input
              type="date"
              value={targetDate}
              onChange={e => setTargetDate(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 dark:bg-gray-700 dark:border-gray-600"
            />
          </div>
        </div>

        <div className="flex gap-2 mt-6">
          <button onClick={onClose} className="flex-1 py-2 border rounded-lg text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700">
            취소
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving}
            className="flex-1 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
          >
            {saving ? '저장 중...' : '목표 설정'}
          </button>
        </div>
      </div>
    </div>
  );
}
