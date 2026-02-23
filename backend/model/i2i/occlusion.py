from PIL import Image
import numpy as np


def apply_sleeve_occlusion(product_rgba: Image.Image) -> Image.Image:
    """
    광고용 기본 오클루전:
    - 제품 상단(스트랩 쪽)이 손목 뒤로 들어간 것처럼 자연스럽게 알파를 줄인다.
    - 직선/사각형 경계가 보이지 않도록 중앙부가 더 강하게 사라지는 가중치를 사용.
    """
    if product_rgba.mode != "RGBA":
        product_rgba = product_rgba.convert("RGBA")

    w, h = product_rgba.size
    r, g, b, a = product_rgba.split()
    alpha = np.array(a).astype(np.float32)

    # 상단 20% 영역에서만 fade (광고 기본값)
    fade_h = int(h * 0.20)

    # x 방향으로 중앙이 더 많이 사라지게 (부드러운 곡률)
    xs = np.linspace(-1.0, 1.0, w)
    center_weight = 1.0 - (xs ** 2)  # 중앙=1, 가장자리=0

    for y in range(fade_h):
        t = y / max(1, fade_h - 1)  # 0..1 (상단=0, 아래=1)
        # 상단일수록 더 투명, 아래로 갈수록 덜 투명
        # 중앙부가 더 강하게 사라지도록 가중
        row_mul = (t ** 1.6) * (0.70 + 0.30 * (1.0 - center_weight))
        alpha[y, :] *= row_mul

    new_alpha = Image.fromarray(np.clip(alpha, 0, 255).astype("uint8"))
    return Image.merge("RGBA", (r, g, b, new_alpha))