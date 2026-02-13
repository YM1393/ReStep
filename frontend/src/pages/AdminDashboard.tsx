import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { dashboardApi, exportApi, siteApi, emrApi } from '../services/api';
import type { AdminDashboardStats, User, Site, SiteStats, EMRStatus } from '../types';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

export default function AdminDashboard() {
  const [stats, setStats] = useState<AdminDashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Multi-site state
  const [sites, setSites] = useState<Site[]>([]);
  const [selectedSiteId, setSelectedSiteId] = useState<string>('');
  const [siteStats, setSiteStats] = useState<SiteStats | null>(null);
  const [sitesLoading, setSitesLoading] = useState(false);

  // EMR state
  const [emrStatus, setEmrStatus] = useState<EMRStatus | null>(null);

  useEffect(() => {
    loadStats();
    loadSites();
    loadEmrStatus();
  }, []);

  useEffect(() => {
    if (selectedSiteId) {
      loadSiteStats(selectedSiteId);
    } else {
      setSiteStats(null);
    }
  }, [selectedSiteId]);

  const loadStats = async () => {
    try {
      const data = await dashboardApi.getStats();
      setStats(data);
    } catch {
      setError('통계 데이터를 불러오는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const loadSites = async () => {
    try {
      const data = await siteApi.getAll();
      setSites(data);
    } catch {
      // Sites feature may not be available yet
    }
  };

  const loadSiteStats = async (siteId: string) => {
    setSitesLoading(true);
    try {
      const data = await siteApi.getStats(siteId);
      setSiteStats(data);
    } catch {
      setSiteStats(null);
    } finally {
      setSitesLoading(false);
    }
  };

  const loadEmrStatus = async () => {
    try {
      const data = await emrApi.getStatus();
      setEmrStatus(data);
    } catch {
      // EMR not available
    }
  };

  const handleExportDownload = async (url: string, defaultFilename: string) => {
    try {
      const headers: Record<string, string> = {};
      const userStr = localStorage.getItem('user');
      if (userStr) {
        const user: User = JSON.parse(userStr);
        headers['X-User-Id'] = user.id;
        headers['X-User-Role'] = user.role;
        headers['X-User-Approved'] = user.is_approved ? 'true' : 'false';
      }
      const accessToken = localStorage.getItem('access_token');
      if (accessToken) {
        headers['Authorization'] = `Bearer ${accessToken}`;
      }

      const response = await fetch(url, { headers });
      if (!response.ok) throw new Error('Download failed');

      const disposition = response.headers.get('Content-Disposition');
      let filename = defaultFilename;
      if (disposition) {
        const match = disposition.match(/filename=(.+)/);
        if (match) filename = match[1];
      }

      const blob = await response.blob();
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      link.click();
      URL.revokeObjectURL(link.href);
    } catch {
      alert('다운로드에 실패했습니다.');
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12" role="status">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        <span className="sr-only">로딩 중...</span>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500 mb-4">{error || '데이터를 불러올 수 없습니다.'}</p>
        <Link to="/" className="text-blue-500 hover:underline">대시보드로 돌아가기</Link>
      </div>
    );
  }

  const PIE_COLORS = ['#10B981', '#F59E0B', '#EF4444'];
  const improvementData = [
    { name: '향상', value: stats.improvement_distribution.improved },
    { name: '유지', value: stats.improvement_distribution.stable },
    { name: '악화', value: stats.improvement_distribution.worsened },
  ].filter(d => d.value > 0);

  return (
    <div className="animate-fadeIn pb-20 sm:pb-0">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 mb-6">
        <Link to="/" className="hover:text-blue-600 dark:hover:text-blue-400">대시보드</Link>
        <span>›</span>
        <span className="text-gray-800 dark:text-gray-200">병원 통계</span>
      </div>

      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">병원 통계 대시보드</h1>

        {/* Site Selector */}
        {sites.length > 0 && (
          <div className="flex items-center gap-2">
            <label htmlFor="site-select" className="text-sm text-gray-600 dark:text-gray-400">
              지점:
            </label>
            <select
              id="site-select"
              value={selectedSiteId}
              onChange={(e) => setSelectedSiteId(e.target.value)}
              className="text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-1.5 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            >
              <option value="">전체</option>
              {sites.map(site => (
                <option key={site.id} value={site.id}>{site.name}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Site-specific stats when a site is selected */}
      {selectedSiteId && siteStats && !sitesLoading && (
        <div className="bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-xl p-4 mb-6">
          <h3 className="font-semibold text-indigo-900 dark:text-indigo-200 mb-3">
            {siteStats.site_name} 지점 통계
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div>
              <p className="text-xs text-indigo-600 dark:text-indigo-400">환자 수</p>
              <p className="text-xl font-bold text-indigo-900 dark:text-indigo-100">{siteStats.total_patients}</p>
            </div>
            <div>
              <p className="text-xs text-indigo-600 dark:text-indigo-400">검사 수</p>
              <p className="text-xl font-bold text-indigo-900 dark:text-indigo-100">{siteStats.total_tests}</p>
            </div>
            <div>
              <p className="text-xs text-indigo-600 dark:text-indigo-400">치료사 수</p>
              <p className="text-xl font-bold text-indigo-900 dark:text-indigo-100">{siteStats.total_therapists}</p>
            </div>
            <div>
              <p className="text-xs text-indigo-600 dark:text-indigo-400">평균 보행속도</p>
              <p className="text-xl font-bold text-indigo-900 dark:text-indigo-100">
                {siteStats.avg_walk_speed_mps != null ? `${siteStats.avg_walk_speed_mps.toFixed(2)} m/s` : '-'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* EMR Status Indicator */}
      {emrStatus && (
        <div className={`flex items-center gap-2 text-sm mb-4 ${emrStatus.connected ? 'text-green-600 dark:text-green-400' : 'text-gray-400 dark:text-gray-500'}`}>
          <span className={`w-2 h-2 rounded-full ${emrStatus.connected ? 'bg-green-500' : 'bg-gray-400'}`}></span>
          EMR (FHIR): {emrStatus.connected ? '연결됨' : '미연결'}
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
        {[
          { label: '전체 환자', value: stats.total_patients, color: 'bg-blue-500/10', text: 'text-blue-600' },
          { label: '총 검사', value: stats.total_tests, color: 'bg-green-500/10', text: 'text-green-600' },
          { label: '이번 주', value: stats.tests_this_week, color: 'bg-cyan-500/10', text: 'text-cyan-600' },
          { label: '이번 달', value: stats.tests_this_month, color: 'bg-purple-500/10', text: 'text-purple-600' },
          { label: '낙상 고위험', value: stats.high_fall_risk_count, color: 'bg-red-500/10', text: 'text-red-600' },
        ].map(card => (
          <div key={card.label} className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-5">
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">{card.label}</p>
            <p className={`text-3xl font-bold ${card.text}`}>{card.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Monthly Tests Chart */}
        <div className="bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-sm">
          <h3 className="font-bold text-gray-900 dark:text-gray-100 mb-4">월별 검사 추이</h3>
          {stats.tests_by_period.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={stats.tests_by_period}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="period" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#3B82F6" radius={[4, 4, 0, 0]} name="검사 수" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-center text-gray-400 py-12">데이터가 없습니다</p>
          )}
        </div>

        {/* Improvement Distribution */}
        <div className="bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-sm">
          <h3 className="font-bold text-gray-900 dark:text-gray-100 mb-4">개선율 분포</h3>
          {improvementData.length > 0 ? (
            <div className="flex items-center justify-center">
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={improvementData}
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    dataKey="value"
                    label={({ name, value }) => `${name}: ${value}명`}
                  >
                    {improvementData.map((_entry, index) => (
                      <Cell key={index} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-center text-gray-400 py-12">비교 가능한 데이터가 없습니다</p>
          )}
          <div className="flex justify-center gap-6 mt-2">
            {[
              { label: '향상', color: 'bg-green-500', val: stats.improvement_distribution.improved },
              { label: '유지', color: 'bg-yellow-500', val: stats.improvement_distribution.stable },
              { label: '악화', color: 'bg-red-500', val: stats.improvement_distribution.worsened },
            ].map(item => (
              <div key={item.label} className="flex items-center gap-1.5">
                <span className={`w-3 h-3 ${item.color} rounded-full`}></span>
                <span className="text-sm text-gray-600 dark:text-gray-400">{item.label}: {item.val}명</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Tag Stats Table */}
      {stats.tag_stats.length > 0 && (
        <div className="bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-sm">
          <h3 className="font-bold text-gray-900 dark:text-gray-100 mb-4">태그별 통계</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <caption className="sr-only">태그별 환자 통계</caption>
              <thead>
                <tr className="border-b dark:border-gray-700">
                  <th className="text-left py-2 px-3 text-gray-500 dark:text-gray-400 font-medium">태그</th>
                  <th className="text-right py-2 px-3 text-gray-500 dark:text-gray-400 font-medium">환자 수</th>
                  <th className="text-right py-2 px-3 text-gray-500 dark:text-gray-400 font-medium">평균 속도</th>
                </tr>
              </thead>
              <tbody>
                {stats.tag_stats.map(tag => (
                  <tr key={tag.tag_name} className="border-b dark:border-gray-700 last:border-0">
                    <td className="py-2.5 px-3">
                      <span
                        className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                        style={{
                          backgroundColor: `${tag.color}20`,
                          color: tag.color,
                          border: `1px solid ${tag.color}40`,
                        }}
                      >
                        {tag.tag_name}
                      </span>
                    </td>
                    <td className="text-right py-2.5 px-3 font-semibold text-gray-900 dark:text-gray-100">
                      {tag.patient_count}명
                    </td>
                    <td className="text-right py-2.5 px-3 font-semibold text-gray-900 dark:text-gray-100">
                      {tag.avg_speed != null ? `${tag.avg_speed.toFixed(2)} m/s` : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Data Export & Backup */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-sm mt-6">
        <h3 className="font-bold text-gray-900 dark:text-gray-100 mb-4">데이터 내보내기 / 백업</h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <button
            onClick={() => handleExportDownload(exportApi.patientsCSV(), 'patients.csv')}
            className="flex items-center gap-3 p-4 border border-gray-200 dark:border-gray-700 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors text-left"
          >
            <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
              <svg className="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <div>
              <p className="font-semibold text-gray-900 dark:text-gray-100 text-sm">환자 목록 CSV</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">전체 환자 데이터 내보내기</p>
            </div>
          </button>

          <button
            onClick={() => handleExportDownload(exportApi.testsCSV(), 'tests.csv')}
            className="flex items-center gap-3 p-4 border border-gray-200 dark:border-gray-700 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors text-left"
          >
            <div className="w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
              <svg className="w-5 h-5 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <p className="font-semibold text-gray-900 dark:text-gray-100 text-sm">검사 결과 CSV</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">전체 검사 데이터 내보내기</p>
            </div>
          </button>

          <button
            onClick={() => handleExportDownload(exportApi.backup(), 'database_backup.db')}
            className="flex items-center gap-3 p-4 border border-gray-200 dark:border-gray-700 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors text-left"
          >
            <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
              <svg className="w-5 h-5 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
            </div>
            <div>
              <p className="font-semibold text-gray-900 dark:text-gray-100 text-sm">DB 백업</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">데이터베이스 파일 다운로드</p>
            </div>
          </button>
        </div>
      </div>
    </div>
  );
}
