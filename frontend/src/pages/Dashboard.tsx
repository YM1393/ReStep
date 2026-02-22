import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { patientApi, testApi, authApi } from '../services/api';
import type { Patient, User, WalkTest, PatientTag } from '../types';
import TagBadge from '../components/TagBadge';
import { useDashboardPrefs } from '../hooks/useDashboardPrefs';
import {
  RecentTestsWidget, RiskPatientsWidget,
  SpeedDistributionWidget, WeeklyActivityWidget, CustomizePanel,
} from '../components/DashboardWidgets';

function calculateAge(birthDate: string): number {
  const today = new Date();
  const birth = new Date(birthDate);
  let age = today.getFullYear() - birth.getFullYear();
  const m = today.getMonth() - birth.getMonth();
  if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) age--;
  return age;
}

function getTimeStatus(time: number) {
  if (time <= 8.3) return { label: '정상', cls: 'bg-green-50 text-green-600' };
  if (time <= 12.5) return { label: '주의', cls: 'bg-orange-50 text-orange-600' };
  return { label: '위험', cls: 'bg-red-50 text-red-600' };
}

function daysAgo(dateStr: string): string {
  const d = Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400000);
  if (d === 0) return '오늘';
  if (d === 1) return '1일 전';
  return `${d}일 전`;
}

interface PatientWithTests extends Patient {
  latestTest?: WalkTest;
  testCount: number;
  tags?: PatientTag[];
}

