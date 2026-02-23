def _clamp(x, lo, hi):
    return max(lo, min(hi, x))

def clamp_hparams(bp: dict) -> dict:
    hp = (bp.get("hparams") or {})
    plate = hp.get("plate") or {}
    comp = hp.get("composite") or {}

    # defaults (누락 방어)
    plate_steps = int(plate.get("steps", 12))
    plate_cfg = float(plate.get("cfg", 6.5))
    plate_seed = int(plate.get("seed", 2100))

    comp_scale = float(comp.get("scale", 1.0))
    comp_tilt = int(comp.get("tilt_deg", 8))
    comp_dx = int(comp.get("pos_dx", 0))
    comp_dy = int(comp.get("pos_dy", 0))
    comp_fade = float(comp.get("occlusion_fade_ratio", 0.18))
    comp_blur = float(comp.get("product_blur", 0.7))
    comp_contrast = float(comp.get("contrast", 0.93))
    comp_color = float(comp.get("color", 0.97))
    comp_shadow_strength = int(comp.get("shadow_strength", 170))
    comp_shadow_blur = float(comp.get("shadow_blur", 3.0))

    bp["hparams"] = {
        "plate": {
            "steps": int(_clamp(plate_steps, 8, 20)),
            "cfg": float(_clamp(plate_cfg, 4.5, 8.0)),
            "seed": int(_clamp(plate_seed, 0, 999999)),
        },
        "composite": {
            "scale": float(_clamp(comp_scale, 0.85, 1.20)),
            "tilt_deg": int(_clamp(comp_tilt, -20, 20)),
            "pos_dx": int(_clamp(comp_dx, -80, 80)),
            "pos_dy": int(_clamp(comp_dy, -80, 80)),
            "occlusion_fade_ratio": float(_clamp(comp_fade, 0.10, 0.28)),
            "product_blur": float(_clamp(comp_blur, 0.0, 1.2)),
            "contrast": float(_clamp(comp_contrast, 0.85, 1.05)),
            "color": float(_clamp(comp_color, 0.85, 1.10)),
            "shadow_strength": int(_clamp(comp_shadow_strength, 80, 220)),
            "shadow_blur": float(_clamp(comp_shadow_blur, 1.5, 6.0)),
        }
    }
    return bp