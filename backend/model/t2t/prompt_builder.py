from .schema import Blueprint
from .prompt_blocks import (
    QUALITY_BLOCK, LENS_BLOCK, LIGHTING_PRESETS, ACTION_PRESETS,
    INTERACTION_BLOCK, BASE_NEGATIVE
)

def build_prompt(bp: Blueprint) -> tuple[str, str]:
    lighting = LIGHTING_PRESETS.get(bp.scene.mood, LIGHTING_PRESETS["clean"])
    action = ACTION_PRESETS[bp.placement_mode]

    blocks = [
        QUALITY_BLOCK,
        bp.scene.subject,
        action,
        lighting,
        LENS_BLOCK,
        bp.scene.environment,
    ]

    if bp.interaction_level == "high":
        blocks.append(INTERACTION_BLOCK)

    prompt = ", ".join(blocks)

    negative = BASE_NEGATIVE
    if bp.placement_mode == "worn":
        negative += ", warped watch, distorted dial, bent strap, melted watch"

    return prompt, negative