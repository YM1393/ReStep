"""
ArUco 마커 생성기 - 10MWT 거리 캘리브레이션용

DICT_4X4_50 사전 사용 (4x4 내부 격자 = 원거리 감지 최적)
마커 ID: 0=START(2m, 측정 시작), 1=FINISH(12m, 측정 종료)
"""

import cv2
import numpy as np
import os
from typing import Dict, List, Tuple


# 마커 설정
ARUCO_DICT_TYPE = cv2.aruco.DICT_4X4_50
MARKER_CONFIG: List[Dict] = [
    {"id": 0, "distance_m": 2, "label": "START", "description": "2m 지점 - 10m 측정 시작",
     "color": (0, 200, 0)},  # 녹색
    {"id": 1, "distance_m": 12, "label": "FINISH", "description": "12m 지점 - 10m 측정 종료",
     "color": (0, 0, 200)},  # 빨간색
]


def generate_aruco_marker_image(marker_id: int, size_px: int = 800) -> np.ndarray:
    """단일 ArUco 마커 이미지 생성

    Args:
        marker_id: 마커 ID (0 또는 1)
        size_px: 출력 이미지 크기 (픽셀)

    Returns:
        마커 이미지 (grayscale numpy array)
    """
    dictionary = cv2.aruco.getPredefinedDictionary(ARUCO_DICT_TYPE)
    marker_img = cv2.aruco.generateImageMarker(dictionary, marker_id, size_px)
    return marker_img


def generate_marker_images(output_dir: str, size_px: int = 800) -> List[str]:
    """모든 마커를 개별 PNG 파일로 저장

    Args:
        output_dir: 출력 디렉토리
        size_px: 마커 이미지 크기 (픽셀)

    Returns:
        생성된 파일 경로 리스트
    """
    os.makedirs(output_dir, exist_ok=True)
    paths = []

    for config in MARKER_CONFIG:
        marker_img = generate_aruco_marker_image(config["id"], size_px)
        filename = f"aruco_{config['label'].lower()}_{config['id']}.png"
        filepath = os.path.join(output_dir, filename)
        cv2.imwrite(filepath, marker_img)
        paths.append(filepath)
        print(f"[ARUCO] {config['label']} (ID={config['id']}) saved: {filepath}")

    return paths


