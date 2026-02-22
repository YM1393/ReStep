import axios from 'axios';
import type { Patient, PatientCreate, WalkTest, AnalysisStatus, ComparisonResult, User, Therapist, VideoInfo, TestType, BBSItemScores, PatientStats, PatientTag, PatientGoal, GoalProgress, ComparisonReportData, AdminDashboardStats, RecommendationsResponse, TrendAnalysisResponse, Site, SiteStats, EMRStatus, ClinicalNormativeResponse, ClinicalTrendsResponse, ClinicalCorrelationsResponse } from '../types';

const API_URL = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: API_URL,
});

// 요청 인터셉터: JWT 토큰 + 기존 X-User-* 헤더 (backward compat)
api.interceptors.request.use((config) => {
  // ngrok 무료 계정 브라우저 경고 페이지 우회
  config.headers['ngrok-skip-browser-warning'] = 'true';

  // JWT 토큰이 있으면 Authorization 헤더에 추가
  const accessToken = localStorage.getItem('access_token');
  if (accessToken) {
    config.headers['Authorization'] = `Bearer ${accessToken}`;
  }

  // 기존 X-User-* 헤더도 유지 (backward compat)
  const userStr = localStorage.getItem('user');
  if (userStr) {
    const user: User = JSON.parse(userStr);
    config.headers['X-User-Id'] = user.id;
    config.headers['X-User-Role'] = user.role;
    config.headers['X-User-Approved'] = user.is_approved ? 'true' : 'false';
  }
  return config;
});

