import { useState, useEffect } from 'react';
import { adminApi } from '../services/api';
import type { Therapist } from '../types';

export default function TherapistManagement() {
  const [pendingTherapists, setPendingTherapists] = useState<Therapist[]>([]);
  const [allTherapists, setAllTherapists] = useState<Therapist[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    loadTherapists();
  }, []);

  const loadTherapists = async () => {
    try {
      setLoading(true);
      const [pending, all] = await Promise.all([
        adminApi.getPendingTherapists(),
        adminApi.getAllTherapists()
      ]);
      setPendingTherapists(pending);
      setAllTherapists(all.filter(t => t.is_approved));
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || '물리치료사 목록을 불러오는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (userId: string) => {
    try {
      setActionLoading(userId);
      await adminApi.approveTherapist(userId);
      await loadTherapists();
    } catch (err: any) {
      setError(err.response?.data?.detail || '승인 처리에 실패했습니다.');
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (userId: string) => {
    if (!confirm('정말 이 물리치료사를 거부(삭제)하시겠습니까?')) {
      return;
    }
    try {
      setActionLoading(userId);
      await adminApi.deleteTherapist(userId);
      await loadTherapists();
    } catch (err: any) {
      setError(err.response?.data?.detail || '거부 처리에 실패했습니다.');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (userId: string) => {
    if (!confirm('정말 이 물리치료사를 삭제하시겠습니까?')) {
      return;
    }
    try {
      setActionLoading(userId);
      await adminApi.deleteTherapist(userId);
      await loadTherapists();
    } catch (err: any) {
      setError(err.response?.data?.detail || '삭제 처리에 실패했습니다.');
    } finally {
      setActionLoading(null);
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12" role="status">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        <span className="sr-only">로딩 중...</span>
      </div>
    );
  }

  return (
    <div className="animate-fadeIn pb-20 sm:pb-0">
      {/* 헤더 */}
      <div className="mb-6">
        <p className="text-gray-500 dark:text-gray-400 text-sm">관리자 메뉴</p>
        <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100">물리치료사 관리</h2>
      </div>

      {error && (
        <div role="alert" className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-3 rounded-xl mb-6">
          {error}
        </div>
      )}

      {/* 승인 대기 섹션 */}
      <div className="mb-8">
        <div className="flex items-center mb-4">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100">승인 대기</h3>
          <span className="ml-2 px-2 py-1 bg-orange-100 text-orange-600 text-sm font-medium rounded-full">
            {pendingTherapists.length}명
          </span>
        </div>

        {pendingTherapists.length === 0 ? (
          <div className="card text-center py-8">
            <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <p className="text-gray-500 dark:text-gray-400">승인 대기 중인 물리치료사가 없습니다.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {pendingTherapists.map((therapist) => (
              <div key={therapist.id} className="card flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center">
                    <span className="text-orange-600 font-bold text-lg">
                      {therapist.name.charAt(0)}
                    </span>
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-800 dark:text-gray-100">{therapist.name}</h4>
                    <p className="text-sm text-gray-500 dark:text-gray-400">@{therapist.username}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">가입일: {formatDate(therapist.created_at)}</p>
                  </div>
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={() => handleApprove(therapist.id)}
                    disabled={actionLoading === therapist.id}
                    className="px-4 py-2 bg-green-500 text-white rounded-xl hover:bg-green-600 transition-colors disabled:opacity-50"
                    aria-label={`${therapist.name} 승인`}
                  >
                    {actionLoading === therapist.id ? '처리 중...' : '승인'}
                  </button>
                  <button
                    onClick={() => handleReject(therapist.id)}
                    disabled={actionLoading === therapist.id}
                    className="px-4 py-2 bg-red-500 text-white rounded-xl hover:bg-red-600 transition-colors disabled:opacity-50"
                    aria-label={`${therapist.name} 거부`}
                  >
                    거부
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 승인된 물리치료사 섹션 */}
      <div>
        <div className="flex items-center mb-4">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100">승인된 물리치료사</h3>
          <span className="ml-2 px-2 py-1 bg-green-100 text-green-600 text-sm font-medium rounded-full">
            {allTherapists.length}명
          </span>
        </div>

        {allTherapists.length === 0 ? (
          <div className="card text-center py-8">
            <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <p className="text-gray-500 dark:text-gray-400">승인된 물리치료사가 없습니다.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {allTherapists.map((therapist) => (
              <div key={therapist.id} className="card flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                    <span className="text-blue-600 font-bold text-lg">
                      {therapist.name.charAt(0)}
                    </span>
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-800 dark:text-gray-100">{therapist.name}</h4>
                    <p className="text-sm text-gray-500 dark:text-gray-400">@{therapist.username}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">가입일: {formatDate(therapist.created_at)}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <span className="px-3 py-1 bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 text-sm rounded-full">
                    승인됨
                  </span>
                  <button
                    onClick={() => handleDelete(therapist.id)}
                    disabled={actionLoading === therapist.id}
                    className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors disabled:opacity-50"
                    aria-label={`${therapist.name} 삭제`}
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