def generate_marker_pdf(output_path: str, marker_size_cm: float = 25.0) -> str:
    """인쇄용 A4 PDF 생성 (START/FINISH 마커 2개 + 설치 안내)

    Args:
        output_path: PDF 출력 경로
        marker_size_cm: 인쇄 시 마커 크기 (cm)

    Returns:
        생성된 PDF 파일 경로
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import black, gray, green, red, HexColor
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import tempfile

    # 한글 폰트 등록 (Windows)
    font_registered = False
    for font_path in [
        "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/gulim.ttc",
        "C:/Windows/Fonts/batang.ttc",
    ]:
        if os.path.exists(font_path):
            try:
                font_name = os.path.splitext(os.path.basename(font_path))[0]
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                font_registered = True
                break
            except Exception:
                continue

    if not font_registered:
        font_name = "Helvetica"

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    c = canvas.Canvas(output_path, pagesize=A4)
    page_w, page_h = A4

    # === 1페이지: 설치 안내 ===
    c.setFont(font_name, 24)
    c.drawCentredString(page_w / 2, page_h - 3 * cm, "10MWT ArUco 마커 설치 안내")

    c.setFont(font_name, 13)
    y = page_h - 5 * cm
    instructions = [
        "1. 다음 페이지의 마커 2개를 A4 용지에 인쇄하세요.",
        "2. 마커를 단단한 판(폼보드 등)에 부착하세요.",
        f"3. 인쇄 크기: 약 {marker_size_cm:.0f}cm x {marker_size_cm:.0f}cm",
        "",
        "[ 마커 배치 ]",
        "• START 마커 (녹색, ID=0): 2m 지점에 배치 (측정 시작)",
        "• FINISH 마커 (빨간색, ID=1): 12m 지점에 배치 (측정 종료)",
        "• 두 마커 사이 거리 = 정확히 10m",
        "",
        "[ 배치 권장 사항 ]",
        "• 보행 경로 옆 벽이나 바닥에 배치 (보행자가 가리지 않도록)",
        "• 카메라에서 마커가 잘 보이는 위치에 배치",
        "• 마커가 구겨지거나 기울어지지 않도록 고정",
        "• 조명이 충분한 환경에서 사용",
        "",
        "[ 보행 경로 ]",
        "  카메라 ← [0m 출발] ← [2m START] ←←← 10m ←←← [12m FINISH]",
        "",
        "[ 참고 ]",
        "• 마커가 없어도 기존 방식으로 분석 가능합니다.",
        "• 마커를 사용하면 보정계수 없이 정확한 10m 측정이 가능합니다.",
    ]

    for line in instructions:
        if line == "":
            y -= 0.5 * cm
            continue
        if line.startswith("["):
            c.setFont(font_name, 14)
            c.drawString(2.5 * cm, y, line)
            c.setFont(font_name, 13)
        else:
            c.drawString(2.5 * cm, y, line)
        y -= 0.7 * cm

    # 하단에 마커 미리보기
    y -= 1 * cm
    c.setFont(font_name, 11)
    c.drawCentredString(page_w / 2, y, "-- 마커 미리보기 --")
    y -= 0.5 * cm

    preview_size = 3.5 * cm
    x_start = (page_w - 2 * preview_size - 2 * cm) / 2
    label_colors = [green, red]
    for i, config in enumerate(MARKER_CONFIG):
        marker_img = generate_aruco_marker_image(config["id"], 200)
        tmp_path = os.path.join(tempfile.gettempdir(), f"aruco_preview_{config['id']}.png")
        cv2.imwrite(tmp_path, marker_img)

        x = x_start + i * (preview_size + 2 * cm)
        c.drawImage(tmp_path, x, y - preview_size, preview_size, preview_size)
        c.setFont(font_name, 11)
        c.setFillColor(label_colors[i])
        c.drawCentredString(x + preview_size / 2, y - preview_size - 0.5 * cm,
                            f"{config['label']} (ID: {config['id']})")
        c.setFillColor(black)
        os.remove(tmp_path)

    c.showPage()

    # === 2~3페이지: 각 마커 (START / FINISH) ===
    marker_size = marker_size_cm * cm
    label_colors_pdf = [green, red]

    for idx, config in enumerate(MARKER_CONFIG):
        marker_img = generate_aruco_marker_image(config["id"], 1000)

        # 흰색 테두리 추가 (ArUco 인식에 필요)
        border = 100
        bordered = np.ones((1200, 1200), dtype=np.uint8) * 255
        bordered[border:border + 1000, border:border + 1000] = marker_img
        marker_img = bordered

        tmp_path = os.path.join(tempfile.gettempdir(), f"aruco_marker_{config['id']}.png")
        cv2.imwrite(tmp_path, marker_img)

        # 마커를 페이지 중앙에 배치
        x = (page_w - marker_size) / 2
        y = (page_h - marker_size) / 2 + 1.5 * cm

        c.drawImage(tmp_path, x, y, marker_size, marker_size)

        # 라벨 (색상 구분)
        c.setFillColor(label_colors_pdf[idx])
        c.setFont(font_name, 28)
        c.drawCentredString(page_w / 2, y - 1.5 * cm,
                            f"{config['label']} (ID: {config['id']})")
        c.setFillColor(black)

        c.setFont(font_name, 14)
        c.drawCentredString(page_w / 2, y - 2.8 * cm, config["description"])

        # 상단 타이틀
        c.setFont(font_name, 12)
        c.drawCentredString(page_w / 2, page_h - 2 * cm, "10MWT ArUco 마커")

        # 인쇄 크기 참고
        c.setFont(font_name, 10)
        c.setFillColor(gray)
        c.drawCentredString(page_w / 2, 1.5 * cm,
                            f"인쇄 크기: {marker_size_cm:.0f}cm x {marker_size_cm:.0f}cm  |  DICT_4X4_50")
        c.setFillColor(black)

        os.remove(tmp_path)
        c.showPage()

    c.save()
    print(f"[ARUCO] Marker PDF saved: {output_path}")
    return output_path
