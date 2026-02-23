import os
import time
import torch
from diffusers import StableDiffusionXLPipeline
from model.config import settings

_PIPE = None

def _get_pipe():
    global _PIPE
    if _PIPE is not None:
        return _PIPE

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    print(f"[i2i] device={device} dtype={dtype}")
    print("[i2i] loading SDXL pipeline...")

    _PIPE = StableDiffusionXLPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        torch_dtype=dtype,
        use_safetensors=True,
    ).to(device)

    print("[i2i] pipeline loaded.")
    return _PIPE

def render_background(prompt: str, negative: str, out_path: str, seed: int = 1000):
    pipe = _get_pipe()
    device = "cuda" if torch.cuda.is_available() else "cpu"

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    w, h = settings.gen_w, settings.gen_h
    steps = 12  # CPU 테스트용
    cfg = 6.5

    print(f"[i2i] render start: {w}x{h}, steps={steps}, cfg={cfg}, seed={seed}")
    t0 = time.time()

    gen = torch.Generator(device=device).manual_seed(seed)

    img = pipe(
        prompt=prompt,
        negative_prompt=negative,
        width=w,
        height=h,
        num_inference_steps=steps,
        guidance_scale=cfg,
        generator=gen,
    ).images[0]

    dt = time.time() - t0
    print(f"[i2i] render done in {dt:.1f}s. saving -> {out_path}")

    img.save(out_path)
    print("[i2i] saved.")
    return out_path