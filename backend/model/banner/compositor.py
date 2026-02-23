from PIL import Image, ImageDraw, ImageFont
from model.banner.layout import LAYOUTS

def _fit_cover(img: Image.Image, w: int, h: int) -> Image.Image:
    iw, ih = img.size
    scale = max(w / iw, h / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    resized = img.resize((nw, nh))
    left = (nw - w) // 2
    top = (nh - h) // 2
    return resized.crop((left, top, left + w, top + h))

def _fit_contain(img: Image.Image, w: int, h: int) -> Image.Image:
    # contain: 비율 유지하며 박스 안에 모두 들어가게(레터박스 가능)
    iw, ih = img.size
    scale = min(w / iw, h / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    resized = img.resize((nw, nh))
    canvas = Image.new("RGB", (w, h), (255, 255, 255))
    left = (w - nw) // 2
    top = (h - nh) // 2
    canvas.paste(resized, (left, top))
    return canvas

def compose_banner(size_key: str, visual_path: str, headline: str, subline: str, cta: str) -> Image.Image:
    layout = LAYOUTS[size_key]
    canvas = Image.new("RGB", layout.canvas, (255, 255, 255))

    visual = Image.open(visual_path).convert("RGB")
    x, y, w, h = layout.image_box
    if size_key == "720x90":
        canvas.paste(_fit_contain(visual, w, h), (x, y))
    else:
        canvas.paste(_fit_cover(visual, w, h), (x, y))

    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()

    tx, ty = layout.text_origin
    draw.text((tx, ty), headline, font=font, fill=(0, 0, 0))
    draw.text((tx, ty + 18), subline, font=font, fill=(40, 40, 40))
    draw.text((tx, ty + 40), f"[ {cta} ]", font=font, fill=(0, 0, 0))
    return canvas
