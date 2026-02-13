import { useState } from 'react';
import { testApi } from '../services/api';
import type { WalkTest } from '../types';

interface VideoComparisonProps {
  patientId: string;
  tests: WalkTest[];
}

export default function VideoComparison({ patientId, tests }: VideoComparisonProps) {
  const [test1Id, setTest1Id] = useState(tests.length > 1 ? tests[tests.length - 1].id : '');
  const [test2Id, setTest2Id] = useState(tests.length > 0 ? tests[0].id : '');
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const videoTests = tests.filter(t => t.video_url);
  if (videoTests.length < 2) return null;

  const handleGenerate = () => {
    if (!test1Id || !test2Id || test1Id === test2Id) {
      setError('서로 다른 두 검사를 선택해주세요.');
      return;
    }
    setLoading(true);
    setError(null);
    const url = testApi.getComparisonVideoUrl(patientId, test1Id, test2Id);
    setVideoUrl(url);
    setLoading(false);
  };

  const formatDate = (d: string) => new Date(d).toLocaleDateString('ko-KR');

  return (
    <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm">
      <h3 className="font-bold text-gray-900 dark:text-gray-100 mb-4">영상 비교 (처음 vs 현재)</h3>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <div>
          <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">처음 검사</label>
          <select
            value={test1Id}
            onChange={e => { setTest1Id(e.target.value); setVideoUrl(null); }}
            className="w-full text-sm border rounded-lg px-2 py-1.5 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200"
          >
            <option value="">선택...</option>
            {videoTests.map(t => (
              <option key={t.id} value={t.id}>
                {formatDate(t.test_date)} - {t.walk_speed_mps.toFixed(2)}m/s
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">최근 검사</label>
          <select
            value={test2Id}
            onChange={e => { setTest2Id(e.target.value); setVideoUrl(null); }}
            className="w-full text-sm border rounded-lg px-2 py-1.5 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200"
          >
            <option value="">선택...</option>
            {videoTests.map(t => (
              <option key={t.id} value={t.id}>
                {formatDate(t.test_date)} - {t.walk_speed_mps.toFixed(2)}m/s
              </option>
            ))}
          </select>
        </div>
      </div>

      <button
        onClick={handleGenerate}
        disabled={loading || !test1Id || !test2Id}
        className="w-full py-2 bg-blue-500 text-white rounded-lg text-sm font-semibold hover:bg-blue-600 disabled:opacity-50 mb-3"
      >
        {loading ? '생성 중...' : '비교 영상 생성'}
      </button>

      {error && (
        <p className="text-sm text-red-500 mb-3">{error}</p>
      )}

      {videoUrl && (
        <div className="bg-gray-900 rounded-xl overflow-hidden">
          <video
            src={videoUrl}
            controls
            className="w-full aspect-video"
            onError={() => setError('비교 영상 생성에 실패했습니다. 두 영상 모두 존재하는지 확인해주세요.')}
          />
          <div className="bg-gray-800 px-4 py-2">
            <span className="text-white text-xs">좌: 처음 검사 / 우: 최근 검사</span>
          </div>
        </div>
      )}
    </div>
  );
}
