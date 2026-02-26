"""
이미지 편집 서비스 모듈

Rembg와 Pillow를 사용하여 이미지 처리 및 합성을 수행합니다.
"""

import io
import logging
from pathlib import Path
from typing import Tuple
import os
from PIL import Image, ImageDraw, ImageFont
from rembg import remove

# 로깅 설정
logger = logging.getLogger(__name__)


class ImageEditService:
    """
    이미지 처리 및 합성 서비스
    
    배경 제거, 이미지 합성, 텍스트 오버레이 기능을 제공합니다.
    """
    
    def __init__(self, font_path: str | None = None, font_size: int = 60):
        self.font_size = font_size
        """
        ImageEditService 초기화
        
        Args:
            font_path: 한글 폰트 파일 경로 (None이면 기본 폰트 사용)
            font_size: 기본 폰트 크기
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        default_font = os.path.join(base_dir, "assets", "NanumGothicBold.ttf")
        self.font_path = font_path or default_font
        self.font = self._load_font()
        
        logger.info("ImageEditService 초기화 완료")
    
    def _load_font(self) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """
        폰트 로드 (폴백 지원)
        
        Returns:
            ImageFont: 로드된 폰트 객체
        """
        try:
            font = ImageFont.truetype(self.font_path, self.font_size)
            logger.info(f"폰트 로드 성공: {self.font_path}")
            return font
        except Exception as e:
            logger.warning(
                f"폰트 로드 실패 ({self.font_path}): {e}. "
                "기본 폰트를 사용합니다."
            )
            # 기본 폰트로 폴백
            return ImageFont.load_default()
    
    def remove_background(self, image_data: bytes) -> Image.Image:
        """
        이미지 배경 제거
        
        Args:
            image_data: 원본 이미지 바이트 데이터
            
        Returns:
            PIL.Image.Image: 배경이 제거된 이미지 (RGBA)
            
        Raises:
            ValueError: 이미지 데이터가 유효하지 않을 때
            RuntimeError: 배경 제거 실패 시
        """
        logger.info("배경 제거 시작")
        
        try:
            # 이미지 로드
            input_image = Image.open(io.BytesIO(image_data))
            logger.debug(f"입력 이미지 크기: {input_image.size}, 모드: {input_image.mode}")
            
            # 배경 제거
            output_data = remove(image_data)
            output_image = Image.open(io.BytesIO(output_data))
            
            logger.info(f"배경 제거 완료 - 크기: {output_image.size}")
            
            return output_image
            
        except Exception as e:
            logger.error(f"배경 제거 중 오류 발생: {e}")
            raise RuntimeError(f"배경 제거 실패: {e}") from e
    
    def composite_image(
        self,
        background: Image.Image,
        product: Image.Image,
        product_scale: float = 0.65,
        position: str = "center-bottom",
        return_mask: bool = False
    ) -> Image.Image | tuple[Image.Image, Image.Image]:
        """
        제품 이미지를 배경에 합성
        
        Args:
            background: 배경 이미지
            product: 제품 이미지 (배경 제거된 RGBA)
            product_scale: 제품 이미지 크기 비율 (배경 높이 대비)
            position: 배치 위치 ("center-bottom", "center", "center-top")
            return_mask: True면 (합성이미지, 마스크) 튜플 반환
            
        Returns:
            PIL.Image.Image: 합성된 이미지
            또는 tuple[PIL.Image.Image, PIL.Image.Image]: (합성이미지, 전체 크기 마스크)
            
        Raises:
            ValueError: 잘못된 position 값
        """
        logger.info(
            f"이미지 합성 시작 - 배경: {background.size}, "
            f"제품: {product.size}, 위치: {position}"
        )
        
        # 배경을 RGB로 변환 (RGBA일 경우)
        if background.mode == "RGBA":
            bg = Image.new("RGB", background.size, (255, 255, 255))
            bg.paste(background, mask=background.split()[3])
            background = bg
        
        # 제품 이미지 크기 조정
        bg_width, bg_height = background.size
        target_height = int(bg_height * product_scale)
        
        # 비율 유지하며 리사이즈
        prod_width, prod_height = product.size
        scale_ratio = target_height / prod_height
        new_width = int(prod_width * scale_ratio)
        new_height = target_height
        
        product_resized = product.resize(
            (new_width, new_height),
            Image.Resampling.LANCZOS
        )
        
        logger.debug(f"제품 이미지 리사이즈: {product.size} -> {product_resized.size}")
        
        # 배치 위치 계산
        if position == "center-bottom":
            x = (bg_width - new_width) // 2
            y = bg_height - new_height - int(bg_height * 0.05)  # 하단 5% 여백
        elif position == "center":
            x = (bg_width - new_width) // 2
            y = (bg_height - new_height) // 2
        elif position == "center-top":
            x = (bg_width - new_width) // 2
            y = int(bg_height * 0.15)  # 상단 15% 위치
        else:
            raise ValueError(
                f"지원하지 않는 position: {position}. "
                "사용 가능: 'center-bottom', 'center', 'center-top'"
            )
        
        # 합성
        result = background.copy()
        
        # RGBA 이미지의 알파 채널을 마스크로 사용
        if product_resized.mode == "RGBA":
            result.paste(product_resized, (x, y), product_resized)
        else:
            result.paste(product_resized, (x, y))
        
        logger.info(f"이미지 합성 완료 - 제품 위치: ({x}, {y})")
        
        # 마스크 반환이 요청된 경우
        if return_mask:
            # 전체 크기의 빈 마스크 생성
            full_mask = Image.new("L", background.size, 0)
            
            # 제품 마스크 추출 및 리사이즈
            if product.mode == "RGBA":
                product_mask = product.split()[3]
                resized_mask = product_mask.resize(
                    (new_width, new_height),
                    Image.Resampling.LANCZOS
                )
                full_mask.paste(resized_mask, (x, y))
                logger.debug(f"마스크 생성 완료: {full_mask.size}")
            
            return result, full_mask
        
        return result
    
    def create_product_mask(self, product_image: Image.Image) -> Image.Image:
        """
        제품 이미지로부터 마스크 생성
        
        RGBA 이미지의 알파 채널을 사용하여 제품 영역 마스크를 생성합니다.
        
        Args:
            product_image: 배경 제거된 제품 이미지 (RGBA)
            
        Returns:
            PIL.Image.Image: 마스크 이미지 (L 모드, 흰색=제품, 검은색=배경)
            
        Raises:
            ValueError: RGBA 이미지가 아닐 때
        """
        logger.info("제품 마스크 생성 시작")
        
        if product_image.mode != "RGBA":
            raise ValueError(
                f"RGBA 이미지가 필요합니다. 현재 모드: {product_image.mode}"
            )
        
        # 알파 채널 추출
        alpha = product_image.split()[3]
        
        logger.info(f"마스크 생성 완료 - 크기: {alpha.size}")
        
        return alpha
    
    def create_edge_mask(
        self,
        product_mask: Image.Image,
        edge_width: int = 30
    ) -> Image.Image:
        """
        제품 경계 주변 마스크 생성 (Inpainting용)
        
        제품 경계 주변만 Inpainting하여 배경과 자연스럽게 블렌딩합니다.
        
        Args:
            product_mask: 제품 마스크 (흰색=제품, 검은색=배경)
            edge_width: 경계 폭 (픽셀)
            
        Returns:
            PIL.Image.Image: 경계 마스크 (흰색=Inpainting 영역, 검은색=보존 영역)
        """
        from scipy.ndimage import binary_dilation, binary_erosion
        import numpy as np
        
        logger.info(f"경계 마스크 생성 시작 - 경계 폭: {edge_width}px")
        
        # 마스크를 numpy 배열로 변환
        mask_arr = np.array(product_mask) > 128
        
        # 구조 요소 생성 (원형)
        iterations = edge_width // 2
        
        # 마스크 확장 (팽창)
        dilated = binary_dilation(mask_arr, iterations=iterations)
        
        # 마스크 축소 (침식)
        eroded = binary_erosion(mask_arr, iterations=iterations)
        
        # 확장 - 축소 = 경계 영역
        edge_arr = (dilated.astype(np.uint8) - eroded.astype(np.uint8)) * 255
        
        edge_mask = Image.fromarray(edge_arr, mode='L')
        
        logger.info(f"경계 마스크 생성 완료 - 크기: {edge_mask.size}")
        
        return edge_mask
    
    def add_text_overlay(
        self,
        image: Image.Image,
        main_text: str,
        sub_text: str,
        position: str = "top-center"
    ) -> Image.Image:
        """
        이미지에 텍스트 오버레이 추가
        
        Args:
            image: 대상 이미지
            main_text: 메인 카피 (큰 텍스트)
            sub_text: 서브 카피 (작은 텍스트)
            position: 텍스트 위치 ("top-center", "top-left", "bottom-center")
            
        Returns:
            PIL.Image.Image: 텍스트가 추가된 이미지
        """
        logger.info(
            f"텍스트 오버레이 추가 - "
            f"메인: '{main_text}', 서브: '{sub_text}', 위치: {position}"
        )
        
        # 이미지 복사
        result = image.copy()
        draw = ImageDraw.Draw(result)
        
        width, height = result.size
        
        # 폰트 설정
        try:
            main_font = ImageFont.truetype(self.font_path, int(self.font_size * 1.2))
            sub_font = ImageFont.truetype(self.font_path, int(self.font_size * 0.7))
        except:
            main_font = self.font
            sub_font = self.font
        
        # 텍스트 크기 계산
        main_bbox = draw.textbbox((0, 0), main_text, font=main_font)
        main_width = main_bbox[2] - main_bbox[0]
        main_height = main_bbox[3] - main_bbox[1]
        
        sub_bbox = draw.textbbox((0, 0), sub_text, font=sub_font)
        sub_width = sub_bbox[2] - sub_bbox[0]
        sub_height = sub_bbox[3] - sub_bbox[1]
        
        # 위치 계산
        margin = int(height * 0.05)  # 5% 여백
        text_spacing = 20  # 메인과 서브 텍스트 간격
        
        if position == "top-center":
            main_x = (width - main_width) // 2
            main_y = margin
            sub_x = (width - sub_width) // 2
            sub_y = main_y + main_height + text_spacing
        elif position == "top-left":
            main_x = margin
            main_y = margin
            sub_x = margin
            sub_y = main_y + main_height + text_spacing
        elif position == "bottom-center":
            total_height = main_height + text_spacing + sub_height
            main_x = (width - main_width) // 2
            main_y = height - total_height - margin
            sub_x = (width - sub_width) // 2
            sub_y = main_y + main_height + text_spacing
        else:
            # 기본값: top-center
            main_x = (width - main_width) // 2
            main_y = margin
            sub_x = (width - sub_width) // 2
            sub_y = main_y + main_height + text_spacing
        
        # 텍스트 외곽선 (가독성 향상)
        outline_color = "black"
        text_color = "white"
        outline_width = 3
        
        # 메인 텍스트 외곽선
        for adj_x in range(-outline_width, outline_width + 1):
            for adj_y in range(-outline_width, outline_width + 1):
                draw.text(
                    (main_x + adj_x, main_y + adj_y),
                    main_text,
                    font=main_font,
                    fill=outline_color
                )
        
        # 메인 텍스트
        draw.text((main_x, main_y), main_text, font=main_font, fill=text_color)
        
        # 서브 텍스트 외곽선
        for adj_x in range(-outline_width, outline_width + 1):
            for adj_y in range(-outline_width, outline_width + 1):
                draw.text(
                    (sub_x + adj_x, sub_y + adj_y),
                    sub_text,
                    font=sub_font,
                    fill=outline_color
                )
        
        # 서브 텍스트
        draw.text((sub_x, sub_y), sub_text, font=sub_font, fill=text_color)
        
        logger.info("텍스트 오버레이 추가 완료")
        
        return result
    
    def compose_vertical_ad(
        self,
        product_image: Image.Image,
        text_data: dict,
        output_size: Tuple[int, int] = (600, 1000)
    ) -> Image.Image:
        """
        세로형 광고 배너 템플릿 합성 (Bamboo Style)
        
        Args:
            product_image: 제품 이미지 (배경 제거 안 된 완성된 이미지 권장, 또는 배경 제거된 이미지)
            text_data: LLM 생성 텍스트 (brand_name, product_headline, etc.)
            output_size: 결과 이미지 크기 (기본 600x1000)
            
        Returns:
            PIL.Image.Image: 합성된 배너 이미지
        """
        width, height = output_size
        logger.info(f"세로형 배너 합성 시작 - 크기: {output_size}")
        
        # 1. 캔버스 생성 (흰색 배경 + 테두리)
        canvas = Image.new("RGB", output_size, "white")
        draw = ImageDraw.Draw(canvas)
        
        # 테두리 그리기 (연한 회색)
        border_color = "#E0E0E0"
        draw.rectangle([(0, 0), (width-1, height-1)], outline=border_color, width=2)
        
        # 2. 헤더 (브랜드명) - 상단 10%
        brand_text = text_data.get("brand_name", "")
        # 상단 중앙, 회색, 작은 폰트
        try:
            brand_font = ImageFont.truetype(self.font_path, int(width * 0.04)) # 약 24px
        except:
            brand_font = self.font
            
        brand_bbox = draw.textbbox((0, 0), brand_text, font=brand_font)
        brand_w = brand_bbox[2] - brand_bbox[0]
        brand_x = (width - brand_w) // 2
        brand_y = int(height * 0.03) # 상단 3% 여백
        
        draw.text((brand_x, brand_y), brand_text, font=brand_font, fill="#808080")
        
        # 3. 메인 이미지 영역 - 상단 (너비와 1:1 비율 유지)
        # 만약 output_size 너비가 1000이면 이미지 높이도 1000 (정사각형)
        img_area_w = width
        # 기본적으로 정사각형 영역 확보
        img_area_h = width 
        
        # 전체 높이가 충분하지 않으면 조정 (최소한 텍스트 영역 30%는 남겨야 함)
        if height < img_area_h * 1.3:
             # 만약 높이가 부족하면 기존 로직대로 50%만 사용
             img_area_h = int(height * 0.5)
             
        img_area_y = int(height * 0.08) # 상단 8% 여백 (브랜드명을 위해 더 내림)
        
        # 제품 이미지 리사이징 (Cover 모드와 유사하게, 하지만 정사각형이면 그대로)
        img_w, img_h = product_image.size
        
        # 이미지 비율 계산
        img_ratio = img_w / img_h
        target_ratio = img_area_w / img_area_h
        
        # 원본 비율 유지하며 리사이즈 (LANCZOS)
        if img_ratio > target_ratio:
            # 이미지가 더 가로로 긴 경우 -> 높이 기준
            new_h = img_area_h
            new_w = int(new_h * img_ratio)
        else:
            # 이미지가 더 세로로 길거나 같은 경우 -> 너비 기준
            new_w = img_area_w
            new_h = int(new_w / img_ratio)
            
        resized_img = product_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # 중앙 크롭 (또는 중앙 배치)
        # Creative Ad는 잘리면 안 되므로 'Cover'보다는 'Contain'이나 'Fill'이 낫지만,
        # 사용자가 "공간을 정사각형으로 바꿔달라"고 했으므로 꽉 채우는 게 맞음.
        # 단, 이미 1:1 이미지가 들어오므로 1:1 영역에 넣으면 잘림 없음.
        
        crop_x = (new_w - img_area_w) // 2
        crop_y = (new_h - img_area_h) // 2
        
        # 만약 crop 좌표가 음수면(이미지가 작으면) 배경색으로 채워야 함.
        # 하지만 여기선 이미지가 더 크거나 같게 리사이즈됨.
        cropped_img = resized_img.crop((crop_x, crop_y, crop_x + img_area_w, crop_y + img_area_h))
        
        canvas.paste(cropped_img, (0, img_area_y))
        
        
        # 4. 텍스트 영역 - 이미지 아래
        text_area_y = img_area_y + img_area_h + int(height * 0.05) # 이미지 아래 5% 여백
        padding_x = int(width * 0.06) # 좌우 6% 여백
        
        import textwrap
        
        # 제목 (Headline)
        headline = text_data.get("product_headline", "")
        try:
            headline_font = ImageFont.truetype(self.font_path, int(width * 0.08)) # 약 80px, Bold (폰트 키움)
        except:
            headline_font = self.font
            
        # 제목 줄바꿈 (폭을 좀 더 여유있게)
        headline_lines = textwrap.wrap(headline, width=14) 
        
        current_y = text_area_y
        for line in headline_lines[:3]: # 최대 3줄로 증가
            draw.text((padding_x, current_y), line, font=headline_font, fill="#333333")
            current_y += int(width * 0.10) # 줄간격
            
        # 본문 (Description)
        description = text_data.get("product_description", "")
        try:
            desc_font = ImageFont.truetype(self.font_path, int(width * 0.05)) # 약 50px
        except:
            desc_font = self.font
            
        current_y += int(height * 0.02) # 제목-본문 간격
        
        desc_lines = textwrap.wrap(description, width=22)
        for line in desc_lines[:5]: # 최대 5줄로 증가
            draw.text((padding_x, current_y), line, font=desc_font, fill="#666666")
            current_y += int(width * 0.07)
            
        # 5. CTA 버튼 - 최하단 (고정 위치가 아니라 콘텐츠에 따라 유동적으로, 혹은 바닥에 붙이기)
        cta_text = text_data.get("cta_text", "열기")
        btn_height = int(width * 0.12) # 너비 비례로 변경 (약 120px)
        btn_width = width - (padding_x * 2) 
        btn_x = padding_x
        
        # 버튼 위치: 텍스트가 끝난 지점 or 하단 고정 중 더 아래쪽 선택 (겹침 방지)
        # 하단 5% 위치
        bottom_fixed_y = height - btn_height - int(height * 0.05)
        
        # 텍스트가 너무 길어서 침범하면?
        if current_y + int(height * 0.02) > bottom_fixed_y:
            # 텍스트 바로 아래에 배치 (단, 캔버스를 벗어나지 않도록 주의)
            btn_y = current_y + int(height * 0.02)
        else:
            # 하단 고정
            btn_y = bottom_fixed_y
        
        # 버튼 배경
        draw.rectangle([(btn_x, btn_y), (btn_x + btn_width, btn_y + btn_height)], fill="#333333")
            
        # 버튼 텍스트
        try:
            btn_font = ImageFont.truetype(self.font_path, int(btn_height * 0.45))
        except:
            btn_font = self.font
            
        btn_text_bbox = draw.textbbox((0, 0), cta_text, font=btn_font)
        btn_text_w = btn_text_bbox[2] - btn_text_bbox[0]
        btn_text_h = btn_text_bbox[3] - btn_text_bbox[1]
        
        btn_text_x = btn_x + (btn_width - btn_text_w) // 2
        btn_text_y = btn_y + (btn_height - btn_text_h) // 2
        
        draw.text((btn_text_x, btn_text_y), cta_text, font=btn_font, fill="white")
        
        logger.info("세로형 배너 합성 완료")
        return canvas

    def compose_horizontal_ad(
        self,
        product_image: Image.Image,
        text_data: dict,
        output_size: Tuple[int, int] = (2000, 1000)
    ) -> Image.Image:
        """
        가로형 광고 배너 템플릿 합성
        
        왼쪽: 정사각형 이미지 영역
        오른쪽: 텍스트 영역 (브랜드명, 제목, 본문, CTA)
        
        Args:
            product_image: 크리에이티브 이미지
            text_data: LLM 생성 텍스트 (brand_name, product_headline, etc.)
            output_size: 결과 이미지 크기 (기본 2000x1000)
            
        Returns:
            PIL.Image.Image: 합성된 배너 이미지
        """
        width, height = output_size
        logger.info(f"가로형 배너 합성 시작 - 크기: {output_size}")
        
        # 1. 캔버스 생성
        canvas = Image.new("RGB", output_size, "white")
        draw = ImageDraw.Draw(canvas)
        
        # 테두리
        border_color = "#E0E0E0"
        draw.rectangle([(0, 0), (width-1, height-1)], outline=border_color, width=2)
        
        # 2. 왼쪽: 이미지 영역 (정사각형, 높이 기준)
        img_area_size = height  # 정사각형
        
        # 이미지 리사이즈 및 크롭
        img_w, img_h = product_image.size
        img_ratio = img_w / img_h
        
        if img_ratio > 1:
            new_h = img_area_size
            new_w = int(new_h * img_ratio)
        else:
            new_w = img_area_size
            new_h = int(new_w / img_ratio)
            
        resized_img = product_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        crop_x = (new_w - img_area_size) // 2
        crop_y = (new_h - img_area_size) // 2
        cropped_img = resized_img.crop((crop_x, crop_y, crop_x + img_area_size, crop_y + img_area_size))
        
        canvas.paste(cropped_img, (0, 0))
        
        # 3. 오른쪽: 텍스트 영역
        text_area_x = img_area_size + int(width * 0.04)  # 이미지 오른쪽 + 4% 여백
        text_area_w = width - img_area_size - int(width * 0.08)  # 좌우 여백 제외 (넉넉하게)
        padding_x = text_area_x
        
        import textwrap
        
        # 브랜드명 (상단)
        brand_text = text_data.get("brand_name", "")
        try:
            brand_font = ImageFont.truetype(self.font_path, int(height * 0.035))
        except:
            brand_font = self.font
            
        brand_y = int(height * 0.08)
        draw.text((padding_x, brand_y), brand_text, font=brand_font, fill="#808080")
        
        # 제목 (Headline)
        headline = text_data.get("product_headline", "")
        try:
            headline_font = ImageFont.truetype(self.font_path, int(height * 0.065))  # 8% -> 6.5%로 축소
        except:
            headline_font = self.font
        
        # 한글은 글자당 폭이 넓으므로 고정 글자수로 줄바꿈
        headline_lines = textwrap.wrap(headline, width=10)  # 한글 기준 10자
        
        current_y = int(height * 0.18)
        for line in headline_lines[:3]:
            draw.text((padding_x, current_y), line, font=headline_font, fill="#333333")
            current_y += int(height * 0.09)
            
        # 본문 (Description)
        description = text_data.get("product_description", "")
        try:
            desc_font = ImageFont.truetype(self.font_path, int(height * 0.035))  # 4% -> 3.5%로 축소
        except:
            desc_font = self.font
            
        current_y += int(height * 0.03)
        
        desc_lines = textwrap.wrap(description, width=18)  # 한글 기준 18자
        for line in desc_lines[:4]:
            draw.text((padding_x, current_y), line, font=desc_font, fill="#666666")
            current_y += int(height * 0.05)
            
        # CTA 버튼 (하단 고정)
        cta_text = text_data.get("cta_text", "열기")
        btn_height = int(height * 0.10)
        btn_width = text_area_w
        btn_x = padding_x
        
        bottom_fixed_y = height - btn_height - int(height * 0.08)
        
        if current_y + int(height * 0.03) > bottom_fixed_y:
            btn_y = current_y + int(height * 0.03)
        else:
            btn_y = bottom_fixed_y
        
        draw.rectangle([(btn_x, btn_y), (btn_x + btn_width, btn_y + btn_height)], fill="#333333")
        
        try:
            btn_font = ImageFont.truetype(self.font_path, int(btn_height * 0.45))
        except:
            btn_font = self.font
            
        btn_text_bbox = draw.textbbox((0, 0), cta_text, font=btn_font)
        btn_text_w = btn_text_bbox[2] - btn_text_bbox[0]
        btn_text_h = btn_text_bbox[3] - btn_text_bbox[1]
        
        btn_text_x = btn_x + (btn_width - btn_text_w) // 2
        btn_text_y = btn_y + (btn_height - btn_text_h) // 2
        
        draw.text((btn_text_x, btn_text_y), cta_text, font=btn_font, fill="white")
        
        logger.info("가로형 배너 합성 완료")
        return canvas
if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 테스트
    try:
        service = ImageEditService()
        
        # 테스트용 이미지 생성
        print("테스트 이미지 생성 중...")
        
        # 배경 이미지
        background = Image.new("RGB", (1024, 1024), (200, 220, 240))
        
        # 제품 이미지 (간단한 원)
        product = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
        draw = ImageDraw.Draw(product)
        draw.ellipse([50, 50, 350, 350], fill=(255, 100, 100, 255))
        
        # 합성
        print("이미지 합성 중...")
        composite = service.composite_image(background, product)
        
        # 텍스트 추가
        print("텍스트 오버레이 추가 중...")
        final = service.add_text_overlay(
            composite,
            main_text="혁신의 시작",
            sub_text="당신의 라이프스타일을 바꿔줄 제품"
        )
        
        # 저장
        output_path = "test_composite.png"
        final.save(output_path)
        print(f"\n생성된 이미지 저장: {output_path}")
        
    except Exception as e:
        print(f"오류 발생: {e}")
