from PIL import Image, ImageFilter, ImageEnhance
import numpy as np
import cv2


def _extract_alpha_mask(rgba: Image.Image) -> np.ndarray:
    return np.array(rgba.split()[-1]).astype(np.uint8)


def _make_shadow_layers(
    alpha: np.ndarray,
    contact_blur: int = 1,
    ambient_blur: int = 18,
    contact_opacity: int = 155,
    ambient_opacity: int = 45,
    contact_erode_iter: int = 2,
    ambient_dilate_iter: int = 1,
) -> tuple[Image.Image, Image.Image]:
    """
    안정형 그림자:
    - contact: 얇고 선명하지만 과하지 않게
    - ambient: 아주 약하게만
    """
    kernel = np.ones((5, 5), np.uint8)

    contact = cv2.erode(alpha, kernel, iterations=contact_erode_iter)
    contact_img = Image.fromarray(contact).filter(ImageFilter.GaussianBlur(radius=contact_blur))

    ambient = cv2.dilate(alpha, kernel, iterations=ambient_dilate_iter)
    ambient_img = Image.fromarray(ambient).filter(ImageFilter.GaussianBlur(radius=ambient_blur))

    w, h = alpha.shape[1], alpha.shape[0]
    contact_rgba = Image.new("RGBA", (w, h), (0, 0, 0, contact_opacity))
    contact_rgba.putalpha(contact_img)

    ambient_rgba = Image.new("RGBA", (w, h), (0, 0, 0, ambient_opacity))
    ambient_rgba.putalpha(ambient_img)

    return contact_rgba, ambient_rgba


def _match_brightness_only(bg_rgba: Image.Image, prod_rgba: Image.Image, x: int, y: int) -> Image.Image:
    """
    안정형 톤 매칭:
    - 색온도(워밍) 같은 공격적 보정 금지
    - 밝기만 아주 약하게 맞춤
    """
    bw, bh = bg_rgba.size
    pw, ph = prod_rgba.size

    pad = int(min(pw, ph) * 0.10)
    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(bw, x + pw + pad)
    y1 = min(bh, y + ph + pad)

    patch = bg_rgba.crop((x0, y0, x1, y1)).convert("RGB")
    patch_np = np.array(patch).astype(np.float32)
    patch_lum = patch_np.mean()

    prod_rgb = prod_rgba.convert("RGB")
    prod_np = np.array(prod_rgb).astype(np.float32)
    prod_lum = prod_np.mean() + 1e-6

    ratio = float(patch_lum / prod_lum)
    ratio = max(0.90, min(1.08, ratio))  # 아주 좁게 제한

    out = ImageEnhance.Brightness(prod_rgba).enhance(ratio)
    return out


def _place_coords(bw: int, bh: int, pw: int, ph: int, placement: str, margin_ratio: float):
    mw = int(bw * margin_ratio)
    mh = int(bh * margin_ratio)

    if placement == "table_center":
        x = (bw - pw) // 2
        y = int(bh * 0.68)  # 테이블 위
        y = min(y, bh - ph - mh)
        return x, y
    elif placement == "bottom_center":
        x = (bw - pw) // 2
        y = bh - ph - mh
        return x, y
    elif placement == "bottom_right":
        x = bw - pw - mw
        y = bh - ph - mh
        return x, y
    elif placement == "bottom_left":
        x = mw
        y = bh - ph - mh
        return x, y

    raise ValueError(f"Unknown placement: {placement}")


def composite_product_on_background(
    background_path: str,
    product_rgba: Image.Image,
    out_path: str,
    placement: str = "table_center",
    scale_ratio: float = 0.40,
    margin_ratio: float = 0.06,
    add_shadow: bool = True,
    shadow_offset: tuple[int, int] = (8, 12),
):
    """
    A 안정형(v2):
    - 제품 변형(rotate/tilt/squash) 금지
    - 그림자는 최소한으로만
    - 밝기만 아주 약하게 맞춤
    """
    bg = Image.open(background_path).convert("RGBA")
    bw, bh = bg.size

    # 1) 스케일 (원본 비율 유지)
    pw0, ph0 = product_rgba.size
    target = int(min(bw, bh) * scale_ratio)
    long_side = max(pw0, ph0)
    scale = target / max(1, long_side)
    new_size = (max(1, int(pw0 * scale)), max(1, int(ph0 * scale)))
    prod = product_rgba.resize(new_size, Image.Resampling.LANCZOS)

    # 2) 위치
    x, y = _place_coords(bw, bh, prod.size[0], prod.size[1], placement, margin_ratio)

    # 3) 밝기만 미세 매칭
    prod = _match_brightness_only(bg, prod, x, y)

    # 4) 그림자(최소)
    if add_shadow:
        alpha = _extract_alpha_mask(prod)
        contact_rgba, ambient_rgba = _make_shadow_layers(alpha)

        sx, sy = shadow_offset
        bg.alpha_composite(ambient_rgba, (x + sx, y + sy))
        bg.alpha_composite(contact_rgba, (x + sx, y + sy))

    # 5) 합성
    bg.alpha_composite(prod, (x, y))
    bg.save(out_path)
    return out_path