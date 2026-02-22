"""
포즈 오버레이 가시성 임계값 최적화 스크립트

TUG 영상을 분석하여 최적의 visibility threshold를 찾습니다.
"""

import cv2
import numpy as np
import mediapipe as mp
from collections import defaultdict

# 분석할 영상 경로
SIDE_VIDEO = r"c:\Users\user\Desktop\TUG\TUG_1_Side.mp4"
FRONT_VIDEO = r"c:\Users\user\Desktop\TUG\TUG_1_Front.MOV"

# 테스트할 임계값들 (1% 단위, 20%~60% 범위)
THRESHOLDS = [i/100 for i in range(20, 61, 1)]  # 0.20 ~ 0.60

# 몸체 랜드마크 인덱스 (11-32, 얼굴 제외)
BODY_LANDMARKS = set(range(11, 33))

# 주요 관절 이름
LANDMARK_NAMES = {
    11: "왼쪽 어깨",
    12: "오른쪽 어깨",
    13: "왼쪽 팔꿈치",
    14: "오른쪽 팔꿈치",
    15: "왼쪽 손목",
    16: "오른쪽 손목",
    23: "왼쪽 엉덩이",
    24: "오른쪽 엉덩이",
    25: "왼쪽 무릎",
    26: "오른쪽 무릎",
    27: "왼쪽 발목",
    28: "오른쪽 발목",
}


