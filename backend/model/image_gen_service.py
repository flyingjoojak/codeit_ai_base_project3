"""
이미지 생성 서비스 모듈

Stable Diffusion XL을 사용하여 톤에 맞는 배경 이미지를 생성합니다.
"""

import logging
from typing import Tuple

import torch
from diffusers import AutoPipelineForText2Image, AutoPipelineForImage2Image, AutoPipelineForInpainting, StableDiffusionXLControlNetPipeline, ControlNetModel
from PIL import Image, ImageChops
 

# 로깅 설정
logger = logging.getLogger(__name__)


class ImageGenService:
    """
    Stable Diffusion XL을 사용한 배경 이미지 생성 서비스
    
    GPU 최적화를 통해 효율적으로 배경 이미지를 생성합니다.
    """
    
    # 톤별 프롬프트 매핑
    TONE_PROMPTS = {
        "모던한": (
            "modern minimal interior, marble table, bright sunlight, "
            "clean background, professional photography, 4k"
        ),
        "따뜻한": (
            "cozy wooden table, warm lighting, soft bokeh, "
            "comfortable atmosphere, natural wood texture, 4k"
        ),
        "럭셔리한": (
            "luxury marble background, gold accents, elegant interior, "
            "premium quality, sophisticated lighting, 4k"
        ),
        "자연스러운": (
            "natural outdoor scene, greenery, soft daylight, "
            "organic background, peaceful atmosphere, 4k"
        ),
        "활기찬": (
            "vibrant colorful background, energetic atmosphere, "
            "bright colors, dynamic composition, 4k"
        ),
        "미니멀": (
            "minimalist background, simple composition, neutral colors, "
            "clean space, modern aesthetic, 4k"
        ),
    }
    
    # 기본 품질 태그
    QUALITY_TAGS = "best quality, photorealistic, high detail, professional"
    
    # 네거티브 프롬프트
    NEGATIVE_PROMPT = (
        "text, watermark, logo, signature, ugly, distorted, blurry, "
        "low quality, bad anatomy, deformed, artifacts, noise"
    )
    
    def __init__(
        self,
        model_id: str = "stabilityai/stable-diffusion-xl-base-1.0",
        device: str | None = None,
        use_fp16: bool = True
    ):
        """
        ImageGenService 초기화
        
        Args:
            model_id: Hugging Face 모델 ID
            device: 사용할 디바이스 ("cuda", "cpu" 등, None이면 자동 선택)
            use_fp16: float16 사용 여부 (VRAM 절약)
            
        Raises:
            RuntimeError: CUDA를 사용할 수 없을 때
        """
        # 디바이스 설정
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        if self.device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA를 사용할 수 없습니다. "
                "GPU 드라이버와 PyTorch CUDA 설치를 확인하세요."
            )
        
        logger.info(f"디바이스: {self.device}")
        
        # dtype 설정
        self.dtype = torch.float16 if use_fp16 and self.device == "cuda" else torch.float32
        logger.info(f"데이터 타입: {self.dtype}")
        
        # 파이프라인 로드
        logger.info(f"모델 로딩 중: {model_id}")
        self.pipe = AutoPipelineForText2Image.from_pretrained(
            model_id,
            torch_dtype=self.dtype,
            use_safetensors=True,
            variant="fp16" if use_fp16 else None
        )
        
        # GPU로 이동
        self.pipe = self.pipe.to(self.device)
        
        # 메모리 및 속도 최적화
        if self.device == "cuda":
            # xformers 사용 가능하면 활성화 (속도 + 메모리 최적화)
            try:
                self.pipe.enable_xformers_memory_efficient_attention()
                logger.info("xformers memory efficient attention 활성화")
            except Exception:
                # xformers 미설치 시 attention slicing으로 폴백
                self.pipe.enable_attention_slicing()
                logger.info("Attention slicing 활성화 (xformers 미설치)")
            
            # torch.compile은 Windows에서 Triton 미지원으로 사용 불가
            # Linux 환경에서는 아래 주석을 해제하면 ~20% 속도 향상 가능
            # try:
            #     self.pipe.unet = torch.compile(self.pipe.unet, mode="reduce-overhead")
            #     logger.info("torch.compile 적용 완료")
            # except Exception as e:
            #     logger.info(f"torch.compile 미적용: {e}")
        
        # Img2Img 파이프라인 (지연 로딩)
        self.img2img_pipe = None
        
        # Inpainting 파이프라인 (지연 로딩)
        self.inpainting_pipe = None
        
        # ControlNet 파이프라인 (지연 로딩)
        self.controlnet_pipe = None
        
        # Depth estimator (지연 로딩)
        self.depth_estimator = None
        
        logger.info("ImageGenService 초기화 완료")
    
    def generate_background(
        self,
        tone: str,
        size: Tuple[int, int] = (1024, 1024),
        num_inference_steps: int = 20,
        guidance_scale: float = 7.5
    ) -> Image.Image:
        """
        톤에 맞는 배경 이미지 생성
        
        Args:
            tone: 원하는 톤 (예: "모던한", "따뜻한")
            size: 생성할 이미지 크기 (width, height)
            num_inference_steps: 추론 스텝 수 (높을수록 품질 향상, 시간 증가)
            guidance_scale: 프롬프트 가이던스 강도 (높을수록 프롬프트에 충실)
            
        Returns:
            PIL.Image.Image: 생성된 배경 이미지
            
        Raises:
            ValueError: 지원하지 않는 톤일 때
            RuntimeError: 이미지 생성 실패 시
        """
        logger.info(f"배경 이미지 생성 시작 - 톤: {tone}, 크기: {size}")
        
        # 톤에 맞는 프롬프트 가져오기
        if tone not in self.TONE_PROMPTS:
            logger.warning(
                f"지원하지 않는 톤: {tone}. "
                f"사용 가능한 톤: {list(self.TONE_PROMPTS.keys())}"
            )
            # 기본 톤으로 폴백
            tone = "모던한"
            logger.info(f"기본 톤으로 변경: {tone}")
        
        base_prompt = self.TONE_PROMPTS[tone]
        
        # 최종 프롬프트 구성
        full_prompt = f"{base_prompt}, {self.QUALITY_TAGS}"
        
        logger.debug(f"프롬프트: {full_prompt}")
        logger.debug(f"네거티브 프롬프트: {self.NEGATIVE_PROMPT}")
        
        try:
            # 이미지 생성
            with torch.inference_mode():
                result = self.pipe(
                    prompt=full_prompt,
                    negative_prompt=self.NEGATIVE_PROMPT,
                    width=size[0],
                    height=size[1],
                    num_inference_steps=num_inference_steps,
                    guidance_scale=guidance_scale,
                    generator=torch.Generator(device=self.device).manual_seed(42)
                )
            
            image = result.images[0]
            logger.info(f"배경 이미지 생성 완료 - 크기: {image.size}")
            
            return image
            
        except Exception as e:
            logger.error(f"이미지 생성 중 오류 발생: {e}")
            raise RuntimeError(f"배경 이미지 생성 실패: {e}") from e
    
    def generate_background_from_product(
        self,
        product_image: Image.Image,
        tone: str,
        strength: float = 0.75,
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
        seed: int = 42
    ) -> Image.Image:
        """
        제품 이미지를 기반으로 자연스러운 배경 생성 (Img2Img)
        
        제품과 배경이 자연스럽게 어울리도록 AI가 배경을 재생성합니다.
        조명, 그림자, 색감이 제품과 조화롭게 생성됩니다.
        
        Args:
            product_image: 제품이 포함된 이미지 (배경 제거 후 흰 배경에 합성된 상태)
            tone: 원하는 톤 (예: "모던한", "따뜻한")
            strength: 변환 강도 (0.0~1.0)
                - 0.5: 배경만 살짝 변경
                - 0.75: 배경 크게 변경, 제품 유지 (권장)
                - 0.9: 전체 이미지 거의 재생성
            num_inference_steps: 추론 스텝 수
            guidance_scale: 프롬프트 가이던스 강도
            
        Returns:
            PIL.Image.Image: 자연스러운 배경이 추가된 이미지
            
        Raises:
            ValueError: 지원하지 않는 톤일 때
            RuntimeError: 이미지 생성 실패 시
        """
        logger.info(
            f"Img2Img 배경 생성 시작 - 톤: {tone}, "
            f"크기: {product_image.size}, strength: {strength}"
        )
        
        # Img2Img 파이프라인 로드 (지연 로딩)
        if self.img2img_pipe is None:
            logger.info("Img2Img 파이프라인 로딩 중...")
            self.img2img_pipe = AutoPipelineForImage2Image.from_pipe(self.pipe)
            logger.info("Img2Img 파이프라인 로딩 완료")
        
        # 톤에 맞는 프롬프트 가져오기
        if tone not in self.TONE_PROMPTS:
            logger.warning(
                f"지원하지 않는 톤: {tone}. "
                f"사용 가능한 톤: {list(self.TONE_PROMPTS.keys())}"
            )
            tone = "모던한"
            logger.info(f"기본 톤으로 변경: {tone}")
        
        base_prompt = self.TONE_PROMPTS[tone]
        
        # Img2Img 전용 프롬프트 (다양한 상황 생성)
        full_prompt = (
            f"professional product advertisement, {base_prompt}, "
            f"product in lifestyle scene, natural setting, "
            f"professional photography, studio lighting, soft shadows, "
            f"depth of field, bokeh background, {self.QUALITY_TAGS}"
        )
        
        # 제품 형태는 유지하되 배경과 조화롭게
        negative_prompt = (
            f"{self.NEGATIVE_PROMPT}, "
            "floating object, unrealistic placement, "
            "distorted product, deformed product, blurry product"
        )
        
        logger.debug(f"프롬프트: {full_prompt}")
        logger.debug(f"네거티브 프롬프트: {negative_prompt}")
        
        try:
            # RGB로 변환 (RGBA일 경우)
            if product_image.mode == "RGBA":
                rgb_image = Image.new("RGB", product_image.size, (255, 255, 255))
                rgb_image.paste(product_image, mask=product_image.split()[3])
                product_image = rgb_image
            
            # Img2Img 생성
            with torch.inference_mode():
                result = self.img2img_pipe(
                    prompt=full_prompt,
                    negative_prompt=negative_prompt,
                    image=product_image,
                    strength=strength,
                    num_inference_steps=num_inference_steps,
                    guidance_scale=guidance_scale,
                    generator=torch.Generator(device=self.device).manual_seed(seed)
                )
            
            image = result.images[0]
            logger.info(f"Img2Img 배경 생성 완료 - 크기: {image.size}")
            
            return image
            
        except Exception as e:
            logger.error(f"Img2Img 생성 중 오류 발생: {e}")
            raise RuntimeError(f"Img2Img 배경 생성 실패: {e}") from e
    
    def generate_background_inpainting(
        self,
        product_image: Image.Image,
        product_mask: Image.Image,
        tone: str,
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5
    ) -> Image.Image:
        """
        Inpainting 방식으로 배경 생성 (제품 영역 보호)
        
        제품 영역을 마스크로 보호하고 배경 부분만 AI로 채웁니다.
        제품이 일그러지지 않고 원본 그대로 유지됩니다.
        
        Args:
            product_image: 제품이 포함된 이미지 (흰 배경에 합성된 상태)
            product_mask: 제품 영역 마스크 (흰색=제품, 검은색=배경)
            tone: 원하는 톤
            num_inference_steps: 추론 스텝 수
            guidance_scale: 프롬프트 가이던스 강도
            
        Returns:
            PIL.Image.Image: 배경이 생성된 이미지 (제품은 원본 유지)
            
        Raises:
            ValueError: 지원하지 않는 톤일 때
            RuntimeError: 이미지 생성 실패 시
        """
        logger.info(
            f"Inpainting 배경 생성 시작 - 톤: {tone}, "
            f"크기: {product_image.size}"
        )
        
        # Inpainting 파이프라인 로드 (지연 로딩)
        if self.inpainting_pipe is None:
            logger.info("Inpainting 파이프라인 로딩 중...")
            self.inpainting_pipe = AutoPipelineForInpainting.from_pipe(self.pipe)
            logger.info("Inpainting 파이프라인 로딩 완료")
        
        # 톤에 맞는 프롬프트 가져오기
        if tone not in self.TONE_PROMPTS:
            logger.warning(
                f"지원하지 않는 톤: {tone}. "
                f"사용 가능한 톤: {list(self.TONE_PROMPTS.keys())}"
            )
            tone = "모던한"
            logger.info(f"기본 톤으로 변경: {tone}")
        
        base_prompt = self.TONE_PROMPTS[tone]
        
        # Inpainting 전용 프롬프트
        full_prompt = (
            f"product photography background, {base_prompt}, "
            f"professional studio lighting, natural shadows, "
            f"depth of field, seamless integration, {self.QUALITY_TAGS}"
        )
        
        # 네거티브 프롬프트
        negative_prompt = (
            f"{self.NEGATIVE_PROMPT}, "
            "product in background, duplicate product, "
            "visible seams, unnatural edges"
        )
        
        logger.debug(f"프롬프트: {full_prompt}")
        logger.debug(f"네거티브 프롬프트: {negative_prompt}")
        
        try:
            # RGB로 변환
            if product_image.mode == "RGBA":
                rgb_image = Image.new("RGB", product_image.size, (255, 255, 255))
                rgb_image.paste(product_image, mask=product_image.split()[3])
                product_image = rgb_image
            
            # 마스크 반전 (Inpainting은 검은색 영역을 채움)
            # 현재: 흰색=제품, 검은색=배경
            # 필요: 검은색=제품(보호), 흰색=배경(채울 영역)
            inverted_mask = ImageChops.invert(product_mask.convert("L"))
            
            # Inpainting 실행
            with torch.inference_mode():
                result = self.inpainting_pipe(
                    prompt=full_prompt,
                    negative_prompt=negative_prompt,
                    image=product_image,
                    mask_image=inverted_mask,
                    width=product_image.size[0],  # 입력 이미지 너비 유지
                    height=product_image.size[1],  # 입력 이미지 높이 유지
                    num_inference_steps=num_inference_steps,
                    guidance_scale=guidance_scale,
                    generator=torch.Generator(device=self.device).manual_seed(42)
                )
            
            image = result.images[0]
            logger.info(f"Inpainting 배경 생성 완료 - 크기: {image.size}")
            
            return image
            
        except Exception as e:
            logger.error(f"Inpainting 생성 중 오류 발생: {e}")
            raise RuntimeError(f"Inpainting 배경 생성 실패: {e}") from e
    
    def get_available_tones(self) -> list[str]:
        """
        사용 가능한 톤 목록 반환
        
        Returns:
            list[str]: 톤 목록
        """
        return list(self.TONE_PROMPTS.keys())
    
    def generate_with_controlnet_depth(
        self,
        product_image: Image.Image,
        tone: str,
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
        controlnet_conditioning_scale: float = 0.8,
        seed: int = 42,
        width: int | None = None,
        height: int | None = None
    ) -> Image.Image:
        """
        ControlNet + Depth map을 사용하여 자연스러운 광고 이미지 생성
        
        제품의 깊이 정보를 추출하여 다양한 각도와 배경을 가진 이미지를 생성합니다.
        
        Args:
            product_image: 제품이 포함된 이미지
            tone: 원하는 톤
            num_inference_steps: 추론 스텝 수
            guidance_scale: 프롬프트 가이던스 강도
            controlnet_conditioning_scale: ControlNet 영향력 (0.0~1.0)
            seed: 랜덤 시드
            width: 생성할 이미지 너비 (None이면 원본 크기)
            height: 생성할 이미지 높이 (None이면 원본 크기)
            
        Returns:
            PIL.Image.Image: 생성된 광고 이미지
        """
        logger.info(
            f"ControlNet + Depth 생성 시작 - 톤: {tone}, "
            f"크기: {product_image.size}, seed: {seed}"
        )
        
        # Depth estimator 로드 (지연 로딩)
        if self.depth_estimator is None:
            logger.info("Depth estimator 로딩 중...")
            self.depth_estimator = MidasDetector.from_pretrained("lllyasviel/Annotators")
            logger.info("Depth estimator 로딩 완료")
        
        # ControlNet 파이프라인 로드 (지연 로딩)
        if self.controlnet_pipe is None:
            logger.info("ControlNet 파이프라인 로딩 중...")
            
            # ControlNet 모델 로드
            controlnet = ControlNetModel.from_pretrained(
                "diffusers/controlnet-depth-sdxl-1.0",
                torch_dtype=self.dtype,
                use_safetensors=True
            )
            
            # ControlNet 파이프라인 생성
            self.controlnet_pipe = StableDiffusionXLControlNetPipeline.from_pretrained(
                "stabilityai/stable-diffusion-xl-base-1.0",
                controlnet=controlnet,
                torch_dtype=self.dtype,
                use_safetensors=True,
                variant="fp16" if self.dtype == torch.float16 else None
            )
            
            # GPU로 이동
            self.controlnet_pipe = self.controlnet_pipe.to(self.device)
            
            # 메모리 최적화
            if self.device == "cuda":
                self.controlnet_pipe.enable_attention_slicing()
            
            logger.info("ControlNet 파이프라인 로딩 완료")
        
        # 톤에 맞는 프롬프트 가져오기
        if tone not in self.TONE_PROMPTS:
            logger.warning(
                f"지원하지 않는 톤: {tone}. "
                f"사용 가능한 톤: {list(self.TONE_PROMPTS.keys())}"
            )
            tone = "모던한"
            logger.info(f"기본 톤으로 변경: {tone}")
        
        base_prompt = self.TONE_PROMPTS[tone]
        
        # ControlNet 전용 프롬프트
        full_prompt = (
            f"professional product advertisement, {base_prompt}, "
            f"product in lifestyle scene, natural setting, "
            f"professional photography, studio lighting, soft shadows, "
            f"depth of field, bokeh background, {self.QUALITY_TAGS}"
        )
        
        negative_prompt = (
            f"{self.NEGATIVE_PROMPT}, "
            "floating object, unrealistic placement, "
            "distorted product, deformed product, blurry product"
        )
        
        logger.debug(f"프롬프트: {full_prompt}")
        logger.debug(f"네거티브 프롬프트: {negative_prompt}")
        
        try:
            # RGB로 변환
            if product_image.mode == "RGBA":
                rgb_image = Image.new("RGB", product_image.size, (255, 255, 255))
                rgb_image.paste(product_image, mask=product_image.split()[3])
                product_image = rgb_image
            
            # Depth map 생성
            logger.info("Depth map 생성 중...")
            depth_map = self.depth_estimator(product_image)
            logger.info(f"Depth map 생성 완료 - 크기: {depth_map.size}")
            
            # ControlNet으로 이미지 생성
            logger.info("ControlNet으로 이미지 생성 중...")
            
            # 원본 이미지 크기 및 타겟 크기 설정
            orig_w, orig_h = product_image.size
            target_w = width if width is not None else orig_w
            target_h = height if height is not None else orig_h
            
            with torch.inference_mode():
                result = self.controlnet_pipe(
                    prompt=full_prompt,
                    negative_prompt=negative_prompt,
                    image=depth_map,
                    num_inference_steps=num_inference_steps,
                    guidance_scale=guidance_scale,
                    controlnet_conditioning_scale=controlnet_conditioning_scale,
                    width=target_w,
                    height=target_h,
                    generator=torch.Generator(device=self.device).manual_seed(seed)
                )
            
            image = result.images[0]
            
            # 요청한 크기와 다를 경우 (사실 파이프라인이 맞춰주지만 안전장치)
            if image.size != (target_w, target_h):
                logger.info(f"이미지 크기 조정: {image.size} -> ({target_w}, {target_h})")
                image = image.resize((target_w, target_h), Image.LANCZOS)
                
            logger.info(f"ControlNet 이미지 생성 완료 - 크기: {image.size}")
            
            return image
            
        except Exception as e:
            logger.error(f"ControlNet 생성 중 오류 발생: {e}")
    
    def generate_creative(
        self,
        product_image: Image.Image,
        prompt: str,
        negative_prompt: str = None,
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
        controlnet_conditioning_scale: float = 0.4,
        seed: int = 42,
        width: int | None = None,
        height: int | None = None,
        use_controlnet: bool = False
    ) -> Image.Image:
        """
        사용자 정의 프롬프트와 약한 ControlNet을 사용하여 창의적인 광고 이미지 생성
        
        Args:
            product_image: 제품 이미지 (ControlNet 입력용, use_controlnet=True일 때만 사용)
            prompt: 생성할 이미지에 대한 상세 프롬프트 (Vision API 생성 등)
            negative_prompt: 네거티브 프롬프트 (None이면 기본값 사용)
            num_inference_steps: 추론 스텝 수
            guidance_scale: 프롬프트 가이던스 강도
            controlnet_conditioning_scale: ControlNet 영향력 (낮을수록 창의적, 높을수록 제품 형태 유지)
            seed: 랜덤 시드
            use_controlnet: ControlNet 사용 여부 (False면 Pure Text2Image)
            
        Returns:
            PIL.Image.Image: 생성된 이미지
        """
        logger.info(
            f"크리에이티브 이미지 생성 시작 - 프롬프트 짧게: {prompt[:30]}..., "
            f"ControlNet: {use_controlnet}"
        )
        
        # 기본 네거티브 프롬프트 병합
        full_negative_prompt = self.NEGATIVE_PROMPT
        if negative_prompt:
            full_negative_prompt = f"{full_negative_prompt}, {negative_prompt}"
            
        # 프롬프트 보강 (품질 태그 추가)
        full_prompt = f"{prompt}, {self.QUALITY_TAGS}"
        
        # 크기 설정 (기본값 또는 지정값)
        if width is None or height is None:
            if product_image:
                orig_w, orig_h = product_image.size
                target_w = width if width is not None else orig_w
                target_h = height if height is not None else orig_h
            else:
                target_w, target_h = 1024, 1024
        else:
             target_w, target_h = width, height

        try:
            # 1. ControlNet 모드 (형태 유지 필요 시)
            if use_controlnet:
                # Depth estimator 로드
                if self.depth_estimator is None:
                    self.depth_estimator = MidasDetector.from_pretrained("lllyasviel/Annotators")
                
                # ControlNet 파이프라인 로드
                if self.controlnet_pipe is None:
                    controlnet = ControlNetModel.from_pretrained(
                        "diffusers/controlnet-depth-sdxl-1.0",
                        torch_dtype=self.dtype,
                        use_safetensors=True
                    )
                    self.controlnet_pipe = StableDiffusionXLControlNetPipeline.from_pretrained(
                        "stabilityai/stable-diffusion-xl-base-1.0",
                        controlnet=controlnet,
                        torch_dtype=self.dtype,
                        use_safetensors=True,
                        variant="fp16" if self.dtype == torch.float16 else None
                    )
                    self.controlnet_pipe = self.controlnet_pipe.to(self.device)
                    if self.device == "cuda":
                        self.controlnet_pipe.enable_attention_slicing()
                
                # RGB 변환
                if product_image.mode == "RGBA":
                    rgb_image = Image.new("RGB", product_image.size, (255, 255, 255))
                    rgb_image.paste(product_image, mask=product_image.split()[3])
                    product_image = rgb_image
                
                # Depth map 생성
                depth_map = self.depth_estimator(product_image)
                
                # 생성
                with torch.inference_mode():
                    result = self.controlnet_pipe(
                        prompt=full_prompt,
                        negative_prompt=full_negative_prompt,
                        image=depth_map,
                        num_inference_steps=num_inference_steps,
                        guidance_scale=guidance_scale,
                        controlnet_conditioning_scale=controlnet_conditioning_scale,
                        width=target_w,
                        height=target_h,
                        generator=torch.Generator(device=self.device).manual_seed(seed)
                    )
            
            # 2. Text2Image 모드 (자유로운 구도 + 상세 묘사 프롬프트)
            else:
                # self.pipe 사용 (AutoPipelineForText2Image)
                with torch.inference_mode():
                    result = self.pipe(
                        prompt=full_prompt,
                        negative_prompt=full_negative_prompt,
                        width=target_w,
                        height=target_h,
                        num_inference_steps=num_inference_steps,
                        guidance_scale=guidance_scale,
                        generator=torch.Generator(device=self.device).manual_seed(seed)
                    )

            image = result.images[0]
            
            # 리사이징
            if image.size != (target_w, target_h):
                image = image.resize((target_w, target_h), Image.LANCZOS)
                
            logger.info("크리에이티브 이미지 생성 완료")
            return image
            
        except Exception as e:
            logger.error(f"크리에이티브 생성 실패: {e}")
            raise RuntimeError(f"크리에이티브 생성 실패: {e}") from e


# 테스트 코드
if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 테스트
    try:
        print("ImageGenService 초기화 중...")
        service = ImageGenService()
        
        print(f"\n사용 가능한 톤: {service.get_available_tones()}")
        
        print("\n배경 이미지 생성 중...")
        image = service.generate_background(
            tone="모던한",
            size=(512, 512),  # 테스트용으로 작은 크기
            num_inference_steps=20  # 테스트용으로 적은 스텝
        )
        
        # 이미지 저장
        output_path = "test_background.png"
        image.save(output_path)
        print(f"\n생성된 이미지 저장: {output_path}")
        
    except Exception as e:
        print(f"오류 발생: {e}")
