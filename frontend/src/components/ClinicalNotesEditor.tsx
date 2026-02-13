import { useState, useEffect } from 'react';
import type { StructuredNotes } from '../types';

const ASSISTIVE_DEVICES = ['없음', '지팡이', '사발 지팡이', '워커', '휠체어', '기타'];
const CONDITIONS = ['양호', '보통', '불량'];
const QUICK_TAGS = ['보조기구 사용', '통증 호소', '컨디션 양호', '낙상 위험', '보행 보조 필요', '의욕 저하'];

interface ClinicalNotesEditorProps {
  notes?: string;
  onSave: (notes: string) => void;
  compact?: boolean;
}

function parseNotes(notes?: string): StructuredNotes {
  if (!notes) return {};
  try {
    const parsed = JSON.parse(notes);
    if (typeof parsed === 'object' && parsed !== null) return parsed;
  } catch { /* plain text */ }
  return { text: notes };
}

export default function ClinicalNotesEditor({ notes, onSave, compact = false }: ClinicalNotesEditorProps) {
  const [data, setData] = useState<StructuredNotes>(() => parseNotes(notes));
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    setData(parseNotes(notes));
    setDirty(false);
  }, [notes]);

  const update = (patch: Partial<StructuredNotes>) => {
    setData(prev => ({ ...prev, ...patch }));
    setDirty(true);
  };

  const toggleTag = (tag: string) => {
    const current = data.tags || [];
    const newTags = current.includes(tag) ? current.filter(t => t !== tag) : [...current, tag];
    update({ tags: newTags });
  };

  const handleSave = () => {
    const serialized = JSON.stringify(data);
    onSave(serialized);
    setDirty(false);
  };

  return (
    <div className="space-y-3">
      {/* 자유 텍스트 */}
      <textarea
        value={data.text || ''}
        onChange={(e) => update({ text: e.target.value })}
        placeholder="메모를 입력하세요..."
        className={`w-full border rounded-lg px-3 py-2 text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200 ${compact ? 'h-16' : 'h-24'}`}
      />

      {!compact && (
        <>
          {/* 보조기구 & 환자 상태 */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">보조기구</label>
              <select
                value={data.assistive_device || '없음'}
                onChange={(e) => update({ assistive_device: e.target.value })}
                className="w-full text-sm border rounded px-2 py-1.5 dark:bg-gray-700 dark:border-gray-600"
              >
                {ASSISTIVE_DEVICES.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">환자 상태</label>
              <div className="flex gap-2">
                {CONDITIONS.map(c => (
                  <button
                    key={c}
                    onClick={() => update({ condition: c })}
                    className={`text-xs px-3 py-1.5 rounded border ${
                      data.condition === c
                        ? 'bg-blue-500 text-white border-blue-500'
                        : 'border-gray-300 dark:border-gray-600 hover:border-blue-400'
                    }`}
                  >
                    {c}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* 통증 수준 */}
          <div>
            <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">
              통증 수준 (NRS): {data.pain_level ?? '-'}/10
            </label>
            <input
              type="range"
              min="0"
              max="10"
              value={data.pain_level ?? 0}
              onChange={(e) => update({ pain_level: parseInt(e.target.value) })}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-600"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-0.5">
              <span>0 (없음)</span>
              <span>5 (중등)</span>
              <span>10 (극심)</span>
            </div>
          </div>
        </>
      )}

      {/* 빠른 태그 */}
      <div>
        <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">빠른 태그</label>
        <div className="flex flex-wrap gap-1">
          {QUICK_TAGS.map(tag => (
            <button
              key={tag}
              onClick={() => toggleTag(tag)}
              className={`text-xs px-2 py-1 rounded-full border ${
                (data.tags || []).includes(tag)
                  ? 'bg-blue-100 text-blue-700 border-blue-300 dark:bg-blue-900 dark:text-blue-300 dark:border-blue-700'
                  : 'border-gray-300 text-gray-600 dark:border-gray-600 dark:text-gray-400 hover:border-blue-400'
              }`}
            >
              {tag}
            </button>
          ))}
        </div>
      </div>

      {/* 저장 버튼 */}
      {dirty && (
        <button
          onClick={handleSave}
          className="w-full text-sm py-1.5 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          메모 저장
        </button>
      )}
    </div>
  );
}
