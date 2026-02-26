"""
LLM 서비스 모듈

OpenAI API를 사용하여 제품 마케팅 카피를 생성합니다.
"""

import base64
import json
import logging
import os
from typing import Dict, List

from openai import OpenAI

# 로깅 설정
logger = logging.getLogger(__name__)


class LLMService:
    """
    LLM을 사용한 마케팅 카피 생성 서비스
    
    OpenAI API를 활용하여 제품명, 키워드, 톤을 기반으로
    한국어 마케팅 카피를 생성합니다.
    """
    
    def __init__(self, api_key: str | None = None, model: str = "gpt-5-mini"):
        """
        LLMService 초기화
        
        Args:
            api_key: OpenAI API 키 (None일 경우 환경변수에서 로드)
            model: 사용할 OpenAI 모델명
            
        Raises:
            ValueError: API 키가 제공되지 않았을 때
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API 키가 필요합니다. "
                "api_key 파라미터로 전달하거나 OPENAI_API_KEY 환경변수를 설정하세요."
            )
        
        self.model = model
        self.client = OpenAI(api_key=self.api_key)
        logger.info(f"LLMService 초기화 완료 (모델: {self.model})")
    
    def generate_copy(
        self,
        product_name: str,
        keywords: List[str],
        tone: str,
        max_retries: int = 3
    ) -> Dict[str, str]:
        """
        마케팅 카피 생성
        
        Args:
            product_name: 제품명
            keywords: 제품 관련 키워드 리스트
            tone: 원하는 톤 (예: "모던한", "따뜻한", "럭셔리한")
            max_retries: JSON 파싱 실패 시 최대 재시도 횟수
            
        Returns:
            Dict[str, str]: {"main_copy": "메인 카피", "sub_copy": "서브 카피"}
            
        Raises:
            Exception: API 호출 실패 또는 최대 재시도 초과 시
        """
        logger.info(
            f"카피 생성 시작 - 제품: {product_name}, "
            f"키워드: {keywords}, 톤: {tone}"
        )
        
        # 시스템 프롬프트
        system_prompt = """당신은 전문 한국어 카피라이터입니다.
제품명, 키워드, 톤을 기반으로 광고 배너용 마케팅 카피를 작성합니다.

반드시 다음 JSON 형식으로만 응답하세요:
{
  "main_copy": "메인 카피 (20자 이하)",
  "sub_copy": "서브 카피 (40자 이하)"
}

규칙:
- main_copy는 20자 이하로 임팩트 있게
- sub_copy는 40자 이하로 제품의 핵심 가치 전달
- 주어진 톤에 맞는 표현 사용
- JSON 형식 외 다른 텍스트 포함 금지"""

        # 사용자 프롬프트
        keywords_str = ", ".join(keywords)
        user_prompt = f"""제품명: {product_name}
키워드: {keywords_str}
톤: {tone}

위 정보를 바탕으로 광고 배너용 마케팅 카피를 생성해주세요."""

        # 재시도 로직
        for attempt in range(max_retries):
            try:
                # OpenAI API 호출
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=1.0
                )
                
                content = response.choices[0].message.content.strip()
                logger.debug(f"LLM 응답: {content}")
                
                # JSON 파싱
                result = json.loads(content)
                
                # 필수 키 검증
                if "main_copy" not in result or "sub_copy" not in result:
                    raise ValueError("응답에 main_copy 또는 sub_copy가 없습니다.")
                
                # 길이 검증
                main_copy = result["main_copy"]
                sub_copy = result["sub_copy"]
                
                if len(main_copy) > 20:
                    logger.warning(
                        f"main_copy가 20자를 초과합니다 ({len(main_copy)}자). "
                        "재시도합니다."
                    )
                    if attempt < max_retries - 1:
                        continue
                
                if len(sub_copy) > 40:
                    logger.warning(
                        f"sub_copy가 40자를 초과합니다 ({len(sub_copy)}자). "
                        "재시도합니다."
                    )
                    if attempt < max_retries - 1:
                        continue
                
                logger.info(
                    f"카피 생성 완료 - "
                    f"메인: '{main_copy}', 서브: '{sub_copy}'"
                )
                
                return {
                    "main_copy": main_copy,
                    "sub_copy": sub_copy
                }
                
            except json.JSONDecodeError as e:
                logger.error(
                    f"JSON 파싱 실패 (시도 {attempt + 1}/{max_retries}): {e}"
                )
                if attempt == max_retries - 1:
                    raise Exception(
                        f"JSON 파싱 실패: {max_retries}회 재시도 후에도 "
                        f"유효한 응답을 받지 못했습니다."
                    ) from e
            
            except Exception as e:
                logger.error(f"카피 생성 중 오류 발생: {e}")
                if attempt == max_retries - 1:
                    raise
        
        # 이 지점에 도달하면 안 됨 (안전장치)
        raise Exception("카피 생성 실패: 예상치 못한 오류")

    def generate_layout_copy(
        self,
        product_name: str,
        keywords: List[str],
        tone: str,
        max_retries: int = 3
    ) -> Dict[str, str]:
        """
        레이아웃 배너용 상세 카피 생성
        
        Args:
            product_name: 제품명
            keywords: 키워드 리스트
            tone: 톤
            max_retries: 재시도 횟수
            
        Returns:
            Dict[str, str]: {
                "brand_name": "브랜드명",
                "product_headline": "제품 헤드라인",
                "product_description": "상세 설명",
                "cta_text": "버튼 텍스트"
            }
        """
        logger.info(f"레이아웃 카피 생성 시작 - {product_name}")
        
        system_prompt = """당신은 전문 광고 카피라이터입니다.
