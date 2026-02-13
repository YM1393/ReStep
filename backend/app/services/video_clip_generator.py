"""보행 영상 하이라이트 클립 생성 서비스"""
import os
import cv2
import numpy as np


def extract_walking_clip(
    video_path: str,
    start_time: float,
    end_time: float,
    output_path: str,
    padding_seconds: float = 0.5
) -> str:
    """10MWT 보행 구간만 추출"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"영상을 열 수 없습니다: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    start_frame = max(0, int((start_time - padding_seconds) * fps))
    end_frame = int((end_time + padding_seconds) * fps)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    current_frame = start_frame

    while current_frame <= end_frame:
        ret, frame = cap.read()
        if not ret:
            break
        writer.write(frame)
        current_frame += 1

    cap.release()
    writer.release()
    return output_path


def generate_side_by_side_clip(
    video1_path: str, start1: float, end1: float,
    video2_path: str, start2: float, end2: float,
    output_path: str,
    labels: tuple = ('처음', '현재'),
    target_height: int = 480
) -> str:
    """두 영상의 보행 구간을 좌우 비교 영상으로 생성"""
    cap1 = cv2.VideoCapture(video1_path)
    cap2 = cv2.VideoCapture(video2_path)

    if not cap1.isOpened() or not cap2.isOpened():
        cap1.release()
        cap2.release()
        raise ValueError("영상을 열 수 없습니다")

    fps1 = cap1.get(cv2.CAP_PROP_FPS)
    fps2 = cap2.get(cv2.CAP_PROP_FPS)
    output_fps = min(fps1, fps2, 30)

    # 보행 구간 프레임 범위
    s1 = max(0, int(start1 * fps1))
    e1 = int(end1 * fps1)
    s2 = max(0, int(start2 * fps2))
    e2 = int(end2 * fps2)

    total1 = e1 - s1
    total2 = e2 - s2
    max_frames = max(total1, total2)

    # 첫 프레임으로 영상 크기 결정
    cap1.set(cv2.CAP_PROP_POS_FRAMES, s1)
    ret1, frame1 = cap1.read()
    cap2.set(cv2.CAP_PROP_POS_FRAMES, s2)
    ret2, frame2 = cap2.read()

    if not ret1 or not ret2:
        cap1.release()
        cap2.release()
        raise ValueError("프레임을 읽을 수 없습니다")

    # 높이를 target_height로 통일
    def resize_frame(frame, target_h):
        h, w = frame.shape[:2]
        scale = target_h / h
        new_w = int(w * scale)
        return cv2.resize(frame, (new_w, target_h))

    frame1_r = resize_frame(frame1, target_height)
    frame2_r = resize_frame(frame2, target_height)
    out_width = frame1_r.shape[1] + frame2_r.shape[1] + 4  # 4px divider

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, output_fps, (out_width, target_height))

    # 리셋
    cap1.set(cv2.CAP_PROP_POS_FRAMES, s1)
    cap2.set(cv2.CAP_PROP_POS_FRAMES, s2)

    last_frame1 = frame1_r
    last_frame2 = frame2_r

    for i in range(max_frames):
        # 프레임 비율에 맞게 읽기
        if i < total1:
            ret1, f1 = cap1.read()
            if ret1:
                last_frame1 = resize_frame(f1, target_height)
        if i < total2:
            ret2, f2 = cap2.read()
            if ret2:
                last_frame2 = resize_frame(f2, target_height)

        # 라벨 추가
        labeled1 = last_frame1.copy()
        labeled2 = last_frame2.copy()
        _add_label(labeled1, labels[0])
        _add_label(labeled2, labels[1])

        # 구분선 추가하여 합치기
        divider = np.zeros((target_height, 4, 3), dtype=np.uint8)
        divider[:] = (200, 200, 200)

        # 너비 맞추기
        w1 = frame1_r.shape[1]
        w2 = frame2_r.shape[1]
        if labeled1.shape[1] != w1:
            labeled1 = cv2.resize(labeled1, (w1, target_height))
        if labeled2.shape[1] != w2:
            labeled2 = cv2.resize(labeled2, (w2, target_height))

        combined = np.hstack([labeled1, divider, labeled2])
        writer.write(combined)

    cap1.release()
    cap2.release()
    writer.release()
    return output_path


def _add_label(frame: np.ndarray, text: str):
    """프레임에 라벨 텍스트 추가"""
    h, w = frame.shape[:2]
    # 배경 박스
    cv2.rectangle(frame, (10, 10), (140, 50), (0, 0, 0), -1)
    cv2.rectangle(frame, (10, 10), (140, 50), (255, 255, 255), 1)
    cv2.putText(frame, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
