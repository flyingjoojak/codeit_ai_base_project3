from dataclasses import dataclass
from typing import Tuple, Dict

@dataclass(frozen=True)
class Layout:
    canvas: Tuple[int, int]
    image_box: Tuple[int, int, int, int]  # x, y, w, h
    text_origin: Tuple[int, int]

LAYOUTS: Dict[str, Layout] = {
    # 이미지 박스는 “대략 안전한 영역” (CSS 정확 반영은 다음에)
    "160x600": Layout((160, 600), (0, 0, 160, 360), (12, 380)),
    "300x300": Layout((300, 300), (20, 20, 260, 160), (20, 195)),
    "728x90":  Layout((728, 90),  (0, 0, 180, 90),  (200, 18)),
}
