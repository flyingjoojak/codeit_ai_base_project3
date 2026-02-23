from rembg import remove
from PIL import Image

def remove_background_to_rgba(product_path: str) -> Image.Image:
    """
    제품 이미지 파일 -> 배경 제거 -> RGBA(PIL Image) 반환
    """
    img = Image.open(product_path).convert("RGBA")
    out = remove(img)  # rembg가 alpha를 만들어줌
    return out