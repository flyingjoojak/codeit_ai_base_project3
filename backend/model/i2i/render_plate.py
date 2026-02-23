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

    print(f"[plate] device={device} dtype={dtype}")
    print("[plate] loading SDXL pipeline...")

    _PIPE = StableDiffusionXLPipeline.from_pretrained(
        settings.i2i_base_model,
        torch_dtype=dtype,
        use_safetensors=True,
    ).to(device)

    print("[plate] pipeline loaded.")
    return _PIPE

def render_plate(prompt: str, negative: str, out_path: str, seed: int = 2000, steps: int = 12, cfg: float = 6.5):
    pipe = _get_pipe()
    device = "cuda" if torch.cuda.is_available() else "cpu"

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    w, h = settings.gen_w, settings.gen_h

    print(f"[plate] render start {w}x{h} steps={steps} cfg={cfg} seed={seed}")
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
    img.save(out_path)
    print(f"[plate] saved -> {out_path} ({dt:.1f}s)")
    return out_path