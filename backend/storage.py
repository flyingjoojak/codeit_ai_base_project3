import os
import json
import time
from typing import Dict, Any

TASK_DIR = "./tasks"
TTL_SECONDS = 600  # 10분

def ensure_task_dir() -> None:
    os.makedirs(TASK_DIR, exist_ok=True)

def task_path(task_id: str) -> str:
    return os.path.join(TASK_DIR, f"{task_id}.json")

def write_task(task_id: str, data: Dict[str, Any]) -> None:
    data["updated_at"] = time.time()   # TTL 기준 시간
    p = task_path(task_id)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, p)

def read_task(task_id: str) -> Dict[str, Any]:
    with open(task_path(task_id), "r", encoding="utf-8") as f:
        return json.load(f)

def task_exists(task_id: str) -> bool:
    return os.path.exists(task_path(task_id))

def delete_task(task_id: str) -> None:
    p = task_path(task_id)
    if os.path.exists(p):
        os.remove(p)

def list_tasks():
    return [
        f[:-5] for f in os.listdir(TASK_DIR)
        if f.endswith(".json")
    ]