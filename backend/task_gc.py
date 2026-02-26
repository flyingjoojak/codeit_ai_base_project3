import asyncio
import time
import os
from storage import TASK_DIR, read_task, delete_task

GC_INTERVAL = 300          # 5분
TTL_SECONDS = 600          # 10분

async def gc_loop():
    while True:
        # 작업 파일 없으면 길게 휴면
        if not os.path.exists(TASK_DIR) or not os.listdir(TASK_DIR):
            await asyncio.sleep(GC_INTERVAL)
            continue

        now = time.time()

        for name in os.listdir(TASK_DIR):
            if not name.endswith(".json"):
                continue

            task_id = name[:-5]
            try:
                t = read_task(task_id)
                done_at = t.get("done_at")

                if done_at and now - done_at > TTL_SECONDS:
                    delete_task(task_id)
            except Exception:
                pass

        await asyncio.sleep(GC_INTERVAL)