from dataclasses import dataclass
from typing import List
from .schema import Blueprint

@dataclass
class Validation:
    ok: bool
    issues: List[str]

def stage_b_validate(bp: Blueprint) -> Validation:
    issues: List[str] = []

    # 1) user_summary: 짧고 사람이 읽을 수 있어야 함
    if not bp.user_summary or len(bp.user_summary.strip()) < 20:
        issues.append("1) user_summary가 너무 짧거나 없음")
    if len(bp.user_summary) > 180:
        issues.append("1) user_summary가 너무 김(180자 초과)")

    # 2) high 우선 정책 (low면 경고지만 치명은 아님)
    if bp.interaction_level not in ("high", "low"):
        issues.append("2) interaction_level 값 오류")
    elif bp.interaction_level == "low":
        issues.append("2) 기본 정책(high 우선)과 다름: low로 나옴")

    # 3) 자동화/방향성: high인데 render_only는 치명
    if bp.interaction_level == "high" and bp.realism_strategy == "render_only":
        issues.append("3) high인데 realism_strategy=render_only (치명)")

    # 4) closeup 고정 X, but 초점 힌트는 있어야 함 + subject 너무 길면 치명
    subj = (bp.scene.subject or "").strip()
    if len(subj) > 160:
        issues.append("4) scene.subject가 너무 김(160자 초과, 치명)")
    subj_l = subj.lower()
    if not any(k in subj_l for k in ["wrist", "hand", "product", "close", "spray", "wear", "wearing", "holding"]):
        issues.append("4) scene.subject에 초점 힌트가 약함(손목/손/제품/행동 등)")

    # 5) 광고 모드
    if bp.ad_mode not in ("commercial_lifestyle", "commercial_studio"):
        issues.append("5) ad_mode 광고 모드 아님(치명)")

    # 6) 자연스러움 전략: high면 최소 composite_light 이상
    if bp.interaction_level == "high" and bp.realism_strategy not in ("composite_occlusion", "composite_light"):
        issues.append("6) high인데 자연스러움 전략 부족(치명)")

    # environment 길이도 제한 (치명은 아니지만 안정성 위해 경고/실패 기준 가능)
    env = (bp.scene.environment or "").strip()
    if len(env) > 200:
        issues.append("6) scene.environment가 너무 김(200자 초과)")

    # ✅ 치명 항목만 ok를 false로 (A 재실행 트리거)
    fatal = any(
        msg.startswith(("1)", "3)", "4) scene.subject가", "5)", "6) high인데 자연스러움"))
        for msg in issues
    )
    return Validation(ok=not fatal, issues=issues)