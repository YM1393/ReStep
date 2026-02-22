import { useState, useEffect, lazy, Suspense } from 'react';
import { useParams, Link } from 'react-router-dom';
import { patientApi, testApi } from '../services/api';
import type { Patient, WalkTest, ComparisonResult, TestType, TUGAnalysisData, BBSAnalysisData, PatientStats, ClinicalVariables } from '../types';
import VideoModal from '../components/VideoModal';
import TUGResult from '../components/TUGResult';
import BBSResult from '../components/BBSResult';
import ClinicalNotesEditor from '../components/ClinicalNotesEditor';
import type { AnalysisData } from '../types';
import WalkingRouteCard from '../components/WalkingRouteCard';

// Lazy-load heavy components (recharts, etc.)
const SpeedChart = lazy(() => import('../components/SpeedChart'));
const FallRiskScore = lazy(() => import('../components/FallRiskScore'));
const NotesAnalysisSummary = lazy(() => import('../components/NotesAnalysis'));
const ComparisonReport = lazy(() => import('../components/ComparisonReport'));
const VideoComparison = lazy(() => import('../components/VideoComparison'));
const ConfidenceScoreComponent = lazy(() => import('../components/ConfidenceScore'));

const ChartLoader = () => (
  <div className="flex items-center justify-center py-8">
    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500" />
  </div>
);

