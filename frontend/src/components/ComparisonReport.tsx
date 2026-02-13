import { useState } from 'react';
import { testApi } from '../services/api';
import type { ComparisonReportData, WalkTest } from '../types';
import ComparisonChart from './ComparisonChart';

interface ComparisonReportProps {
  patientId: string;
  testId?: string;
  prevId?: string;
  currentTest?: WalkTest;
  previousTest?: WalkTest;
}

export default function ComparisonReport({ patientId, testId, prevId, currentTest, previousTest }: ComparisonReportProps) {
  const [report, setReport] = useState<ComparisonReportData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const loadReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await testApi.getComparisonReport(patientId, testId, prevId);
      setReport(data);
    } catch {
      setError('비교 리포트 생성에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!report) return;
    try {
      await navigator.clipboard.writeText(report.summary_text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
      const textarea = document.createElement('textarea');
      textarea.value = report.summary_text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (!report && !loading) {
    return (
      <button
        onClick={loadReport}
        disabled={loading}
        className="w-full px-4 py-3 text-center bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 rounded-lg font-semibold text-sm hover:bg-indigo-100 dark:hover:bg-indigo-900/40 transition-colors flex items-center justify-center gap-2"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        비교 리포트 생성
      </button>
    );
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center py-6">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-500"></div>
        <span className="ml-2 text-sm text-gray-500">리포트 생성 중...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-4">
        <p className="text-sm text-red-500 mb-2">{error}</p>
        <button onClick={loadReport} className="text-sm text-blue-500 hover:underline">
          다시 시도
        </button>
      </div>
    );
  }

  if (!report) return null;

  return (
    <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm">
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
          비교 리포트
          {report.is_improved ? (
            <span className="text-xs px-2 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded-full">
              향상
            </span>
          ) : (
            <span className="text-xs px-2 py-0.5 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded-full">
              주의
            </span>
          )}
        </h3>
        <button
          onClick={handleCopy}
          className="text-xs px-3 py-1.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 flex items-center gap-1"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
          </svg>
          {copied ? '복사됨!' : '복사'}
        </button>
      </div>

      <div className="bg-gray-50 dark:bg-gray-700/50 p-4 rounded-xl">
        <pre className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-sans leading-relaxed">
          {report.summary_text}
        </pre>
      </div>

      {/* Comparison Charts */}
      {currentTest && previousTest && (
        <div className="mt-5">
          <ComparisonChart currentTest={currentTest} previousTest={previousTest} />
        </div>
      )}
    </div>
  );
}
