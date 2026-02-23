from dataclasses import dataclass
from typing import Literal, List, Optional, Dict, Any

PlacementMode = Literal["worn", "held", "slot"]
InteractionLevel = Literal["high", "low"]
AdMode = Literal["commercial_lifestyle", "commercial_studio"]
RealismStrategy = Literal["composite_occlusion", "composite_light", "render_only"]
Mood = Literal["warm", "minimal", "luxury", "clean"]

@dataclass
class Scene:
    subject: str        # 짧은 시각 묘사만
    environment: str    # 짧은 시각 묘사만
    mood: Mood

@dataclass
class Blueprint:
    ad_mode: AdMode
    interaction_level: InteractionLevel
    placement_mode: PlacementMode
    realism_strategy: RealismStrategy

    scene: Scene

    size: List[int]          # [W, H]
    seed_plan: str           # "multi_seed_4"
    confidence: float        # 0.0~1.0
    user_summary: str        # 1~2문장, 짧게

    # 정책/제약(프롬프트에 섞지 않기 위해 분리)
    constraints: List[str]

    product_hint: Optional[str] = None
    keywords: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ad_mode": self.ad_mode,
            "interaction_level": self.interaction_level,
            "placement_mode": self.placement_mode,
            "realism_strategy": self.realism_strategy,
            "scene": {
                "subject": self.scene.subject,
                "environment": self.scene.environment,
                "mood": self.scene.mood,
            },
            "size": self.size,
            "seed_plan": self.seed_plan,
            "confidence": self.confidence,
            "user_summary": self.user_summary,
            "constraints": self.constraints,
            "product_hint": self.product_hint,
            "keywords": self.keywords or [],
        }