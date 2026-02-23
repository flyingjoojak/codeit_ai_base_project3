STAGE_A_BLUEPRINT_PROMPT = """
You generate an advertising image blueprint for a product using ONLY text.
Return ONLY valid JSON.

Goal:
- Generate a photorealistic commercial ad setup
- Also choose hyperparameters (hparams) for stable diffusion plate generation and 2D compositing.
- Prioritize automation and stability over perfection.

Constraints:
- Keep values within safe ranges (below).
- Do NOT output extra keys.
- Do NOT include commentary. JSON only.

SAFE RANGES:
plate.steps: integer 8..20
plate.cfg: float 4.5..8.0
plate.seed: integer 0..999999

composite.scale: float 0.85..1.20
composite.tilt_deg: integer -20..20
composite.pos_dx: integer -80..80
composite.pos_dy: integer -80..80
composite.occlusion_fade_ratio: float 0.10..0.28
composite.product_blur: float 0.0..1.2
composite.contrast: float 0.85..1.05
composite.color: float 0.85..1.10
composite.shadow_strength: integer 80..220
composite.shadow_blur: float 1.5..6.0

Blueprint rules:
- ad_mode should be "commercial_lifestyle"
- interaction_level default "high"
- placement_mode for watch should be "worn"
- realism_strategy: "composite_occlusion" or "composite_light"
- size: [768,768] unless strong reason

JSON schema:
{
  "ad_mode": "commercial_lifestyle",
  "interaction_level": "high",
  "placement_mode": "worn",
  "realism_strategy": "composite_occlusion",
  "scene": {
    "subject": "...",
    "environment": "...",
    "mood": "warm"
  },
  "size": [768,768],
  "product_hint": "...",
  "keywords": ["..."],
  "hparams": {
    "plate": { "steps": 12, "cfg": 6.5, "seed": 2100 },
    "composite": {
      "scale": 1.0, "tilt_deg": 8, "pos_dx": 0, "pos_dy": 0,
      "occlusion_fade_ratio": 0.18,
      "product_blur": 0.7, "contrast": 0.93, "color": 0.97,
      "shadow_strength": 170, "shadow_blur": 3.0
    }
  }
}

Input:
product_name: {product_name}
keywords: {keywords_csv}
product_hint: {product_hint}
"""