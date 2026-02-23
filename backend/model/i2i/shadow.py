from PIL import Image, ImageDraw, ImageFilter


def add_contact_shadow(base_rgba: Image.Image,
                       product_rgba: Image.Image,
                       position: tuple[int, int]) -> Image.Image:
    """
    광고용 기본 접촉 그림자:
    - 다이얼 하단 접촉부 중심으로 좁게/진하게
    """
    x, y = position
    w, h = product_rgba.size

    shadow = Image.new("RGBA", base_rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow)

    # 다이얼 하단 중심의 얇은 타원 그림자
    shadow_box = (
        x + int(w * 0.28),
        y + int(h * 0.70),
        x + int(w * 0.72),
        y + int(h * 0.84),
    )
    draw.ellipse(shadow_box, fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=3.0))

    return Image.alpha_composite(base_rgba, shadow)