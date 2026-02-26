
import logging
import io
import time
import json
import base64
import os
import tempfile
from typing import Dict, List, Optional, Any

from PIL import Image

from .llm_service import LLMService
from .image_gen_service import ImageGenService
from .image_edit_service import ImageEditService

# 로깅 설정
logger = logging.getLogger(__name__)

class BannerGenerator:
    """
    크리에이티브 광고 배너 생성 워크플로우 관리자
    
    Vision API + SDXL Text2Image + Layout 합성을 통해 
    제품 광고 배너를 생성합니다.
    """
    
    def __init__(self):
        self.llm_service = LLMService()
        self.image_gen_service = ImageGenService()
        self.image_edit_service = ImageEditService()
        
        logger.info("BannerGenerator 초기화 완료")
        
    def process(
        self,
        image_file: bytes,
        product_name: str,
        keywords: List[str],
        tone: str,
        layout: str = "vertical",
        save_intermediate: bool = False,
        seed: int = 42
    ) -> Dict[str, Any]:
        """
        크리에이티브 광고 배너 생성 프로세스 실행
        
        Args:
            image_file: 제품 이미지 바이너리 데이터
            product_name: 제품명
            keywords: 키워드 리스트
            tone: 디자인 톤
            layout: 레이아웃 선택 ("vertical" = 세로형, "horizontal" = 가로형)
            save_intermediate: 중간 결과 저장 여부
            seed: 랜덤 시드
            
        Returns:
            Dict: 생성된 배너 정보 (final_image, main_image, copy_data, scenarios 등)
        """
        if layout not in ("vertical", "horizontal"):
            raise ValueError(f"지원하지 않는 레이아웃: {layout}. 'vertical' 또는 'horizontal'을 선택하세요.")
        
        logger.info("=" * 60)
        logger.info("크리에이티브 광고 생성 워크플로우 시작")
        logger.info(f"제품: {product_name}, 톤: {tone}, 레이아웃: {layout}, 시드: {seed}")
        logger.info("=" * 60)
        
        try:
            return self._process_creative_ad(image_file, product_name, seed, keywords, tone, layout)
        except Exception as e:
            logger.error(f"워크플로우 실행 중 오류 발생: {e}")
            raise e

    def pil_to_base64(self, img: Image.Image) -> str:
        if img is None:
            return None
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    

    def _process_creative_ad(self, image_file: bytes, product_name: str, seed: int, keywords: List[str] = None, tone: str = None, layout: str = "vertical") -> Dict[str, Any]:
        """
        상황 기반 크리에이티브 광고 생성 (Vision + Creative Gen + Layout)
        
        1. Vision API로 제품 분석 → 광고 시나리오 & 프롬프트 생성
        2. LLM으로 광고 카피 생성 (제목/본문/CTA)
        3. SDXL Text2Image로 크리에이티브 이미지 생성
        4. Layout 합성으로 최종 배너 조립
        """
        logger.info(f"크리에이티브 광고 생성 모드 진입 - {product_name}")
        
        # 이미지 로드
        image = Image.open(io.BytesIO(image_file)).convert("RGBA")
        
        # 임시 파일로 저장 (Vision API용)
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            rgb_image = image.convert("RGB")
            rgb_image.save(tmp.name)
            tmp_path = tmp.name
            
        try:
            # 1. Vision API로 상황 분석 및 프롬프트 생성
            logger.info("Vision API로 제품 분석 및 시나리오 생성 요청...")
            scenarios = self.llm_service.analyze_image_scenarios(tmp_path, product_name, n=1)
            logger.info(f"제안된 시나리오 {len(scenarios)}개")
            
            # 2. 카피 생성 (레이아웃용)
            copy_data = {}
            if keywords and tone:
                try:
                    logger.info("레이아웃 카피 생성 요청...")
                    if hasattr(self.llm_service, 'generate_layout_copy'):
                        copy_data = self.llm_service.generate_layout_copy(product_name, keywords, tone)
                        logger.info(f"카피 생성 완료: {copy_data}")
                    else:
                        logger.warning("generate_layout_copy 메서드가 없습니다.")
                        copy_data = {"brand_name": "BRAND", "product_headline": product_name, "cta_text": "Shop Now"}
                except Exception as e:
                    logger.warning(f"카피 생성 실패: {e}")
                    copy_data = {"brand_name": "BRAND", "product_headline": product_name, "cta_text": "Shop Now"}
            
            generated_images = []
            
            # 3. 각 시나리오별 이미지 생성
            for i, scenario in enumerate(scenarios):
                logger.info(f"[Scenario {i+1}] {scenario['scenario']}")
                prompt = scenario['prompt']
                
                # Creative Generation (Pure Text2Image based on Visual Description)
                gen_image = self.image_gen_service.generate_creative(
                    product_image=image,  
                    prompt=prompt,
                    controlnet_conditioning_scale=0.0,
                    seed=seed + i,
                    width=1024,
                    height=1024,
                    use_controlnet=False 
                )
                
                # 4. 레이아웃 합성 (선택된 레이아웃에 따라 분기)
                layout_image = None
                if copy_data:
                    try:
                        if layout == "horizontal":
                            layout_image = self.image_edit_service.compose_horizontal_ad(
                                product_image=gen_image,
                                text_data=copy_data,
                                output_size=(2000, 1000)
                            )
                        else:
                            layout_image = self.image_edit_service.compose_vertical_ad(
                                product_image=gen_image,
                                text_data=copy_data,
                                output_size=(1000, 2000)
                            )
                    except Exception as e:
                        logger.error(f"레이아웃 합성 실패: {e}")
                
                generated_images.append({
                    "scenario": scenario['scenario'],
                    "prompt": prompt,
                    "image": gen_image,
                    "layout_image": layout_image
                })
                
            if not generated_images:
                raise RuntimeError("이미지 생성 실패")
                
            main_result = generated_images[0]
            final_img = main_result['layout_image'] if main_result['layout_image'] else main_result['image']

            
            return {
                "final_image": self.pil_to_base64(final_img),
                "copy_data": copy_data
            }
            
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