제품명, 키워드, 톤을 기반으로 디스플레이 광고 배너에 들어갈 텍스트 요소를 작성합니다.

반드시 다음 JSON 형식으로만 응답하세요:
{
  "brand_name": "브랜드명 (영어 또는 한글, 10자 이내)",
  "product_headline": "제품 헤드라인 (20자 이내, 임팩트 있게)",
  "product_description": "제품 상세 설명 (60자 내외, 2-3문장, 핵심 가치 전달)",
  "cta_text": "행동 유도 버튼 (예: 구매하기, 더 알아보기, 열기 - 5자 이내)"
}

규칙:
- brand_name: 제품명에서 브랜드를 유추하거나 가상의 어울리는 브랜드명 생성
- product_headline: 제품명을 포함하거나 강조하는 짧은 문구
- product_description: 고객의 이득을 구체적으로 명시
- cta_text: 클릭을 유도하는 짧은 단어
- 모든 리턴값은 문자열이어야 함
- JSON 외 다른 텍스트 포함 금지"""

        keywords_str = ", ".join(keywords)
        user_prompt = f"""제품명: {product_name}
키워드: {keywords_str}
톤: {tone}

위 정보를 바탕으로 배너 광고 텍스트를 생성해주세요."""

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=1.0
                )
                
                content = response.choices[0].message.content.strip()
                logger.debug(f"LLM 응답(레이아웃): {content}")
                
                result = json.loads(content)
                
                required_keys = ["brand_name", "product_headline", "product_description", "cta_text"]
                if not all(k in result for k in required_keys):
                    raise ValueError(f"필수 키 누락: {required_keys} 중 일부가 없음")
                
                return result
                
            except Exception as e:
                logger.error(f"레이아웃 카피 생성 실패 (시도 {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    # 실패 시 기본값 반환
                    logger.warning("기본값으로 대체합니다.")
                    return {
                        "brand_name": "Premium Brand",
                        "product_headline": product_name,
                        "product_description": "최고의 품질과 디자인을 경험하세요. 당신의 라이프스타일을 업그레이드합니다.",
                        "cta_text": "자세히 보기"
                    }


    def analyze_image_scenarios(
        self,
        image_path: str,
        product_name: str,
        n: int = 3
    ) -> List[Dict[str, str]]:
        """
        Vision API를 사용하여 제품 이미지를 분석하고 광고 상황을 제안합니다.
        
        Args:
            image_path: 이미지 파일 경로
            product_name: 제품명
            n: 제안할 시나리오 개수
            
        Returns:
            List[Dict]: [{"scenario": "상황 설명", "prompt": "SDXL 프롬프트"}, ...]
        """
        logger.info(f"이미지 분석 및 시나리오 생성 요청 - {product_name}")
        
        try:
            # 이미지 읽기 및 인코딩
            with open(image_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
                
            system_prompt = """당신은 크리에이티브 디렉터이자 AI 프롬프트 엔지니어입니다.
제품 이미지를 분석하여 광고에 적합한 매력적인 상황(Context)을 기획해야 합니다.

[절대 규칙]
- 반드시 JSON 배열만 출력하세요. 다른 텍스트, 설명, 질문, 옵션 제안 등은 절대 포함하지 마세요.
- 이미지와 제품명이 다르게 느껴지더라도 질문하지 말고, 이미지에 보이는 제품을 기준으로 작업하세요.
- 이미지가 무엇이든 제품으로 간주하고 광고 시나리오를 만드세요.

