# backend/model/t2t/plate_prompt_builder.py

from typing import Tuple


def _canonical_pose_for_anchor(anchor: str, occlusion_goal: str) -> str:
    """
    SDXL prompt에서 안정적으로 재현되는 짧은 포즈 템플릿.
    (긴 설명 금지: CLIP 77 토큰 제한 때문에)
    """
    sleeve = "rolled sleeve partially covering the upper wrist" if occlusion_goal == "sleeve_partial" else "sleeve slightly rolled back"

    if anchor == "wrist":
        return (
            "single forearm on table, wrist centered, "
            f"{sleeve}, "
            "hand relaxed, wrist unobstructed"
        )
    if anchor == "hand":
        return "hands on table, empty hands, no objects, clear insertion area"
    if anchor == "neck":
        return "neck and lower face crop below nose, no accessories, clear insertion area"
    return "clear insertion area, no accessories, no objects"


def build_plate_prompt(bp: dict):
    scene = bp.get("scene", {}) or {}
    anchor_spec = bp.get("anchor_spec", {}) or {}

    anchor = anchor_spec.get("anchor", "wrist")
    mood = scene.get("mood", "warm")

    mood_block = {
        "warm": "warm natural window light, soft shadows",
        "minimal": "soft daylight, neutral tone",
        "luxury": "cinematic soft key light",
        "clean": "bright clean daylight",
    }.get(mood, "warm natural window light")

    if anchor == "wrist":
        subject_block = (
            "real human forearm and wrist, "
            "close-up of forearm only, "
            "face out of frame or completely blurred, "
            "wrist centered and dominant, "
            "empty wrist (no watch, no bracelet), "
            "sleeve slightly rolled back"
        )
    else:
        subject_block = "real human hand and forearm, no visible face"

    prompt = (
        "photorealistic commercial photography, "
        "85mm lens, shallow depth of field, "
        f"{mood_block}, "
        f"{subject_block}, "
        "realistic skin texture, natural anatomy"
    )

    negative = (
        "watch, wristwatch, bracelet, jewelry, accessory, "
        "camera, phone, laptop, monitor, object in hand, "
        "3D render, CGI, mannequin, sculpture, "
        "full face portrait, face centered, headshot, "
        "text, watermark, logo, cartoon, anime, illustration"
    )

    return prompt, negative