def analyze_video_visibility(video_path: str, video_name: str):
    """영상의 각 프레임에서 랜드마크 가시성 분석"""

    print(f"\n{'='*60}")
    print(f"분석 중: {video_name}")
    print(f"파일: {video_path}")
    print(f"{'='*60}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"ERROR: 영상을 열 수 없습니다: {video_path}")
        return None

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0

    print(f"FPS: {fps:.1f}, 총 프레임: {total_frames}, 길이: {duration:.1f}초")

    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=2,
        smooth_landmarks=True,
        enable_segmentation=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    # 각 랜드마크별 가시성 데이터 수집
    visibility_data = defaultdict(list)
    frame_count = 0
    detected_frames = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(frame_rgb)

        if results.pose_landmarks:
            detected_frames += 1
            for idx in BODY_LANDMARKS:
                if idx < len(results.pose_landmarks.landmark):
                    lm = results.pose_landmarks.landmark[idx]
                    visibility_data[idx].append(lm.visibility)

        frame_count += 1

        # 진행률 출력
        if frame_count % 100 == 0:
            print(f"  처리 중: {frame_count}/{total_frames} ({100*frame_count/total_frames:.0f}%)")

    cap.release()
    pose.close()

    print(f"\n포즈 감지율: {detected_frames}/{frame_count} ({100*detected_frames/frame_count:.1f}%)")

    return visibility_data


def analyze_threshold_impact(visibility_data: dict, video_name: str, verbose: bool = False):
    """각 임계값에서 보이는 랜드마크 비율 분석"""

    print(f"\n분석 중: {video_name} ({len(THRESHOLDS)}개 임계값 테스트)")

    results = {}

    for threshold in THRESHOLDS:
        landmark_detection_rates = {}

        for idx in BODY_LANDMARKS:
            if idx in visibility_data and len(visibility_data[idx]) > 0:
                visible_count = sum(1 for v in visibility_data[idx] if v > threshold)
                total_count = len(visibility_data[idx])
                rate = visible_count / total_count
                landmark_detection_rates[idx] = rate

        # 전체 평균 감지율
        if landmark_detection_rates:
            avg_rate = np.mean(list(landmark_detection_rates.values()))
        else:
            avg_rate = 0

        results[threshold] = {
            'avg_rate': avg_rate,
            'landmark_rates': landmark_detection_rates
        }

        if verbose:
            print(f"\n임계값 {threshold}:")
            print(f"  평균 감지율: {avg_rate*100:.1f}%")

            # 주요 관절별 감지율
            print(f"  주요 관절별 감지율:")
            for idx in sorted(LANDMARK_NAMES.keys()):
                if idx in landmark_detection_rates:
                    rate = landmark_detection_rates[idx]
                    status = "[OK]" if rate > 0.8 else ("[--]" if rate > 0.5 else "[XX]")
                    print(f"    {status} {LANDMARK_NAMES[idx]}: {rate*100:.1f}%")

    return results


def find_optimal_threshold(side_results: dict, front_results: dict):
    """측면/정면 영상 모두에서 최적의 임계값 찾기"""

    print(f"\n{'='*60}")
    print("최적 임계값 분석")
    print(f"{'='*60}")

    # 중요 관절 (기립/착석, 보행에 중요)
    critical_landmarks = {23, 24, 25, 26, 27, 28}  # 엉덩이, 무릎, 발목

    all_scores = []

    for threshold in THRESHOLDS:
        side_avg = side_results[threshold]['avg_rate'] if side_results else 0
        front_avg = front_results[threshold]['avg_rate'] if front_results else 0

        # 중요 관절의 감지율
        side_critical = 0
        front_critical = 0

        if side_results:
            rates = [side_results[threshold]['landmark_rates'].get(idx, 0) for idx in critical_landmarks]
            side_critical = np.mean(rates) if rates else 0

        if front_results:
            rates = [front_results[threshold]['landmark_rates'].get(idx, 0) for idx in critical_landmarks]
            front_critical = np.mean(rates) if rates else 0

        # 종합 점수 (중요 관절 가중치 2배)
        score = (side_avg + front_avg) / 2 + (side_critical + front_critical)

        all_scores.append({
            'threshold': threshold,
            'side_avg': side_avg,
            'front_avg': front_avg,
            'side_critical': side_critical,
            'front_critical': front_critical,
            'score': score
        })

    # 점수 기준 정렬
    all_scores.sort(key=lambda x: x['score'], reverse=True)

    # 상위 10개 출력
    print("\n[TOP 10 임계값]")
    print("-" * 80)
    print(f"{'순위':^4} {'임계값':^8} {'측면평균':^10} {'정면평균':^10} {'측면중요':^10} {'정면중요':^10} {'점수':^8}")
    print("-" * 80)

    for i, item in enumerate(all_scores[:10]):
        print(f"{i+1:^4} {item['threshold']:^8.2f} {item['side_avg']*100:^10.1f} {item['front_avg']*100:^10.1f} {item['side_critical']*100:^10.1f} {item['front_critical']*100:^10.1f} {item['score']:^8.3f}")

    print("-" * 80)

    best = all_scores[0]
    best_threshold = best['threshold']

    # 정확도와 가시성 균형점 찾기 (가시성은 높이고, 노이즈는 줄이기)
    # 0.3~0.4 범위에서 가장 좋은 것 찾기
    balanced_scores = [s for s in all_scores if 0.30 <= s['threshold'] <= 0.45]
    if balanced_scores:
        balanced_best = max(balanced_scores, key=lambda x: x['score'])
        print(f"\n[균형점 분석 (0.30~0.45 범위)]")
        print(f"균형 추천: {balanced_best['threshold']:.2f} (점수: {balanced_best['score']:.3f})")

    print(f"\n{'='*60}")
    print(f">>> BEST THRESHOLD: {best_threshold:.2f}")
    print(f">>> 측면 평균: {best['side_avg']*100:.1f}%, 정면 평균: {best['front_avg']*100:.1f}%")
    print(f">>> 중요관절 - 측면: {best['side_critical']*100:.1f}%, 정면: {best['front_critical']*100:.1f}%")
    print(f"{'='*60}")

    return best_threshold


def main():
    print("=" * 60)
    print("TUG 포즈 오버레이 가시성 임계값 최적화")
    print("=" * 60)

    # 측면 영상 분석
    side_visibility = analyze_video_visibility(SIDE_VIDEO, "측면 영상")
    side_results = None
    if side_visibility:
        side_results = analyze_threshold_impact(side_visibility, "측면 영상")

    # 정면 영상 분석
    front_visibility = analyze_video_visibility(FRONT_VIDEO, "정면 영상")
    front_results = None
    if front_visibility:
        front_results = analyze_threshold_impact(front_visibility, "정면 영상")

    # 최적 임계값 찾기
    if side_results or front_results:
        optimal = find_optimal_threshold(side_results, front_results)

        print(f"\n" + "=" * 60)
        print("결론")
        print("=" * 60)
        print(f"현재 임계값: 0.5 (50%)")
        print(f"추천 임계값: {optimal} ({optimal*100:.0f}%)")

        if optimal != 0.5:
            print(f"\ntug_analyzer.py, gait_analyzer.py의")
            print(f"'if lm.visibility > 0.5:' 를")
            print(f"'if lm.visibility > {optimal}:' 로 변경하세요.")
    else:
        print("영상 분석에 실패했습니다.")


if __name__ == "__main__":
    main()
