import { useState, useEffect } from 'react';
import type { BBSItemScores } from '../types';

// AI 추천 점수 타입
export interface AIScoreItem {
  score: number;
  confidence: number;
  message: string;
  details: Record<string, any>;
}

export type AIScores = Partial<Record<keyof BBSItemScores, AIScoreItem>>;

interface BBSFormProps {
  onSubmit: (scores: BBSItemScores, notes?: string) => void;
  isLoading?: boolean;
  aiScores?: AIScores;  // AI 추천 점수
}

// BBS 14개 항목 정보 (Berg Balance Scale 원본 기준)
const BBS_ITEMS = [
  {
    id: 'item1_sitting_to_standing',
    label: '1. 앉은 자세에서 일어나기',
    criteria: [
      '일어서기 위해 중간 정도 또는 최대한의 도움이 필요하다',
      '일어서기 위해 도움을 필요로 하고 안정성을 유지하기 위해서는 최소한의 도움이 필요하다',
      '일어서기를 여러 번 시도하고 난 후 손을 사용하여 일어설 수 있다',
      '손을 사용하여 스스로 일어설 수 있다',
      '손을 사용하지 않고 일어서서 안정된 자세를 유지할수 있다'
    ]
  },
  {
    id: 'item2_standing_unsupported',
    label: '2. 잡지 않고 서 있기',
    criteria: [
      '도움없이는 30초 동안 서 있을 수 없다',
      '잡지 않고 30초 동안 서 있기 위해서는 여러번의 시도가 필요하다',
      '잡지 않고 30초 동안 서있을 수 있다',
      '감독하에 지지받으며 2분동안 서 있을 수 있다',
      '안전하게 2분동안 서 있을 수 있다'
    ]
  },
  {
    id: 'item3_sitting_unsupported',
    label: '3. 의자의 등받이에 기대지 않고 바른 자세로 앉기',
    criteria: [
      '도움없이는 10초 동안 앉아 있을 수 없다',
      '10초 동안 앉아 있을 수 있다',
      '30초 동안 앉아 있을 수 있다',
      '등에서 지지받으며 주면 2분 동안 앉을 수 있다',
      '2분 동안 안전하고 확실하게 앉을 수 있다'
    ]
  },
  {
    id: 'item4_standing_to_sitting',
    label: '4. 선자세에서 앉기',
    criteria: [
      '앉을때 도움이 필요하다',
      '앉을때 잡지는 하지만 뒷부분 속도 조절을 않는다',
      '앉을 때 다리 뒤쪽으로 의자에 닿게 하여 천천히 앉는다',
      '의자가 반듬으로 앉을때 손으로 잡고 확실하게 하며 내려 앉는다',
      '손을 거의 사용하지 않으면서 안전하게 앉을 수 있다'
    ]
  },
  {
    id: 'item5_transfers',
    label: '5. 의자에서 의자로 이동하기',
    criteria: [
      '의자에서 이동하기 위해서는 두 사람의 도움이나 지지받이 주어야 할 수 있다',
      '한 사람의 도움이 필요하거나 지지받이 있어야 한다',
      '말로 지시하거나 감독하면 안전 할 수 있다',
      '완전히 손을 사용하면서 안전하게 옮겨 앉을 수 있다',
      '손을 거의 사용하지 않고도 조금 사용하여 안전하게 옮겨 앉을 수 있다'
    ]
  },
  {
    id: 'item6_standing_eyes_closed',
    label: '6. 두눈을 감고 잡지 않고 서 있기',
    criteria: [
      '넘어지는 것을 방지하기 위하여 도움이 필요하다',
      '안전하게으로 서 있으나 두 눈을 감고 3초 동안 유지할수는 없다',
      '3초동안 서 있을 수 있다',
      '감독하에 지지받으며 주면 10초동안 서 있을 수 있다',
      '10초동안 안전하게 서 있을 수 있다'
    ]
  },
  {
    id: 'item7_standing_feet_together',
    label: '7. 두발을 붙이고 잡지 않고 서 있기',
    criteria: [
      '두발을 붙이는데 도움이 필요하며 15초 동안 서 있을 수 없다',
      '두발을 붙이는데 도움이 필요하며 도움을 받아 15초동안 서 있을 수 있다',
      '두발을 붙이고 혼자서 지지받으며 30초 동안 유지할 수 있다',
      '두발을 붙이고 독립적으로 1분 동안 안전하게 서 있을 수 있다',
      '혼자서 두발을 붙이고 1분 동안 안전하게 서 있을 수 있다'
    ]
  },
  {
    id: 'item8_reaching_forward',
    label: '8. 선자세에서 앞으로 팔을 뻗쳐 내밀기',
    criteria: [
      '넘어지지 않기 위해 도움이 필요하다',
      '앞으로 뻗을 수 있으나 감독이 필요하다',
      '5cm 이상 안전하게 앞으로 뻗을 수 있다',
      '12.5cm 이상 안전하게 앞으로 뻗을 수 있다',
      '25cm 이상 앞으로 자신 있게 뻗을 수 있다'
    ]
  },
  {
    id: 'item9_pick_up_object',
    label: '9. 바닥에 있는 물건을 집어 올리기',
    criteria: [
      '구부려도 잡을 수 시도하는 동안 넘어지지 않게 하려면 지지받 주는 것이 필요하다',
      '구부려도 시도는 하지만 물건을 지정하게 서 있거나 감독이 필요하다',
      '잡을 수는 없으나 낮아야 지지받으면 2.5-5cm의 거리까지 손이 뻗을 수 있다',
      '안전하고 쉽게 신발을 잡을 수 있다',
      '안전하고 쉽게 신발을 잡을 수 있다'
    ]
  },
  {
    id: 'item10_turning_to_look_behind',
    label: '10. 일어서서 오른쪽으로 뒤 돌아보기',
    criteria: [
      '넘어지지 않도록 하기 위해 도움이 필요하다',
      '회전할 때 지지받 소음 또는 가까이 감독이 필요하다',
      '옆으로만 돌아볼 수 있으나 균형을 유지한다',
      '한쪽으로만 뒤돌아볼 수 있으나 균형 잡으며 체중 이동 할 수 있다',
      '왼쪽과 오른쪽 모두로로 뒤돌아볼때, 체중의 분명한 전환을 잘 할 수 있다'
    ]
  },
  {
    id: 'item11_turn_360_degrees',
    label: '11. 제자리에서 360도 회전하기',
    criteria: [
      '돌때 도움이 필요하다',
      '근접한 감독이나 말로 지시를 해주어야 한다',
      '안전하게 360도 돌 수 있으나 느리다',
      '한 방향으로만 4초 이내에 안전하게 360도 돌 수 있다',
      '각 방향으로 4초 이내에 안전하게 360도 돌 수 있다'
    ]
  },
  {
    id: 'item12_stool_stepping',
    label: '12. 일정한 높이의 발판에 발을 교대로 올려 놓기',
    criteria: [
      '넘어지지 않도록 하기 위해 도움이 필요하거나 과제를 시행할 수 없다',
      '보조자의 도움을 받아 안전하게 2회 이상 발판 위에 발을 올릴 수 있다',
      '보조자가 안전하게 교대로 발판에 4회 이상 발판 위에 발을 올릴 수 있다',
      '혼자서 안전하게 교대로 발판에 8회 올릴때 발판이에는 20초 이내 운동할 수 있다',
      '혼자서 안전하게 서서, 20초 이내에 안전하게 8회 올릴수 있다'
    ]
  },
  {
    id: 'item13_standing_one_foot_front',
    label: '13. 한 발 앞에 다른 발을 일렬로 세고 서있기',
    criteria: [
      '발을 내딛거나 서 있는 동안 균형을 잃는다',
      '걸음 내딛거나 내리는데 도움이 필요하지만 15초 동안 유지할 수 있다',
      '혼자 크게 발을 내디디어 30초 동안 유지할 수 있다',
      '혼자 일렬로 발을 앞에 놓고 30초 동안 유지할 수 있다',
      '혼자서 일렬로 서서 30초 동안 유지할 수 있다'
    ]
  },
  {
    id: 'item14_standing_on_one_leg',
    label: '14. 한다리로 서 있기',
    criteria: [
      '한발을 들려고 시도하며, 3초동안 유지하지는 못하지만 혼자서 서 있을수 있다',
      '혼자서 한발을 들고 3초 동안 또는 그이상 서 있을 수 있다',
      '혼자서 한발을 들고 5-10초 정도 서 있을 수 있다',
      '혼자서 한발을 들고 10초 동안 서 있을 수 있다',
      '혼자서 한발을 들고 서 있을 수 있다'
    ]
  }
];

