def make_background_prompt(scene_environment: str, mood: str) -> tuple[str, str]:
    """
    광고 구도용 배경 프롬프트:
    - foreground surface(테이블) 강제
    - 제품이 놓일 hero space(비어있는 자리) 강제
    - 제품 자체(시계/향수/책 등) 생성 금지
    """

    # 무드 블록(너가 말한 high 중심, 광고 톤)
    mood_map = {
        "warm": "warm premium commercial tone, cozy cinematic lighting",
        "minimal": "minimal premium commercial tone, clean soft lighting",
        "luxury": "luxury cinematic commercial tone, elegant highlights",
        "clean": "clean bright commercial tone, soft daylight",
    }
    mood_block = mood_map.get(mood, mood_map["warm"])

    # ✅ 핵심: 구도/세팅을 강하게 지정
    prompt = (
        "photorealistic product photography background, "
        "professional DSLR shot, 85mm lens, shallow depth of field, soft bokeh, "
        f"{mood_block}, "
        "foreground: wooden table surface clearly visible with natural wood grain, "
        "composition: large empty hero space on the table for product placement, "
        "midground: subtle props out of focus (ceramic cup, notebook, small plant) optional, "
        "background: soft interior ambience with warm bokeh lights, "
        "soft natural window light from one side, realistic shadows, "
        f"{scene_environment}"
    )

    # ✅ 제품 생성 막는 negative 강화 (가장 중요)
    negative = (
        "watch, wristwatch, clock, dial, strap, bracelet, "
        "perfume, bottle, sprayer, atomizer, "
        "book, magazine, "
        "product, object in focus, "
        "logo, text, watermark, letters, numbers, "
        "hands, person, face, body, "
        "lowres, blurry, cartoon, anime"
    )

    return prompt, negative