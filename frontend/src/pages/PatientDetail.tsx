import { useState, useEffect, useRef, lazy, Suspense } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { patientApi, testApi } from '../services/api';
import type { Patient, WalkTest, ComparisonResult, AnalysisData, TUGAnalysisData, PatientStats, AsymmetryWarning, PatientTag, ClinicalNormativeResponse } from '../types';
import TagManager from '../components/TagManager';
import ClinicalNotesEditor from '../components/ClinicalNotesEditor';
import WalkingHighlight from '../components/WalkingHighlight';
import ConfidenceScoreComponent from '../components/ConfidenceScore';
import DashboardSummary from '../components/DashboardSummary';

// Lazy-loaded components (초기 렌더에 불필요)
const VideoModal = lazy(() => import('../components/VideoModal'));
const AngleChart = lazy(() => import('../components/AngleChart'));
const ComparisonReport = lazy(() => import('../components/ComparisonReport'));
const TrendChart = lazy(() => import('../components/TrendChart'));
const AIReport = lazy(() => import('../components/AIReport'));
const ClinicalTrendChart = lazy(() => import('../components/ClinicalTrendChart'));
const CorrelationAnalysis = lazy(() => import('../components/CorrelationAnalysis'));
const WalkingRouteCard = lazy(() => import('../components/WalkingRouteCard'));
const TUGPhaseComparison = lazy(() => import('../components/TUGPhaseComparison'));