중요 목표:
사용자가 "시계 이미지를 주면, 사람이 차고 있는 모습" 등을 원합니다.
하지만 ControlNet 없이 텍스트로만 이미지를 생성할 것이므로, **"제품의 시각적 외형"**을 프롬프트에 아주 상세하게 묘사해야 합니다.

요청사항:
0. **[중요] 단순한 스튜디오 촬영이나 배경색만 있는 이미지는 제안하지 마세요.** 역동적인 라이프스타일이나 감성적인 배경을 원합니다.
1. **제품 외형 묘사**: 색상, 재질, 형태, 끈(스트랩) 종류, 다이얼 특징 등을 상세한 영어 단어로 추출하세요. (예: black round dial, silver metal strap, minimalist design)
2. **자연스러운 상황**: 제품이 사용되는 자연스러운 순간을 포착하세요. (예: wearing on wrist while hiking, placed on a cafe table with coffee, business meeting context)
3. **통합 프롬프트**: "상황 묘사 + 제품 외형 묘사 + 고품질 태그"가 합쳐진 SDXL용 영문 프롬프트를 작성하세요.

출력 형식 (JSON 리스트만, 다른 텍스트 없이):
[
  {
    "scenario": "상황 설명 (한국어)",
    "prompt": "A close-up shot of a [Visual Description of Product] [Action/Context], cinematic lighting, professional photography, 4k, ..."
  },
  ...
]"""

            user_prompt = f"이 이미지는 '{product_name}'입니다. 이 제품의 외형을 상세히 묘사하고, 이를 포함하여 광고하기 좋은 상황 {n}가지를 제안해주세요. 반드시 JSON 배열만 출력하세요."

            response = self.client.chat.completions.create(
                model="gpt-5-mini",  # Vision 지원 모델
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{encoded_image}"
                                }
                            }
                        ]
                    }
                ],
                temperature=1.0  # 창의적인 결과 유도
            )
            print("테스트스트", response)
            content = response.choices[0].message.content
            
            print(f"\n[DEBUG] Vision API Raw Content (Start):\n{content}\n(End)\n", flush=True)

            if not content:
                print("[ERROR] Vision API Returned Empty Content!")
                raise ValueError("Vision API Returned Empty Content!")

            content = content.strip()
            # 마크다운 코드 블록 제거 (혹시 있을 경우)
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            # JSON 배열 추출 시도 (응답에 다른 텍스트가 섞여있을 경우 대비)
            import re
            json_match = re.search(r'\[[\s\S]*\]', content)
            if json_match:
                content = json_match.group(0)
                
            logger.debug(f"Vision 응답: {content}")
            
            try:
                scenarios = json.loads(content)
            except json.JSONDecodeError as je:
                print(f"[ERROR] JSON Decode Failed: {je}")
                print(f"[ERROR] Content causing failure:\n{content}")
                # 최후의 폴백: 기본 시나리오 반환
                logger.warning("JSON 파싱 실패 - 기본 시나리오로 대체합니다.")
                scenarios = [
                    {
                        "scenario": "도시 거리에서의 자연스러운 모습",
                        "prompt": f"A realistic photo of a {product_name} in an urban street setting, natural lighting, lifestyle photography, high detail, 4k, professional"
                    },
                    {
                        "scenario": "카페에서의 여유로운 순간",
                        "prompt": f"A close-up shot of a {product_name} on a modern cafe table with coffee, warm ambient lighting, bokeh background, professional photography, 4k"
                    },
                    {
                        "scenario": "자연 속 활동적인 장면",
                        "prompt": f"A dynamic shot of a {product_name} during outdoor hiking in a forest, natural sunlight, adventure lifestyle, professional photography, 4k"
                    }
                ]
                
            return scenarios
            
        except Exception as e:
            logger.error(f"이미지 분석 실패: {e}")
            print(f"\n[CRITICAL ERROR] Vision API 호출 중 치명적인 오류 발생:\n{e}\n")
            print("오류 분석을 위해 프로그램을 중단하고 에러 코드를 출력합니다.")
            raise e  # 에러를 숨기지 않고 상위로 전파

# 테스트 코드
if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 테스트
    try:
        service = LLMService()
        
        result = service.generate_copy(
            product_name="스마트워치 Pro",
            keywords=["건강", "스타일", "혁신"],
            tone="모던한"
        )
        
        print("\n=== 생성된 마케팅 카피 ===")
        print(f"메인 카피: {result['main_copy']}")
        print(f"서브 카피: {result['sub_copy']}")
        
    except Exception as e:
        print(f"오류 발생: {e}")