export default function Dashboard() {
  const [patients, setPatients] = useState<PatientWithTests[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchMode, setSearchMode] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [filterRisk, setFilterRisk] = useState('all');
  const [sortBy, setSortBy] = useState('recent');
  const [allTags, setAllTags] = useState<PatientTag[]>([]);
  const [filterTag, setFilterTag] = useState('');
  const [showCustomize, setShowCustomize] = useState(false);
  const { widgets, toggleWidget, moveWidget, resetPrefs } = useDashboardPrefs();

  useEffect(() => {
    const currentUser = authApi.getCurrentUser();
    setUser(currentUser);
    loadPatients();
    loadTags();
  }, []);

  const loadTags = async () => {
    try {
      const tags = await patientApi.getAllTags();
      setAllTags(tags);
    } catch { /* ignore */ }
  };

  const loadPatients = async () => {
    try {
      setLoading(true);
      setSearchMode(false);
      const data = await patientApi.getAllWithLatestTest();

      // 단일 쿼리 결과를 PatientWithTests 형태로 변환
      const enriched: PatientWithTests[] = data.map((row: any) => {
        const patient: any = {
          id: row.id,
          patient_number: row.patient_number,
          name: row.name,
          gender: row.gender,
          birth_date: row.birth_date,
          height_cm: row.height_cm,
          diagnosis: row.diagnosis,
          created_at: row.created_at,
        };
        const latestTest = row.latest_test_id ? {
          id: row.latest_test_id,
          patient_id: row.id,
          test_date: row.latest_test_date,
          walk_speed_mps: row.latest_walk_speed_mps,
          walk_time_seconds: row.latest_walk_time_seconds,
          test_type: row.latest_test_type,
          video_filename: row.latest_video_filename,
        } as unknown as WalkTest : undefined;
        return { ...patient, latestTest, testCount: row.test_count || 0 };
      });

      setPatients(enriched);
      setError(null);
    } catch (err) {
      setError('환자 목록을 불러오는데 실패했습니다.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) {
      loadPatients();
      return;
    }
    try {
      setLoading(true);
      setSearchMode(true);
      const data = await patientApi.search(searchQuery);
      const enriched: PatientWithTests[] = await Promise.all(
        data.map(async (p: Patient) => {
          try {
            const [tests, tags] = await Promise.all([
              testApi.getPatientTests(p.id),
              patientApi.getPatientTags(p.id).catch(() => [] as PatientTag[]),
            ]);
            return { ...p, latestTest: tests[0], testCount: tests.length, tags };
          } catch {
            return { ...p, testCount: 0, tags: [] };
          }
        })
      );
      setPatients(enriched);
      setError(null);
    } catch (err) {
      setError('검색에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  }, [searchQuery]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch();
  };

  const isAdmin = user?.role === 'admin';
  const isApprovedTherapist = user?.role === 'therapist' && user?.is_approved;

  // Stats
  const totalPatients = patients.length;
  const patientsWithTests = patients.filter(p => p.latestTest);
  const weeklyTests = patientsWithTests.filter(p => {
    if (!p.latestTest) return false;
    const d = (Date.now() - new Date(p.latestTest.test_date).getTime()) / 86400000;
    return d <= 7;
  }).length;
  const cautionCount = patientsWithTests.filter(p =>
    p.latestTest && p.latestTest.walk_time_seconds > 0 && p.latestTest.walk_time_seconds > 12.5
  ).length;
  const avgTime = patientsWithTests.length > 0
    ? (patientsWithTests.reduce((s, p) => s + (p.latestTest?.walk_time_seconds || 0), 0) / patientsWithTests.length).toFixed(1)
    : '0.0';

  // Filtering & sorting
  let filtered = [...patients];
  if (filterRisk === 'normal') filtered = filtered.filter(p => p.latestTest && p.latestTest.walk_time_seconds > 0 && p.latestTest.walk_time_seconds <= 8.3);
  else if (filterRisk === 'caution') filtered = filtered.filter(p => p.latestTest && p.latestTest.walk_time_seconds > 8.3 && p.latestTest.walk_time_seconds <= 12.5);
  else if (filterRisk === 'risk') filtered = filtered.filter(p => p.latestTest && p.latestTest.walk_time_seconds > 12.5);

  if (filterTag) {
    filtered = filtered.filter(p => p.tags?.some(t => t.id === filterTag));
  }

  if (sortBy === 'recent') {
    filtered.sort((a, b) => {
      const ta = a.latestTest ? new Date(a.latestTest.test_date).getTime() : 0;
      const tb = b.latestTest ? new Date(b.latestTest.test_date).getTime() : 0;
      return tb - ta;
    });
  } else if (sortBy === 'name') {
    filtered.sort((a, b) => a.name.localeCompare(b.name));
  }

  return (
    <div className="animate-fadeIn pb-20 sm:pb-0">
      {/* Stats Grid */}
      {widgets.find(w => w.id === 'stats')?.visible !== false && <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[
          { icon: '👥', label: '전체 환자', value: totalPatients, color: 'bg-blue-500/10' },
          { icon: '✓', label: '이번 주 검사', value: weeklyTests, color: 'bg-green-500/10' },
          { icon: '⚠️', label: '주의 필요', value: cautionCount, color: 'bg-orange-500/10' },
          { icon: '📊', label: '평균 시간', value: `${avgTime}초`, color: 'bg-cyan-500/10' },
        ].map(s => (
          <div key={s.label} className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-5 flex items-center gap-4 transition-all hover:-translate-y-0.5 hover:shadow-md">
            <div className={`w-14 h-14 ${s.color} rounded-xl flex items-center justify-center text-2xl`} role="img" aria-label={s.label}>{s.icon}</div>
            <div>
              <div className="text-sm text-gray-500 dark:text-gray-400 mb-0.5">{s.label}</div>
              <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{s.value}</div>
            </div>
          </div>
        ))}
      </div>}

      {/* Admin notice */}
      {isAdmin && (
        <div className="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300 px-4 py-3 rounded-xl mb-6 text-sm flex items-center gap-2">
          <span className="text-lg">ℹ️</span>
          관리자는 환자 등록/수정/삭제를 할 수 없습니다. 환자 관리는 승인된 물리치료사만 가능합니다.
        </div>
      )}

      {/* Customize Panel */}
      {showCustomize && (
        <CustomizePanel
          widgets={widgets}
          onToggle={toggleWidget}
          onMove={moveWidget}
          onReset={resetPrefs}
          onClose={() => setShowCustomize(false)}
        />
      )}

      {/* Dynamic Widgets */}
      {!showCustomize && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
          {widgets.filter(w => w.visible && w.id !== 'stats').map(w => {
            switch (w.id) {
              case 'recentTests':
                return <RecentTestsWidget key={w.id} />;
              case 'riskPatients':
                return <RiskPatientsWidget key={w.id} patients={patients.filter(p => p.latestTest).map(p => ({
                  id: p.id, name: p.name, patient_number: p.patient_number,
                  speed: p.latestTest?.walk_speed_mps || 0,
                  walkTime: p.latestTest?.walk_time_seconds || 0,
                }))} />;
              case 'speedDistribution':
                return <SpeedDistributionWidget key={w.id} />;
              case 'weeklyActivity':
                return <WeeklyActivityWidget key={w.id} />;
              default:
                return null;
            }
          })}
        </div>
      )}

      {/* Filter Bar */}
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4 mb-6 flex flex-wrap gap-4 items-center">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px]">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
          </span>
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="환자 이름 또는 번호 검색..."
            aria-label="환자 이름 또는 번호 검색"
            className="w-full pl-9 pr-10 py-2.5 border-2 border-gray-200 dark:border-gray-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#0066CC] focus:border-[#0066CC] dark:bg-gray-700 dark:text-gray-100 transition-colors"
          />
          {searchQuery && (
            <button onClick={() => { setSearchQuery(''); loadPatients(); }}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              aria-label="검색어 지우기">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          )}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">위험도:</span>
          <select value={filterRisk} onChange={e => setFilterRisk(e.target.value)}
            aria-label="위험도 필터"
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm dark:bg-gray-700 dark:text-gray-100">
            <option value="all">전체</option>
            <option value="normal">정상</option>
            <option value="caution">주의</option>
            <option value="risk">위험</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">정렬:</span>
          <select value={sortBy} onChange={e => setSortBy(e.target.value)}
            aria-label="정렬 기준"
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm dark:bg-gray-700 dark:text-gray-100">
            <option value="recent">최근 검사순</option>
            <option value="name">이름순</option>
          </select>
        </div>

        {allTags.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">태그:</span>
            <select value={filterTag} onChange={e => setFilterTag(e.target.value)}
              aria-label="태그 필터"
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm dark:bg-gray-700 dark:text-gray-100">
              <option value="">전체</option>
              {allTags.map(tag => (
                <option key={tag.id} value={tag.id}>{tag.name}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Section Header */}
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          환자 목록
          {searchMode && <span aria-live="polite" className="text-base font-normal text-gray-500 ml-2">({filtered.length}명 검색됨)</span>}
        </h2>
        <div className="flex gap-3">
          <button
            onClick={() => setShowCustomize(!showCustomize)}
            className="px-4 py-2.5 rounded-lg font-semibold text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-600 transition-all inline-flex items-center gap-1.5"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            위젯 설정
          </button>
          {isApprovedTherapist && (
            <Link to="/patients/new"
              className="px-5 py-2.5 rounded-lg font-semibold text-white text-sm transition-all hover:-translate-y-0.5 hover:shadow-lg inline-flex items-center gap-2"
              style={{ background: '#0066CC' }}>
              <span>+</span> 새 환자 등록
            </Link>
          )}
          {isAdmin && (
            <Link to="/admin/therapists"
              className="px-5 py-2.5 rounded-lg font-semibold text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-600 transition-all inline-flex items-center gap-2">
              👨‍⚕️ 치료사 관리
            </Link>
          )}
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex justify-center items-center py-12" role="status">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <span className="sr-only">로딩 중...</span>
        </div>
      )}

      {/* Error */}
      {error && (
        <div role="alert" className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-3 rounded-xl mb-6">{error}</div>
      )}

      {/* Patients Grid */}
      {!loading && !error && (
        <>
          {filtered.length === 0 ? (
            <div className="text-center py-16 bg-white dark:bg-gray-800 rounded-xl border-2 border-dashed border-gray-300 dark:border-gray-600">
              <div className="text-5xl mb-4 opacity-50">👥</div>
              <h3 className="text-xl font-bold mb-2 text-gray-900 dark:text-gray-100">
                {searchMode ? '검색 결과가 없습니다' : '등록된 환자가 없습니다'}
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                {searchMode ? '다른 검색어를 시도해보세요.' : '새 환자를 등록해주세요.'}
              </p>
              {!searchMode && isApprovedTherapist && (
                <Link to="/patients/new" className="px-6 py-3 rounded-lg font-semibold text-white inline-block" style={{ background: '#0066CC' }}>
                  + 새 환자 등록
                </Link>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
              {filtered.map(patient => {
                const age = calculateAge(patient.birth_date);
                const lt = patient.latestTest;
                const walkTime = lt?.walk_time_seconds || 0;
                const status = walkTime > 0 ? getTimeStatus(walkTime) : null;
                const riskScore = lt?.analysis_data && 'fall_risk_score' in lt.analysis_data
                  ? (lt.analysis_data as any).fall_risk_score : null;

                return (
                  <Link key={patient.id} to={`/patients/${patient.id}`}
                    className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6 transition-all hover:-translate-y-1 hover:shadow-xl hover:border-[#0066CC] dark:hover:border-[#0066CC] block">
                    {/* Header */}
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-0.5">{patient.name}</h3>
                        <div className="text-sm text-gray-500 dark:text-gray-400">#{patient.patient_number}</div>
                        {patient.tags && patient.tags.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-1">
                            {patient.tags.slice(0, 3).map(tag => (
                              <TagBadge key={tag.id} tag={tag} />
                            ))}
                            {patient.tags.length > 3 && (
                              <span className="text-xs text-gray-400">+{patient.tags.length - 3}</span>
                            )}
                          </div>
                        )}
                      </div>
                      {status && (
                        <span className={`px-3 py-1 rounded-full text-sm font-semibold ${status.cls}`}>{status.label}</span>
                      )}
                    </div>

                    {/* Details Grid */}
                    <div className="grid grid-cols-2 gap-3 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg mb-4">
                      <div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 mb-0.5">성별/나이</div>
                        <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">{patient.gender === 'M' ? '남성' : '여성'} / {age}세</div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 mb-0.5">키</div>
                        <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">{patient.height_cm} cm</div>
                      </div>
                      {patient.diagnosis && (
                        <div>
                          <div className="text-xs text-gray-500 dark:text-gray-400 mb-0.5">진단명</div>
                          <div className="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">{patient.diagnosis}</div>
                        </div>
                      )}
                      <div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 mb-0.5">총 검사 횟수</div>
                        <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">{patient.testCount}회</div>
                      </div>
                    </div>

                    {/* Metrics */}
                    {lt && walkTime > 0 && (
                      <div className="grid grid-cols-2 gap-3 mb-4">
                        <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg border-l-[3px] border-[#0066CC]">
                          <div className="text-xs text-gray-500 dark:text-gray-400 mb-0.5">최근 보행 시간</div>
                          <div className="text-xl font-bold text-[#0066CC]">
                            {walkTime.toFixed(1)}<span className="text-sm font-normal text-gray-500 ml-1">초</span>
                          </div>
                        </div>
                        <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg border-l-[3px] border-[#0066CC]">
                          <div className="text-xs text-gray-500 dark:text-gray-400 mb-0.5">
                            {riskScore !== null ? '낙상 위험 점수' : '보행 속도'}
                          </div>
                          <div className="text-xl font-bold text-[#0066CC]">
                            {riskScore !== null
                              ? <>{riskScore}<span className="text-sm font-normal text-gray-500 ml-1">/100</span></>
                              : <>{lt.walk_speed_mps.toFixed(2)}<span className="text-sm font-normal text-gray-500 ml-1">m/s</span></>
                            }
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Footer */}
                    <div className="flex justify-between items-center pt-4 border-t border-gray-200 dark:border-gray-600">
                      <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1.5">
                        {lt && (
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                            (lt.test_type || '10MWT') === 'TUG'
                              ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'
                              : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                          }`}>
                            {lt.test_type || '10MWT'}
                          </span>
                        )}
                        {lt ? daysAgo(lt.test_date) : '검사 기록 없음'}
                      </div>
                      <div className="flex gap-1">
                        {isApprovedTherapist && (
                          <span className="w-11 h-11 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 rounded-md flex items-center justify-center text-sm hover:bg-[#0066CC] hover:text-white hover:border-[#0066CC] transition-colors" aria-hidden="true">📹</span>
                        )}
                        <span className="w-11 h-11 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 rounded-md flex items-center justify-center text-sm hover:bg-[#0066CC] hover:text-white hover:border-[#0066CC] transition-colors" aria-hidden="true">📊</span>
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}
