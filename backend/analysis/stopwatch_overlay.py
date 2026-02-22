"""
오버레이 영상에 스톱워치 UI를 추가하는 공통 유틸리티
TUG, 10MWT 모두에서 사용
"""
import os
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont


# --- 한글 텍스트 렌더링 ---
_KOREAN_FONT_PATH = "C:/Windows/Fonts/malgunbd.ttf"
_korean_font_cache: Dict[int, ImageFont.FreeTypeFont] = {}
_text_patch_cache: Dict[tuple, Tuple[np.ndarray, np.ndarray]] = {}


def _get_korean_font(size: int) -> ImageFont.FreeTypeFont:
    if size not in _korean_font_cache:
        try:
            _korean_font_cache[size] = ImageFont.truetype(_KOREAN_FONT_PATH, size)
        except OSError:
            _korean_font_cache[size] = ImageFont.load_default()
    return _korean_font_cache[size]


def render_text_patch(text: str, font_size: int, color_bgr: Tuple[int, int, int]) -> Tuple[np.ndarray, np.ndarray]:
    """텍스트를 BGRA 패치로 렌더링 (캐시). Returns (patch_bgr, alpha_mask)."""
    cache_key = (text, font_size, color_bgr)
    if cache_key in _text_patch_cache:
        return _text_patch_cache[cache_key]

    font = _get_korean_font(font_size)
    dummy_img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
    draw = ImageDraw.Draw(dummy_img)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0] + 4
    th = bbox[3] - bbox[1] + 4

    text_img = Image.new('RGBA', (tw, th), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_img)
    rgb_color = (color_bgr[2], color_bgr[1], color_bgr[0], 255)
    draw.text((-bbox[0] + 2, -bbox[1] + 2), text, font=font, fill=rgb_color)

    arr = np.array(text_img)
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
    alpha = arr[:, :, 3]

    _text_patch_cache[cache_key] = (bgr, alpha)
    return bgr, alpha


def blit_text_patch(image: np.ndarray, patch_bgr: np.ndarray, alpha: np.ndarray, x: int, y: int) -> None:
    """알파 합성으로 텍스트 패치를 프레임에 그리기."""
    ph, pw = patch_bgr.shape[:2]
    ih, iw = image.shape[:2]

    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(iw, x + pw), min(ih, y + ph)
    px1, py1 = x1 - x, y1 - y

    if x2 <= x1 or y2 <= y1:
        return

    roi = image[y1:y2, x1:x2]
    mask = alpha[py1:py1 + (y2 - y1), px1:px1 + (x2 - x1)].astype(np.float32) / 255.0
    mask3 = mask[:, :, np.newaxis]

    blended = (patch_bgr[py1:py1 + (y2 - y1), px1:px1 + (x2 - x1)].astype(np.float32) * mask3 +
               roi.astype(np.float32) * (1 - mask3))
    image[y1:y2, x1:x2] = blended.astype(np.uint8)


