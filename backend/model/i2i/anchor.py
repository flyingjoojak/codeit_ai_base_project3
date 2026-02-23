from PIL import Image
import numpy as np
import cv2


def guess_wrist_roi(image: Image.Image):
    """
    단순 휴리스틱 기반 wrist ROI 추정 (안정적)
    중앙 하단을 wrist zone으로 가정
    """
    w, h = image.size

    y1 = int(h * 0.38)
    y2 = int(h * 0.80)

    x1 = int(w * 0.20)
    x2 = int(w * 0.80)

    roi_w = x2 - x1
    roi_h = int(roi_w * 0.42)  # 밴드 영역 비율

    cx = (x1 + x2) // 2
    cy = int((y1 + y2) * 0.52)

    final_x = max(0, cx - roi_w // 2)
    final_y = max(0, cy - roi_h // 2)

    return (final_x, final_y, roi_w, roi_h)


def estimate_wrist_angle(image: Image.Image, roi, debug: bool = False):
    """
    ROI 근처에서 팔 방향(주 방향)을 Hough line으로 추정.
    반환: angle_deg (시계 회전에 사용)
    """
    x, y, w, h = roi
    img = image.convert("RGB")
    arr = np.array(img)

    # ROI 주변을 조금 넓게 잡아 선(팔 윤곽/소매)을 잘 잡음
    pad = int(min(w, h) * 0.35)
    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(arr.shape[1], x + w + pad)
    y1 = min(arr.shape[0], y + h + pad)

    crop = arr[y0:y1, x0:x1]
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)

    # 엣지 → 라인
    edges = cv2.Canny(gray, threshold1=50, threshold2=150)
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=50,
        minLineLength=int(min(crop.shape[0], crop.shape[1]) * 0.25),
        maxLineGap=15,
    )

    if lines is None or len(lines) == 0:
        # fallback: 손목은 보통 좌->우로 약간 기울어짐 (안정적 기본값)
        return -8.0

    angles = []
    for (x1l, y1l, x2l, y2l) in lines[:, 0]:
        dx = x2l - x1l
        dy = y2l - y1l
        if dx == 0:
            continue
        angle = np.degrees(np.arctan2(dy, dx))  # -180~180
        # 수평에 가까운 선(팔 방향)만 사용: -60~60도
        if -60 <= angle <= 60:
            angles.append(angle)

    if not angles:
        return -8.0

    # 중앙값이 튐에 강함
    angle_deg = float(np.median(angles))

    # 너무 과한 각은 제한 (합성 안정성)
    angle_deg = max(-20.0, min(20.0, angle_deg))

    return angle_deg


def guess_wrist_roi_and_angle(image: Image.Image):
    roi = guess_wrist_roi(image)
    angle = estimate_wrist_angle(image, roi)
    return roi, angle