import { useState, useEffect, lazy, Suspense, Component, type ReactNode, type ErrorInfo } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import { authApi } from './services/api'

// Lazy-loaded pages — each becomes a separate JS chunk
const Dashboard = lazy(() => import('./pages/Dashboard'))
const PatientForm = lazy(() => import('./pages/PatientForm'))
const PatientDetail = lazy(() => import('./pages/PatientDetail'))
const VideoUpload = lazy(() => import('./pages/VideoUpload'))
const History = lazy(() => import('./pages/History'))
const Login = lazy(() => import('./pages/Login'))
const Register = lazy(() => import('./pages/Register'))
const Landing = lazy(() => import('./pages/Landing'))
const TUGRealtimePage = lazy(() => import('./pages/TUGRealtimePage'))
const TherapistManagement = lazy(() => import('./pages/TherapistManagement'))
const AdminDashboard = lazy(() => import('./pages/AdminDashboard'))
import type { User } from './types'
import { ThemeProvider } from './contexts/ThemeContext'
import ToastContainer from './components/Toast'

class ErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean; error: Error | null }> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }
  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 text-center">
          <h2 className="text-xl font-bold text-red-600 mb-2">렌더링 오류 발생</h2>
          <pre className="text-left bg-gray-100 p-4 rounded text-sm overflow-auto max-h-96 text-red-800">
            {this.state.error?.message}{'\n'}{this.state.error?.stack}
          </pre>
          <button onClick={() => this.setState({ hasError: false, error: null })} className="mt-4 px-4 py-2 bg-blue-600 text-white rounded">
            다시 시도
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

function OfflineBanner() {
  const [offline, setOffline] = useState(!navigator.onLine);

  useEffect(() => {
    const goOffline = () => setOffline(true);
    const goOnline = () => setOffline(false);
    window.addEventListener('offline', goOffline);
    window.addEventListener('online', goOnline);
    return () => {
      window.removeEventListener('offline', goOffline);
      window.removeEventListener('online', goOnline);
    };
  }, []);

  if (!offline) return null;

  return (
    <div className="bg-amber-500 text-white text-center text-sm py-2 px-4 font-medium" role="alert">
      오프라인 모드 - 캐시된 데이터만 표시됩니다
    </div>
  );
}

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 저장된 사용자 정보 확인
    const savedUser = authApi.getCurrentUser();
    if (savedUser) {
      setUser(savedUser);
    }
    setLoading(false);
  }, []);

  const handleLogin = (loggedInUser: User) => {
    setUser(loggedInUser);
  };

  const handleLogout = () => {
    authApi.logout();
    setUser(null);
  };

  if (loading) {
    return (
      <ThemeProvider>
        <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      </ThemeProvider>
    );
  }

  const PageLoader = (
    <div className="flex items-center justify-center py-20">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
    </div>
  );

  // 로그인하지 않은 경우
  if (!user) {
    return (
      <ThemeProvider>
        <OfflineBanner />
        <Suspense fallback={PageLoader}>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login onLogin={handleLogin} />} />
            <Route path="/register" element={<Register />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </ThemeProvider>
    );
  }

  const isAdmin = user.role === 'admin';
  const isApprovedTherapist = user.role === 'therapist' && user.is_approved;

  return (
    <ThemeProvider>
      <OfflineBanner />
      <ToastContainer />
      <Layout user={user} onLogout={handleLogout}>
        <Suspense fallback={PageLoader}>
          <Routes>
            <Route path="/" element={<Dashboard />} />

            {/* 승인된 물리치료사만 접근 가능한 라우트 */}
            {isApprovedTherapist && (
              <>
                <Route path="/patients/new" element={<PatientForm />} />
                <Route path="/patients/:id/edit" element={<PatientForm />} />
                <Route path="/patients/:id/test" element={<VideoUpload />} />
                <Route path="/patients/:id/tug-realtime" element={<TUGRealtimePage />} />
              </>
            )}

            {/* 모든 로그인 사용자가 접근 가능한 라우트 */}
            <Route path="/patients/:id" element={<ErrorBoundary><PatientDetail /></ErrorBoundary>} />
            <Route path="/patients/:id/history" element={<History />} />

            {/* 관리자만 접근 가능한 라우트 */}
            {isAdmin && (
              <>
                <Route path="/admin/therapists" element={<TherapistManagement />} />
                <Route path="/admin/dashboard" element={<AdminDashboard />} />
              </>
            )}

            <Route path="/login" element={<Navigate to="/" replace />} />
            <Route path="/register" element={<Navigate to="/" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </Layout>
    </ThemeProvider>
  )
}

export default App
