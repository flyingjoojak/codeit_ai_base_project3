# 더미worker.py
import asyncio
from typing import Any, Dict
import base64

from storage import read_task, write_task

async def worker_loop(q: asyncio.Queue[str]):
    while True:
        task_id = await q.get()
        try:
            t: Dict[str, Any] = read_task(task_id)
            t["status"] = "running"
            write_task(task_id, t)

            dummy_image = base64.b64encode(b"dummy_image").decode("utf-8")
            result = {
                "image": dummy_image,
                "main_copy": "테스트 메인 카피",
                "sub_copy": "테스트 서브 카피",
            }

            t["status"] = "done"
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