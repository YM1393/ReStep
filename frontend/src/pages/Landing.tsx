import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

export default function Landing() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollTo = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      window.scrollTo({ top: el.offsetTop - 80, behavior: 'smooth' });
    }
  };

  return (
    <div className="min-h-screen bg-white text-gray-800 overflow-x-hidden" style={{ fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans KR', sans-serif" }}>
      {/* Navigation */}
      <nav aria-label="메인 네비게이션" className={`fixed top-0 w-full z-50 transition-all duration-300 ${scrolled ? 'shadow-lg' : 'shadow-sm'}`}
        style={{ background: 'rgba(255,255,255,0.95)', backdropFilter: 'blur(10px)' }}>
        <div className="max-w-[1200px] mx-auto px-8 py-4 flex justify-between items-center">
          <div className="flex items-center gap-2 text-2xl font-bold text-[#0066CC]">
            <div className="w-9 h-9 rounded-lg flex items-center justify-center text-white text-sm font-bold"
              style={{ background: 'linear-gradient(135deg, #0066CC, #06B6D4)' }}>10M</div>
            보행검사 시스템
          </div>
          <ul className="hidden md:flex gap-8 items-center list-none">
            <li><button onClick={() => scrollTo('features')} className="font-medium hover:text-[#0066CC] focus:text-[#0066CC] focus:outline-none focus:ring-2 focus:ring-[#0066CC] focus:ring-offset-2 rounded transition-colors">기능</button></li>
            <li><button onClick={() => scrollTo('technology')} className="font-medium hover:text-[#0066CC] focus:text-[#0066CC] focus:outline-none focus:ring-2 focus:ring-[#0066CC] focus:ring-offset-2 rounded transition-colors">기술</button></li>
            <li><button onClick={() => scrollTo('tests')} className="font-medium hover:text-[#0066CC] focus:text-[#0066CC] focus:outline-none focus:ring-2 focus:ring-[#0066CC] focus:ring-offset-2 rounded transition-colors">검사항목</button></li>
            <li><button onClick={() => scrollTo('benefits')} className="font-medium hover:text-[#0066CC] focus:text-[#0066CC] focus:outline-none focus:ring-2 focus:ring-[#0066CC] focus:ring-offset-2 rounded transition-colors">장점</button></li>
            <li>
              <Link to="/login" className="px-6 py-2.5 rounded-lg font-semibold text-white transition-all hover:-translate-y-0.5"
                style={{ background: '#0066CC' }}>로그인</Link>
            </li>
          </ul>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-24 px-8 relative overflow-hidden"
        style={{ background: 'linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%)' }}>
        <div className="absolute -top-1/2 -right-[10%] w-[600px] h-[600px] rounded-full"
          style={{ background: 'radial-gradient(circle, rgba(6,182,212,0.1) 0%, transparent 70%)' }} />
        <div className="max-w-[1200px] mx-auto grid grid-cols-1 lg:grid-cols-2 gap-16 items-center relative">
          <div>
            <h1 className="text-4xl lg:text-5xl font-extrabold leading-tight mb-6 text-gray-900">
              AI로 혁신하는<br />
              <span className="text-[#0066CC]">임상 보행 분석</span>
            </h1>
            <p className="text-xl text-gray-600 mb-8 leading-relaxed">
              MediaPipe AI 기술로 10MWT, TUG, BBS 검사를 자동 분석합니다.
              영상 업로드 한 번으로 정확한 보행 분석 리포트를 즉시 받아보세요.
            </p>
            <div className="flex gap-4 flex-wrap">
              <Link to="/register" className="px-6 py-3 rounded-lg font-semibold text-white transition-all hover:-translate-y-0.5 hover:shadow-lg"
                style={{ background: '#0066CC' }}>
                무료 체험 시작
              </Link>
              <button onClick={() => scrollTo('technology')}
                className="px-6 py-3 rounded-lg font-semibold text-[#0066CC] border-2 border-[#0066CC] bg-white transition-all hover:bg-[#0066CC] hover:text-white">
                기술 알아보기
              </button>
            </div>
          </div>
          <div className="flex justify-center items-center">
            <div className="w-full max-w-[500px] bg-white rounded-2xl p-6 relative animate-[float_3s_ease-in-out_infinite]"
              style={{ boxShadow: '0 20px 60px rgba(0,0,0,0.15)' }}>
              <div className="flex gap-2 mb-4">
                <div className="w-3 h-3 rounded-full bg-red-500" />
                <div className="w-3 h-3 rounded-full bg-yellow-500" />
                <div className="w-3 h-3 rounded-full bg-green-500" />
              </div>
              <div className="bg-gray-50 rounded-xl p-6 space-y-4">
                <div className="flex gap-3">
                  <div className="flex-1 bg-white p-4 rounded-lg">
                    <div className="text-gray-600 text-sm">보행 속도</div>
                    <div className="text-[#0066CC] text-2xl font-bold">1.18 m/s</div>
                  </div>
                  <div className="flex-1 bg-white p-4 rounded-lg">
                    <div className="text-gray-600 text-sm">낙상 위험</div>
                    <div className="text-green-700 text-2xl font-bold">정상</div>
                  </div>
                </div>
                <div className="bg-white p-4 rounded-lg">
                  <div className="text-gray-600 text-sm mb-2">AI 분석 진행률</div>
                  <div className="bg-gray-200 h-2 rounded-full overflow-hidden">
                    <div className="h-full w-3/4 rounded-full" style={{ background: 'linear-gradient(90deg, #0066CC, #06B6D4)' }} />
                  </div>
                </div>
                <div className="bg-white p-4 rounded-lg">
                  <div className="text-gray-600 text-sm mb-2">검사 유형</div>
                  <div className="flex gap-2">
                    <span className="bg-[#0066CC] text-white px-3 py-1 rounded-full text-xs font-medium">10MWT</span>
                    <span className="bg-cyan-700 text-white px-3 py-1 rounded-full text-xs font-medium">TUG</span>
                    <span className="bg-green-700 text-white px-3 py-1 rounded-full text-xs font-medium">BBS</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-12 px-8 text-white" style={{ background: '#0066CC' }}>
        <div className="max-w-[1200px] mx-auto grid grid-cols-2 lg:grid-cols-4 gap-8 text-center">
          {[
            { value: '33개', label: 'AI 랜드마크 감지' },
            { value: '3가지', label: '표준 임상 검사' },
            { value: '90%', label: '시간 절약' },
            { value: '100%', label: '객관적 데이터' },
          ].map((stat) => (
            <div key={stat.label}>
              <h3 className="text-4xl font-extrabold mb-2">{stat.value}</h3>
              <p className="opacity-90">{stat.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-24 px-8 bg-white">
        <div className="text-center max-w-[700px] mx-auto mb-16">
          <h2 className="text-4xl font-extrabold mb-4 text-gray-900">핵심 기능</h2>
          <p className="text-lg text-gray-600">물리치료 임상 현장에 최적화된 강력한 기능들</p>
        </div>
        <div className="max-w-[1200px] mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {[
            { icon: '🎯', title: '자동 영상 분석', desc: 'MediaPipe AI가 33개 인체 랜드마크를 실시간 감지하여 보행 패턴을 정밀 분석합니다.' },
            { icon: '⚡', title: '즉시 결과 제공', desc: '영상 업로드 후 30-120초 내에 상세한 분석 리포트를 자동 생성합니다.' },
            { icon: '📊', title: '낙상 위험 평가', desc: '속도와 시간 기반 0-100점 종합 위험도 평가로 객관적인 판단을 지원합니다.' },
            { icon: '📈', title: '추이 분석', desc: '환자의 보행 능력 변화를 시각적 차트로 추적하여 치료 효과를 확인합니다.' },
            { icon: '📄', title: 'PDF/CSV 리포트', desc: '전문적인 임상 리포트를 PDF 및 CSV 형식으로 다운로드하여 기록 관리가 용이합니다.' },
            { icon: '👥', title: '다중 사용자 관리', desc: '관리자와 치료사 역할 기반 접근 제어로 안전한 협업 환경을 제공합니다.' },
          ].map((f) => (
            <div key={f.title} className="bg-white border-2 border-gray-100 rounded-2xl p-8 transition-all hover:border-[#0066CC] hover:-translate-y-1 hover:shadow-lg">
              <div className="w-16 h-16 rounded-xl flex items-center justify-center text-3xl mb-6"
                style={{ background: 'linear-gradient(135deg, #0066CC, #06B6D4)' }}
                role="img" aria-hidden="true">
                {f.icon}
              </div>
              <h3 className="text-xl font-bold mb-3 text-gray-900">{f.title}</h3>
              <p className="text-gray-600 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Technology Section */}
      <section id="technology" className="py-24 px-8 bg-gray-50">
        <div className="text-center max-w-[700px] mx-auto mb-16">
          <h2 className="text-4xl font-extrabold mb-4 text-gray-900">첨단 AI 기술</h2>
          <p className="text-lg text-gray-600">Google MediaPipe 기반의 정확하고 빠른 자세 추정</p>
        </div>
        <div className="max-w-[1200px] mx-auto grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          <div>
            <h3 className="text-3xl font-bold mb-4">MediaPipe Pose 엔진</h3>
            <p className="text-gray-600 mb-6 leading-relaxed">
              세계적으로 검증된 Google의 MediaPipe 기술을 활용하여
              실시간으로 인체 자세를 정밀하게 분석합니다.
            </p>
            <ul className="space-y-3">
              {[
                { bold: '33개 랜드마크 감지:', text: '얼굴, 상체, 하체 전신 분석' },
                { bold: '3D 좌표 지원:', text: '입체적인 움직임 파악' },
                { bold: '높은 정확도:', text: '임상 표준에 부합하는 신뢰성' },
                { bold: '실시간 처리:', text: '빠른 분석 속도' },
                { bold: '색상 코딩:', text: '좌측(파란색)/우측(주황색) 구분 표시' },
              ].map((item) => (
                <li key={item.bold} className="flex items-start gap-2">
                  <span className="text-green-700 font-bold text-lg mt-0.5">&#10003;</span>
                  <span><strong>{item.bold}</strong> {item.text}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="bg-white rounded-2xl p-8 shadow-lg">
            <div className="space-y-4">
              {[
                { num: '1', title: '영상 업로드', desc: '환자 보행 영상을 드래그 앤 드롭' },
                { num: '2', title: 'AI 자세 추정', desc: 'MediaPipe가 33개 포인트 감지' },
                { num: '3', title: '패턴 분석', desc: '보행 속도, 기울기, 균형 분석' },
                { num: '4', title: '리포트 생성', desc: '상세 분석 결과 및 위험도 평가' },
              ].map((step) => (
                <div key={step.num} className="flex items-center gap-4 p-4 bg-gray-50 rounded-xl border-l-4 border-[#0066CC]">
                  <div className="w-10 h-10 bg-[#0066CC] text-white rounded-full flex items-center justify-center font-bold shrink-0">
                    {step.num}
                  </div>
                  <div>
                    <div className="font-semibold">{step.title}</div>
                    <div className="text-sm text-gray-600">{step.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Clinical Tests Section */}
      <section id="tests" className="py-24 px-8 bg-white">
        <div className="text-center max-w-[700px] mx-auto mb-16">
          <h2 className="text-4xl font-extrabold mb-4 text-gray-900">3가지 표준 임상 검사</h2>
          <p className="text-lg text-gray-600">국제적으로 검증된 보행 및 균형 평가 도구</p>
        </div>
        <div className="max-w-[1200px] mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {[
            {
              badge: '10MWT', title: '10m 보행검사', subtitle: '10 Meter Walk Test',
              desc: '10미터 거리 보행 속도와 시간을 측정하여 기능적 이동성을 평가합니다.',
              metrics: [
                { label: '정상 기준', value: '≤ 8.3초' },
                { label: '위험 기준', value: '> 12.5초' },
                { label: '분석 항목', value: '어깨/골반 기울기' },
              ]
            },
            {
              badge: 'TUG', title: '일어나 걷기 검사', subtitle: 'Timed Up and Go',
              desc: '의자에서 일어나 3m 걷고 돌아와 앉는 동작의 소요 시간을 측정합니다.',
              metrics: [
                { label: '정상 시간', value: '< 10초' },
                { label: '위험 기준', value: '>= 30초' },
                { label: '분석 단계', value: '5단계 자동 감지' },
              ]
            },
            {
              badge: 'BBS', title: '버그 균형척도', subtitle: 'Berg Balance Scale',
              desc: '14개 항목으로 정적/동적 균형 능력을 종합 평가합니다.',
              metrics: [
                { label: '총점', value: '56점 만점' },
                { label: '독립 기준', value: '41-56점' },
                { label: '평가 항목', value: '14개 균형 동작' },
              ]
            },
          ].map((test) => (
            <div key={test.badge}
              className="bg-gradient-to-br from-gray-50 to-white border-2 border-gray-200 rounded-2xl p-8 relative overflow-hidden transition-all hover:-translate-y-1 hover:shadow-xl">
              <div className="absolute top-0 left-0 w-full h-1" style={{ background: 'linear-gradient(90deg, #0066CC, #06B6D4)' }} />
              <span className="inline-block bg-[#0066CC] text-white px-4 py-1.5 rounded-full text-sm font-semibold mb-4">{test.badge}</span>
              <h3 className="text-2xl font-bold mb-1 text-gray-900">{test.title}</h3>
              <p className="text-gray-600 text-sm mb-4">{test.subtitle}</p>
              <p className="text-gray-600 leading-relaxed mb-6">{test.desc}</p>
              <div className="space-y-3">
                {test.metrics.map((m) => (
                  <div key={m.label} className="flex justify-between p-3 bg-white rounded-lg text-sm">
                    <span className="text-gray-600">{m.label}</span>
                    <span className="font-semibold text-[#0066CC]">{m.value}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Benefits Section */}
      <section id="benefits" className="py-24 px-8 text-white"
        style={{ background: 'linear-gradient(135deg, #0066CC 0%, #004C99 100%)' }}>
        <div className="text-center max-w-[700px] mx-auto mb-16">
          <h2 className="text-4xl font-extrabold mb-4">왜 선택해야 하나요?</h2>
          <p className="text-lg opacity-90">임상 현장의 효율성과 정확성을 동시에 향상시킵니다</p>
        </div>
        <div className="max-w-[1200px] mx-auto grid grid-cols-1 lg:grid-cols-2 gap-12">
          {[
            { icon: '⏱️', title: '시간 절약', desc: '수동 측정 대비 90% 시간 단축. 영상 업로드만으로 자동 분석이 완료되어 치료사는 환자 케어에 집중할 수 있습니다.' },
            { icon: '🎯', title: '높은 정확도', desc: 'AI 기반 정밀 측정으로 인간의 눈으로 놓치기 쉬운 미세한 보행 패턴까지 객관적으로 분석합니다.' },
            { icon: '📊', title: '데이터 기반 의사결정', desc: '정량적 데이터와 시각적 차트로 환자 상태를 명확히 파악하고 치료 계획을 수립할 수 있습니다.' },
            { icon: '💰', title: '비용 효율성', desc: '고가의 센서 장비 없이 일반 카메라로 촬영한 영상만으로 전문적인 보행 분석이 가능합니다.' },
          ].map((b) => (
            <div key={b.title} className="flex gap-6">
              <div className="w-[60px] h-[60px] rounded-xl flex items-center justify-center text-3xl shrink-0"
                style={{ background: 'rgba(255,255,255,0.2)' }}
                role="img" aria-hidden="true">
                {b.icon}
              </div>
              <div>
                <h3 className="text-xl font-bold mb-3">{b.title}</h3>
                <p className="opacity-90 leading-relaxed">{b.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Use Cases Section */}
      <section className="py-24 px-8 bg-white">
        <div className="text-center max-w-[700px] mx-auto mb-16">
          <h2 className="text-4xl font-extrabold mb-4 text-gray-900">활용 분야</h2>
          <p className="text-lg text-gray-600">다양한 임상 환경에서 검증된 솔루션</p>
        </div>
        <div className="max-w-[1200px] mx-auto grid grid-cols-1 lg:grid-cols-2 gap-8">
          {[
            { icon: '🏥', title: '물리치료 클리닉', items: ['근골격계 재활 환자 보행 평가', '낙상 위험 환자 스크리닝', '치료 전후 비교 분석', '운동 프로그램 효과 측정'] },
            { icon: '🏨', title: '요양병원 / 요양원', items: ['노인 낙상 위험 정기 평가', '기능적 이동성 모니터링', '보행 보조기구 필요성 판단', '재활 프로그램 개별화'] },
            { icon: '🏋️', title: '스포츠 재활센터', items: ['선수 부상 후 복귀 평가', '보행 패턴 비대칭 분석', '재활 진행도 객관적 추적', '경기 복귀 준비도 판단'] },
            { icon: '🧪', title: '임상 연구', items: ['보행 관련 연구 데이터 수집', '치료법 효과 정량적 비교', '대규모 코호트 연구 지원', '표준화된 평가 프로토콜'] },
          ].map((uc) => (
            <div key={uc.title} className="bg-gray-50 rounded-2xl p-8 border-l-[6px] border-[#0066CC]">
              <h3 className="text-xl font-bold mb-4 text-gray-900">{uc.icon} {uc.title}</h3>
              <ul className="space-y-3">
                {uc.items.map((item) => (
                  <li key={item} className="relative pl-6 text-gray-700">
                    <span className="absolute left-0 text-[#0066CC] font-bold">&rarr;</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 px-8 text-center"
        style={{ background: 'linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%)' }}>
        <div className="max-w-[800px] mx-auto">
          <h2 className="text-4xl font-extrabold mb-6 text-gray-900">지금 바로 시작하세요</h2>
          <p className="text-xl text-gray-600 mb-10">
            무료 체험으로 AI 보행 분석의 강력함을 경험해보세요.<br />
            신용카드 등록 없이 즉시 사용 가능합니다.
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <Link to="/register"
              className="px-8 py-4 rounded-lg font-semibold text-lg text-white transition-all hover:-translate-y-0.5 hover:shadow-lg"
              style={{ background: '#0066CC' }}>
              무료 체험 시작하기
            </Link>
            <Link to="/login"
              className="px-8 py-4 rounded-lg font-semibold text-lg text-[#0066CC] border-2 border-[#0066CC] bg-white transition-all hover:bg-[#0066CC] hover:text-white">
              로그인하기
            </Link>
          </div>
          <p className="mt-6 text-gray-600">
            &#10003; 30일 무료 체험 &nbsp;&nbsp; &#10003; 신용카드 불필요 &nbsp;&nbsp; &#10003; 언제든 해지 가능
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white pt-12 pb-6 px-8">
        <div className="max-w-[1200px] mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-12 mb-8">
            <div>
              <h3 className="text-xl font-bold mb-4">10m 보행검사 시스템</h3>
              <p className="opacity-80 leading-relaxed">
                AI 기반 임상 보행 분석 플랫폼으로
                물리치료사와 환자 모두를 위한
                혁신적인 솔루션을 제공합니다.
              </p>
            </div>
            <div>
              <h4 className="text-lg font-semibold mb-4">제품</h4>
              <ul className="space-y-2">
                {['기능', '기술', '검사 항목', '가격'].map((item) => (
                  <li key={item}><button className="text-white/70 hover:text-white focus:text-white focus:outline-none focus:ring-2 focus:ring-white/50 rounded transition-colors">{item}</button></li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="text-lg font-semibold mb-4">지원</h4>
              <ul className="space-y-2">
                {['문서', 'FAQ', '문의하기', '기술 지원'].map((item) => (
                  <li key={item}><button className="text-white/70 hover:text-white focus:text-white focus:outline-none focus:ring-2 focus:ring-white/50 rounded transition-colors">{item}</button></li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="text-lg font-semibold mb-4">회사</h4>
              <ul className="space-y-2">
                {['소개', '블로그', '개인정보처리방침', '이용약관'].map((item) => (
                  <li key={item}><button className="text-white/70 hover:text-white focus:text-white focus:outline-none focus:ring-2 focus:ring-white/50 rounded transition-colors">{item}</button></li>
                ))}
              </ul>
            </div>
          </div>
          <div className="border-t border-white/10 pt-6 text-center opacity-70">
            <p>&copy; 2026 10m 보행검사 시스템. All rights reserved.</p>
          </div>
        </div>
      </footer>

      {/* Float animation keyframes */}
      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-20px); }
        }
        @media (prefers-reduced-motion: reduce) {
          * {
            animation: none !important;
            transition-duration: 0.01ms !important;
          }
        }
      `}</style>
    </div>
  );
}