// 응답 인터셉터: 401 시 토큰 갱신 시도
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // 401이고 이미 retry한 요청이 아닌 경우 토큰 갱신 시도
    if (error.response?.status === 401 && !originalRequest._retry) {
      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) {
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers['Authorization'] = `Bearer ${token}`;
            return api(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const response = await axios.post(`${API_URL}/api/auth/refresh`, {
          refresh_token: refreshToken,
        });
        const newAccessToken = response.data.access_token;
        localStorage.setItem('access_token', newAccessToken);
        originalRequest.headers['Authorization'] = `Bearer ${newAccessToken}`;
        processQueue(null, newAccessToken);
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        // 리프레시 실패 시 로그아웃
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  login: async (username: string, password: string) => {
    const response = await api.post('/api/auth/login', { username, password });
    const data = response.data;

    // JWT 토큰 저장
    if (data.access_token) {
      localStorage.setItem('access_token', data.access_token);
    }
    if (data.refresh_token) {
      localStorage.setItem('refresh_token', data.refresh_token);
    }

    return data;
  },

  register: async (username: string, password: string, name: string) => {
    const response = await api.post('/api/auth/register', { username, password, name });
    return response.data;
  },

  logout: () => {
    localStorage.removeItem('user');
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },

  getCurrentUser: (): User | null => {
    const user = localStorage.getItem('user');
    return user ? JSON.parse(user) : null;
  },
};

// Admin API
export const adminApi = {
  getAllTherapists: async (): Promise<Therapist[]> => {
    const response = await api.get('/api/admin/therapists');
    return response.data;
  },

  getPendingTherapists: async (): Promise<Therapist[]> => {
    const response = await api.get('/api/admin/therapists/pending');
    return response.data;
  },

  approveTherapist: async (userId: string): Promise<Therapist> => {
    const response = await api.post(`/api/admin/therapists/${userId}/approve`);
    return response.data;
  },

  deleteTherapist: async (userId: string): Promise<void> => {
    await api.delete(`/api/admin/therapists/${userId}`);
  },
};

// 환자 API
export const patientApi = {
  create: async (data: PatientCreate): Promise<Patient> => {
    const response = await api.post('/api/patients/', data);
    return response.data;
  },

  getAll: async (limit = 50): Promise<Patient[]> => {
    const response = await api.get(`/api/patients/?limit=${limit}`);
    return response.data;
  },

  getAllWithLatestTest: async (limit = 50): Promise<any[]> => {
    const response = await api.get(`/api/patients/with-latest-test?limit=${limit}`);
    return response.data;
  },

  search: async (query: string): Promise<Patient[]> => {
    const response = await api.get(`/api/patients/search?q=${encodeURIComponent(query)}`);
    return response.data;
  },

  getById: async (id: string): Promise<Patient> => {
    const response = await api.get(`/api/patients/${id}`);
    return response.data;
  },

  update: async (id: string, data: Partial<PatientCreate>): Promise<Patient> => {
    const response = await api.put(`/api/patients/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/api/patients/${id}`);
  },

  // 태그 관련
  getAllTags: async (): Promise<PatientTag[]> => {
    const response = await api.get('/api/patients/tags/all');
    return response.data;
  },

  createTag: async (name: string, color: string): Promise<PatientTag> => {
    const response = await api.post('/api/patients/tags', { name, color });
    return response.data;
  },

  deleteTag: async (tagId: string): Promise<void> => {
    await api.delete(`/api/patients/tags/${tagId}`);
  },

  getPatientTags: async (patientId: string): Promise<PatientTag[]> => {
    const response = await api.get(`/api/patients/${patientId}/tags`);
    return response.data;
  },

  addPatientTag: async (patientId: string, tagId: string): Promise<void> => {
    await api.post(`/api/patients/${patientId}/tags/${tagId}`);
  },

  removePatientTag: async (patientId: string, tagId: string): Promise<void> => {
    await api.delete(`/api/patients/${patientId}/tags/${tagId}`);
  },

  getPatientsByTag: async (tagId: string): Promise<Patient[]> => {
    const response = await api.get(`/api/patients/by-tag/${tagId}`);
    return response.data;
  },
};

// 검사 API
export const testApi = {
  upload: async (
    patientId: string,
    file: File,
    onProgress?: (progress: number) => void,
    walkingDirection: 'toward' | 'away' = 'away',
    testType: TestType = '10MWT'
  ): Promise<{ file_id: string; status_endpoint: string }> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post(`/api/tests/${patientId}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
        'X-Walking-Direction': walkingDirection,
        'X-Test-Type': testType,
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });
    return response.data;
  },

  // TUG 검사용 두 영상 업로드
  uploadTUG: async (
    patientId: string,
    sideVideo: File,
    frontVideo: File,
    onProgress?: (progress: number) => void
  ): Promise<{ file_id: string; status_endpoint: string }> => {
    const formData = new FormData();
    formData.append('side_video', sideVideo);
    formData.append('front_video', frontVideo);

    const response = await api.post(`/api/tests/${patientId}/upload-tug`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });
    return response.data;
  },

  getStatus: async (fileId: string): Promise<AnalysisStatus> => {
    const response = await api.get(`/api/tests/status/${fileId}`);
    return response.data;
  },

  getPatientTests: async (patientId: string, testType?: TestType | 'ALL'): Promise<WalkTest[]> => {
    const params = testType && testType !== 'ALL' ? `?test_type=${testType}` : '';
    const response = await api.get(`/api/tests/patient/${patientId}${params}`);
    return response.data;
  },

  getById: async (testId: string): Promise<WalkTest> => {
    const response = await api.get(`/api/tests/${testId}`);
    return response.data;
  },

  compare: async (patientId: string): Promise<ComparisonResult> => {
    const response = await api.get(`/api/tests/patient/${patientId}/compare`);
    return response.data;
  },

  getStats: async (patientId: string, testType: TestType = '10MWT'): Promise<PatientStats> => {
    const response = await api.get(`/api/tests/patient/${patientId}/stats?test_type=${testType}`);
    return response.data;
  },

  downloadCsv: (testId: string): string => {
    return `${API_URL}/api/tests/${testId}/report/csv`;
  },

  downloadPdf: (testId: string, template?: string): string => {
    const params = template ? `?template=${template}` : '';
    return `${API_URL}/api/tests/${testId}/report/pdf${params}`;
  },

  sendReportEmail: async (testId: string, toEmail: string, message?: string, template?: string): Promise<{ success: boolean; message: string }> => {
    const response = await api.post(`/api/tests/${testId}/report/email`, {
      to_email: toEmail,
      message: message || null,
      template: template || 'standard',
    });
    return response.data;
  },

  // 영상 관련 메서드
  getVideoUrl: (test: WalkTest): string | null => {
    if (!test.video_url) return null;
    return `${API_URL}${test.video_url}`;
  },

  getVideoInfo: async (testId: string): Promise<VideoInfo> => {
    const response = await api.get(`/api/tests/${testId}/video/info`);
    return response.data;
  },

  downloadVideo: (testId: string): string => {
    return `${API_URL}/api/tests/${testId}/video/download`;
  },

  // MediaPipe 포즈 오버레이 영상 스트리밍 URL
  getVideoOverlayUrl: (testId: string): string => {
    return `${API_URL}/api/tests/${testId}/video/overlay`;
  },

  // MediaPipe 포즈 오버레이 단일 프레임 URL
  getVideoOverlayFrameUrl: (testId: string, frameNum: number): string => {
    return `${API_URL}/api/tests/${testId}/video/overlay/frame?frame_num=${frameNum}`;
  },

  // TUG 단계별 클립 URL
  getPhaseClipUrl: (testId: string, phaseName: string): string => {
    return `${API_URL}/api/tests/${testId}/phase-clip/${phaseName}`;
  },

  updateTestDate: async (testId: string, testDate: string): Promise<WalkTest> => {
    const response = await api.put(`/api/tests/${testId}/date`, { test_date: testDate });
    return response.data.test;
  },

  updateTestNotes: async (testId: string, notes: string): Promise<WalkTest> => {
    const response = await api.put(`/api/tests/${testId}/notes`, { notes });
    return response.data.test;
  },

  delete: async (testId: string): Promise<void> => {
    await api.delete(`/api/tests/${testId}`);
  },

  // BBS 검사 저장
  createBBS: async (
    patientId: string,
    scores: BBSItemScores,
    notes?: string
  ): Promise<{ test_id: string; total_score: number; assessment: string; assessment_label: string }> => {
    const response = await api.post(`/api/tests/${patientId}/bbs`, { scores, notes });
    return response.data;
  },

  // 비교 리포트
  getComparisonReport: async (patientId: string, testId?: string, prevId?: string): Promise<ComparisonReportData> => {
    const params = new URLSearchParams();
    if (testId) params.set('test_id', testId);
    if (prevId) params.set('prev_id', prevId);
    const response = await api.get(`/api/tests/patient/${patientId}/comparison-report?${params}`);
    return response.data;
  },

  // 영상 하이라이트 클립
  getWalkingClipUrl: (testId: string): string => {
    return `${API_URL}/api/tests/${testId}/video/walking-clip`;
  },

  getComparisonVideoUrl: (patientId: string, test1Id: string, test2Id: string): string => {
    return `${API_URL}/api/tests/patient/${patientId}/video/comparison?test1_id=${test1Id}&test2_id=${test2Id}`;
  },

  // BBS 영상 업로드 (AI 분석)
  uploadBBS: async (
    patientId: string,
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<{ file_id: string; status_endpoint: string }> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post(`/api/tests/${patientId}/upload-bbs`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });
    return response.data;
  },

  // AI 리포트
  getAIReport: async (testId: string): Promise<any> => {
    const response = await api.get(`/api/tests/${testId}/ai-report`);
    return response.data;
  },

  // 재활 추천
  getRecommendations: async (patientId: string): Promise<RecommendationsResponse> => {
    const response = await api.get(`/api/tests/patient/${patientId}/recommendations`);
    return response.data;
  },

  // 추세 분석
  getTrends: async (patientId: string, testType: TestType = '10MWT'): Promise<TrendAnalysisResponse> => {
    const response = await api.get(`/api/tests/patient/${patientId}/trends?test_type=${testType}`);
    return response.data;
  },

  // 임상 변수 연령/성별 정상 범위
  getClinicalNormative: async (patientId: string, testId?: string): Promise<ClinicalNormativeResponse> => {
    const params = testId ? `?test_id=${testId}` : '';
    const response = await api.get(`/api/tests/patient/${patientId}/clinical-normative${params}`);
    return response.data;
  },

  // 임상 변수 추세
  getClinicalTrends: async (patientId: string, testType: TestType = '10MWT'): Promise<ClinicalTrendsResponse> => {
    const response = await api.get(`/api/tests/patient/${patientId}/clinical-trends?test_type=${testType}`);
    return response.data;
  },

  // 임상 변수 상관관계
  getClinicalCorrelations: async (patientId: string, testType: TestType = '10MWT'): Promise<ClinicalCorrelationsResponse> => {
    const response = await api.get(`/api/tests/patient/${patientId}/clinical-correlations?test_type=${testType}`);
    return response.data;
  },
};

// 목표 API
export const goalApi = {
  create: async (patientId: string, data: Partial<PatientGoal>): Promise<PatientGoal> => {
    const response = await api.post(`/api/goals/${patientId}`, data);
    return response.data;
  },

  getAll: async (patientId: string, status?: string): Promise<PatientGoal[]> => {
    const params = status ? `?status=${status}` : '';
    const response = await api.get(`/api/goals/${patientId}${params}`);
    return response.data;
  },

  update: async (goalId: string, data: Partial<PatientGoal>): Promise<PatientGoal> => {
    const response = await api.put(`/api/goals/${goalId}/update`, data);
    return response.data;
  },

  delete: async (goalId: string): Promise<void> => {
    await api.delete(`/api/goals/${goalId}/delete`);
  },

  getProgress: async (patientId: string): Promise<GoalProgress[]> => {
    const response = await api.get(`/api/goals/${patientId}/progress`);
    return response.data;
  },
};

// 보행 경로 API
export interface WalkingRoute {
  id: string;
  patient_id: string;
  origin_address: string;
  origin_lat: number;
  origin_lng: number;
  dest_address: string;
  dest_lat: number;
  dest_lng: number;
  distance_meters: number | null;
  created_at: string;
}

export const walkingRouteApi = {
  getAll: async (patientId: string): Promise<WalkingRoute[]> => {
    const response = await api.get(`/api/walking-routes/${patientId}`);
    return response.data;
  },
  create: async (patientId: string, data: Omit<WalkingRoute, 'id' | 'patient_id' | 'created_at'>): Promise<WalkingRoute> => {
    const response = await api.post(`/api/walking-routes/${patientId}`, data);
    return response.data;
  },
  delete: async (routeId: string): Promise<void> => {
    await api.delete(`/api/walking-routes/${routeId}/delete`);
  },
};

// 맞춤형 거리 목표 API
export interface DistanceGoal {
  id: string;
  patient_id: string;
  distance_meters: number;
  label: string;
  emoji: string;
  created_at: string;
}

export const distanceGoalApi = {
  getAll: async (patientId: string): Promise<DistanceGoal[]> => {
    const response = await api.get(`/api/distance-goals/${patientId}`);
    return response.data;
  },
  create: async (patientId: string, data: { distance_meters: number; label: string; emoji?: string }): Promise<DistanceGoal> => {
    const response = await api.post(`/api/distance-goals/${patientId}`, data);
    return response.data;
  },
  delete: async (goalId: string): Promise<void> => {
    await api.delete(`/api/distance-goals/${goalId}/delete`);
  },
};

// 관리자 대시보드 API
export const dashboardApi = {
  getStats: async (): Promise<AdminDashboardStats> => {
    const response = await api.get('/api/admin/dashboard/stats');
    return response.data;
  },
  getRecentTests: async (limit = 5): Promise<{
    id: string; patient_id: string; test_date: string; test_type: string;
    walk_time_seconds: number; walk_speed_mps: number;
    patient_name: string; patient_number: string;
  }[]> => {
    const response = await api.get(`/api/dashboard/recent-tests?limit=${limit}`);
    return response.data;
  },
  getWeeklyActivity: async (): Promise<{ day: string; date: string; count: number }[]> => {
    const response = await api.get('/api/dashboard/weekly-activity');
    return response.data;
  },
  getSpeedDistribution: async (): Promise<{ name: string; value: number; color: string }[]> => {
    const response = await api.get('/api/dashboard/speed-distribution');
    return response.data;
  },
};

// 데이터 내보내기 API
export const exportApi = {
  patientsCSV: (): string => `${API_URL}/api/admin/export/patients-csv`,
  testsCSV: (params?: { test_type?: string; date_from?: string; date_to?: string }): string => {
    const searchParams = new URLSearchParams();
    if (params?.test_type) searchParams.set('test_type', params.test_type);
    if (params?.date_from) searchParams.set('date_from', params.date_from);
    if (params?.date_to) searchParams.set('date_to', params.date_to);
    const qs = searchParams.toString();
    return `${API_URL}/api/admin/export/tests-csv${qs ? '?' + qs : ''}`;
  },
  backup: (): string => `${API_URL}/api/admin/export/backup`,
  batchPdf: (patientId: string): string => `${API_URL}/api/tests/patient/${patientId}/report/batch-pdf`,
};

// Multi-site API
export const siteApi = {
  getAll: async (): Promise<Site[]> => {
    const response = await api.get('/api/admin/sites');
    return response.data;
  },
  create: async (data: { name: string; address?: string; phone?: string }): Promise<Site> => {
    const response = await api.post('/api/admin/sites', data);
    return response.data;
  },
  update: async (siteId: string, data: { name?: string; address?: string; phone?: string }): Promise<Site> => {
    const response = await api.put(`/api/admin/sites/${siteId}`, data);
    return response.data;
  },
  getStats: async (siteId: string): Promise<SiteStats> => {
    const response = await api.get(`/api/admin/sites/${siteId}/stats`);
    return response.data;
  },
};

// 알림 API
export interface Notification {
  id: string;
  user_id: string;
  type: 'analysis_complete' | 'goal_achieved' | 'therapist_approved';
  title: string;
  message: string;
  data?: { patient_id?: string; test_id?: string; test_type?: string };
  is_read: number;
  created_at: string;
}

export const notificationApi = {
  getAll: async (limit = 20, offset = 0): Promise<Notification[]> => {
    const response = await api.get(`/api/notifications?limit=${limit}&offset=${offset}`);
    return response.data;
  },
  getUnreadCount: async (): Promise<number> => {
    const response = await api.get('/api/notifications/unread-count');
    return response.data.count;
  },
  markRead: async (id: string): Promise<void> => {
    await api.put(`/api/notifications/${id}/read`);
  },
  markAllRead: async (): Promise<void> => {
    await api.put('/api/notifications/read-all');
  },
};

// EMR API
export const emrApi = {
  getStatus: async (): Promise<EMRStatus> => {
    const response = await api.get('/api/emr/status');
    return response.data;
  },
  search: async (name: string): Promise<{ patients: unknown[] }> => {
    const response = await api.get(`/api/emr/search?name=${encodeURIComponent(name)}`);
    return response.data;
  },
  exportPatient: async (patientId: string): Promise<{ message: string; tests_exported: number }> => {
    const response = await api.post(`/api/emr/patients/${patientId}/export`);
    return response.data;
  },
  importPatient: async (fhirUrl: string, patientId: string): Promise<{ message: string; patient: Patient; imported: boolean }> => {
    const response = await api.post('/api/emr/import', { fhir_url: fhirUrl, patient_id: patientId });
    return response.data;
  },
};
