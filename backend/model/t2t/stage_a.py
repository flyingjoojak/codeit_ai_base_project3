import json
from typing import Optional, List
from openai import OpenAI
from .prompts import STAGE_A_BLUEPRINT_PROMPT

from model.config import settings
from .schema import Blueprint, Scene

client = OpenAI(api_key=settings.openai_api_key)

SYSTEM_BASE = """
You generate an execution BLUEPRINT for an ad image pipeline.
Return VALID JSON ONLY. No markdown, no commentary.

Hard rules:
- Do NOT output long step-by-step production plans.
- scene.subject must be visual description only (<= 160 chars).
- scene.environment must be visual description only (<= 200 chars).
- user_summary must be <= 180 chars (1-2 sentences).
- Default interaction_level: "high" unless clearly unsuitable.
- Keep ad_mode commercial.
- Put policies/guardrails into constraints[] (max 5 short strings).
- Do NOT include policies like "no text" inside scene.subject/environment.

Output schema:
{
  "ad_mode": "commercial_lifestyle"|"commercial_studio",
  "interaction_level": "high"|"low",
  "placement_mode": "worn"|"held"|"slot",
  "realism_strategy": "composite_occlusion"|"composite_light"|"render_only",
  "scene": {"subject": "...", "environment": "...", "mood": "warm|minimal|luxury|clean"},
  "constraints": ["..."],
  "size": [W,H],
  "seed_plan": "multi_seed_N",
  "confidence": 0.0-1.0,
  "user_summary": "..."
}
"""

SYSTEM_REPAIR = """
You are repairing an existing blueprint to satisfy validation issues.
Return VALID JSON ONLY. No markdown, no commentary.

Repair policy:
- Keep the same overall intent, ad_mode, placement_mode, interaction_level, realism_strategy, size, seed_plan.
- Do NOT change scene mood unless required.
- Fix ONLY what the issues demand.
- user_summary MUST be <= 180 chars.
- Keep scene.subject <= 160 chars and scene.environment <= 200 chars.
"""

def _client() -> OpenAI:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY가 .env에 없습니다.")
    return OpenAI(api_key=settings.openai_api_key)

def _to_blueprint(data: dict, product_hint: Optional[str], keywords: Optional[List[str]]) -> Blueprint:
    constraints = data.get("constraints") or []
    if not isinstance(constraints, list):
        constraints = []
    scene = Scene(
        subject=data["scene"]["subject"],
        environment=data["scene"]["environment"],
        mood=data["scene"]["mood"],
    )
    return Blueprint(
        ad_mode=data["ad_mode"],
        interaction_level=data["interaction_level"],
        placement_mode=data["placement_mode"],
        realism_strategy=data["realism_strategy"],
        scene=scene,
        constraints=constraints[:5],
        size=data["size"],
        seed_plan=data["seed_plan"],
        confidence=float(data["confidence"]),
        user_summary=data["user_summary"],
        product_hint=product_hint,
        keywords=keywords or [],
    )

def stage_a_generate_blueprint(product_name: str, product_hint: str, keywords: list[str]) -> dict:
    prompt = STAGE_A_BLUEPRINT_PROMPT.format(
        product_name=product_name,
        keywords_csv=",".join(keywords),
        product_hint=product_hint
    )

    resp = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": "Return ONLY valid JSON."},
            {"role": "user", "content": prompt},
        ],
        # temperature 넣지 마! (gpt-5-mini에서 에러났던 부분)
    )

    content = resp.choices[0].message.content
    return json.loads(content)


def stage_a_regenerate_blueprint(
    previous_blueprint: Blueprint,
    issues: List[str],
) -> Blueprint:
    """
    Validation 이슈를 반영해서 '같은 방향성'으로 blueprint를 다시 작성.
    (B는 수정하지 않고 A를 재실행한다는 정책 구현)
    """
    client = _client()

    repair_payload = {
        "previous_blueprint": previous_blueprint.to_dict(),
        "issues": issues,
        "hard_constraints": {
            "user_summary_max_chars": 180,
            "subject_max_chars": 160,
            "environment_max_chars": 200
        }
    }

    resp = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_REPAIR},
            {"role": "user", "content": json.dumps(repair_payload, ensure_ascii=False)},
        ],
    )

    data = json.loads(resp.choices[0].message.content)
    return _to_blueprint(data, previous_blueprint.product_hint, previous_blueprint.keywords)