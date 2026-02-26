import base64
from io import BytesIO
from PIL import Image

def b64_to_bytes(b64_str: str) -> bytes:
    return base64.b64decode(b64_str)

def convert_image_bytes(src_bytes:bytes, out_fmt: str) -> tuple[bytes, str]:
    mime_map = {"png":"image/png", "jpg":"image/jpeg", "jpeg":"image/jpeg"}
    save_fmt_map = {"png":"PNG", "jpg":"JPEG", "jpeg":"JPEG"}

    out_fmt = out_fmt.lower()
    mime = mime_map[out_fmt]
    save_fmt = save_fmt_map[out_fmt]

    img = Image.open(BytesIO(src_bytes))

    if save_fmt == "jpeg":
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            rgba = img.convert("RGBA")
            bg = Image.new("RGB", img.size, (255,255,255))
            bg.paste(rgba, mask=rgba.split()[-1])
            img = bg
        else:
            img = img.convert("RGB")
    out= BytesIO()
    if save_fmt == "JPEG":
        img.save(out, format=save_fmt, quality=95)
    else:
        img.save(out, format=save_fmt)
    return out.getvalue(),mime

def add_image_overlay(base_bytes:bytes, overlay_bytes: bytes,  scale: float = 0.25, opacity: float = 1.0,x_ratio:float=1.0, y_ratio: float=0.0, margin_px:int=0) -> bytes:

    scale = max(0.01, min(1.0, float(scale)))
    x_ratio = max(0.0, min(1.0, float(x_ratio)))
    y_ratio = max(0.0, min(1.0, float(y_ratio)))
    opacity = max(0.0, min(1.0, float(opacity)))
    margin_px = max(0, int(margin_px))


    base = Image.open(BytesIO(base_bytes)).convert("RGBA")
    overlay = Image.open(BytesIO(overlay_bytes)).convert("RGBA")

    W,H = base.size

    target_w = max(1, int(W * scale))
    ratio = target_w / max(1, overlay.size[0])
    target_h = max(1, int(overlay.size[1] * ratio))
    overlay = overlay.resize((target_w, target_h))

    if opacity < 1.0:
        r, g, b, a = overlay.split()
        a = a.point(lambda v: int(v * opacity))
        overlay.putalpha(a)

    ow, oh = overlay.size

    max_x = max(0, (W - ow) - margin_px * 2)
    max_y = max(0, (H - oh) - margin_px * 2)

    x = margin_px + int(max_x * x_ratio)
    y = margin_px + int(max_y * y_ratio)

    base.alpha_composite(overlay, (x,y))

    out = BytesIO()
    base.save(out, format="PNG")
    return out.getvalue()