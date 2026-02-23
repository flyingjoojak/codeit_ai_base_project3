import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    # OpenAI
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5-mini")

    # SDXL
    i2i_base_model: str = os.getenv("I2I_BASE_MODEL", "stabilityai/stable-diffusion-xl-base-1.0")

    # image size
    gen_w: int = int(os.getenv("GEN_W", "768"))
    gen_h: int = int(os.getenv("GEN_H", "768"))

settings = Settings()