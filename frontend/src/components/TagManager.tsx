import { useState, useEffect } from 'react';
import { patientApi } from '../services/api';
import type { PatientTag } from '../types';
import TagBadge from './TagBadge';

const PRESET_TAGS = [
  { name: '뇌졸중', color: '#EF4444' },
  { name: '파킨슨', color: '#8B5CF6' },
  { name: '고관절치환', color: '#F59E0B' },
  { name: '무릎수술', color: '#10B981' },
  { name: '척추손상', color: '#3B82F6' },
  { name: '낙상이력', color: '#EC4899' },
  { name: '뇌성마비', color: '#6366F1' },
];

interface TagManagerProps {
  patientId: string;
  patientTags: PatientTag[];
  onTagsChange: (tags: PatientTag[]) => void;
}

export default function TagManager({ patientId, patientTags, onTagsChange }: TagManagerProps) {
  const [allTags, setAllTags] = useState<PatientTag[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [newTagName, setNewTagName] = useState('');

  useEffect(() => {
    loadTags();
  }, []);

  const loadTags = async () => {
    try {
      const tags = await patientApi.getAllTags();
      setAllTags(tags);
    } catch { /* ignore */ }
  };

  const handleAddTag = async (tag: PatientTag) => {
    if (patientTags.find(t => t.id === tag.id)) return;
    try {
      await patientApi.addPatientTag(patientId, tag.id);
      onTagsChange([...patientTags, tag]);
    } catch { /* ignore */ }
  };

  const handleRemoveTag = async (tagId: string) => {
    try {
      await patientApi.removePatientTag(patientId, tagId);
      onTagsChange(patientTags.filter(t => t.id !== tagId));
    } catch { /* ignore */ }
  };

  const handleCreateAndAdd = async (name: string, color: string) => {
    try {
      const tag = await patientApi.createTag(name, color);
      setAllTags(prev => [...prev, tag]);
      await patientApi.addPatientTag(patientId, tag.id);
      onTagsChange([...patientTags, tag]);
      setNewTagName('');
    } catch { /* ignore */ }
  };

  const availableTags = allTags.filter(t => !patientTags.find(pt => pt.id === t.id));
  const availablePresets = PRESET_TAGS.filter(p =>
    !allTags.find(t => t.name === p.name) && !patientTags.find(t => t.name === p.name)
  );

  return (
    <div className="relative">
      <div className="flex flex-wrap gap-1 items-center">
        {patientTags.map(tag => (
          <TagBadge key={tag.id} tag={tag} onRemove={handleRemoveTag} />
        ))}
        <button
          onClick={() => setShowDropdown(!showDropdown)}
          className="text-xs px-2 py-0.5 rounded-full border border-dashed border-gray-400 text-gray-500 hover:border-blue-500 hover:text-blue-500 dark:border-gray-600 dark:text-gray-400"
        >
          + 태그
        </button>
      </div>

      {showDropdown && (
        <div className="absolute z-50 mt-1 w-64 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3">
          {availableTags.length > 0 && (
            <div className="mb-2">
              <p className="text-xs text-gray-500 mb-1">기존 태그</p>
              <div className="flex flex-wrap gap-1">
                {availableTags.map(tag => (
                  <button key={tag.id} onClick={() => { handleAddTag(tag); setShowDropdown(false); }}>
                    <TagBadge tag={tag} />
                  </button>
                ))}
              </div>
            </div>
          )}

          {availablePresets.length > 0 && (
            <div className="mb-2">
              <p className="text-xs text-gray-500 mb-1">추천 태그</p>
              <div className="flex flex-wrap gap-1">
                {availablePresets.map(p => (
                  <button
                    key={p.name}
                    onClick={() => { handleCreateAndAdd(p.name, p.color); setShowDropdown(false); }}
                    className="text-xs px-2 py-0.5 rounded-full border border-dashed"
                    style={{ borderColor: p.color, color: p.color }}
                  >
                    + {p.name}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="flex gap-1 mt-2">
            <input
              type="text"
              value={newTagName}
              onChange={(e) => setNewTagName(e.target.value)}
              placeholder="새 태그 이름"
              className="flex-1 text-xs border rounded px-2 py-1 dark:bg-gray-700 dark:border-gray-600"
            />
            <button
              onClick={() => { if (newTagName.trim()) { handleCreateAndAdd(newTagName.trim(), '#6B7280'); setShowDropdown(false); } }}
              className="text-xs px-2 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              추가
            </button>
          </div>

          <button
            onClick={() => setShowDropdown(false)}
            className="mt-2 text-xs text-gray-400 hover:text-gray-600 w-full text-center"
          >
            닫기
          </button>
        </div>
      )}
    </div>
  );
}