const initialScores: BBSItemScores = {
  item1_sitting_to_standing: 0,
  item2_standing_unsupported: 0,
  item3_sitting_unsupported: 0,
  item4_standing_to_sitting: 0,
  item5_transfers: 0,
  item6_standing_eyes_closed: 0,
  item7_standing_feet_together: 0,
  item8_reaching_forward: 0,
  item9_pick_up_object: 0,
  item10_turning_to_look_behind: 0,
  item11_turn_360_degrees: 0,
  item12_stool_stepping: 0,
  item13_standing_one_foot_front: 0,
  item14_standing_on_one_leg: 0
};

export default function BBSForm({ onSubmit, isLoading = false, aiScores }: BBSFormProps) {
  const [scores, setScores] = useState<BBSItemScores>(initialScores);
  const [notes, setNotes] = useState('');
  const [expandedItem, setExpandedItem] = useState<string | null>(null);

  // AI 추천 점수가 있으면 자동 적용
  useEffect(() => {
    if (aiScores && Object.keys(aiScores).length > 0) {
      setScores(prev => {
        const newScores = { ...prev };
        for (const [key, value] of Object.entries(aiScores)) {
          if (value && value.score !== null && value.score !== undefined) {
            newScores[key as keyof BBSItemScores] = value.score;
          }
        }
        return newScores;
      });
    }
  }, [aiScores]);

  const totalScore = Object.values(scores).reduce((sum, score) => sum + score, 0);

  // AI 추천 항목 확인
  const hasAIScore = (itemId: string): boolean => {
    return !!aiScores && !!aiScores[itemId as keyof BBSItemScores];
  };

  const getAIScore = (itemId: string): AIScoreItem | undefined => {
    return aiScores?.[itemId as keyof BBSItemScores];
  };

  const getAssessment = (score: number) => {
    if (score <= 20) return { label: '휠체어 의존', color: 'text-red-600', bg: 'bg-red-100' };
    if (score <= 40) return { label: '보조 보행', color: 'text-yellow-600', bg: 'bg-yellow-100' };
    return { label: '독립적', color: 'text-green-600', bg: 'bg-green-100' };
  };

  const assessment = getAssessment(totalScore);

  const handleScoreChange = (itemId: string, value: number) => {
    setScores(prev => ({
      ...prev,
      [itemId]: value
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(scores, notes || undefined);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* 총점 및 평가 결과 */}
      <div className={`card ${assessment.bg} border-2 border-current`}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">현재 총점</p>
            <p className="text-3xl font-bold text-gray-800 dark:text-gray-100">
              {totalScore}<span className="text-lg text-gray-500">/56</span>
            </p>
          </div>
          <div className={`px-4 py-2 rounded-xl ${assessment.bg}`}>
            <p className={`text-lg font-bold ${assessment.color}`}>{assessment.label}</p>
          </div>
        </div>
        <div className="mt-3 text-xs text-gray-500">
          <span className="text-red-600">0-20: 휠체어 의존</span>
          <span className="mx-2">|</span>
          <span className="text-yellow-600">21-40: 보조 보행</span>
          <span className="mx-2">|</span>
          <span className="text-green-600">41-56: 독립적</span>
        </div>
      </div>

      {/* AI 분석 결과 안내 */}
      {aiScores && Object.keys(aiScores).length > 0 && (
        <div className="card bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 border border-purple-200 dark:border-purple-700">
          <div className="flex items-center">
            <div className="w-10 h-10 bg-purple-500 rounded-lg flex items-center justify-center mr-3">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <div>
              <h4 className="font-semibold text-purple-800 dark:text-purple-200">AI 분석 결과 적용됨</h4>
              <p className="text-sm text-purple-600 dark:text-purple-300">
                {Object.keys(aiScores).length}개 항목이 자동 분석되었습니다. 필요시 수정 가능합니다.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 14개 항목 */}
      <div className="space-y-3">
        {BBS_ITEMS.map((item) => {
          const aiScore = getAIScore(item.id);
          const hasAI = hasAIScore(item.id);

          return (
          <div key={item.id} className={`card ${hasAI ? 'ring-2 ring-purple-300 dark:ring-purple-600' : ''}`}>
            <div
              className="flex items-center justify-between cursor-pointer"
              role="button"
              tabIndex={0}
              aria-expanded={expandedItem === item.id}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setExpandedItem(expandedItem === item.id ? null : item.id); } }}
              onClick={() => setExpandedItem(expandedItem === item.id ? null : item.id)}
            >
              <div className="flex-1">
                <div className="flex items-center">
                  <p className="font-medium text-gray-800 dark:text-gray-100">{item.label}</p>
                  {hasAI && (
                    <span className="ml-2 px-2 py-0.5 bg-purple-100 dark:bg-purple-900/40 text-purple-600 dark:text-purple-300 text-xs rounded-full flex items-center">
                      <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                      </svg>
                      AI
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-500">
                  현재 점수: <span className="font-bold text-primary-600">{scores[item.id as keyof BBSItemScores]}점</span>
                  {aiScore && (
                    <span className="ml-2 text-purple-500 text-xs">
                      (AI 신뢰도: {Math.round(aiScore.confidence * 100)}%)
                    </span>
                  )}
                </p>
                {aiScore?.message && (
                  <p className="text-xs text-purple-600 dark:text-purple-400 mt-1">{aiScore.message}</p>
                )}
              </div>
              <div className="flex items-center space-x-2">
                {/* 빠른 점수 선택 버튼 */}
                <div className="flex space-x-1">
                  {[0, 1, 2, 3, 4].map((score) => (
                    <button
                      key={score}
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleScoreChange(item.id, score);
                      }}
                      aria-label={`${item.label.split('.')[0]}번 항목 ${score}점`}
                      aria-pressed={scores[item.id as keyof BBSItemScores] === score}
                      className={`w-8 h-8 rounded-full text-sm font-medium transition-colors ${
                        scores[item.id as keyof BBSItemScores] === score
                          ? 'bg-primary-500 text-white'
                          : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                      }`}
                    >
                      {score}
                    </button>
                  ))}
                </div>
                <svg
                  className={`w-5 h-5 text-gray-400 transition-transform ${expandedItem === item.id ? 'rotate-180' : ''}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </div>

            {/* 채점 기준 상세 */}
            <div
              className={`overflow-hidden transition-all duration-300 ease-in-out ${
                expandedItem === item.id
                  ? 'max-h-[800px] opacity-100 mt-4 pt-4 border-t border-gray-200 dark:border-gray-600'
                  : 'max-h-24 opacity-40 mt-3 pt-3 border-t border-gray-100 dark:border-gray-700'
              }`}
            >
              <p className="text-xs text-gray-500 mb-2 font-medium">채점 기준</p>
              <div className="space-y-2">
                {item.criteria.map((criterion, index) => (
                  <label
                    key={index}
                    className={`flex items-start p-2 rounded-lg cursor-pointer transition-colors ${
                      scores[item.id as keyof BBSItemScores] === index
                        ? 'bg-primary-50 dark:bg-primary-900/30 border border-primary-200 dark:border-primary-800'
                        : 'hover:bg-gray-50 dark:hover:bg-gray-700'
                    }`}
                  >
                    <input
                      type="radio"
                      name={item.id}
                      value={index}
                      checked={scores[item.id as keyof BBSItemScores] === index}
                      onChange={() => handleScoreChange(item.id, index)}
                      className="mt-1 mr-3"
                    />
                    <div>
                      <span className="font-medium text-primary-600">{index}점:</span>
                      <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">{criterion}</span>
                    </div>
                  </label>
                ))}
              </div>
            </div>
          </div>
          );
        })}
      </div>

      {/* 메모 */}
      <div className="card">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          메모 (선택사항)
        </label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          className="input-field min-h-[100px]"
          placeholder="검사 중 특이사항이나 관찰 내용을 입력하세요..."
        />
      </div>

      {/* 제출 버튼 */}
      <button
        type="submit"
        disabled={isLoading}
        className="w-full btn-primary py-3 text-lg font-medium"
      >
        {isLoading ? (
          <span className="flex items-center justify-center">
            <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            저장 중...
          </span>
        ) : (
          `BBS 검사 결과 저장 (총점: ${totalScore}점)`
        )}
      </button>
    </form>
  );
}
