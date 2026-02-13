import { useState, useEffect } from 'react';
import { testApi } from '../services/api';
import type { RecommendationsResponse, RehabRecommendation } from '../types';

interface Props {
  patientId: string;
}

const PRIORITY_CONFIG = {
  high: { label: '높음', bg: 'bg-red-100 dark:bg-red-900/30', text: 'text-red-700 dark:text-red-400', border: 'border-red-400' },
  medium: { label: '보통', bg: 'bg-yellow-100 dark:bg-yellow-900/30', text: 'text-yellow-800 dark:text-yellow-300', border: 'border-yellow-400' },
  low: { label: '낮음', bg: 'bg-green-100 dark:bg-green-900/30', text: 'text-green-700 dark:text-green-400', border: 'border-green-400' },
};

const RISK_LEVEL_CONFIG: Record<string, { label: string; color: string }> = {
  normal: { label: '정상', color: 'bg-green-500' },
  mild: { label: '경도 위험', color: 'bg-blue-500' },
  moderate: { label: '중등도 위험', color: 'bg-orange-500' },
  high: { label: '고위험', color: 'bg-red-500' },
};

export default function RehabRecommendations({ patientId }: Props) {
  const [data, setData] = useState<RecommendationsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set());

  useEffect(() => {
    loadRecommendations();
  }, [patientId]);

  const loadRecommendations = async () => {
    try {
      setLoading(true);
      const result = await testApi.getRecommendations(patientId);
      setData(result);
    } catch {
      // Recommendations are optional
    } finally {
      setLoading(false);
    }
  };

  const toggleExpand = (index: number) => {
    setExpandedItems(prev => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm">
        <h3 className="font-bold text-gray-900 dark:text-gray-100 mb-3">재활 추천</h3>
        <div className="flex justify-center py-4">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
        </div>
      </div>
    );
  }

  if (!data || data.recommendations.length === 0) {
    return null;
  }

  const riskConfig = RISK_LEVEL_CONFIG[data.risk_level] || RISK_LEVEL_CONFIG.normal;

  // Group by priority
  const grouped: Record<string, RehabRecommendation[]> = { high: [], medium: [], low: [] };
  for (const rec of data.recommendations) {
    if (grouped[rec.priority]) {
      grouped[rec.priority].push(rec);
    }
  }

  return (
    <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-bold text-gray-900 dark:text-gray-100">재활 추천</h3>
        <div className="flex items-center gap-2">
          {data.disease_profile !== 'default' && (
            <span className="px-2 py-0.5 bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400 text-xs font-medium rounded-full">
              {data.disease_profile_display}
            </span>
          )}
          <span className={`px-2 py-0.5 text-white text-xs font-medium rounded-full ${riskConfig.color}`}>
            {riskConfig.label}
          </span>
        </div>
      </div>

      <div className="space-y-2">
        {data.recommendations.map((rec, index) => {
          const priorityCfg = PRIORITY_CONFIG[rec.priority];
          const isExpanded = expandedItems.has(index);

          return (
            <div
              key={index}
              className={`rounded-lg border-l-4 ${priorityCfg.border} overflow-hidden`}
            >
              <button
                onClick={() => toggleExpand(index)}
                className="w-full text-left p-3 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`px-1.5 py-0.5 text-xs font-semibold rounded ${priorityCfg.bg} ${priorityCfg.text}`}>
                        {priorityCfg.label}
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {rec.category}
                      </span>
                    </div>
                    <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                      {rec.title}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      {rec.frequency}
                    </p>
                  </div>
                  <svg
                    className={`w-4 h-4 text-gray-400 flex-shrink-0 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                    fill="none" stroke="currentColor" viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </button>

              {isExpanded && (
                <div className="px-3 pb-3 space-y-2">
                  <p className="text-sm text-gray-700 dark:text-gray-300">
                    {rec.description}
                  </p>
                  <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded text-xs text-blue-700 dark:text-blue-400">
                    <span className="font-semibold">근거: </span>
                    {rec.rationale}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
