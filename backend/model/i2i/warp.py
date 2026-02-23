from PIL import Image, ImageFilter


def fit_product_to_wrist_roi(product_rgba: Image.Image, roi, angle_deg: float):
    """
    제품 RGBA를 wrist ROI 크기에 맞춰 스케일하고, wrist angle에 맞춰 회전.
    반환: 변환된 RGBA
    """
    x, y, w, h = roi

    # 1) wrist ROI에 맞는 크기 목표:
    # 시계는 ROI 높이의 1.6~2.1배 정도가 자연스러운 경우가 많음(다이얼 포함)
    target_h = int(h * 2.0)
    target_w = int(w * 0.90)

    pw, ph = product_rgba.size
    scale = min(target_w / max(1, pw), target_h / max(1, ph))
    new_size = (max(1, int(pw * scale)), max(1, int(ph * scale)))
    prod = product_rgba.resize(new_size, Image.Resampling.LANCZOS)

    # 2) 회전 (팔 방향에 따라 자동)
    prod = prod.rotate(angle_deg, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=(0, 0, 0, 0))

    # 3) 경계 feather (자연스러움)
    # 알파만 살짝 blur
    r, g, b, a = prod.split()
    a = a.filter(ImageFilter.GaussianBlur(radius=1.2))
    prod = Image.merge("RGBA", (r, g, b, a))

    return prod