export default function History() {
  const { id } = useParams();

  const [patient, setPatient] = useState<Patient | null>(null);
  const [tests, setTests] = useState<WalkTest[]>([]);
  const [_comparison, setComparison] = useState<ComparisonResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedVideoTest, setSelectedVideoTest] = useState<WalkTest | null>(null);
  const [editingTestId, setEditingTestId] = useState<string | null>(null);
  const [editingDate, setEditingDate] = useState('');
  const [editingNotesId, setEditingNotesId] = useState<string | null>(null);
  const [editingNotes, setEditingNotes] = useState('');
  const [selectedTestType, setSelectedTestType] = useState<TestType | 'ALL'>('ALL');
  const [stats, setStats] = useState<PatientStats | null>(null);
  const [emailTestId, setEmailTestId] = useState<string | null>(null);
  const [emailTo, setEmailTo] = useState('');
  const [emailMessage, setEmailMessage] = useState('');
  const [emailSending, setEmailSending] = useState(false);
  const [emailResult, setEmailResult] = useState<{ success: boolean; message: string } | null>(null);

  useEffect(() => {
    if (id) loadData(id);
  }, [id]);

  const loadData = async (patientId: string) => {
    try {
      setLoading(true);
      const [patientData, testsData] = await Promise.all([
        patientApi.getById(patientId),
        testApi.getPatientTests(patientId),
      ]);
      setPatient(patientData);
      setTests(testsData);
      setError(null);
      setLoading(false);
      // Load optional data in background (non-blocking)
      if (testsData.length >= 1) {
        testApi.compare(patientId).then(setComparison).catch(() => {});
        testApi.getStats(patientId, testsData[0]?.test_type || '10MWT').then(setStats).catch(() => {});
      }
    } catch (err) {
      setError('히스토리를 불러오는데 실패했습니다.');
      console.error(err);
      setLoading(false);
    }
  };

  const handleDeleteTest = async (testId: string) => {
    if (!window.confirm('정말 이 검사 기록을 삭제하시겠습니까?')) return;
    try {
      await testApi.delete(testId);
      setTests(tests.filter((t) => t.id !== testId));
    } catch (err) {
      alert('삭제에 실패했습니다.');
      console.error(err);
    }
  };

  const handleEditDate = (test: WalkTest) => {
    setEditingTestId(test.id);
    const date = new Date(test.test_date);
    setEditingDate(date.toISOString().slice(0, 16));
  };

  const handleSaveDate = async (testId: string) => {
    try {
      const newDate = new Date(editingDate).toISOString();
      await testApi.updateTestDate(testId, newDate);
      setTests(tests.map(t => t.id === testId ? { ...t, test_date: newDate } : t));
      setEditingTestId(null);
      if (id) {
        try {
          const comparisonData = await testApi.compare(id);
          setComparison(comparisonData);
        } catch (err) { /* ignore */ }
      }
    } catch (err) {
      alert('날짜 수정에 실패했습니다.');
      console.error(err);
    }
  };

  const handleEditNotes = (test: WalkTest) => {
    setEditingNotesId(test.id);
    setEditingNotes(test.notes || '');
  };


  const calculateAge = (birthDate: string): number => {
    const today = new Date();
    const birth = new Date(birthDate);
    let age = today.getFullYear() - birth.getFullYear();
    const monthDiff = today.getMonth() - birth.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) age--;
    return age;
  };

  const getTimeStatus = (time: number) => {
    if (time <= 8.3) return { label: '정상', bgColor: 'bg-green-100 dark:bg-green-900/30', textColor: 'text-green-700 dark:text-green-400' };
    if (time <= 10.0) return { label: '경도', bgColor: 'bg-blue-100 dark:bg-blue-900/30', textColor: 'text-blue-700 dark:text-blue-400' };
    if (time <= 12.5) return { label: '주의', bgColor: 'bg-orange-100 dark:bg-orange-900/30', textColor: 'text-orange-700 dark:text-orange-400' };
    return { label: '위험', bgColor: 'bg-red-100 dark:bg-red-900/30', textColor: 'text-red-700 dark:text-red-400' };
  };

  const getTUGAssessment = (time: number) => {
    if (time < 10) return { label: '정상', bgColor: 'bg-green-100 dark:bg-green-900/30', textColor: 'text-green-700 dark:text-green-400' };
    if (time < 20) return { label: '양호', bgColor: 'bg-blue-100 dark:bg-blue-900/30', textColor: 'text-blue-700 dark:text-blue-400' };
    if (time < 30) return { label: '주의', bgColor: 'bg-orange-100 dark:bg-orange-900/30', textColor: 'text-orange-700 dark:text-orange-400' };
    return { label: '위험', bgColor: 'bg-red-100 dark:bg-red-900/30', textColor: 'text-red-700 dark:text-red-400' };
  };

  const getBBSAssessment = (totalScore: number) => {
    if (totalScore >= 41) return { label: '독립적', bgColor: 'bg-green-100 dark:bg-green-900/30', textColor: 'text-green-700 dark:text-green-400' };
    if (totalScore >= 21) return { label: '보조 보행', bgColor: 'bg-yellow-100 dark:bg-yellow-900/30', textColor: 'text-yellow-800 dark:text-yellow-300' };
    return { label: '휠체어 의존', bgColor: 'bg-red-100 dark:bg-red-900/30', textColor: 'text-red-700 dark:text-red-400' };
  };

  const getTestAssessment = (test: WalkTest) => {
    if (test.test_type === 'TUG') return getTUGAssessment(test.walk_time_seconds);
    if (test.test_type === 'BBS') return getBBSAssessment(test.walk_time_seconds);
    return getTimeStatus(test.walk_time_seconds);
  };

  const getTestTypeBadge = (type: string) => {
    if (type === 'TUG') return { label: 'TUG', bg: 'bg-green-100 dark:bg-green-900/30', text: 'text-green-700 dark:text-green-400' };
    if (type === 'BBS') return { label: 'BBS', bg: 'bg-purple-100 dark:bg-purple-900/30', text: 'text-purple-700 dark:text-purple-400' };
    return { label: '10MWT', bg: 'bg-blue-100 dark:bg-blue-900/30', text: 'text-blue-700 dark:text-blue-400' };
  };

  const filteredTests = selectedTestType === 'ALL'
    ? tests
    : tests.filter(t => (t.test_type || '10MWT') === selectedTestType);

  const testCounts = {
    all: tests.length,
    '10MWT': tests.filter(t => (t.test_type || '10MWT') === '10MWT').length,
    'TUG': tests.filter(t => t.test_type === 'TUG').length,
    'BBS': tests.filter(t => t.test_type === 'BBS').length,
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12" role="status">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        <span className="sr-only">로딩 중...</span>
      </div>
    );
  }

  if (!patient) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500">{error || '환자를 찾을 수 없습니다.'}</p>
        <Link to="/" className="text-blue-500 hover:underline mt-4 inline-block">
          대시보드로 돌아가기
        </Link>
      </div>
    );
  }

  return (
    <div className="animate-fadeIn max-w-7xl mx-auto pb-20 sm:pb-0">
      {/* Page Header */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-sm mb-6">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 mb-4">
          <Link to="/" className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">대시보드</Link>
          <span>›</span>
          <Link to={`/patients/${patient.id}`} className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
            {patient.name}
          </Link>
          <span>›</span>
          <span className="text-gray-800 dark:text-gray-200">검사 히스토리</span>
        </div>

        {/* Header Content */}
        <div className="flex flex-col sm:flex-row justify-between items-start gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">검사 히스토리</h1>
            <div className="flex flex-wrap gap-4 text-sm text-gray-600 dark:text-gray-400 mt-2">
              <span>{patient.name}</span>
              <span>#{patient.patient_number}</span>
              <span>{patient.gender === 'M' ? '남' : '여'} · {calculateAge(patient.birth_date)}세</span>
              {patient.diagnosis && <span>{patient.diagnosis}</span>}
            </div>
          </div>
          <Link
            to={`/patients/${patient.id}/test`}
            className="px-4 py-2.5 bg-blue-600 text-white rounded-lg font-semibold text-sm hover:bg-blue-700 transition-all flex items-center gap-2 flex-shrink-0"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            새 검사 시작
          </Link>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        <div className="bg-white dark:bg-gray-800 p-4 rounded-2xl shadow-sm text-center">
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">총 검사</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{tests.length}<span className="text-sm font-normal text-gray-400">회</span></p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-4 rounded-2xl shadow-sm text-center">
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">10MWT</p>
          <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">{testCounts['10MWT']}<span className="text-sm font-normal text-gray-400">회</span></p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-4 rounded-2xl shadow-sm text-center">
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">TUG</p>
          <p className="text-2xl font-bold text-green-600 dark:text-green-400">{testCounts['TUG']}<span className="text-sm font-normal text-gray-400">회</span></p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-4 rounded-2xl shadow-sm text-center">
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">BBS</p>
          <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">{testCounts['BBS']}<span className="text-sm font-normal text-gray-400">회</span></p>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="bg-white dark:bg-gray-800 p-4 rounded-2xl shadow-sm mb-6">
        <div className="flex gap-2 flex-wrap">
          {([
            { key: 'ALL' as const, label: '전체', count: testCounts.all, active: 'bg-gray-800 text-white dark:bg-gray-100 dark:text-gray-800', inactive: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600' },
            { key: '10MWT' as const, label: '10m 보행', count: testCounts['10MWT'], active: 'bg-blue-600 text-white', inactive: 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/50' },
            { key: 'TUG' as const, label: 'TUG', count: testCounts['TUG'], active: 'bg-green-600 text-white', inactive: 'bg-green-50 text-green-600 dark:bg-green-900/30 dark:text-green-400 hover:bg-green-100 dark:hover:bg-green-900/50' },
            { key: 'BBS' as const, label: 'BBS', count: testCounts['BBS'], active: 'bg-purple-600 text-white', inactive: 'bg-purple-50 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400 hover:bg-purple-100 dark:hover:bg-purple-900/50' },
          ]).map(tab => (
            <button
              key={tab.key}
              onClick={() => setSelectedTestType(tab.key)}
              className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                selectedTestType === tab.key ? tab.active : tab.inactive
              }`}
            >
              {tab.label} ({tab.count})
            </button>
          ))}
        </div>
      </div>

      {/* Main Grid: 2fr + 1fr */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Comparison Analysis */}
          {filteredTests.length >= 2 && (
            <div className="bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-sm">
              <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-4">
                최근 검사 비교
              </h3>

              {/* Speed comparison - only for 10MWT tab */}
              {selectedTestType !== 'TUG' && selectedTestType !== 'BBS' && selectedTestType !== 'ALL' && (
                <div className="mb-4">
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-2 font-medium">보행 속도 (m/s)</p>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="text-center p-4 bg-gray-50 dark:bg-gray-700/50 rounded-xl">
                      <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">이전</p>
                      <p className="text-xl font-bold text-gray-700 dark:text-gray-200">{filteredTests[1].walk_speed_mps.toFixed(2)}</p>
                      <p className="text-xs text-gray-400 dark:text-gray-400 mt-1">
                        {new Date(filteredTests[1].test_date).toLocaleDateString('ko-KR')}
                      </p>
                    </div>
                    <div className="flex items-center justify-center">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                        (filteredTests[0].walk_speed_mps - filteredTests[1].walk_speed_mps) > 0
                          ? 'bg-green-500' : (filteredTests[0].walk_speed_mps - filteredTests[1].walk_speed_mps) < 0
                          ? 'bg-red-500' : 'bg-gray-400'
                      }`}>
                        <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                        </svg>
                      </div>
                    </div>
                    <div className="text-center p-4 bg-gray-50 dark:bg-gray-700/50 rounded-xl">
                      <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">최근</p>
                      <p className="text-xl font-bold text-blue-600 dark:text-blue-400">{filteredTests[0].walk_speed_mps.toFixed(2)}</p>
                      <p className="text-xs text-gray-400 dark:text-gray-400 mt-1">
                        {new Date(filteredTests[0].test_date).toLocaleDateString('ko-KR')}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Time comparison - not for ALL tab */}
              {selectedTestType !== 'ALL' && (
              <div className="mb-4">
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2 font-medium">
                  {selectedTestType === 'TUG' ? 'TUG 시간 (초)' : '보행 시간 (초)'}
                </p>
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-center p-4 bg-gray-50 dark:bg-gray-700/50 rounded-xl">
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">이전</p>
                    <p className="text-xl font-bold text-gray-700 dark:text-gray-200">{filteredTests[1].walk_time_seconds.toFixed(2)}</p>
                    {selectedTestType === 'TUG' && (
                      <p className="text-xs text-gray-400 dark:text-gray-400 mt-1">
                        {new Date(filteredTests[1].test_date).toLocaleDateString('ko-KR')}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center justify-center">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                      (filteredTests[0].walk_time_seconds - filteredTests[1].walk_time_seconds) < 0
                        ? 'bg-green-500' : (filteredTests[0].walk_time_seconds - filteredTests[1].walk_time_seconds) > 0
                        ? 'bg-red-500' : 'bg-gray-400'
                    }`}>
                      <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                      </svg>
                    </div>
                  </div>
                  <div className="text-center p-4 bg-gray-50 dark:bg-gray-700/50 rounded-xl">
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">최근</p>
                    <p className={`text-xl font-bold ${selectedTestType === 'TUG' ? 'text-green-600 dark:text-green-400' : 'text-purple-600 dark:text-purple-400'}`}>
                      {filteredTests[0].walk_time_seconds.toFixed(2)}
                    </p>
                    {selectedTestType === 'TUG' && (
                      <p className="text-xs text-gray-400 dark:text-gray-400 mt-1">
                        {new Date(filteredTests[0].test_date).toLocaleDateString('ko-KR')}
                      </p>
                    )}
                  </div>
                </div>
              </div>
              )}

              {/* Comparison Message - not for ALL tab */}
              {selectedTestType !== 'ALL' && (() => {
                const timeDiff = filteredTests[0].walk_time_seconds - filteredTests[1].walk_time_seconds;
                let message = '';
                let colorClass = '';
                if (selectedTestType === 'TUG') {
                  if (timeDiff < -1) { message = `TUG 시간이 ${Math.abs(timeDiff).toFixed(1)}초 단축되어 기능이 향상되었습니다.`; colorClass = 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400'; }
                  else if (timeDiff > 1) { message = `TUG 시간이 ${timeDiff.toFixed(1)}초 증가하여 주의가 필요합니다.`; colorClass = 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400'; }
                  else { message = 'TUG 시간 변화가 미미합니다.'; colorClass = 'bg-yellow-50 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'; }
                } else {
                  if (timeDiff < -0.5) { message = `보행 시간이 ${Math.abs(timeDiff).toFixed(1)}초 단축되어 낙상 위험이 감소된 것으로 추정됩니다.`; colorClass = 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400'; }
                  else if (timeDiff > 0.5) { message = `보행 시간이 ${timeDiff.toFixed(1)}초 증가하여 낙상 위험이 증가된 것으로 추정됩니다.`; colorClass = 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400'; }
                  else { message = '보행 시간 변화가 미미하여 낙상 위험도에 큰 변화가 없는 것으로 추정됩니다.'; colorClass = 'bg-yellow-50 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'; }
                }
                return <div className={`p-3 rounded-xl text-sm font-medium ${colorClass}`}>{message}</div>;
              })()}
            </div>
          )}

          {/* Speed Chart (not for BBS) */}
          {filteredTests.length > 0 && selectedTestType !== 'BBS' && (
            <Suspense fallback={<ChartLoader />}>
              <SpeedChart tests={filteredTests} testType={selectedTestType} normativeRange={stats?.normative?.normative} />
            </Suspense>
          )}

          {/* Clinical Gait Variables Summary */}
          {filteredTests.length > 0 && selectedTestType !== 'BBS' && (() => {
            const latestAnalysis = filteredTests[0]?.analysis_data as AnalysisData | undefined;
            const cv = latestAnalysis?.clinical_variables as ClinicalVariables | undefined;
            if (!cv || Object.keys(cv).length === 0) return null;
            return (
              <div className="bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-sm">
                <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-4">
                  보행 임상 변수
                  <span className="text-sm font-normal text-gray-500 dark:text-gray-400 ml-2">(최신 검사)</span>
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                  {cv.cadence && (filteredTests[0]?.test_type || '10MWT') !== 'TUG' && (
                    <div className="bg-gray-50 dark:bg-gray-700/50 p-3 rounded-xl border-l-4 border-indigo-500">
                      <p className="text-xs text-gray-500 dark:text-gray-400">분당 걸음수</p>
                      <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{cv.cadence.value}<span className="text-xs font-normal text-gray-500 ml-1">steps/min</span></p>
                      <p className={`text-xs ${cv.cadence.value >= 100 && cv.cadence.value <= 130 ? 'text-green-600' : 'text-orange-600'}`}>
                        {cv.cadence.value >= 100 && cv.cadence.value <= 130 ? 'Normal' : 'Abnormal'}
                      </p>
                    </div>
                  )}
                  {cv.cadence && cv.cadence.total_steps > 0 && (filteredTests[0]?.test_type || '10MWT') !== 'TUG' && (
                    <div className="bg-gray-50 dark:bg-gray-700/50 p-3 rounded-xl border-l-4 border-violet-500">
                      <p className="text-xs text-gray-500 dark:text-gray-400">총 걸음수</p>
                      <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{cv.cadence.total_steps}<span className="text-xs font-normal text-gray-500 ml-1">걸음</span></p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">10m 보행 기준</p>
                    </div>
                  )}
                  {selectedTestType !== '10MWT' && cv.stride_length && (
                    <div className="bg-gray-50 dark:bg-gray-700/50 p-3 rounded-xl border-l-4 border-blue-500">
                      <p className="text-xs text-gray-500 dark:text-gray-400">보폭</p>
                      <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{cv.stride_length.value}<span className="text-xs font-normal text-gray-500 ml-1">m</span></p>
                      <p className={`text-xs ${cv.stride_length.value >= 1.2 && cv.stride_length.value <= 1.8 ? 'text-green-600' : 'text-orange-600'}`}>
                        {cv.stride_length.value >= 1.2 && cv.stride_length.value <= 1.8 ? 'Normal' : 'Abnormal'}
                      </p>
                    </div>
                  )}
                  {cv.double_support && (
                    <div className="bg-gray-50 dark:bg-gray-700/50 p-3 rounded-xl border-l-4 border-cyan-500">
                      <p className="text-xs text-gray-500 dark:text-gray-400">이중 지지기</p>
                      <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{cv.double_support.value}<span className="text-xs font-normal text-gray-500 ml-1">%</span></p>
                      <p className={`text-xs ${cv.double_support.value <= 30 ? 'text-green-600' : 'text-orange-600'}`}>
                        {cv.double_support.value <= 30 ? 'Normal' : 'Elevated'}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            );
          })()}

          {/* Test Records List */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-sm">
            <div className="flex justify-between items-center mb-6 pb-4 border-b-2 border-gray-100 dark:border-gray-700">
              <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-3">
                검사 기록
                <span className="px-2.5 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-sm font-semibold rounded-full">
                  {filteredTests.length}
                </span>
              </h2>
            </div>

            {filteredTests.length === 0 ? (
              <div className="text-center py-12">
                <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                </div>
                <p className="text-gray-500 dark:text-gray-400">
                  {selectedTestType === 'ALL' ? '검사 기록이 없습니다' : `${selectedTestType} 검사 기록이 없습니다`}
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {filteredTests.map((test, index) => {
                  const assessment = getTestAssessment(test);
                  const typeBadge = getTestTypeBadge(test.test_type || '10MWT');

                  return (
                    <div key={test.id} className="border border-gray-100 dark:border-gray-700 rounded-xl overflow-hidden hover:border-gray-200 dark:hover:border-gray-600 transition-colors">
                      <div className="p-4 flex items-center justify-between gap-4">
                        {/* Left: number + info */}
                        <div className="flex items-center gap-4 min-w-0 flex-1">
                          <div className="w-10 h-10 rounded-xl bg-gray-100 dark:bg-gray-700 flex items-center justify-center flex-shrink-0">
                            <span className="font-bold text-sm text-gray-600 dark:text-gray-300">{filteredTests.length - index}</span>
                          </div>

                          <div className="min-w-0 flex-1">
                            {editingTestId === test.id ? (
                              <div className="flex items-center gap-2">
                                <input
                                  type="datetime-local"
                                  value={editingDate}
                                  onChange={(e) => setEditingDate(e.target.value)}
                                  className="text-sm border dark:border-gray-600 rounded-lg px-3 py-1.5 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200"
                                />
                                <button onClick={() => handleSaveDate(test.id)} className="p-1.5 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/30 rounded-lg">
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                                </button>
                                <button onClick={() => setEditingTestId(null)} className="p-1.5 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                                </button>
                              </div>
                            ) : (
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${typeBadge.bg} ${typeBadge.text}`}>
                                  {typeBadge.label}
                                </span>
                                <span className="font-medium text-gray-900 dark:text-gray-100 text-sm flex items-center gap-1">
                                  {new Date(test.test_date).toLocaleDateString('ko-KR')}
                                  <button onClick={() => handleEditDate(test)} className="text-gray-400 hover:text-blue-500 dark:hover:text-blue-400">
                                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
                                  </button>
                                </span>
                                {selectedTestType !== 'ALL' && (
                                  <>
                                    <span className="text-gray-300 dark:text-gray-600">·</span>
                                    {test.test_type === 'BBS' ? (
                                      <span className="text-sm text-purple-600 dark:text-purple-400 font-semibold">{test.walk_time_seconds}점/56</span>
                                    ) : (
                                      <>
                                        <span className="text-sm text-gray-600 dark:text-gray-400">{test.walk_time_seconds.toFixed(2)}초</span>
                                        {(test.test_type || '10MWT') !== 'TUG' && (
                                          <>
                                            <span className="text-gray-300 dark:text-gray-600">·</span>
                                            <span className="text-sm font-semibold text-blue-600 dark:text-blue-400">{test.walk_speed_mps.toFixed(2)}m/s</span>
                                          </>
                                        )}
                                      </>
                                    )}
                                  </>
                                )}
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Right: badge + actions */}
                        <div className="flex items-center gap-3 flex-shrink-0">
                          {(test.analysis_data as AnalysisData)?.confidence_score && (
                            <Suspense fallback={null}>
                              <ConfidenceScoreComponent
                                confidence={(test.analysis_data as AnalysisData).confidence_score!}
                                compact
                              />
                            </Suspense>
                          )}
                          <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${assessment.bgColor} ${assessment.textColor}`}>
                            {assessment.label}
                          </span>
                          <div className="flex items-center gap-1">
                            <a href={testApi.downloadPdf(test.id)} className="flex flex-col items-center p-2 text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg transition-colors" aria-label="PDF 다운로드">
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                              <span className="text-[10px] mt-0.5" aria-hidden="true">PDF</span>
                            </a>
                            <a href={testApi.downloadCsv(test.id)} className="flex flex-col items-center p-2 text-gray-400 hover:text-green-500 dark:hover:text-green-400 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg transition-colors" aria-label="CSV 다운로드">
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                              <span className="text-[10px] mt-0.5" aria-hidden="true">CSV</span>
                            </a>
                            <button onClick={() => { setEmailTestId(test.id); setEmailResult(null); }} className="flex flex-col items-center p-2 text-gray-400 hover:text-green-600 dark:hover:text-green-400 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg transition-colors" aria-label="이메일 전송">
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>
                              <span className="text-[10px] mt-0.5" aria-hidden="true">Email</span>
                            </button>
                            {test.video_url && (
                              <button onClick={() => setSelectedVideoTest(test)} className="flex flex-col items-center p-2 text-gray-400 hover:text-purple-500 dark:hover:text-purple-400 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg transition-colors" aria-label="영상 보기">
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                                <span className="text-[10px] mt-0.5" aria-hidden="true">영상</span>
                              </button>
                            )}
                            <button
                              onClick={() => handleEditNotes(test)}
                              className={`flex flex-col items-center p-2 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg transition-colors ${test.notes ? 'text-yellow-500' : 'text-gray-400 hover:text-yellow-500'}`}
                              aria-label="메모 편집"
                            >
                              <svg className="w-4 h-4" fill={test.notes ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                              <span className="text-[10px] mt-0.5" aria-hidden="true">메모</span>
                            </button>
                            <button onClick={() => handleDeleteTest(test.id)} className="flex flex-col items-center p-2 text-gray-400 hover:text-red-500 dark:hover:text-red-400 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg transition-colors" aria-label="검사 기록 삭제">
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                              <span className="text-[10px] mt-0.5" aria-hidden="true">삭제</span>
                            </button>
                          </div>
                        </div>
                      </div>

                      {/* Clinical Gait Variables per test */}
                      {(() => {
                        const testCv = (test.analysis_data as AnalysisData | undefined)?.clinical_variables as ClinicalVariables | undefined;
                        if (!testCv || Object.keys(testCv).length === 0 || test.test_type === 'BBS') return null;
                        return (
                          <div className="px-4 pb-3 border-t border-gray-100 dark:border-gray-700 pt-3">
                            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 text-center">
                              {testCv.cadence && (test.test_type || '10MWT') !== 'TUG' && (
                                <div className="bg-gray-50 dark:bg-gray-700/50 p-2 rounded-lg">
                                  <p className="text-[10px] text-gray-400">분당 걸음수</p>
                                  <p className={`text-sm font-bold ${testCv.cadence.value >= 100 && testCv.cadence.value <= 130 ? 'text-green-600' : 'text-orange-600'}`}>{testCv.cadence.value}<span className="text-[10px] font-normal"> spm</span></p>
                                </div>
                              )}
                              {(test.test_type || '10MWT') !== '10MWT' && testCv.stride_length && (
                                <div className="bg-gray-50 dark:bg-gray-700/50 p-2 rounded-lg">
                                  <p className="text-[10px] text-gray-400">보폭</p>
                                  <p className={`text-sm font-bold ${testCv.stride_length.value >= 1.2 && testCv.stride_length.value <= 1.8 ? 'text-green-600' : 'text-orange-600'}`}>{testCv.stride_length.value}<span className="text-[10px] font-normal"> m</span></p>
                                </div>
                              )}
                              {testCv.double_support && (
                                <div className="bg-gray-50 dark:bg-gray-700/50 p-2 rounded-lg">
                                  <p className="text-[10px] text-gray-400">이중 지지기</p>
                                  <p className={`text-sm font-bold ${testCv.double_support.value <= 30 ? 'text-green-600' : 'text-orange-600'}`}>{testCv.double_support.value}<span className="text-[10px] font-normal"> %</span></p>
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })()}

                      {/* Notes editing/display */}
                      {editingNotesId === test.id ? (
                        <div className="px-4 pb-4 border-t border-gray-100 dark:border-gray-700 pt-3">
                          <ClinicalNotesEditor
                            notes={editingNotes}
                            onSave={async (newNotes) => {
                              try {
                                await testApi.updateTestNotes(test.id, newNotes);
                                setTests(tests.map(t => t.id === test.id ? { ...t, notes: newNotes } : t));
                                setEditingNotesId(null);
                              } catch (err) {
                                alert('메모 저장에 실패했습니다.');
                                console.error(err);
                              }
                            }}
                            compact
                          />
                          <button onClick={() => setEditingNotesId(null)} className="mt-2 text-xs text-gray-400 hover:text-gray-600">
                            닫기
                          </button>
                        </div>
                      ) : test.notes ? (
                        <div className="px-4 pb-4 border-t border-gray-100 dark:border-gray-700 pt-3">
                          <div className="flex items-start gap-2">
                            <svg className="w-4 h-4 text-yellow-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
                              <path d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                            <p className="text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap">{test.notes}</p>
                          </div>
                        </div>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* TUG 감지 기준 + 검사 기준 (검사 기록 아래) */}
          {selectedTestType === 'TUG' && filteredTests.length > 0 && (
            <div className="bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-sm">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* TUG 검사 기준 */}
                <div>
                  <h3 className="font-bold text-gray-900 dark:text-gray-100 mb-4 flex items-center">
                    <svg className="w-5 h-5 mr-2 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    TUG 검사 기준
                  </h3>
                  <div className="space-y-2">
                    {[
                      { color: 'bg-green-500', label: '정상: 10초 미만', desc: '독립적 이동 가능' },
                      { color: 'bg-blue-500', label: '양호: 10-20초', desc: '대부분 독립적' },
                      { color: 'bg-orange-500', label: '주의: 20-30초', desc: '보행 보조 필요 가능성' },
                      { color: 'bg-red-500', label: '낙상위험: 30초 이상', desc: '낙상 위험 높음' },
                    ].map((item, i) => (
                      <div key={i} className="flex items-center gap-2">
                        <span className={`w-3 h-3 ${item.color} rounded-full flex-shrink-0`}></span>
                        <span className="text-sm text-gray-600 dark:text-gray-300">{item.label}</span>
                        <span className="text-xs text-gray-400 dark:text-gray-400">- {item.desc}</span>
                      </div>
                    ))}
                    <p className="text-xs text-gray-400 dark:text-gray-400 mt-3">
                      * TUG: 의자에서 일어나 3m 걷고 돌아와 앉는 시간
                    </p>
                  </div>
                </div>

                {/* 단계별 감지 기준 */}
                <div>
                  <h3 className="font-bold text-gray-900 dark:text-gray-100 mb-4 flex items-center">
                    <svg className="w-5 h-5 mr-2 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                    단계별 감지 기준
                  </h3>
                  <div className="space-y-2">
                    {[
                      { phase: '일어서기', color: 'bg-purple-500', criteria: '다리 각도 120°→160° 이상 + 상체 수직 75° 이상' },
                      { phase: '걷기(나감)', color: 'bg-blue-500', criteria: '기립 완료 후 발이 전방으로 이동 시작' },
                      { phase: '돌아서기', color: 'bg-yellow-500', criteria: '어깨 방향 변화가 최대인 지점 감지' },
                      { phase: '걷기(돌아옴)', color: 'bg-green-500', criteria: '회전 완료 후 반대 방향 이동 시작' },
                      { phase: '앉기', color: 'bg-pink-500', criteria: '다리 각도 160°→120° 이하로 변화' },
                    ].map((item, i) => (
                      <div key={i} className="flex items-start gap-2">
                        <span className={`w-3 h-3 ${item.color} rounded-full flex-shrink-0 mt-1`}></span>
                        <div>
                          <span className="text-sm font-medium text-gray-700 dark:text-gray-200">{item.phase}</span>
                          <p className="text-xs text-gray-500 dark:text-gray-400">{item.criteria}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Sidebar */}
        <div className="space-y-6">
          <Suspense fallback={<ChartLoader />}>
          {/* Comparison Report */}
          {id && filteredTests.length >= 2 && (
            <ComparisonReport patientId={id} testId={filteredTests[0]?.id} prevId={filteredTests[1]?.id} currentTest={filteredTests[0]} previousTest={filteredTests[1]} />
          )}

          {/* Video Comparison */}
          {id && filteredTests.length >= 2 && (
            <VideoComparison patientId={id} tests={filteredTests} />
          )}

          {/* Notes Analysis */}
          {filteredTests.length > 0 && (
            <NotesAnalysisSummary tests={filteredTests} />
          )}

          {/* Fall Risk Score - 10MWT only */}
          {filteredTests.length > 0 && selectedTestType !== 'TUG' && selectedTestType !== 'BBS' && (
            <FallRiskScore
              speedMps={filteredTests[0].walk_speed_mps}
              timeSeconds={filteredTests[0].walk_time_seconds}
            />
          )}
          </Suspense>

          {/* Walking Route Card - 10MWT only, uses average speed */}
          {id && filteredTests.length > 0 && (selectedTestType === '10MWT' || selectedTestType === 'ALL') && (() => {
            const mwtTests = filteredTests.filter(t => (t.test_type || '10MWT') === '10MWT' && t.walk_speed_mps > 0);
            if (mwtTests.length === 0) return null;
            const avgSpeed = mwtTests.reduce((s, t) => s + t.walk_speed_mps, 0) / mwtTests.length;
            return <WalkingRouteCard patientId={id} speedMps={avgSpeed} />;
          })()}

          {/* TUG Result */}
          {filteredTests.length > 0 && selectedTestType === 'TUG' && filteredTests[0].test_type === 'TUG' && filteredTests[0].analysis_data && (
            <TUGResult data={filteredTests[0].analysis_data as TUGAnalysisData} testId={filteredTests[0].id} />
          )}

          {/* BBS Result */}
          {filteredTests.length > 0 && selectedTestType === 'BBS' && filteredTests[0].test_type === 'BBS' && filteredTests[0].analysis_data && (
            <BBSResult data={filteredTests[0].analysis_data as BBSAnalysisData} />
          )}

          {/* BBS/10MWT Reference Info - sidebar only for non-TUG */}
          {selectedTestType !== 'TUG' && (
            <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm">
              <h3 className="font-bold text-gray-900 dark:text-gray-100 mb-4">보행 시간 기준</h3>
              <div className="space-y-2">
                {[
                  { color: 'bg-green-500', label: '정상: 8.3초 이하' },
                  { color: 'bg-blue-500', label: '경도: 8.3~10.0초' },
                  { color: 'bg-orange-500', label: '주의: 10.0~12.5초' },
                  { color: 'bg-red-500', label: '위험: 12.5초 초과' },
                ].map((item, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <span className={`w-3 h-3 ${item.color} rounded-full flex-shrink-0`}></span>
                    <span className="text-sm text-gray-600 dark:text-gray-300">{item.label}</span>
                  </div>
                ))}
                <p className="text-xs text-gray-400 dark:text-gray-400 mt-3">
                  * 12.5초 초과는 낙상 위험 증가와 연관됩니다.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Video Modal */}
      {selectedVideoTest && (
        <VideoModal
          test={selectedVideoTest}
          onClose={() => setSelectedVideoTest(null)}
        />
      )}

      {/* Email Report Modal */}
      {emailTestId && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setEmailTestId(null)} role="dialog" aria-modal="true" aria-labelledby="email-modal-title">
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl w-full max-w-md p-6" onClick={e => e.stopPropagation()}>
            <h3 id="email-modal-title" className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-4">리포트 이메일 전송</h3>
            <div className="space-y-4">
              <div>
                <label htmlFor="email-to" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">받는 사람 이메일</label>
                <input
                  id="email-to"
                  type="email"
                  value={emailTo}
                  onChange={e => setEmailTo(e.target.value)}
                  placeholder="doctor@hospital.com"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500"
                />
              </div>
              <div>
                <label htmlFor="email-message" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">메시지 (선택)</label>
                <textarea
                  id="email-message"
                  value={emailMessage}
                  onChange={e => setEmailMessage(e.target.value)}
                  placeholder="추가 메시지를 입력하세요..."
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500"
                />
              </div>
              {emailResult && (
                <div className={`p-3 rounded-lg text-sm ${
                  emailResult.success
                    ? 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                    : 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                }`}>
                  {emailResult.message}
                </div>
              )}
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => setEmailTestId(null)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
                >
                  닫기
                </button>
                <button
                  onClick={async () => {
                    if (!emailTo || !emailTestId) return;
                    setEmailSending(true);
                    setEmailResult(null);
                    try {
                      const result = await testApi.sendReportEmail(emailTestId, emailTo, emailMessage || undefined);
                      setEmailResult(result);
                      if (result.success) {
                        setEmailTo('');
                        setEmailMessage('');
                      }
                    } catch (err: any) {
                      setEmailResult({ success: false, message: err?.response?.data?.detail || '이메일 전송에 실패했습니다.' });
                    } finally {
                      setEmailSending(false);
                    }
                  }}
                  disabled={!emailTo || emailSending}
                  className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {emailSending ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" aria-hidden="true"></div>
                      전송 중...
                    </>
                  ) : (
                    '전송'
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
