import asyncio
from typing import Any, Dict
from model import BannerGenerator
from storage import read_task, write_task
import random
import time


async def worker_loop(q: asyncio.Queue[str], generator: BannerGenerator):
    while True:
        task_id = await q.get()
        try:
            t: Dict[str, Any] = read_task(task_id)
            t["status"] = "running"
            write_task(task_id, t)

            payload = t["payload"]
            result = generator.process(
                image_file=bytes.fromhex(payload["image_hex"]),
                product_name=payload["product_name"],
                keywords=payload["keywords"],
                tone=payload["tone"],
                layout=payload.get("layout", "vertical"),
                seed=random.randint(0, 99999),
                save_intermediate=False,
            )

            

            t["status"] = "done"
            t["done_at"] = time.time()
            t["result"] = result
            t.pop("payload", None)
            write_task(task_id, t)

        except Exception as e:
            t = read_task(task_id)
            t["status"] = "failed"
            t["error"] = str(e)
            write_task(task_id, t)

        finally:
            q.task_done()