def _draw_panel_background(frame: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> None:
    """반투명 배경 패널 그리기."""
    overlay = frame.copy()
    cv2.rectangle(overlay, (x0, y0), (x1, y1), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
    cv2.rectangle(frame, (x0, y0), (x1, y1), (70, 70, 70), 1)


def _draw_progress_bar(
    frame: np.ndarray,
    bar_x0: int, bar_y0: int, bar_x1: int, bar_y1: int,
    current_time: float, timeline: List[Dict], total_duration: float
) -> None:
    """단계별 색상 진행 바 그리기."""
    bar_w = bar_x1 - bar_x0
    cv2.rectangle(frame, (bar_x0, bar_y0), (bar_x1, bar_y1), (50, 50, 50), -1)

    if total_duration > 0:
        for p in timeline:
            seg_x0 = bar_x0 + int((p['start'] / total_duration) * bar_w)
            fill_end = min(current_time, p['end'])
            if fill_end > p['start']:
                seg_x1 = bar_x0 + int((fill_end / total_duration) * bar_w)
                cv2.rectangle(frame, (seg_x0, bar_y0), (seg_x1, bar_y1), p['color'], -1)


# ===== TUG 스톱워치 =====

TUG_PHASE_COLORS_BGR = {
    'stand_up':  (128, 0, 128),
    'walk_out':  (255, 0, 0),
    'turn':      (0, 200, 255),
    'walk_back': (0, 200, 0),
    'sit_down':  (180, 130, 255)
}

TUG_PHASE_LABELS = {
    'stand_up':  '일어서기',
    'walk_out':  '걷기 (나감)',
    'turn':      '돌아서기',
    'walk_back': '걷기 (돌아옴)',
    'sit_down':  '앉기'
}

TUG_PHASE_ORDER = ['stand_up', 'walk_out', 'turn', 'walk_back', 'sit_down']


def build_tug_timeline(phases: Dict) -> Tuple[List[Dict], float]:
    """TUG phases dict에서 타임라인 리스트 생성."""
    timeline = []
    for pname in TUG_PHASE_ORDER:
        pinfo = phases.get(pname)
        if isinstance(pinfo, dict) and 'start_time' in pinfo and 'end_time' in pinfo:
            timeline.append({
                'start': pinfo['start_time'],
                'end': pinfo['end_time'],
                'name': pname,
                'label': TUG_PHASE_LABELS.get(pname, pname),
                'color': TUG_PHASE_COLORS_BGR.get(pname, (255, 255, 255))
            })
    total_duration = phases.get('total_duration', 0)
    return timeline, total_duration


def draw_tug_stopwatch(
    frame: np.ndarray,
    current_time: float,
    current_phase: Optional[Dict],
    timeline: List[Dict],
    total_duration: float,
    frame_width: int,
    frame_height: int
) -> None:
    """TUG 스톱워치 UI를 프레임에 그리기 (우측 하단)."""
    scale = max(frame_height / 1080.0, 0.5)

    panel_w = int(460 * scale)
    panel_h = int(115 * scale)
    margin = int(20 * scale)

    x0 = frame_width - panel_w - margin
    y0 = frame_height - panel_h - margin
    x1 = frame_width - margin
    y1 = frame_height - margin

    _draw_panel_background(frame, x0, y0, x1, y1)

    font_size = int(28 * scale)

    if current_phase:
        color = current_phase['color']
        label = current_phase['label']
        elapsed = current_time - current_phase['start']

        # 색상 인디케이터
        dot_x = x0 + int(22 * scale)
        dot_y = y0 + int(32 * scale)
        dot_r = int(10 * scale)
        cv2.circle(frame, (dot_x, dot_y), dot_r, color, -1)
        cv2.circle(frame, (dot_x, dot_y), dot_r, (255, 255, 255), 1)

        # 단계명 (한글)
        text_x = dot_x + int(18 * scale)
        text_y = y0 + int(10 * scale)
        patch, alpha = render_text_patch(label, font_size, color)
        blit_text_patch(frame, patch, alpha, text_x, text_y)

        # 경과 시간
        time_str = f"{elapsed:.2f}s"
        font_scale = 0.9 * scale
        (tw, _), _ = cv2.getTextSize(time_str, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)
        time_x = x1 - tw - int(16 * scale)
        time_y = y0 + int(38 * scale)
        cv2.putText(frame, time_str, (time_x, time_y),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 2, cv2.LINE_AA)
    else:
        if timeline and current_time < timeline[0]['start']:
            patch, alpha = render_text_patch("준비", font_size, (150, 150, 150))
            blit_text_patch(frame, patch, alpha, x0 + int(22 * scale), y0 + int(10 * scale))
        elif timeline and current_time > timeline[-1]['end']:
            patch, alpha = render_text_patch("완료", font_size, (100, 255, 100))
            blit_text_patch(frame, patch, alpha, x0 + int(22 * scale), y0 + int(10 * scale))

    # 진행 바
    bar_x0 = x0 + int(16 * scale)
    bar_y0 = y0 + int(60 * scale)
    bar_x1 = x1 - int(16 * scale)
    bar_y1 = y0 + int(78 * scale)
    _draw_progress_bar(frame, bar_x0, bar_y0, bar_x1, bar_y1, current_time, timeline, total_duration)

    # 총 시간
    if total_duration > 0:
        display_time = min(current_time, total_duration)
        total_str = f"{display_time:.1f} / {total_duration:.1f}s"
        font_scale_s = 0.5 * scale
        bar_w = bar_x1 - bar_x0
        (tw, _), _ = cv2.getTextSize(total_str, cv2.FONT_HERSHEY_SIMPLEX, font_scale_s, 1)
        total_x = bar_x0 + (bar_w - tw) // 2
        total_y = bar_y1 + int(20 * scale)
        cv2.putText(frame, total_str, (total_x, total_y),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale_s, (170, 170, 170), 1, cv2.LINE_AA)


# ===== 10MWT 스톱워치 =====

def _draw_mwt_stopwatch_frame(
    frame: np.ndarray,
    frame_idx: int,
    start_frame: int,
    end_frame: int,
    measure_time: float,
    fps: float,
    frame_width: int,
    frame_height: int
) -> None:
    """10MWT 스톱워치 UI - 측정 시간만 심플하게 표시 (우측 하단).
    프레임 번호 기반 비교로 정확한 타이밍 보장.
    """
    scale = max(frame_height / 1080.0, 0.5)

    panel_w = int(300 * scale)
    panel_h = int(70 * scale)
    margin = int(20 * scale)

    x0 = frame_width - panel_w - margin
    y0 = frame_height - panel_h - margin
    x1 = frame_width - margin
    y1 = frame_height - margin

    _draw_panel_background(frame, x0, y0, x1, y1)

    font_size = int(28 * scale)
    total_measure_frames = max(end_frame - start_frame, 1)

    if frame_idx < start_frame:
        # 측정 시작 전
        patch, alpha = render_text_patch("대기", font_size, (150, 150, 150))
        blit_text_patch(frame, patch, alpha, x0 + int(22 * scale), y0 + int(10 * scale))
    elif frame_idx <= end_frame:
        # 측정 중 - 경과 시간 표시 (보정된 시간 기준으로 비례 계산)
        progress = (frame_idx - start_frame) / total_measure_frames
        elapsed = progress * measure_time
        time_str = f"{elapsed:.2f}s"
        font_scale = 1.0 * scale
        (tw, th), _ = cv2.getTextSize(time_str, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)
        time_x = x0 + (panel_w - tw) // 2
        time_y = y0 + (panel_h + th) // 2
        cv2.putText(frame, time_str, (time_x, time_y),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 2, cv2.LINE_AA)
    else:
        # 측정 완료 - 최종 시간 표시
        time_str = f"{measure_time:.2f}s"
        font_scale = 1.0 * scale
        (tw, th), _ = cv2.getTextSize(time_str, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)
        time_x = x0 + (panel_w - tw) // 2
        time_y = y0 + (panel_h + th) // 2
        cv2.putText(frame, time_str, (time_x, time_y),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (100, 255, 100), 2, cv2.LINE_AA)


# ===== 공통: 오버레이 영상에 스톱워치 후처리 =====

def add_stopwatch_to_video(
    overlay_video_path: str,
    timeline: List[Dict],
    total_duration: float,
    fps: float,
    frame_width: int,
    frame_height: int,
    draw_fn,
    label: str = "TUG",
    time_offset: float = 0.0
) -> None:
    """오버레이 영상을 읽어 스톱워치 UI를 추가 후 덮어쓰기.
    time_offset: 영상 시작 시점의 원본 타임라인 시각 (phase clip용)
    """
    if not overlay_video_path or not os.path.exists(overlay_video_path):
        return

    cap = cv2.VideoCapture(overlay_video_path)
    if not cap.isOpened():
        return

    tmp_path = overlay_video_path + ".tmp.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    writer = cv2.VideoWriter(tmp_path, fourcc, fps, (frame_width, frame_height))
    if not writer.isOpened():
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(tmp_path, fourcc, fps, (frame_width, frame_height))

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_time = time_offset + frame_idx / fps

        # 현재 단계 결정
        current_phase = None
        for p in timeline:
            if p['start'] <= current_time <= p['end']:
                current_phase = p
                break

        draw_fn(frame, current_time, current_phase, timeline, total_duration, frame_width, frame_height)

        writer.write(frame)
        frame_idx += 1

    cap.release()
    writer.release()

    try:
        os.replace(tmp_path, overlay_video_path)
        print(f"[{label}] Stopwatch overlay added ({frame_idx} frames)")
    except Exception as e:
        print(f"[{label}] Failed to replace overlay: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def add_tug_stopwatch(overlay_video_path: str, phases: Dict, fps: float,
                      frame_width: int, frame_height: int,
                      time_offset: float = 0.0) -> None:
    """TUG 오버레이 영상에 스톱워치 추가."""
    timeline, total_duration = build_tug_timeline(phases)
    add_stopwatch_to_video(
        overlay_video_path, timeline, total_duration, fps,
        frame_width, frame_height, draw_tug_stopwatch, "TUG SIDE",
        time_offset=time_offset
    )


def add_mwt_stopwatch(overlay_video_path: str, start_frame: int, end_frame: int,
                      measure_time: float, fps: float,
                      frame_width: int, frame_height: int) -> None:
    """10MWT 오버레이 영상에 스톱워치 추가 (프레임 번호 기반, 보정된 측정 시간 표시)."""
    if not overlay_video_path or not os.path.exists(overlay_video_path):
        return

    cap = cv2.VideoCapture(overlay_video_path)
    if not cap.isOpened():
        return

    tmp_path = overlay_video_path + ".tmp.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    writer = cv2.VideoWriter(tmp_path, fourcc, fps, (frame_width, frame_height))
    if not writer.isOpened():
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(tmp_path, fourcc, fps, (frame_width, frame_height))

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        _draw_mwt_stopwatch_frame(frame, frame_idx, start_frame, end_frame,
                                   measure_time, fps, frame_width, frame_height)
        writer.write(frame)
        frame_idx += 1

    cap.release()
    writer.release()

    try:
        os.replace(tmp_path, overlay_video_path)
        print(f"[10MWT] Stopwatch overlay added ({frame_idx} frames, start={start_frame}, end={end_frame})")
    except Exception as e:
        print(f"[10MWT] Failed to replace overlay: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
