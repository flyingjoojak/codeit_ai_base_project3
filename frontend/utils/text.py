def normalize_keywords(raw:str) -> str:
    items = [x.strip() for x in raw.split(",")]
    items = [x for x in items if x]

    seen = set()
    dedup = []
    for x in items:
        if x not in seen:
            seen.add(x)
            dedup.append(x)
    return ",".join(dedup)