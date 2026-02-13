interface UploadProgressProps {
  uploadProgress: number;
  analysisProgress: number;
  status: 'idle' | 'uploading' | 'analyzing' | 'completed' | 'error';
  message: string;
}

export default function UploadProgress({
  uploadProgress,
  analysisProgress,
  status,
  message,
}: UploadProgressProps) {
  const getStatusColor = () => {
    switch (status) {
      case 'completed':
        return 'bg-green-500';
      case 'error':
        return 'bg-red-500';
      case 'uploading':
      case 'analyzing':
        return 'bg-blue-500';
      default:
        return 'bg-gray-300';
    }
  };

  const totalProgress = status === 'uploading' ? uploadProgress : analysisProgress;

  return (
    <div className="card border-2 border-blue-100">
      {/* 상단 상태 */}
      <div className="flex items-center space-x-4 mb-6">
        <div className={`w-14 h-14 rounded-2xl flex items-center justify-center ${
          status === 'completed' ? 'bg-green-100' :
          status === 'error' ? 'bg-red-100' : 'bg-blue-100'
        }`}>
          {status === 'completed' ? (
            <svg className="w-7 h-7 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          ) : status === 'error' ? (
            <svg className="w-7 h-7 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          ) : (
            <svg className="w-7 h-7 text-blue-500 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          )}
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-gray-800 dark:text-gray-100" aria-live="polite">
            {status === 'uploading' && '동영상 업로드 중...'}
            {status === 'analyzing' && 'MediaPipe로 분석 중...'}
            {status === 'completed' && '분석 완료!'}
            {status === 'error' && '분석 실패'}
            {status === 'idle' && '대기 중'}
          </h3>
          <p className="text-sm text-gray-500" aria-live="polite">{message}</p>
        </div>
        <div className="text-right">
          <span className="text-3xl font-bold text-blue-600">{totalProgress}</span>
          <span className="text-lg text-gray-400">%</span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden mb-6">
        <div
          className={`h-full rounded-full transition-all duration-500 ${getStatusColor()}`}
          style={{ width: `${totalProgress}%` }}
          role="progressbar"
          aria-valuenow={totalProgress}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="분석 진행률"
        />
      </div>

      {/* 단계 표시 */}
      <div className="flex justify-between">
        <div className="flex flex-col items-center">
          <div className={`w-10 h-10 rounded-full flex items-center justify-center mb-2 ${
            uploadProgress >= 100 ? 'bg-green-500 text-white' :
            uploadProgress > 0 ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-400'
          }`}>
            {uploadProgress >= 100 ? (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <span className="text-sm font-bold">1</span>
            )}
          </div>
          <span className={`text-xs font-medium ${uploadProgress > 0 ? 'text-blue-600' : 'text-gray-400'}`}>
            업로드
          </span>
        </div>

        <div className="flex-1 flex items-center px-4 mt-[-20px]">
          <div className={`h-0.5 w-full ${uploadProgress >= 100 ? 'bg-green-500' : 'bg-gray-200'}`}></div>
        </div>

        <div className="flex flex-col items-center">
          <div className={`w-10 h-10 rounded-full flex items-center justify-center mb-2 ${
            status === 'completed' ? 'bg-green-500 text-white' :
            status === 'analyzing' ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-400'
          }`}>
            {status === 'completed' ? (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <span className="text-sm font-bold">2</span>
            )}
          </div>
          <span className={`text-xs font-medium ${status === 'analyzing' || status === 'completed' ? 'text-blue-600' : 'text-gray-400'}`}>
            분석
          </span>
        </div>

        <div className="flex-1 flex items-center px-4 mt-[-20px]">
          <div className={`h-0.5 w-full ${status === 'completed' ? 'bg-green-500' : 'bg-gray-200'}`}></div>
        </div>

        <div className="flex flex-col items-center">
          <div className={`w-10 h-10 rounded-full flex items-center justify-center mb-2 ${
            status === 'completed' ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-400'
          }`}>
            {status === 'completed' ? (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <span className="text-sm font-bold">3</span>
            )}
          </div>
          <span className={`text-xs font-medium ${status === 'completed' ? 'text-green-600' : 'text-gray-400'}`}>
            완료
          </span>
        </div>
      </div>
    </div>
  );
}
