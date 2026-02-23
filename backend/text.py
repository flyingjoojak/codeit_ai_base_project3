import os
import json
import argparse
from datetime import datetime
from PIL import Image, ImageFilter, ImageEnhance

import inspect

# -----------------------------
# t2t
# -----------------------------
# 너 프로젝트에서 쓰는 t2t 인터페이스에 맞춰 import 유지
# (이미 사용 중이던 함수명 기준)
from model.t2t import stage_b_generate_plate_blueprint
from model.t2t.plate_prompt_builder import build_plate_prompt

# -----------------------------
# i2i (plate 생성 + 합성 유틸)
# -----------------------------
from model.i2i.render_plate import render_plate
from model.i2i.rembg_utils import remove_background_to_rgba

from model.i2i.anchor import guess_wrist_roi_and_angle
from model.i2i.warp import fit_product_to_wrist_roi
from model.i2i.occlusion import apply_sleeve_occlusion
from model.i2i.shadow import add_contact_shadow


# =========================================================
# Utils
# =========================================================

def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def _dump_json(obj, title="JSON"):
    print(f"\n=== {title} ===")
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _open_rgba(path: str) -> Image.Image:
    return Image.open(path).convert("RGBA")


# =========================================================
# 광고 느낌을 위한 "고정" 블렌딩 (하이퍼파라미터 최소화)
# =========================================================

def _ad_blend_product(product_rgba: Image.Image) -> Image.Image:
    """
    제품이 plate보다 너무 선명/쨍하면 합성티가 나서
    광고 느낌을 위해 아주 약하게만 정리.
    """
    out = product_rgba.filter(ImageFilter.GaussianBlur(radius=0.6))
    out = ImageEnhance.Contrast(out).enhance(0.93)
    out = ImageEnhance.Color(out).enhance(0.97)
    return out


def _call_render_plate(render_fn, prompt: str, neg: str, out_path: str, seed: int, steps: int):
    """
    프로젝트마다 render_plate 시그니처가 달라도 동작하도록 안전 호출.
    - negative prompt 파라미터명이 다를 수 있음 (negative, neg, negative_prompt ...)
    - 아예 없을 수도 있음
    """
    sig = inspect.signature(render_fn)
    params = sig.parameters

    kwargs = {}

    # prompt 인자
    if "prompt" in params:
        kwargs["prompt"] = prompt
    else:
        # prompt가 첫 positional일 가능성
        # (아래 positional fallback에서 처리)
        pass

    # out_path 인자
    if "out_path" in params:
        kwargs["out_path"] = out_path
    elif "save_path" in params:
        kwargs["save_path"] = out_path
    elif "output_path" in params:
        kwargs["output_path"] = out_path

    # seed/steps 인자
    if "seed" in params:
        kwargs["seed"] = seed
    if "steps" in params:
        kwargs["steps"] = steps
    elif "num_inference_steps" in params:
        kwargs["num_inference_steps"] = steps
        
    if "cfg" in params:
        kwargs["cfg"] = cfg
    elif "guidance_scale" in params:
        kwargs["guidance_scale"] = cfg    

    # negative prompt 인자 (있으면 넣고, 없으면 스킵)
    for neg_name in ["negative_prompt", "negative", "neg", "negative_text", "negative_prompt_text"]:
        if neg_name in params:
            kwargs[neg_name] = neg
            break

    # 1) 키워드 호출 먼저 시도
    try:
        return render_fn(**kwargs)
    except TypeError:
        # 2) positional fallback: (prompt, neg?, out_path, seed, steps)
        args = []
        # prompt
        args.append(prompt)
        # negative가 파라미터에 있으면 두번째로
        has_neg = any(n in params for n in ["negative_prompt", "negative", "neg", "negative_text", "negative_prompt_text"])
        if has_neg:
            args.append(neg)
        # out_path / seed / steps는 있으면 뒤에 붙임
        args.append(out_path)
        if "seed" in params:
            args.append(seed)
        if "steps" in params or "num_inference_steps" in params:
            args.append(steps)
        return render_fn(*args)

# =========================================================
# B1: Plate 생성 (사람 손목/팔만)
# =========================================================

def generate_plate(product_hint: str, keywords: list[str], out_dir: str, seed: int, steps: int) -> str:
    _ensure_dir(out_dir)

    # blueprint는 설명용/로그용 (prompt는 build_plate_prompt가 짧게 안정적으로 생성)
    bp = stage_b_generate_plate_blueprint(product_hint=product_hint, keywords=keywords)
    _dump_json(bp, "Plate Blueprint(JSON)")

    prompt, neg = build_plate_prompt(bp)

    print("\n=== Plate Prompt ===")
    print(prompt)
    print("\n=== Plate Negative ===")
    print(neg)

    plate_path = os.path.join(out_dir, f"plate_seed{seed}.png")
    _call_render_plate(
        render_plate,
        prompt=prompt,
        neg=neg,
        out_path=plate_path,
        seed=seed,
        steps=steps
    )

    print("\n✅ plate saved:", plate_path)
    return plate_path


