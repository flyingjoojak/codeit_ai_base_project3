from pydantic import BaseModel
from typing import Optional, Literal

ControlType = Literal["canny", "softedge"]
ControlSource = Literal["product", "scene_reference"]

class ImageGenRequest(BaseModel):
    # input product image (img2img init)
    input_image_path: str

    # optional: 광고/포즈 레퍼런스 이미지 (있으면 컨트롤로 쓰기 좋음)
    scene_reference_image_path: Optional[str] = None

    # output
    output_path: str

    # prompts
    positive: str
    negative: str

    # generation params
    strength: float = 0.65
    guidance_scale: float = 6.0
    steps: int = 30

    # sizing (SDXL 기본 1024 권장)
    width: int = 768
    height: int = 768

    # controlnet
    control_type: ControlType = "canny"
    control_source: ControlSource = "product"  # "scene_reference" 추천(가능하면)
    control_image_path: Optional[str] = None   # 직접 컨트롤 이미지 제공 시

class ImageGenResult(BaseModel):
    output_path: str