export default function PatientDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [patient, setPatient] = useState<Patient | null>(null);
  const [tests, setTests] = useState<WalkTest[]>([]);
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedVideoTest, setSelectedVideoTest] = useState<WalkTest | null>(null);
  const [notes, setNotes] = useState('');
  const [, setNoteSaving] = useState(false);
  const [showOverlay, setShowOverlay] = useState(true);
  const [stats, setStats] = useState<PatientStats | null>(null);
  const [patientTags, setPatientTags] = useState<PatientTag[]>([]);
  const [clinicalNormative, setClinicalNormative] = useState<ClinicalNormativeResponse | null>(null);
  const [showEmailModal, setShowEmailModal] = useState(false);
  const [emailTo, setEmailTo] = useState('');
  const [emailMessage, setEmailMessage] = useState('');
  const [emailSending, setEmailSending] = useState(false);
  const [emailResult, setEmailResult] = useState<{ success: boolean; message: string } | null>(null);


  const videoRef = useRef<HTMLVideoElement>(null);

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
      if (testsData.length > 0) {
        setNotes(testsData[0].notes || '');
      }
      // 부가 API 병렬 호출
      const testType = testsData[0]?.test_type || '10MWT';
      const hasTests = testsData.length >= 1;
      const results = await Promise.allSettled([
        patientApi.getPatientTags(patientId),
        hasTests ? testApi.compare(patientId) : Promise.reject('no tests'),
        hasTests ? testApi.getStats(patientId, testType) : Promise.reject('no tests'),
        hasTests ? testApi.getClinicalNormative(patientId) : Promise.reject('no tests'),
      ]);
      if (results[0].status === 'fulfilled') setPatientTags(results[0].value);
      if (results[1].status === 'fulfilled') setComparison(results[1].value);
      if (results[2].status === 'fulfilled') setStats(results[2].value);
      if (results[3].status === 'fulfilled') setClinicalNormative(results[3].value);
      setError(null);
    } catch (err) {
      setError('환자 정보를 불러오는데 실패했습니다.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!patient || !window.confirm('정말 이 환자를 삭제하시겠습니까?')) return;
    try {
      await patientApi.delete(patient.id);
      navigate('/');
    } catch (err) {
      setError('삭제에 실패했습니다.');
      console.error(err);
    }
  };


  const calculateAge = (birthDate: string): number => {
    const today = new Date();
    const birth = new Date(birthDate);
    let age = today.getFullYear() - birth.getFullYear();
    const monthDiff = today.getMonth() - birth.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) age--;
    return age;
  };

  const calculateRiskScore = (speed: number, time: number) => {
    const speedScore = Math.min(50, Math.round((speed / 1.2) * 50));
    const idealTime = 10 / 1.2;
    const timeScore = time <= idealTime
      ? 50
      : Math.max(0, Math.round(50 - ((time - idealTime) / idealTime) * 50));
    const total = speedScore + timeScore;

    let level: string;
    let levelColor: string;
    if (total >= 80) {
      level = '정상 (낙상 위험 낮음)';
      levelColor = 'text-white';
    } else if (total >= 60) {
      level = '주의 (낙상 위험 중간)';
      levelColor = 'text-yellow-200';
    } else {
      level = '위험 (낙상 위험 높음)';
      levelColor = 'text-red-200';
    }
    return { total, speedScore, timeScore, level, levelColor };
  };

  const getOverlayUrl = (test: WalkTest): string | null => {
    const data = test.analysis_data;
    if (!data) return null;
    if ('overlay_video_filename' in data && (data as AnalysisData).overlay_video_filename) {
      return `/uploads/${(data as AnalysisData).overlay_video_filename}`;
    }
    if ('side_overlay_video_filename' in data) {
      const tug = data as TUGAnalysisData;
      if (tug.front_overlay_video_filename) return `/uploads/${tug.front_overlay_video_filename}`;
      if (tug.side_overlay_video_filename) return `/uploads/${tug.side_overlay_video_filename}`;
    }
    return null;
  };

  // TUG: 측면 오버레이 URL 가져오기
  const getTUGOverlayUrl = (test: WalkTest) => {
    const data = test.analysis_data as TUGAnalysisData | null;
    if (!data) return null;
    if (data.side_overlay_video_filename) return `/uploads/${data.side_overlay_video_filename}`;
    if (data.overlay_video_filename) return `/uploads/${data.overlay_video_filename}`;
    return null;
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12" role="status">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        <span className="sr-only">로딩 중...</span>
      </div>
    );
  }

  if (error || !patient) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500">{error || '환자를 찾을 수 없습니다.'}</p>
        <Link to="/" className="text-blue-500 hover:underline mt-4 inline-block">
          대시보드로 돌아가기
        </Link>
      </div>
    );
  }

  const latestTest = comparison?.current_test || tests[0];
  const previousTest = comparison?.previous_test;
  const analysisData = latestTest?.analysis_data as AnalysisData | undefined;
  const gaitPattern = analysisData?.gait_pattern;
  const clinicalVars = analysisData?.clinical_variables;
  const hasClinicalVars = clinicalVars && Object.keys(clinicalVars).length > 0;
  const testType = latestTest?.test_type || '10MWT';
  const testBadgeLabel = testType === '10MWT' ? '10MWT' : testType === 'TUG' ? 'TUG' : 'BBS';

  const risk = latestTest && latestTest.walk_speed_mps != null && latestTest.walk_time_seconds != null
    ? calculateRiskScore(latestTest.walk_speed_mps, latestTest.walk_time_seconds) : null;
  const isTUGTest = testType === 'TUG';
  const overlayUrl = isTUGTest
    ? (latestTest ? getTUGOverlayUrl(latestTest) : null)
    : (latestTest ? getOverlayUrl(latestTest) : null);
  const baseVideoUrl = latestTest ? testApi.getVideoUrl(latestTest) : null;
  const videoUrl = baseVideoUrl;
  const confidenceScore = analysisData?.confidence_score;
  const asymmetryWarnings = analysisData?.asymmetry_warnings;


  return (
    <div className="animate-fadeIn max-w-7xl mx-auto pb-20 sm:pb-0 overflow-x-hidden">
      {/* Page Header */}
      <div className="bg-white dark:bg-gray-800 p-4 sm:p-6 rounded-2xl shadow-sm mb-6 overflow-visible">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 mb-4">
          <Link to="/" className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">대시보드</Link>
          <span>›</span>
          <span>{patient.name}</span>
          <span>›</span>
          <span className="text-gray-800 dark:text-gray-200">검사 결과</span>
        </div>

        {/* Header Content */}
        <div className="flex flex-col sm:flex-row justify-between items-start gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {patient.name} - {testBadgeLabel} 검사 결과
            </h1>
            {id && (
              <div className="mt-2">
                <TagManager
                  patientId={id}
                  patientTags={patientTags}
                  onTagsChange={setPatientTags}
                />
              </div>
            )}
            <div className="flex flex-wrap gap-4 text-sm text-gray-600 dark:text-gray-400 mt-2">
              <span>#{patient.patient_number}</span>
              {latestTest && (
                <span>
                  {new Date(latestTest.test_date).toLocaleDateString('ko-KR', {
                    year: 'numeric', month: 'long', day: 'numeric',
                  })}
                </span>
              )}
              <span>{patient.gender === 'M' ? '남' : '여'} · {calculateAge(patient.birth_date)}세</span>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 sm:gap-3 flex-shrink-0">
            {latestTest && (
              <a
                href={testApi.downloadPdf(latestTest.id)}
                className="px-4 py-2.5 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg font-semibold text-sm hover:bg-gray-300 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                PDF 다운로드
              </a>
            )}
            {latestTest && (
              <button
                onClick={() => { setShowEmailModal(true); setEmailResult(null); }}
                className="px-4 py-2.5 bg-green-600 text-white rounded-lg font-semibold text-sm hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 transition-all flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                Email 전송
              </button>
            )}
            <Link
              to={`/patients/${patient.id}/tug-realtime`}
              className="px-4 py-2.5 bg-green-600 text-white rounded-lg font-semibold text-sm hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 transition-all flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              실시간 TUG
            </Link>
            <Link
              to={`/patients/${patient.id}/test`}
              className="px-4 py-2.5 bg-blue-600 text-white rounded-lg font-semibold text-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              영상 업로드
            </Link>
          </div>
        </div>
      </div>

      {/* No test data */}
      {!latestTest ? (
        <div className="bg-white dark:bg-gray-800 p-12 rounded-2xl shadow-sm text-center">
          <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </div>
          <p className="text-gray-500 dark:text-gray-400 mb-4">검사 기록이 없습니다</p>
          <Link to={`/patients/${patient.id}/test`} className="text-blue-600 font-medium hover:underline">
            첫 검사 시작하기
          </Link>
        </div>
      ) : (
        <>
        {/* Dashboard Summary Cards */}
        {latestTest && (
          <div className="mb-6">
            <DashboardSummary
              latestTest={latestTest}
              previousTest={previousTest}
              clinicalNormative={clinicalNormative}
            />
          </div>
        )}

        {/* Main Grid: 2fr + 1fr */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white dark:bg-gray-800 p-4 sm:p-6 rounded-2xl shadow-sm overflow-hidden">
              {/* Card Header */}
              <div className="flex flex-wrap justify-between items-center mb-6 pb-4 border-b-2 border-gray-100 dark:border-gray-700 gap-2">
                <h2 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2 sm:gap-3 flex-wrap">
                  검사 결과
                  <span className="px-3 py-1 bg-blue-600 text-white text-sm font-semibold rounded-full">
                    {testBadgeLabel}
                  </span>
                  {confidenceScore && (
                    <ConfidenceScoreComponent confidence={confidenceScore} compact />
                  )}
                </h2>
              </div>

              {/* Scores Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
                <div className="bg-gradient-to-br from-gray-50 to-white dark:from-gray-700/50 dark:to-gray-800 p-5 rounded-xl border-2 border-gray-200 dark:border-gray-600 text-center hover:border-blue-500 dark:hover:border-blue-400 transition-all">
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">보행 시간</p>
                  <p className="text-3xl font-extrabold text-blue-600 dark:text-blue-400">
                    {(latestTest.walk_time_seconds ?? 0).toFixed(2)}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">초</p>
                </div>
                {testType !== 'TUG' && (
                <div className="bg-gradient-to-br from-gray-50 to-white dark:from-gray-700/50 dark:to-gray-800 p-5 rounded-xl border-2 border-gray-200 dark:border-gray-600 text-center hover:border-blue-500 dark:hover:border-blue-400 transition-all">
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">보행 속도</p>
                  <p className="text-3xl font-extrabold text-blue-600 dark:text-blue-400">
                    {(latestTest.walk_speed_mps ?? 0).toFixed(2)}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">m/s</p>
                </div>
                )}
                <div className="bg-gradient-to-br from-gray-50 to-white dark:from-gray-700/50 dark:to-gray-800 p-5 rounded-xl border-2 border-gray-200 dark:border-gray-600 text-center hover:border-blue-500 dark:hover:border-blue-400 transition-all">
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">분석 프레임</p>
                  <p className="text-3xl font-extrabold text-blue-600 dark:text-blue-400">
                    {analysisData?.frames_analyzed || '-'}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">프레임</p>
                </div>
              </div>


              {/* Fall Risk Score */}
              {risk && (
                <div className="bg-gradient-to-br from-blue-600 to-cyan-500 p-6 rounded-xl text-white mb-6">
                  <h3 className="text-center text-lg opacity-90 mb-4">낙상 위험도 평가</h3>
                  <p className="text-center text-5xl font-extrabold mb-2">{risk.total}</p>
                  <p className={`text-center text-xl font-bold mb-4 ${risk.levelColor}`}>{risk.level}</p>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-white/15 p-3 rounded-lg">
                      <p className="text-sm opacity-90 mb-1">속도 점수</p>
                      <p className="text-xl font-bold">{risk.speedScore}/50</p>
                    </div>
                    <div className="bg-white/15 p-3 rounded-lg">
                      <p className="text-sm opacity-90 mb-1">시간 점수</p>
                      <p className="text-xl font-bold">{risk.timeScore}/50</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Asymmetry Warnings */}
              {asymmetryWarnings && asymmetryWarnings.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-3">보행 비대칭 경고</h3>
                  <div className="space-y-2">
                    {asymmetryWarnings.map((w: AsymmetryWarning, i: number) => (
                      <div key={i} className={`p-4 rounded-xl border-l-4 ${
                        w.severity === 'severe' ? 'bg-red-50 dark:bg-red-900/20 border-red-500' :
                        w.severity === 'moderate' ? 'bg-orange-50 dark:bg-orange-900/20 border-orange-500' :
                        'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-500'
                      }`}>
                        <div className="flex items-center justify-between">
                          <div>
                            <span className={`text-sm font-bold ${
                              w.severity === 'severe' ? 'text-red-700 dark:text-red-400' :
                              w.severity === 'moderate' ? 'text-orange-700 dark:text-orange-400' :
                              'text-yellow-800 dark:text-yellow-300'
                            }`}>
                              {w.label}
                            </span>
                            <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">{w.description}</p>
                          </div>
                          <span className="text-lg font-bold text-gray-900 dark:text-gray-100">
                            {w.value}{w.unit}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Gait Pattern Analysis */}
              {gaitPattern && (
                <div className="mb-6">
                  <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-4">보행 패턴 분석</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="bg-gray-50 dark:bg-gray-700/50 p-5 rounded-xl border-l-4 border-blue-600">
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">어깨 기울기 평균</p>
                      <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-1">
                        {gaitPattern.shoulder_tilt_avg}°
                      </p>
                      <p className={`text-sm font-semibold ${
                        gaitPattern.shoulder_tilt_avg <= 5
                          ? 'text-green-600 dark:text-green-400'
                          : 'text-orange-600 dark:text-orange-400'
                      }`}>
                        {gaitPattern.shoulder_tilt_avg <= 5 ? '✓ 양호' : '⚠ 주의 필요'}
                      </p>
                    </div>
                    <div className="bg-gray-50 dark:bg-gray-700/50 p-5 rounded-xl border-l-4 border-blue-600">
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">골반 기울기 평균</p>
                      <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-1">
                        {gaitPattern.hip_tilt_avg}°
                      </p>
                      <p className={`text-sm font-semibold ${
                        gaitPattern.hip_tilt_avg <= 5
                          ? 'text-green-600 dark:text-green-400'
                          : 'text-orange-600 dark:text-orange-400'
                      }`}>
                        {gaitPattern.hip_tilt_avg <= 5 ? '✓ 양호' : '⚠ 주의 필요'}
                      </p>
                    </div>
                  </div>
                  {gaitPattern.assessment && (
                    <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border-l-4 border-green-500">
                      <span className="font-bold text-green-600 dark:text-green-400">종합 평가: </span>
                      <span className="text-gray-700 dark:text-gray-300">{gaitPattern.assessment}</span>
                    </div>
                  )}
                </div>
              )}

              {/* Clinical Variables Section (10MWT) */}
              {hasClinicalVars && (
                <div className="mb-6">
                  <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
                    보행 임상 변수
                    {analysisData?.disease_profile_display && analysisData.disease_profile !== 'default' && (
                      <span className="px-2 py-0.5 bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400 text-xs font-medium rounded-full">
                        {analysisData.disease_profile_display}
                      </span>
                    )}
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {/* Cadence - TUG에서는 숨김 */}
                    {clinicalVars.cadence && testType !== 'TUG' && (() => {
                      const norm = clinicalNormative?.cadence;
                      const isNormal = norm ? norm.comparison === 'normal' : (clinicalVars.cadence!.value >= 100 && clinicalVars.cadence!.value <= 130);
                      const rangeText = norm?.normative ? `${norm.normative.range_low}-${norm.normative.range_high}` : '100-130';
                      return (
                        <div className="bg-gray-50 dark:bg-gray-700/50 p-4 rounded-xl border-l-4 border-indigo-500">
                          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">분당 걸음수 (Cadence)</p>
                          <p className="text-xl font-bold text-gray-900 dark:text-gray-100">
                            {clinicalVars.cadence!.value}
                            <span className="text-sm font-normal text-gray-500 ml-1">steps/min</span>
                          </p>
                          <p className={`text-xs mt-1 ${isNormal ? 'text-green-600 dark:text-green-400' : 'text-orange-600 dark:text-orange-400'}`}>
                            {norm?.comparison_label ?? (isNormal ? '✓ 양호' : '⚠ 주의 필요')}
                            {' '}({rangeText})
                          </p>
                        </div>
                      );
                    })()}

                    {/* 총 걸음수 */}
                    {clinicalVars.cadence && testType !== 'TUG' && clinicalVars.cadence.total_steps > 0 && (
                      <div className="bg-gray-50 dark:bg-gray-700/50 p-4 rounded-xl border-l-4 border-violet-500">
                        <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">총 걸음수</p>
                        <p className="text-xl font-bold text-gray-900 dark:text-gray-100">
                          {clinicalVars.cadence.total_steps}
                          <span className="text-sm font-normal text-gray-500 ml-1">걸음</span>
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">10m 보행 기준</p>
                      </div>
                    )}

                    {/* Stride Length - 측면 촬영(TUG)에서만 표시 */}
                    {testType !== '10MWT' && clinicalVars.stride_length && (() => {
                      const norm = clinicalNormative?.stride_length;
                      const isNormal = norm ? norm.comparison === 'normal' : (clinicalVars.stride_length!.value >= 1.2 && clinicalVars.stride_length!.value <= 1.8);
                      const rangeText = norm?.normative ? `${norm.normative.range_low}-${norm.normative.range_high}m` : '1.2-1.8m';
                      return (
                        <div className="bg-gray-50 dark:bg-gray-700/50 p-4 rounded-xl border-l-4 border-blue-500">
                          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">보폭 (Stride Length)</p>
                          <p className="text-xl font-bold text-gray-900 dark:text-gray-100">
                            {clinicalVars.stride_length!.value}
                            <span className="text-sm font-normal text-gray-500 ml-1">m</span>
                          </p>
                          <p className={`text-xs mt-1 ${isNormal ? 'text-green-600 dark:text-green-400' : 'text-orange-600 dark:text-orange-400'}`}>
                            {norm?.comparison_label ?? (isNormal ? '✓ 양호' : '⚠ 주의 필요')}
                            {' '}({rangeText})
                          </p>
                        </div>
                      );
                    })()}

                    {/* Arm Swing */}
                    {clinicalVars.arm_swing && (
                      <div className="bg-gray-50 dark:bg-gray-700/50 p-4 rounded-xl border-l-4 border-teal-500">
                        <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">팔 흔들기 (Arm Swing)</p>
                        <p className="text-xl font-bold text-gray-900 dark:text-gray-100">
                          비대칭: {clinicalVars.arm_swing.asymmetry_index}
                          <span className="text-sm font-normal text-gray-500 ml-1">%</span>
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          L: {(clinicalVars.arm_swing.left_amplitude ?? 0).toFixed(4)} / R: {(clinicalVars.arm_swing.right_amplitude ?? 0).toFixed(4)}
                        </p>
                      </div>
                    )}

                    {/* Double Support */}
                    {clinicalVars.double_support && (
                      <div className="bg-gray-50 dark:bg-gray-700/50 p-4 rounded-xl border-l-4 border-cyan-500">
                        <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">이중 지지기 (Double Support)</p>
                        <p className="text-xl font-bold text-gray-900 dark:text-gray-100">
                          {clinicalVars.double_support.value}
                          <span className="text-sm font-normal text-gray-500 ml-1">%</span>
                        </p>
                        <p className={`text-xs mt-1 ${
                          clinicalVars.double_support.value <= 30
                            ? 'text-green-600 dark:text-green-400'
                            : 'text-orange-600 dark:text-orange-400'
                        }`}>
                          {clinicalVars.double_support.value <= 30 ? '✓ 양호' : '⚠ 증가 (불안정)'}
                          {' '}(20-30%)
                        </p>
                      </div>
                    )}

                    {/* Foot Clearance */}
                    {clinicalVars.foot_clearance && (
                      <div className="bg-gray-50 dark:bg-gray-700/50 p-4 rounded-xl border-l-4 border-teal-500">
                        <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">발 높이 (Foot Clearance)</p>
                        <p className="text-xl font-bold text-gray-900 dark:text-gray-100">
                          {clinicalVars.foot_clearance.mean_clearance}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          최소: {clinicalVars.foot_clearance.min_clearance}
                        </p>
                      </div>
                    )}

                    {/* Trunk Inclination */}
                    {clinicalVars.trunk_inclination && (
                      <div className="bg-gray-50 dark:bg-gray-700/50 p-4 rounded-xl border-l-4 border-amber-500">
                        <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">체간 경사 (Trunk Inclination)</p>
                        <p className="text-xl font-bold text-gray-900 dark:text-gray-100">
                          {clinicalVars.trunk_inclination.mean}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          SD: {clinicalVars.trunk_inclination.std}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Video Section */}
              {(videoUrl || overlayUrl) && (
                <div className="mb-6">
                  <div className="bg-gray-900 rounded-xl overflow-hidden">
                    <div className="relative">
                      {showOverlay && overlayUrl ? (
                        <video
                          ref={videoRef}
                          key="overlay-side"
                          src={overlayUrl}
                          controls
                          className="w-full aspect-video"
                          onError={() => setShowOverlay(false)}
                        />
                      ) : videoUrl ? (
                        <video
                          ref={videoRef}
                          key="original-side"
                          src={videoUrl}
                          controls
                          className="w-full aspect-video"
                        />
                      ) : null}
                    </div>
                    <div className="bg-gray-800 px-4 py-3 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
                      <span className="text-white text-sm">
                        {showOverlay && overlayUrl
                          ? (isTUGTest ? '측면 포즈 오버레이 영상' : '포즈 오버레이 영상')
                          : (isTUGTest ? '측면 원본 영상' : '원본 영상')
                        } · {(latestTest.walk_time_seconds ?? 0).toFixed(1)}초
                      </span>
                      <div className="flex gap-2">
                        {overlayUrl && (
                          <button
                            onClick={() => setShowOverlay(!showOverlay)}
                            className="px-3 py-1.5 bg-white/10 text-white text-sm rounded-md hover:bg-white/20 transition-colors"
                          >
                            {showOverlay ? '원본 영상' : '포즈 ON'}
                          </button>
                        )}
                        <button
                          onClick={() => setSelectedVideoTest(latestTest)}
                          className="px-3 py-1.5 bg-white/10 text-white text-sm rounded-md hover:bg-white/20 transition-colors"
                        >
                          전체화면
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* 3D Skeleton Model - hidden for now */}

              {/* Angle Chart (Timeline) */}
              {analysisData?.angle_data && (
                <div>
                  <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-4">보행 기울기 추이</h3>
                  <Suspense fallback={null}><AngleChart data={analysisData.angle_data} /></Suspense>
                </div>
              )}

              {/* Notes Card */}
              <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm">
                <h3 className="font-bold text-gray-900 dark:text-gray-100 mb-3">치료사 메모</h3>
                <ClinicalNotesEditor
                  notes={notes}
                  onSave={async (newNotes) => {
                    const lt = tests[0];
                    if (!lt) return;
                    try {
                      setNoteSaving(true);
                      await testApi.updateTestNotes(lt.id, newNotes);
                      setNotes(newNotes);
                    } catch (err) {
                      console.error(err);
                    } finally {
                      setNoteSaving(false);
                    }
                  }}
                />
              </div>
            </div>
          </div>

          {/* Right Sidebar */}
          <div className="space-y-6">
            {/* Confidence Score Card */}
            {confidenceScore && (
              <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm">
                <h3 className="font-bold text-gray-900 dark:text-gray-100 mb-3">분석 신뢰도</h3>
                <ConfidenceScoreComponent confidence={confidenceScore} />
              </div>
            )}

            {/* Comparison Card */}
            {comparison && previousTest && (
              <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm">
                <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-4">이전 검사 비교</h3>

                {/* Time (primary) */}
                <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg mb-3">
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">보행 시간</p>
                  <div className="text-right">
                    <span className="text-xl font-bold text-gray-900 dark:text-gray-100">
                      {(latestTest.walk_time_seconds ?? 0).toFixed(2)}초
                    </span>
                    {comparison.time_difference != null && (
                      <span className={`ml-2 inline-block px-2 py-0.5 rounded text-xs font-semibold ${
                        comparison.time_difference < 0
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                          : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                      }`}>
                        {comparison.time_difference < 0 ? '↓' : '↑'} {Math.abs(comparison.time_difference).toFixed(2)}
                      </span>
                    )}
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      이전: {(previousTest.walk_time_seconds ?? 0).toFixed(2)}초
                    </p>
                  </div>
                </div>

                {/* Speed - TUG 제외 */}
                {testType !== 'TUG' && (
                <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg mb-3">
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">보행 속도</p>
                  <div className="text-right">
                    <span className="text-xl font-bold text-gray-900 dark:text-gray-100">
                      {(latestTest.walk_speed_mps ?? 0).toFixed(2)} m/s
                    </span>
                    {comparison.speed_difference != null && (
                      <span className={`ml-2 inline-block px-2 py-0.5 rounded text-xs font-semibold ${
                        comparison.speed_difference > 0
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                          : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                      }`}>
                        {comparison.speed_difference > 0 ? '↑' : '↓'} {Math.abs(comparison.speed_difference).toFixed(2)}
                      </span>
                    )}
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      이전: {(previousTest.walk_speed_mps ?? 0).toFixed(2)} m/s
                    </p>
                  </div>
                </div>
                )}

                {/* Risk Score Comparison */}
                {risk && previousTest && (
                  <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg mb-3">
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">낙상 위험 점수</p>
                    <div className="text-right">
                      {(() => {
                        const prevRisk = calculateRiskScore(previousTest.walk_speed_mps, previousTest.walk_time_seconds);
                        const diff = risk.total - prevRisk.total;
                        return (
                          <>
                            <span className="text-xl font-bold text-gray-900 dark:text-gray-100">
                              {risk.total}점
                            </span>
                            {diff !== 0 && (
                              <span className={`ml-2 inline-block px-2 py-0.5 rounded text-xs font-semibold ${
                                diff > 0
                                  ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                  : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                              }`}>
                                {diff > 0 ? '↑' : '↓'} {Math.abs(diff)}
                              </span>
                            )}
                            <p className="text-sm text-gray-500 dark:text-gray-400">
                              이전: {prevRisk.total}점
                            </p>
                          </>
                        );
                      })()}
                    </div>
                  </div>
                )}

                {/* Overall Message */}
                {comparison.comparison_message && (
                  <div className={`mt-3 p-3 rounded-lg text-center font-semibold text-sm ${
                    comparison.time_difference != null && comparison.time_difference < 0
                      ? 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                      : comparison.time_difference != null && comparison.time_difference > 0
                      ? 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                      : 'bg-yellow-50 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                  }`}>
                    {comparison.time_difference != null && comparison.time_difference < 0 ? '✓ ' : ''}
                    {comparison.comparison_message}
                  </div>
                )}
              </div>
            )}

            {/* Measurement Stats Card */}
            {stats && stats.test_count >= 2 && (
              <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm">
                <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-4">
                  반복 측정 통계
                  <span className="ml-2 text-sm font-normal text-gray-500 dark:text-gray-400">({stats.test_count}회)</span>
                </h3>
                <div className="space-y-3">
                  <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">보행 시간</p>
                    <p className="text-xl font-bold text-gray-900 dark:text-gray-100">
                      {stats.walk_time.mean}<span className="text-sm font-normal text-gray-500 ml-1">초</span>
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      SD: {stats.walk_time.std}초 | 범위: {stats.walk_time.min}-{stats.walk_time.max}초
                    </p>
                  </div>
                  {testType !== 'TUG' && (
                  <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">보행 속도</p>
                    <p className="text-xl font-bold text-gray-900 dark:text-gray-100">
                      {stats.walk_speed.mean}<span className="text-sm font-normal text-gray-500 ml-1">m/s</span>
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      SD: {stats.walk_speed.std} | 범위: {stats.walk_speed.min}-{stats.walk_speed.max} m/s
                    </p>
                  </div>
                  )}
                </div>
              </div>
            )}

            <Suspense fallback={null}>
              {/* Walking Route Card - 10MWT only */}
              {id && latestTest && testType === '10MWT' && (
                <WalkingRouteCard
                  patientId={id}
                  speedMps={latestTest?.walk_speed_mps ?? 0}
                />
              )}

              {/* Trend Analysis Chart */}
              {id && tests.length >= 3 && (
                <TrendChart patientId={id} testType={testType as any} />
              )}

              {/* Clinical Variable Trend Chart */}
              {id && tests.length >= 2 && hasClinicalVars && (
                <ClinicalTrendChart patientId={id} testType={testType as any} clinicalNormative={clinicalNormative} />
              )}

              {/* Correlation Analysis */}
              {id && tests.length >= 3 && hasClinicalVars && (
                <CorrelationAnalysis patientId={id} testType={testType as any} />
              )}

              {/* TUG Phase Comparison */}
              {id && isTUGTest && tests.filter(t => t.test_type === 'TUG').length >= 2 && (
                <TUGPhaseComparison patientId={id} tests={tests} />
              )}

              {/* Comparison Report */}
              {id && tests.length >= 2 && (
                <ComparisonReport patientId={id} testId={latestTest?.id} currentTest={tests[0]} previousTest={tests[1]} />
              )}

              {/* AI Report */}
              {latestTest && (
                <AIReport testId={latestTest.id} />
              )}
            </Suspense>

            {/* 3D Pose Visualization - disabled for 10MWT (rear-view only, low accuracy) */}


            {/* Walking Highlight */}
            {latestTest && latestTest.video_url && (
              <WalkingHighlight testId={latestTest.id} />
            )}

            {/* Test Info Card */}
            <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm">
              <h3 className="font-bold text-gray-900 dark:text-gray-100 mb-4">검사 정보</h3>
              <div>
                {[
                  {
                    label: '검사 유형',
                    value: testType === '10MWT' ? '10MWT (10미터 보행검사)'
                      : testType === 'TUG' ? 'TUG (일어나 걷기)'
                      : 'BBS (버그 균형 척도)',
                  },
                  { label: 'AI 모델', value: 'MediaPipe Pose' },
                  {
                    label: '분석 프레임',
                    value: analysisData?.frames_analyzed ? `${analysisData.frames_analyzed}프레임` : '-',
                  },
                  { label: '환자 키', value: `${patient.height_cm} cm` },
                  { label: '총 검사 횟수', value: `${tests.length}회` },
                ].map((item, i) => (
                  <div
                    key={i}
                    className="flex justify-between py-3 border-b border-gray-100 dark:border-gray-700 last:border-0"
                  >
                    <span className="text-sm text-gray-600 dark:text-gray-400">{item.label}</span>
                    <span className="font-semibold text-gray-900 dark:text-gray-100 text-sm">{item.value}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Quick Actions */}
            <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl shadow-sm space-y-3">
              <Link
                to={`/patients/${patient.id}/history`}
                className="block w-full px-4 py-3 text-center bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg font-semibold text-sm hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              >
                히스토리 보기
              </Link>
              <Link
                to={`/patients/${patient.id}/edit`}
                className="block w-full px-4 py-3 text-center bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg font-semibold text-sm hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              >
                환자 정보 수정
              </Link>
              <button
                onClick={handleDelete}
                className="w-full px-4 py-3 text-center bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg font-semibold text-sm hover:bg-red-100 dark:hover:bg-red-900/40 transition-colors"
              >
                환자 삭제
              </button>
            </div>
          </div>
        </div>
        </>
      )}

      {/* Video Modal */}
      {selectedVideoTest && (
        <Suspense fallback={null}>
          <VideoModal
            test={selectedVideoTest}
            previousTest={
              selectedVideoTest.test_type === 'TUG'
                ? tests
                    .filter(t => t.test_type === 'TUG' && t.id !== selectedVideoTest.id && t.test_date < selectedVideoTest.test_date)
                    .sort((a, b) => b.test_date.localeCompare(a.test_date))[0]
                : undefined
            }
            onClose={() => setSelectedVideoTest(null)}
          />
        </Suspense>
      )}


      {/* Email Report Modal */}
      {showEmailModal && latestTest && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowEmailModal(false)} role="dialog" aria-modal="true" aria-labelledby="email-modal-title">
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
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
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
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
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
                  onClick={() => setShowEmailModal(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
                >
                  닫기
                </button>
                <button
                  onClick={async () => {
                    if (!emailTo) return;
                    setEmailSending(true);
                    setEmailResult(null);
                    try {
                      const result = await testApi.sendReportEmail(latestTest.id, emailTo, emailMessage || undefined);
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
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
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
