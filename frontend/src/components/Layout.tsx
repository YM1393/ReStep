import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ReactNode, useState, useEffect, useRef } from 'react';
import type { User, Patient } from '../types';
import { patientApi } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';
import NotificationBell from './NotificationBell';

interface LayoutProps {
  children: ReactNode;
  user?: User;
  onLogout?: () => void;
}

export default function Layout({ children, user, onLogout }: LayoutProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();

  // 환자 검색 관련 상태
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Patient[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);

  const isAdmin = user?.role === 'admin';
  const isApprovedTherapist = user?.role === 'therapist' && user?.is_approved;

  // 검색 디바운스
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      setShowDropdown(false);
      return;
    }

    const timer = setTimeout(async () => {
      setIsSearching(true);
      try {
        const results = await patientApi.search(searchQuery);
        setSearchResults(results.slice(0, 5)); // 최대 5개만 표시
        setShowDropdown(true);
      } catch (error) {
        console.error('검색 오류:', error);
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // 외부 클릭 시 드롭다운 닫기
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const [activeSearchIndex, setActiveSearchIndex] = useState(-1);

  // 환자 선택 시 히스토리 페이지로 이동
  const handlePatientSelect = (patient: Patient) => {
    setSearchQuery('');
    setShowDropdown(false);
    setActiveSearchIndex(-1);
    navigate(`/patients/${patient.id}/history`);
  };

  // 검색 드롭다운 키보드 네비게이션 (WCAG 2.1.1)
  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (!showDropdown || searchResults.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveSearchIndex(prev => Math.min(prev + 1, searchResults.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveSearchIndex(prev => Math.max(prev - 1, -1));
    } else if (e.key === 'Enter' && activeSearchIndex >= 0) {
      e.preventDefault();
      handlePatientSelect(searchResults[activeSearchIndex]);
    } else if (e.key === 'Escape') {
      setShowDropdown(false);
      setActiveSearchIndex(-1);
    }
  };

  const getRoleBadge = () => {
    if (isAdmin) {
      return (
        <span className="px-2 py-0.5 bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300 text-xs rounded-full">
          관리자
        </span>
      );
    }
    if (user?.role === 'therapist') {
      return (
        <span className="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 text-xs rounded-full">
          물리치료사
        </span>
      );
    }
    return null;
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* 본문 건너뛰기 링크 */}
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[100] focus:px-4 focus:py-2 focus:bg-blue-600 focus:text-white focus:rounded-lg focus:ring-2 focus:ring-blue-400 focus:ring-offset-2">
        본문으로 건너뛰기
      </a>

      {/* 헤더 */}
      <header className="bg-white dark:bg-gray-800 shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            {/* 로고 */}
            <Link to="/" className="flex items-center">
              <span className="text-2xl font-extrabold text-[#1A8CFF] tracking-tight">ReStep</span>
            </Link>

            {/* 네비게이션 */}
            <div className="flex items-center space-x-2">
              <nav aria-label="주 메뉴" className="hidden sm:flex items-center space-x-1 bg-gray-100 dark:bg-gray-700 rounded-xl p-1">
                <Link
                  to="/"
                  aria-current={location.pathname === '/' ? 'page' : undefined}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                    location.pathname === '/'
                      ? 'bg-white dark:bg-gray-600 text-blue-600 dark:text-blue-400 shadow-sm'
                      : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white'
                  }`}
                >
                  대시보드
                </Link>
                {isApprovedTherapist && (
                  <Link
                    to="/patients/new"
                    aria-current={location.pathname === '/patients/new' ? 'page' : undefined}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                      location.pathname === '/patients/new'
                        ? 'bg-white dark:bg-gray-600 text-blue-600 dark:text-blue-400 shadow-sm'
                        : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white'
                    }`}
                  >
                    환자 등록
                  </Link>
                )}
                {/* 환자 검색 */}
                {(isApprovedTherapist || isAdmin) && (
                  <div ref={searchRef} className="relative">
                    <div className="flex items-center bg-white dark:bg-gray-600 rounded-lg px-3 py-1.5 shadow-sm">
                      <svg className="w-4 h-4 text-gray-400 dark:text-gray-300 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                      <input
                        type="text"
                        placeholder="환자 검색..."
                        value={searchQuery}
                        onChange={(e) => { setSearchQuery(e.target.value); setActiveSearchIndex(-1); }}
                        onFocus={() => searchQuery && setShowDropdown(true)}
                        onKeyDown={handleSearchKeyDown}
                        className="w-32 text-sm bg-transparent border-none outline-none focus:w-40 transition-all duration-200 placeholder-gray-400 dark:placeholder-gray-400 text-gray-800 dark:text-gray-100"
                        role="combobox"
                        aria-label="환자 검색"
                        aria-expanded={showDropdown && searchResults.length > 0}
                        aria-autocomplete="list"
                        aria-controls="search-results-listbox"
                        aria-activedescendant={activeSearchIndex >= 0 ? `search-result-${activeSearchIndex}` : undefined}
                      />
                      {isSearching && (
                        <svg className="w-4 h-4 text-blue-500 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                      )}
                    </div>
                    {/* 검색 결과 드롭다운 */}
                    {showDropdown && searchResults.length > 0 && (
                      <div id="search-results-listbox" role="listbox" className="absolute top-full left-0 mt-1 w-64 bg-white dark:bg-gray-700 rounded-lg shadow-lg border border-gray-200 dark:border-gray-600 py-1 z-50">
                        {searchResults.map((patient, index) => (
                          <button
                            key={patient.id}
                            id={`search-result-${index}`}
                            role="option"
                            aria-selected={activeSearchIndex === index}
                            onClick={() => handlePatientSelect(patient)}
                            className={`w-full px-4 py-2 text-left transition-colors ${activeSearchIndex === index ? 'bg-blue-50 dark:bg-gray-600' : 'hover:bg-blue-50 dark:hover:bg-gray-600'}`}
                          >
                            <div className="text-sm font-medium text-gray-800 dark:text-gray-100">{patient.name}</div>
                            <div className="text-xs text-gray-500 dark:text-gray-400">
                              {patient.patient_number} · {patient.gender === 'M' ? '남' : '여'}
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                    {showDropdown && searchQuery && searchResults.length === 0 && !isSearching && (
                      <div className="absolute top-full left-0 mt-1 w-64 bg-white dark:bg-gray-700 rounded-lg shadow-lg border border-gray-200 dark:border-gray-600 py-3 px-4 z-50">
                        <p className="text-sm text-gray-500 dark:text-gray-400 text-center">검색 결과가 없습니다</p>
                      </div>
                    )}
                  </div>
                )}
                {isAdmin && (
                  <>
                    <Link
                      to="/admin/therapists"
                      aria-current={location.pathname === '/admin/therapists' ? 'page' : undefined}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                        location.pathname === '/admin/therapists'
                          ? 'bg-white dark:bg-gray-600 text-purple-600 dark:text-purple-400 shadow-sm'
                          : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white'
                      }`}
                    >
                      치료사 관리
                    </Link>
                    <Link
                      to="/admin/dashboard"
                      aria-current={location.pathname === '/admin/dashboard' ? 'page' : undefined}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                        location.pathname === '/admin/dashboard'
                          ? 'bg-white dark:bg-gray-600 text-purple-600 dark:text-purple-400 shadow-sm'
                          : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white'
                      }`}
                    >
                      통계
                    </Link>
                  </>
                )}
              </nav>

              {/* 알림 */}
              <NotificationBell />

              {/* 다크 모드 토글 */}
              <button
                onClick={toggleTheme}
                className="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-all duration-200"
                aria-label={theme === 'light' ? '다크 모드로 전환' : '라이트 모드로 전환'}
              >
                {theme === 'light' ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                  </svg>
                )}
              </button>

              {/* 사용자 정보 */}
              {user && (
                <div className="flex items-center space-x-3 ml-2">
                  <div className="flex items-center space-x-2 bg-gray-100 dark:bg-gray-700 rounded-xl px-3 py-2">
                    <div className="avatar-sm text-sm">
                      {user.name?.charAt(0).toUpperCase() || user.username.charAt(0).toUpperCase()}
                    </div>
                    <div className="hidden sm:block">
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-200 block">
                        {user.name || user.username}
                      </span>
                      {getRoleBadge()}
                    </div>
                  </div>
                  {onLogout && (
                    <button
                      onClick={onLogout}
                      className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-all duration-200"
                      aria-label="로그아웃"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                      </svg>
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* 메인 콘텐츠 */}
      <main id="main-content" className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        {children}
      </main>

      {/* 모바일 하단 네비게이션 */}
      <nav aria-label="모바일 메뉴" className="sm:hidden fixed bottom-0 left-0 right-0 bg-white dark:bg-gray-800 border-t dark:border-gray-700 shadow-lg">
        <div className="flex justify-around py-2">
          <Link
            to="/"
            className={`flex flex-col items-center px-4 py-2 ${
              location.pathname === '/' ? 'text-blue-600 dark:text-blue-400' : 'text-gray-500 dark:text-gray-400'
            }`}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            </svg>
            <span className="text-xs mt-1">홈</span>
          </Link>
          {/* 다크 모드 토글 (모바일) */}
          <button
            onClick={toggleTheme}
            aria-label={theme === 'light' ? '다크 모드로 전환' : '라이트 모드로 전환'}
            className="flex flex-col items-center px-4 py-2 text-gray-500 dark:text-gray-400"
          >
            {theme === 'light' ? (
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
              </svg>
            ) : (
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
            )}
            <span className="text-xs mt-1">{theme === 'light' ? '다크' : '라이트'}</span>
          </button>
          {(isApprovedTherapist || isAdmin) && (
            <button
              onClick={() => {
                const query = prompt('환자 이름 또는 번호 검색:');
                if (query) {
                  patientApi.search(query).then(results => {
                    if (results.length > 0) {
                      navigate(`/patients/${results[0].id}/history`);
                    } else {
                      alert('검색 결과가 없습니다.');
                    }
                  });
                }
              }}
              className="flex flex-col items-center px-4 py-2 text-gray-500 dark:text-gray-400"
              aria-label="환자 검색"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <span className="text-xs mt-1">환자검색</span>
            </button>
          )}
          {isApprovedTherapist && (
            <Link
              to="/patients/new"
              className={`flex flex-col items-center px-4 py-2 ${
                location.pathname === '/patients/new' ? 'text-blue-600 dark:text-blue-400' : 'text-gray-500 dark:text-gray-400'
              }`}
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
              </svg>
              <span className="text-xs mt-1">환자등록</span>
            </Link>
          )}
          {isAdmin && (
            <>
              <Link
                to="/admin/therapists"
                className={`flex flex-col items-center px-4 py-2 ${
                  location.pathname === '/admin/therapists' ? 'text-purple-600 dark:text-purple-400' : 'text-gray-500 dark:text-gray-400'
                }`}
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
                <span className="text-xs mt-1">치료사관리</span>
              </Link>
              <Link
                to="/admin/dashboard"
                className={`flex flex-col items-center px-4 py-2 ${
                  location.pathname === '/admin/dashboard' ? 'text-purple-600 dark:text-purple-400' : 'text-gray-500 dark:text-gray-400'
                }`}
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                <span className="text-xs mt-1">통계</span>
              </Link>
            </>
          )}
        </div>
      </nav>

      {/* 푸터 (모바일에서는 숨김) */}
      <footer className="hidden sm:block bg-white dark:bg-gray-800 border-t dark:border-gray-700 mt-8">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-gray-500 dark:text-gray-400">
            다시 걷는 그날까지 ReStep이 함께합니다
          </p>
        </div>
      </footer>
    </div>
  );
}
