import json
import re
from openai import OpenAI
from model.config import settings

client = OpenAI(api_key=settings.openai_api_key)

def _safe_json_loads(text: str) -> dict:
    """
    모델이 JSON 외 텍스트를 섞어도 최대한 복구해서 dict로 변환.
    """
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        # 첫 번째 {...} 블록 추출
        m = re.search(r"\{.*\}", text, flags=re.S)
        if not m:
            raise ValueError(f"JSON parse failed. Raw:\n{text}")
        return json.loads(m.group(0))

def stage_b_generate_plate_blueprint(product_hint: str, keywords: list[str]) -> dict:
    """
    사람(또는 신체 일부) plate용 blueprint 생성.
    - 제품은 절대 등장하지 않음(나중에 합성)
    - anchor_spec: 제품이 들어갈 위치(손목/손/목 주변 등) 명시
    """
    system = (
        "You are an advertising scene planner.\n"
        "Return ONLY valid JSON.\n\n"
        "Goal: Create a human plate for later product insertion.\n\n"
        "CRITICAL RULES:\n"
        "- The product must NOT appear.\n"
        "- The anchor area (wrist/hand/etc) MUST be clearly visible and dominant in frame.\n"
        "- Avoid portrait-style face dominance.\n"
        "- If face appears, crop below nose OR keep it out of focus.\n"
        "- The anchor must occupy at least 30-50% of the frame.\n"
        "- Clear empty space for product insertion.\n"
        "- Photorealistic commercial lifestyle photography.\n"
        "- No text, no watermark, no logos.\n\n"
        "JSON schema:\n"
        "{\n"
        "  \"shot_type\": \"human_plate\",\n"
        "  \"interaction_level\": \"high\",\n"
        "  \"anchor_spec\": {\n"
        "    \"anchor\": \"wrist|hand|neck|table_contact|other\",\n"
        "    \"framing\": \"closeup|medium_closeup|medium\",\n"
        "    \"pose_notes\": \"...\",\n"
        "    \"occlusion_goal\": \"none|sleeve_partial|finger_partial|hair_partial\"\n"
        "  },\n"
        "  \"scene\": {\n"
        "    \"subject\": \"...\",\n"
        "    \"environment\": \"...\",\n"
        "    \"mood\": \"warm|minimal|luxury|clean\"\n"
        "  },\n"
        "  \"constraints\": [\"...\"],\n"
        "  \"size\": [W,H]\n"
        "}\n"
    )

    user = (
        f"Product hint: {product_hint}\n"
        f"Keywords: {', '.join(keywords)}\n\n"
        "Generate a human plate specifically for inserting the product.\n"
        "For a wristwatch, prioritize a close-up wrist framing.\n"
        "The wrist must be the main focus, not the face.\n"
    )

    resp = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        # temperature 넣지 않음 (gpt-5-mini 제한)
    )

    content = resp.choices[0].message.content
    bp = _safe_json_loads(content)

    # size가 없으면 config로 채움
    if "size" not in bp:
        bp["size"] = [settings.gen_w, settings.gen_h]
    return bp