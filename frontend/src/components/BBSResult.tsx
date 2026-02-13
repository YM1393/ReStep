import type { BBSAnalysisData, BBSItemScores } from '../types';

interface BBSResultProps {
  data: BBSAnalysisData;
}

// BBS 항목 레이블
const BBS_ITEM_LABELS: Record<keyof BBSItemScores, string> = {
  item1_sitting_to_standing: '앉은 자세에서 일어나기',
  item2_standing_unsupported: '지지없이 서있기',
  item3_sitting_unsupported: '의자의 등받이에 기대지 않고 바른 자세로 앉기',
  item4_standing_to_sitting: '선 자세에서 앉기',
  item5_transfers: '이동하기',
  item6_standing_eyes_closed: '두 눈을 감고 지지없이 서있기',
  item7_standing_feet_together: '두 발을 붙이고 지지없이 서있기',
  item8_reaching_forward: '선 자세에서 앞으로 팔 뻗기',
  item9_pick_up_object: '선 자세에서 바닥의 물건 집어올리기',
  item10_turning_to_look_behind: '선 자세에서 좌우로 뒤돌아보기',
  item11_turn_360_degrees: '제자리에서 360도 회전',
  item12_stool_stepping: '일정한 높이의 발판 위에 발 교대로 놓기',
  item13_standing_one_foot_front: '일렬로 서기 (Tandem)',
  item14_standing_on_one_leg: '한 발로 서기'
};

const assessmentColors = {
  wheelchair_bound: {
    bg: 'bg-red-100 dark:bg-red-900/30',
    text: 'text-red-700 dark:text-red-300',
    border: 'border-red-200 dark:border-red-800'
  },
  walking_with_assistance: {
    bg: 'bg-yellow-100 dark:bg-yellow-900/30',
    text: 'text-yellow-700 dark:text-yellow-300',
    border: 'border-yellow-200 dark:border-yellow-800'
  },
  independent: {
    bg: 'bg-green-100 dark:bg-green-900/30',
    text: 'text-green-700 dark:text-green-300',
    border: 'border-green-200 dark:border-green-800'
  }
};

export default function BBSResult({ data }: BBSResultProps) {
  const colors = assessmentColors[data.assessment];
  const scores = data.scores as BBSItemScores;

  // 점수별 색상
  const getScoreColor = (score: number) => {
    if (score === 4) return 'bg-green-500';
    if (score === 3) return 'bg-blue-500';
    if (score === 2) return 'bg-yellow-500';
    if (score === 1) return 'bg-orange-500';
    return 'bg-red-500';
  };

  return (
    <div className={`card border-2 ${colors.border} ${colors.bg}`}>
      <h3 className="font-semibold text-gray-800 dark:text-gray-100 mb-4 flex items-center">
        <svg className="w-5 h-5 mr-2 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        BBS (Berg Balance Scale) 검사 결과
      </h3>

      {/* 총점 및 평가 */}
      <div className="flex items-center justify-between mb-6">
        <div className="text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">총점</p>
          <p className="text-4xl font-bold text-gray-800 dark:text-gray-100">
            {data.total_score}
            <span className="text-lg text-gray-500 dark:text-gray-400 ml-1">/56</span>
          </p>
        </div>
        <div className={`px-6 py-3 rounded-xl ${colors.bg} ${colors.border} border`}>
          <p className={`text-2xl font-bold ${colors.text}`}>
            {data.assessment_label}
          </p>
        </div>
      </div>

      {/* 평가 기준 안내 */}
      <div className="mb-6 p-3 bg-gray-50 dark:bg-gray-800 rounded-xl">
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-2 font-medium">BBS 평가 기준</p>
        <div className="flex items-center justify-between text-xs">
          <span className="text-red-600 dark:text-red-400">0-20: 휠체어 의존</span>
          <span className="text-yellow-600 dark:text-yellow-400">21-40: 보조 보행</span>
          <span className="text-green-600 dark:text-green-400">41-56: 독립적</span>
        </div>
      </div>

      {/* 점수 분포 바 */}
      <div className="mb-6">
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">점수 분포</p>
        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all ${
              data.total_score <= 20 ? 'bg-red-500' :
              data.total_score <= 40 ? 'bg-yellow-500' : 'bg-green-500'
            }`}
            style={{ width: `${(data.total_score / 56) * 100}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>0</span>
          <span>20</span>
          <span>40</span>
          <span>56</span>
        </div>
      </div>

      {/* 항목별 점수 */}
      <div className="mb-4">
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">항목별 점수</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {Object.entries(scores).map(([key, score], index) => (
            <div
              key={key}
              className="flex items-center justify-between p-2 bg-white dark:bg-gray-700 rounded-lg"
            >
              <div className="flex items-center flex-1 min-w-0">
                <span className="text-xs text-gray-500 mr-2 w-5">{index + 1}.</span>
                <span className="text-xs text-gray-700 dark:text-gray-300 truncate">
                  {BBS_ITEM_LABELS[key as keyof BBSItemScores]}
                </span>
              </div>
              <div className="flex items-center ml-2">
                <div className={`w-6 h-6 rounded-full ${getScoreColor(score)} flex items-center justify-center`}>
                  <span className="text-white text-xs font-bold">{score}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 점수 범례 */}
      <div className="flex flex-wrap gap-2 justify-center text-xs">
        <div className="flex items-center">
          <div className="w-3 h-3 rounded-full bg-green-500 mr-1"></div>
          <span className="text-gray-600 dark:text-gray-400">4점</span>
        </div>
        <div className="flex items-center">
          <div className="w-3 h-3 rounded-full bg-blue-500 mr-1"></div>
          <span className="text-gray-600 dark:text-gray-400">3점</span>
        </div>
        <div className="flex items-center">
          <div className="w-3 h-3 rounded-full bg-yellow-500 mr-1"></div>
          <span className="text-gray-600 dark:text-gray-400">2점</span>
        </div>
        <div className="flex items-center">
          <div className="w-3 h-3 rounded-full bg-orange-500 mr-1"></div>
          <span className="text-gray-600 dark:text-gray-400">1점</span>
        </div>
        <div className="flex items-center">
          <div className="w-3 h-3 rounded-full bg-red-500 mr-1"></div>
          <span className="text-gray-600 dark:text-gray-400">0점</span>
        </div>
      </div>

      {/* 메모 (있는 경우) */}
      {data.notes && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-600">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">메모</p>
          <p className="text-sm text-gray-600 dark:text-gray-400 whitespace-pre-wrap">{data.notes}</p>
        </div>
      )}
    </div>
  );
}
