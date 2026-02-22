import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { patientApi, testApi } from '../services/api';
import type { Patient, AnalysisStatus, TestType, BBSItemScores } from '../types';
import UploadProgress from '../components/UploadProgress';
import BBSForm, { AIScores } from '../components/BBSForm';
import WebSocketService from '../services/websocket';
import { showToast } from '../components/Toast';

export default function VideoUpload() {
  const { id } = useParams();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const sideVideoInputRef = useRef<HTMLInputElement>(null);
  const frontVideoInputRef = useRef<HTMLInputElement>(null);

  const [patient, setPatient] = useState<Patient | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);

  // TUG 두 영상용 상태
  const [sideVideo, setSideVideo] = useState<File | null>(null);
  const [frontVideo, setFrontVideo] = useState<File | null>(null);
  const [sideDragActive, setSideDragActive] = useState(false);
  const [frontDragActive, setFrontDragActive] = useState(false);

  const [uploadProgress, setUploadProgress] = useState(0);
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [status, setStatus] = useState<'idle' | 'uploading' | 'analyzing' | 'completed' | 'error'>('idle');
  const [message, setMessage] = useState('동영상 파일을 선택하세요');
  const [result, setResult] = useState<AnalysisStatus['result'] | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [testType, setTestType] = useState<TestType>('10MWT');
  const [bbsLoading, setBbsLoading] = useState(false);

  // BBS AI 분석용 상태
  const [bbsVideo, setBbsVideo] = useState<File | null>(null);
  const [bbsDragActive, setBbsDragActive] = useState(false);
  const [bbsAIScores, setBbsAIScores] = useState<AIScores | undefined>(undefined);
  const [bbsMode, setBbsMode] = useState<'manual' | 'ai'>('manual');
  const [bbsOverlayUrl, setBbsOverlayUrl] = useState<string | null>(null);
  const bbsVideoInputRef = useRef<HTMLInputElement>(null);

  // WebSocket for real-time progress
  const wsRef = useRef<WebSocketService | null>(null);
  const activeFileIdRef = useRef<string | null>(null);
  const pollingFallbackRef = useRef(false);

  // Connect WebSocket on mount
  useEffect(() => {
    const ws = WebSocketService.getInstance();
    wsRef.current = ws;
    ws.connect();

    return () => {
      // Don't disconnect singleton on unmount - other components may use it
    };
  }, []);

  // Request notification permission once
  const requestNotificationPermission = useCallback(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

  const showBrowserNotification = useCallback((title: string, body: string) => {
    if ('Notification' in window && Notification.permission === 'granted' && document.hidden) {
      new Notification(title, { body, icon: '/favicon.ico' });
    }
  }, []);

  // Subscribe to WS events for a file_id, with polling fallback
  const startMonitoring = useCallback((fileId: string, isBBS: boolean = false) => {
    activeFileIdRef.current = fileId;
    pollingFallbackRef.current = false;
    requestNotificationPermission();

    const ws = wsRef.current;
    if (ws && ws.isConnected) {
      ws.subscribe(fileId);

      const onProgress = (msg: any) => {
        if (msg.file_id !== fileId) return;
        setAnalysisProgress(msg.progress);
        setMessage(msg.message);
      };

      const onCompleted = (msg: any) => {
        if (msg.file_id !== fileId) return;
        if (isBBS) {
          setStatus('idle');
          if (msg.result?.ai_scores) {
            setBbsAIScores(msg.result.ai_scores);
            setMessage('AI 분석 완료! 점수를 확인하고 필요시 수정하세요.');
          }
          if (msg.result?.overlay_video_url) {
            setBbsOverlayUrl(msg.result.overlay_video_url);
          }
        } else {
          setStatus('completed');
          setResult(msg.result || null);
        }
        showToast({ type: 'success', title: '분석 완료!', message: msg.message });
        showBrowserNotification('분석 완료', msg.message || '검사 분석이 완료되었습니다.');
        cleanup();
      };

      const onError = (msg: any) => {
        if (msg.file_id !== fileId) return;
        setStatus('error');
        setMessage(msg.message);
        showToast({ type: 'error', title: '분석 실패', message: msg.message });
        cleanup();
      };

      const onDisconnected = () => {
        // WS disconnected - fall back to polling
        if (activeFileIdRef.current === fileId) {
          pollingFallbackRef.current = true;
          startPolling(fileId, isBBS);
        }
      };

      const cleanup = () => {
        ws.off('progress', onProgress);
        ws.off('completed', onCompleted);
        ws.off('error', onError);
        ws.off('disconnected', onDisconnected);
        activeFileIdRef.current = null;
      };

      ws.on('progress', onProgress);
      ws.on('completed', onCompleted);
      ws.on('error', onError);
      ws.on('disconnected', onDisconnected);
    } else {
      // No WS connection - use polling directly
      pollingFallbackRef.current = true;
      startPolling(fileId, isBBS);
    }
  }, [requestNotificationPermission, showBrowserNotification]);

  // Polling fallback
  const startPolling = useCallback((fileId: string, isBBS: boolean = false) => {
    const pollStatus = async () => {
      if (activeFileIdRef.current !== fileId) return;
      try {
        const statusData = await testApi.getStatus(fileId);
        setAnalysisProgress(statusData.progress);
        setMessage(statusData.message);

        if (statusData.status === 'completed') {
          if (isBBS) {
            setStatus('idle');
            if (statusData.result?.ai_scores) {
              setBbsAIScores(statusData.result.ai_scores);
              setMessage('AI 분석 완료! 점수를 확인하고 필요시 수정하세요.');
            }
            if (statusData.result?.overlay_video_url) {
              setBbsOverlayUrl(statusData.result.overlay_video_url);
            }
          } else {
            setStatus('completed');
            setResult(statusData.result || null);
          }
          showToast({ type: 'success', title: '분석 완료!', message: statusData.message });
          showBrowserNotification('분석 완료', statusData.message || '검사 분석이 완료되었습니다.');
          activeFileIdRef.current = null;
          return;
        } else if (statusData.status === 'error') {
          setStatus('error');
          setMessage(statusData.message);
          showToast({ type: 'error', title: '분석 실패', message: statusData.message });
          activeFileIdRef.current = null;
          return;
        }

        setTimeout(pollStatus, 200);
      } catch (err) {
        console.error('Polling error:', err);
        if (activeFileIdRef.current === fileId) {
          setTimeout(pollStatus, 1000);
        }
      }
    };
    pollStatus();
  }, [showBrowserNotification]);

  useEffect(() => {
    if (id) {
      loadPatient(id);
    }
  }, [id]);

  const loadPatient = async (patientId: string) => {
    try {
      const data = await patientApi.getById(patientId);
      setPatient(data);
      setError(null);
    } catch (err) {
      setError('환자 정보를 불러오는데 실패했습니다.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = (selectedFile: File) => {
    if (!selectedFile.type.startsWith('video/')) {
      setError('동영상 파일만 업로드 가능합니다.');
      return;
    }

    setFile(selectedFile);
    setError(null);
    setMessage(`선택됨: ${selectedFile.name}`);
  };

  // TUG 측면 영상 드래그 핸들러
  const handleSideDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setSideDragActive(true);
    } else if (e.type === 'dragleave') {
      setSideDragActive(false);
    }
  };

  const handleSideDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setSideDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleSideVideo(e.dataTransfer.files[0]);
    }
  };

  const handleSideVideoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleSideVideo(e.target.files[0]);
    }
  };

  const handleSideVideo = (selectedFile: File) => {
    if (!selectedFile.type.startsWith('video/')) {
      setError('동영상 파일만 업로드 가능합니다.');
      return;
    }
    setSideVideo(selectedFile);
    setError(null);
  };

  // TUG 정면 영상 드래그 핸들러
  const handleFrontDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setFrontDragActive(true);
    } else if (e.type === 'dragleave') {
      setFrontDragActive(false);
    }
  };

  const handleFrontDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setFrontDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFrontVideo(e.dataTransfer.files[0]);
    }
  };

  const handleFrontVideoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFrontVideo(e.target.files[0]);
    }
  };

  const handleFrontVideo = (selectedFile: File) => {
    if (!selectedFile.type.startsWith('video/')) {
      setError('동영상 파일만 업로드 가능합니다.');
      return;
    }
    setFrontVideo(selectedFile);
    setError(null);
  };

  // BBS 영상 드래그 핸들러
  const handleBbsDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setBbsDragActive(true);
    } else if (e.type === 'dragleave') {
      setBbsDragActive(false);
    }
  };

  const handleBbsDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setBbsDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleBbsVideo(e.dataTransfer.files[0]);
    }
  };

  const handleBbsVideoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleBbsVideo(e.target.files[0]);
    }
  };

  const handleBbsVideo = (selectedFile: File) => {
    if (!selectedFile.type.startsWith('video/')) {
      setError('동영상 파일만 업로드 가능합니다.');
      return;
    }
    setBbsVideo(selectedFile);
    setError(null);
  };

  // BBS AI 분석 시작
  const handleBbsAIUpload = async () => {
    if (!bbsVideo || !id) return;

    try {
      setStatus('uploading');
      setMessage('BBS 검사 영상 업로드 중...');
      setUploadProgress(0);
      setAnalysisProgress(0);

      const response = await testApi.uploadBBS(id, bbsVideo, (progress) => {
        setUploadProgress(progress);
      });

      setStatus('analyzing');
      setUploadProgress(100);
      setMessage('AI가 BBS 항목 분석 중...');

      startMonitoring(response.file_id, true);
    } catch (err: any) {
      setStatus('error');
      setMessage(err.response?.data?.detail || 'BBS 영상 업로드에 실패했습니다.');
      console.error(err);
    }
  };

  const handleUpload = async () => {
    // TUG 검사인 경우 두 영상 모두 필요
    if (testType === 'TUG') {
      if (!sideVideo || !frontVideo || !id) {
        setError('TUG 검사를 위해 측면 영상과 정면 영상이 모두 필요합니다.');
        return;
      }
    } else {
      if (!file || !id) return;
    }

    try {
      setStatus('uploading');
      setMessage('동영상 업로드 중...');
      setUploadProgress(0);
      setAnalysisProgress(0);

      let file_id: string;

      if (testType === 'TUG') {
        // TUG 두 영상 업로드
        const response = await testApi.uploadTUG(id, sideVideo!, frontVideo!, (progress) => {
          setUploadProgress(progress);
        });
        file_id = response.file_id;
      } else {
        // 10MWT 단일 영상 업로드 (카메라에서 멀어지는 방향만 지원)
        const response = await testApi.upload(id, file!, (progress) => {
          setUploadProgress(progress);
        }, 'away', testType);
        file_id = response.file_id;
      }

      setStatus('analyzing');
      setUploadProgress(100);
      setMessage('MediaPipe로 분석 중...');

      startMonitoring(file_id);
    } catch (err: any) {
      setStatus('error');
      setMessage(err.response?.data?.detail || '업로드에 실패했습니다.');
      console.error(err);
    }
  };

  const handleReset = () => {
    activeFileIdRef.current = null;  // Stop WS/polling monitoring
    setFile(null);
    setSideVideo(null);
    setFrontVideo(null);
    setBbsVideo(null);
    setBbsAIScores(undefined);
    setBbsMode('manual');
    setStatus('idle');
    setUploadProgress(0);
    setAnalysisProgress(0);
    setMessage('동영상 파일을 선택하세요');
    setResult(null);
    setTestType('10MWT');
    setBbsLoading(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    if (sideVideoInputRef.current) {
      sideVideoInputRef.current.value = '';
    }
    if (frontVideoInputRef.current) {
      frontVideoInputRef.current.value = '';
    }
    if (bbsVideoInputRef.current) {
      bbsVideoInputRef.current.value = '';
    }
  };

  // BBS 검사 제출 핸들러
  const handleBBSSubmit = async (scores: BBSItemScores, notes?: string) => {
    if (!id) return;

    setBbsLoading(true);
    try {
      const response = await testApi.createBBS(id, scores, notes);
      setStatus('completed');
      setResult({
        test_id: response.test_id,
        test_type: 'BBS',
        walk_time_seconds: response.total_score,  // BBS는 총점
        walk_speed_mps: 0
      });
      setMessage(`BBS 검사 완료 - 총점: ${response.total_score}/56 (${response.assessment_label})`);
    } catch (err: any) {
      setStatus('error');
      setMessage(err.response?.data?.detail || 'BBS 검사 저장에 실패했습니다.');
      console.error(err);
    } finally {
      setBbsLoading(false);
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
    <div className="max-w-2xl mx-auto animate-fadeIn pb-20 sm:pb-0">
      {/* 헤더 */}
      <div className="mb-6">
        <Link to={`/patients/${patient.id}`} className="text-blue-500 text-sm font-medium flex items-center mb-2">
          <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          {patient.name}
        </Link>
        <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100">
          {testType === 'TUG' ? 'TUG 검사' : testType === 'BBS' ? 'BBS 검사' : '10m 보행 검사'}
        </h2>
        <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">
          {testType === 'TUG'
            ? 'TUG (Timed Up and Go) 검사 동영상을 업로드하여 분석합니다'
            : testType === 'BBS'
            ? 'Berg Balance Scale 14개 항목을 직접 평가합니다'
            : '동영상을 업로드하여 보행 속도를 분석합니다'}
        </p>
      </div>

      {/* 환자 정보 */}
      <div className="card-blue mb-6">
        <div className="flex items-center space-x-4">
          <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center text-lg font-bold">
            {patient.name.charAt(0)}
          </div>
          <div>
            <p className="font-semibold">{patient.name}</p>
            <p className="text-blue-100 text-sm">키: {patient.height_cm}cm (원근법 보정에 사용)</p>
          </div>
        </div>
      </div>

      {/* 검사 유형 선택 (파일 선택 전) */}
      {status === 'idle' && !file && !sideVideo && !frontVideo && (
        <div className="card mb-4">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">검사 유형 선택</p>
          <div className="grid grid-cols-3 gap-3">
            <button
              onClick={() => setTestType('10MWT')}
              className={`p-3 rounded-xl border-2 transition-all ${
                testType === '10MWT'
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                  : 'border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:border-gray-300'
              }`}
            >
              <div className="flex flex-col items-center">
                <svg className="w-8 h-8 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
                <span className="text-sm font-medium">10m 보행</span>
                <span className="text-xs text-gray-500 dark:text-gray-400 mt-1">영상 1개</span>
              </div>
            </button>
            <button
              onClick={() => setTestType('TUG')}
              className={`p-3 rounded-xl border-2 transition-all ${
                testType === 'TUG'
                  ? 'border-green-500 bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                  : 'border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:border-gray-300'
              }`}
            >
              <div className="flex flex-col items-center">
                <svg className="w-8 h-8 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-sm font-medium">TUG</span>
                <span className="text-xs text-gray-500 dark:text-gray-400 mt-1">영상 2개</span>
              </div>
            </button>
            <button
              onClick={() => setTestType('BBS')}
              className={`p-3 rounded-xl border-2 transition-all ${
                testType === 'BBS'
                  ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
                  : 'border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:border-gray-300'
              }`}
            >
              <div className="flex flex-col items-center">
                <svg className="w-8 h-8 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                <span className="text-sm font-medium">BBS</span>
                <span className="text-xs text-gray-500 dark:text-gray-400 mt-1">직접 평가</span>
              </div>
            </button>
          </div>
        </div>
      )}

      {/* 10MWT 업로드 영역 (단일 영상) */}
      {status === 'idle' && testType === '10MWT' && (
        <div
          className={`card border-2 border-dashed transition-all duration-200 ${
            dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          aria-label="10m 보행검사 동영상 업로드 영역"
        >
          <div className="text-center py-8">
            <div className="w-16 h-16 bg-blue-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            </div>

            <p className="text-gray-700 dark:text-gray-300 font-medium mb-2">
              동영상 파일을 드래그하거나
            </p>

            <input
              ref={fileInputRef}
              type="file"
              accept="video/*"
              onChange={handleFileSelect}
              className="hidden"
              id="video-upload"
            />
            <label
              htmlFor="video-upload"
              className="btn-primary inline-block cursor-pointer"
            >
              파일 선택
            </label>

            <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">
              지원 형식: MP4, AVI, MOV 등
            </p>
          </div>
        </div>
      )}

      {/* TUG 업로드 영역 (두 영상) */}
      {status === 'idle' && testType === 'TUG' && (
        <div className="space-y-4">
          {/* 측면 영상 업로드 */}
          <div
            className={`card border-2 border-dashed transition-all duration-200 ${
              sideDragActive ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20' : sideVideo ? 'border-purple-300 bg-purple-50 dark:bg-purple-900/10' : 'border-gray-200 dark:border-gray-600'
            }`}
            onDragEnter={handleSideDrag}
            onDragLeave={handleSideDrag}
            onDragOver={handleSideDrag}
            onDrop={handleSideDrop}
          >
            <div className="flex items-center mb-3">
              <div className="w-8 h-8 bg-purple-500 rounded-lg flex items-center justify-center mr-3">
                <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              </div>
              <div>
                <h4 className="font-semibold text-gray-800 dark:text-gray-100">측면 영상</h4>
                <p className="text-xs text-gray-500 dark:text-gray-400">보행 분석 및 기립/착석 속도 측정용</p>
              </div>
            </div>

            {sideVideo ? (
              <div className="flex items-center justify-between bg-white dark:bg-gray-700 rounded-xl p-3">
                <div className="flex items-center">
                  <svg className="w-5 h-5 text-purple-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{sideVideo.name}</span>
                  <span className="text-xs text-gray-400 ml-2">({(sideVideo.size / 1024 / 1024).toFixed(2)} MB)</span>
                </div>
                <button onClick={() => setSideVideo(null)} className="p-1 text-gray-400 hover:text-gray-600" aria-label="측면 영상 제거">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ) : (
              <div className="text-center py-4">
                <input
                  ref={sideVideoInputRef}
                  type="file"
                  accept="video/*"
                  onChange={handleSideVideoSelect}
                  className="hidden"
                  id="side-video-upload"
                />
                <label
                  htmlFor="side-video-upload"
                  className="inline-flex items-center px-4 py-2 bg-purple-500 text-white rounded-lg cursor-pointer hover:bg-purple-600 transition-colors"
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  측면 영상 선택
                </label>
              </div>
            )}
          </div>

          {/* 정면 영상 업로드 */}
          <div
            className={`card border-2 border-dashed transition-all duration-200 ${
              frontDragActive ? 'border-teal-500 bg-teal-50 dark:bg-teal-900/20' : frontVideo ? 'border-teal-300 bg-teal-50 dark:bg-teal-900/10' : 'border-gray-200 dark:border-gray-600'
            }`}
            onDragEnter={handleFrontDrag}
            onDragLeave={handleFrontDrag}
            onDragOver={handleFrontDrag}
            onDrop={handleFrontDrop}
          >
            <div className="flex items-center mb-3">
              <div className="w-8 h-8 bg-teal-500 rounded-lg flex items-center justify-center mr-3">
                <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
              <div>
                <h4 className="font-semibold text-gray-800 dark:text-gray-100">정면 영상</h4>
                <p className="text-xs text-gray-500 dark:text-gray-400">어깨/골반 기울기 분석용</p>
              </div>
            </div>

            {frontVideo ? (
              <div className="flex items-center justify-between bg-white dark:bg-gray-700 rounded-xl p-3">
                <div className="flex items-center">
                  <svg className="w-5 h-5 text-teal-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{frontVideo.name}</span>
                  <span className="text-xs text-gray-400 ml-2">({(frontVideo.size / 1024 / 1024).toFixed(2)} MB)</span>
                </div>
                <button onClick={() => setFrontVideo(null)} className="p-1 text-gray-400 hover:text-gray-600" aria-label="정면 영상 제거">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ) : (
              <div className="text-center py-4">
                <input
                  ref={frontVideoInputRef}
                  type="file"
                  accept="video/*"
                  onChange={handleFrontVideoSelect}
                  className="hidden"
                  id="front-video-upload"
                />
                <label
                  htmlFor="front-video-upload"
                  className="inline-flex items-center px-4 py-2 bg-teal-500 text-white rounded-lg cursor-pointer hover:bg-teal-600 transition-colors"
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  정면 영상 선택
                </label>
              </div>
            )}
          </div>

          {/* TUG 분석 시작 버튼 */}
          {sideVideo && frontVideo && (
            <button onClick={handleUpload} className="w-full btn-primary">
              TUG 분석 시작
            </button>
          )}
        </div>
      )}

      {/* BBS 검사 폼 */}
      {status === 'idle' && testType === 'BBS' && (
        <div>
          <div className="card-purple mb-4">
            <div className="flex items-center">
              <div className="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center mr-3">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div>
                <h4 className="font-semibold">Berg Balance Scale (BBS)</h4>
                <p className="text-purple-100 text-sm">14개 항목 균형 평가 검사 (총 56점)</p>
              </div>
            </div>
          </div>

          {/* 평가 방식 선택 */}
          <div className="card mb-4">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">평가 방식 선택</p>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => { setBbsMode('manual'); setBbsAIScores(undefined); }}
                className={`p-3 rounded-xl border-2 transition-all ${
                  bbsMode === 'manual'
                    ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
                    : 'border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:border-gray-300'
                }`}
              >
                <div className="flex flex-col items-center">
                  <svg className="w-8 h-8 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                  </svg>
                  <span className="text-sm font-medium">직접 평가</span>
                  <span className="text-xs text-gray-500 dark:text-gray-400 mt-1">수동 채점</span>
                </div>
              </button>
              <button
                onClick={() => setBbsMode('ai')}
                className={`p-3 rounded-xl border-2 transition-all ${
                  bbsMode === 'ai'
                    ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
                    : 'border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:border-gray-300'
                }`}
              >
                <div className="flex flex-col items-center">
                  <svg className="w-8 h-8 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  <span className="text-sm font-medium">AI 분석</span>
                  <span className="text-xs text-gray-500 dark:text-gray-400 mt-1">영상 업로드</span>
                </div>
              </button>
            </div>
          </div>

          {/* AI 분석 모드: 영상 업로드 */}
          {bbsMode === 'ai' && !bbsAIScores && (
            <div
              className={`card border-2 border-dashed mb-4 transition-all duration-200 ${
                bbsDragActive ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20' : bbsVideo ? 'border-purple-300 bg-purple-50 dark:bg-purple-900/10' : 'border-gray-200 dark:border-gray-600'
              }`}
              onDragEnter={handleBbsDrag}
              onDragLeave={handleBbsDrag}
              onDragOver={handleBbsDrag}
              onDrop={handleBbsDrop}
            >
              <div className="flex items-center mb-3">
                <div className="w-8 h-8 bg-purple-500 rounded-lg flex items-center justify-center mr-3">
                  <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                </div>
                <div>
                  <h4 className="font-semibold text-gray-800 dark:text-gray-100">BBS 검사 영상</h4>
                  <p className="text-xs text-gray-500 dark:text-gray-400">AI가 영상을 분석하여 점수를 추천합니다</p>
                </div>
              </div>

              {bbsVideo ? (
                <div className="flex items-center justify-between bg-white dark:bg-gray-700 rounded-xl p-3">
                  <div className="flex items-center">
                    <svg className="w-5 h-5 text-purple-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{bbsVideo.name}</span>
                    <span className="text-xs text-gray-400 ml-2">({(bbsVideo.size / 1024 / 1024).toFixed(2)} MB)</span>
                  </div>
                  <button onClick={() => setBbsVideo(null)} className="p-1 text-gray-400 hover:text-gray-600" aria-label="BBS 영상 제거">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ) : (
                <div className="text-center py-4">
                  <input
                    ref={bbsVideoInputRef}
                    type="file"
                    accept="video/*"
                    onChange={handleBbsVideoSelect}
                    className="hidden"
                    id="bbs-video-upload"
                  />
                  <label
                    htmlFor="bbs-video-upload"
                    className="inline-flex items-center px-4 py-2 bg-purple-500 text-white rounded-lg cursor-pointer hover:bg-purple-600 transition-colors"
                  >
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                    BBS 검사 영상 선택
                  </label>
                </div>
              )}

              {bbsVideo && (
                <button onClick={handleBbsAIUpload} className="w-full btn-primary mt-4">
                  <svg className="w-4 h-4 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  AI 분석 시작
                </button>
              )}

              {/* AI 분석 가능 항목 안내 */}
              <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <p className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-2">AI 자동 분석 항목 (14개 전체)</p>
                <div className="flex flex-wrap gap-1.5">
                  {['1. 일어나기', '2. 서있기', '3. 앉기', '4. 앉기', '5. 이동', '6. 눈감고', '7. 발모음'].map((item) => (
                    <span key={item} className="px-2 py-0.5 bg-purple-100 dark:bg-purple-900/40 text-purple-600 dark:text-purple-300 text-xs rounded-full">
                      {item}
                    </span>
                  ))}
                </div>
                <div className="flex flex-wrap gap-1.5 mt-1.5">
                  {['8. 팔뻗기', '9. 물건줍기', '10. 뒤돌아보기', '11. 360도', '12. 발판', '13. 탄뎀', '14. 한발'].map((item) => (
                    <span key={item} className="px-2 py-0.5 bg-purple-100 dark:bg-purple-900/40 text-purple-600 dark:text-purple-300 text-xs rounded-full">
                      {item}
                    </span>
                  ))}
                </div>
                <p className="text-xs text-gray-500 mt-2">※ AI 분석 후 점수를 확인하고 필요시 수정하세요</p>
              </div>
            </div>
          )}

          {/* BBS 포즈 오버레이 영상 */}
          {bbsOverlayUrl && (
            <div className="card mb-4">
              <div className="flex items-center mb-3">
                <div className="w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center mr-3">
                  <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                </div>
                <div>
                  <h4 className="font-semibold text-gray-800 dark:text-gray-100">Pose Landmark 분석 영상</h4>
                  <p className="text-xs text-gray-500 dark:text-gray-400">MediaPipe Pose로 감지된 관절점이 표시됩니다</p>
                </div>
              </div>
              <video
                src={bbsOverlayUrl}
                controls
                className="w-full rounded-xl"
                playsInline
              />
            </div>
          )}

          {/* AI 분석 완료 또는 수동 모드: BBS 폼 */}
          {(bbsMode === 'manual' || bbsAIScores) && (
            <BBSForm onSubmit={handleBBSSubmit} isLoading={bbsLoading} aiScores={bbsAIScores} />
          )}
        </div>
      )}

      {/* 파일 선택됨 (10MWT) */}
      {file && status === 'idle' && testType === '10MWT' && (
        <div className="card mt-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-xl flex items-center justify-center">
                <svg className="w-6 h-6 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </div>
              <div>
                <p className="font-medium text-gray-800 dark:text-gray-100">{file.name}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </div>
            <button onClick={handleReset} className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300" aria-label="파일 제거">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <button onClick={handleUpload} className="w-full btn-primary mt-4">
            분석 시작
          </button>
        </div>
      )}

      {/* 진행 상태 */}
      {(status === 'uploading' || status === 'analyzing') && (
        <UploadProgress
          uploadProgress={uploadProgress}
          analysisProgress={analysisProgress}
          status={status}
          message={message}
        />
      )}

      {/* 완료 */}
      {status === 'completed' && result && (
        <div className="card border-2 border-green-200 bg-green-50">
          <div className="flex items-center space-x-4 mb-6">
            <div className="w-14 h-14 bg-green-500 rounded-2xl flex items-center justify-center">
              <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-bold text-green-800">분석 완료!</h3>
              <p className="text-green-600 text-sm">검사 결과가 저장되었습니다</p>
            </div>
          </div>

          <div className={`grid ${result.test_type === 'TUG' ? 'grid-cols-1' : 'grid-cols-2'} gap-4 mb-6`}>
            <div className="text-center p-4 bg-white rounded-xl">
              <p className="text-xs text-gray-500 mb-1">{result.test_type === 'TUG' ? '총 소요 시간' : '보행 시간'}</p>
              <p className="text-3xl font-bold text-gray-800">{result.walk_time_seconds?.toFixed(2)}<span className="text-sm text-gray-500">초</span></p>
            </div>
            {result.test_type !== 'TUG' && (
              <div className="text-center p-4 bg-white rounded-xl">
                <p className="text-xs text-gray-500 mb-1">보행 속도</p>
                <p className="text-3xl font-bold text-blue-600">{result.walk_speed_mps?.toFixed(2)}<span className="text-sm text-gray-500">m/s</span></p>
              </div>
            )}
          </div>

          <div className="flex space-x-3">
            <button onClick={handleReset} className="flex-1 btn-secondary">
              새 검사
            </button>
            <Link to={`/patients/${patient.id}`} className="flex-1 btn-primary text-center">
              환자 정보
            </Link>
          </div>
        </div>
      )}

      {/* 에러 */}
      {status === 'error' && (
        <div role="alert" className="card border-2 border-red-200 bg-red-50">
          <div className="flex items-center space-x-4 mb-4">
            <div className="w-14 h-14 bg-red-500 rounded-2xl flex items-center justify-center">
              <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-bold text-red-800">분석 실패</h3>
              <p className="text-red-600 text-sm">{message}</p>
            </div>
          </div>

          <button onClick={handleReset} className="w-full btn-primary">
            다시 시도
          </button>
        </div>
      )}

      {/* 촬영 가이드 */}
      <div className="card mt-6 bg-gray-50 dark:bg-gray-800">
        <h4 className="font-semibold text-gray-800 dark:text-gray-100 mb-3">
          {testType === 'TUG' ? 'TUG 검사 촬영 가이드' : '촬영 가이드'}
        </h4>
        {testType === 'TUG' ? (
          <div className="space-y-4">
            {/* TUG 검사 순서 */}
            <div>
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">검사 순서</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                의자에서 일어나 → 3m 걷기 → 돌아서기 → 3m 돌아오기 → 앉기
              </p>
            </div>

            {/* 측면 영상 가이드 */}
            <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-xl">
              <p className="text-sm font-medium text-purple-700 dark:text-purple-300 mb-2 flex items-center">
                <span className="w-5 h-5 bg-purple-500 rounded-full flex items-center justify-center text-white text-xs mr-2">1</span>
                측면 영상 촬영
              </p>
              <ul className="text-sm text-purple-600 dark:text-purple-400 space-y-1 ml-7">
                <li>• 환자의 측면에서 전체 동작이 보이도록 촬영</li>
                <li>• 기립/착석 동작과 보행이 모두 포함되어야 함</li>
                <li>• 엉덩이와 무릎의 움직임이 잘 보여야 함</li>
              </ul>
            </div>

            {/* 정면 영상 가이드 */}
            <div className="p-3 bg-teal-50 dark:bg-teal-900/20 rounded-xl">
              <p className="text-sm font-medium text-teal-700 dark:text-teal-300 mb-2 flex items-center">
                <span className="w-5 h-5 bg-teal-500 rounded-full flex items-center justify-center text-white text-xs mr-2">2</span>
                정면 영상 촬영
              </p>
              <ul className="text-sm text-teal-600 dark:text-teal-400 space-y-1 ml-7">
                <li>• 환자의 정면에서 어깨와 골반이 보이도록 촬영</li>
                <li>• 보행 중 좌우 기울기 분석에 사용됨</li>
                <li>• 걷는 방향으로 카메라를 향하게 설정</li>
              </ul>
            </div>

            {/* 평가 기준 */}
            <div className="text-xs text-gray-500 dark:text-gray-400 pt-2 border-t border-gray-200 dark:border-gray-600">
              평가 기준: &lt;10초 정상 / 10-20초 양호 / 20-30초 주의 / &gt;30초 낙상위험
            </div>
          </div>
        ) : (
          <ul className="text-sm text-gray-600 dark:text-gray-300 space-y-2">
            <li className="flex items-start">
              <span className="text-blue-500 mr-2">•</span>
              환자의 측후면에서 촬영하세요
            </li>
            <li className="flex items-start">
              <span className="text-blue-500 mr-2">•</span>
              10m 보행 경로가 모두 보이도록 하세요
            </li>
            <li className="flex items-start">
              <span className="text-blue-500 mr-2">•</span>
              환자가 자연스러운 속도로 걷도록 안내하세요
            </li>
            <li className="flex items-start">
              <span className="text-blue-500 mr-2">•</span>
              밝은 조명 환경을 권장합니다
            </li>
            <li className="flex items-start">
              <span className="text-green-500 mr-2">•</span>
              <span>
                START/FINISH 마커를 2m/12m 지점에 배치하면 정확도가 향상됩니다.{' '}
                <a href="/api/tests/aruco/markers/pdf"
                   className="text-blue-600 dark:text-blue-400 underline font-medium hover:text-blue-800 dark:hover:text-blue-300"
                   download>
                  마커 PDF 다운로드
                </a>
              </span>
            </li>
          </ul>
        )}
      </div>
    </div>
  );
}