# =========================================================
# B2~B5: 제품 합성(광고용)
# =========================================================

def compose_watch_on_plate(
    plate_path: str,
    product_path: str,
    out_dir: str,
    save_debug: bool = True
) -> str:
    _ensure_dir(out_dir)

    # 1) load plate
    plate = _open_rgba(plate_path)

    # 2) 제품 배경 제거 → RGBA
    product_cutout = remove_background_to_rgba(product_path)

    if save_debug:
        dbg_prod = os.path.join(out_dir, "debug_product_cutout.png")
        product_cutout.save(dbg_prod)
        print("✅ debug saved:", dbg_prod)

    # 3) wrist ROI + angle 추정
    roi, angle = guess_wrist_roi_and_angle(plate)
    x, y, w, h = roi
    print("\n=== Wrist ROI ===", roi)
    print("=== Wrist angle(deg) ===", angle)

    # 4) ROI에 맞춰 제품 fit + 회전
    product_fitted = fit_product_to_wrist_roi(product_cutout, roi, angle_deg=angle)

    if save_debug:
        dbg_fit = os.path.join(out_dir, "debug_product_fitted.png")
        product_fitted.save(dbg_fit)
        print("✅ debug saved:", dbg_fit)

    # 5) 오클루전(스트랩 상단 자연스럽게 숨김)
    product_occluded = apply_sleeve_occlusion(product_fitted)

    if save_debug:
        dbg_occ = os.path.join(out_dir, "debug_product_occluded.png")
        product_occluded.save(dbg_occ)
        print("✅ debug saved:", dbg_occ)

    # 6) 광고 느낌 블렌딩(미세 블러 + 톤 다운)
    product_ready = _ad_blend_product(product_occluded)

    if save_debug:
        dbg_ready = os.path.join(out_dir, "debug_product_ready.png")
        product_ready.save(dbg_ready)
        print("✅ debug saved:", dbg_ready)

    # 7) 배치 위치(ROI 중심에 제품 중심)
    px = x + (w // 2) - (product_ready.size[0] // 2)
    py = y + (h // 2) - (product_ready.size[1] // 2)

    # 8) 접촉 그림자 먼저
    plate_shadowed = add_contact_shadow(
        base_rgba=plate,
        product_rgba=product_ready,
        position=(px, py),
    )

    # 9) 제품 합성
    out = plate_shadowed.copy()
    out.alpha_composite(product_ready, (px, py))

    out_path = os.path.join(out_dir, "final_ad.png")
    out.save(out_path)
    print("\n✅ final ad saved:", out_path)

    return out_path


# =========================================================
# CLI
# =========================================================

def parse_args():
    p = argparse.ArgumentParser("Ad Image End-to-End Runner (plate -> compose)")

    p.add_argument("--mode", type=str, default="full", choices=["plate", "compose", "full"])
    p.add_argument("--out_dir", type=str, default="backend/model/outputs/run")

    p.add_argument("--product_path", type=str, default="backend/model/inputs/product.png")
    p.add_argument("--plate_path", type=str, default="")

    p.add_argument("--seed", type=int, default=2100)
    p.add_argument("--steps", type=int, default=12)

    p.add_argument("--product_hint", type=str, default="minimal wooden wristwatch with brown leather strap")
    p.add_argument("--keywords", type=str, default="premium,warm,classic,minimal")

    p.add_argument("--no_debug", action="store_true")

    return p.parse_args()


def main():
    args = parse_args()
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]

    run_dir = os.path.join(args.out_dir, _ts())
    _ensure_dir(run_dir)

    print("\n==============================")
    print(" mode:", args.mode)
    print(" run_dir:", run_dir)
    print(" product_path:", args.product_path)
    print("==============================\n")

    debug = not args.no_debug

    if args.mode == "plate":
        generate_plate(
            product_hint=args.product_hint,
            keywords=keywords,
            out_dir=run_dir,
            seed=args.seed,
            steps=args.steps
        )
        return

    if args.mode == "compose":
        if not args.plate_path:
            raise ValueError("--mode compose 는 --plate_path 가 필요합니다.")
        compose_watch_on_plate(
            plate_path=args.plate_path,
            product_path=args.product_path,
            out_dir=run_dir,
            save_debug=debug
        )
        return

    # full
    plate_path = generate_plate(
        product_hint=args.product_hint,
        keywords=keywords,
        out_dir=run_dir,
        seed=args.seed,
        steps=args.steps
    )

    compose_watch_on_plate(
        plate_path=plate_path,
        product_path=args.product_path,
        out_dir=run_dir,
        save_debug=debug
    )


if __name__ == "__main__":
    main()