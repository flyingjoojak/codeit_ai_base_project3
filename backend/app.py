import uuid
import asyncio
import uvicorn
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form
from model import BannerGenerator
from schemas import StatusResponse
from storage import ensure_task_dir, write_task, read_task, task_exists
from worker_true import worker_loop
from task_gc import gc_loop
from storage import delete_task
from matplotlib import font_manager
from dotenv import load_dotenv
load_dotenv()



generator = BannerGenerator()
q: asyncio.Queue[str] = asyncio.Queue()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, "assets", "NanumGothicBold.ttf")

if os.path.exists(FONT_PATH):
    font_manager.fontManager.addfont(FONT_PATH)
    print("Font loaded:", FONT_PATH)
else:
    print("Font NOT found:", FONT_PATH)

@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_task_dir()
    asyncio.create_task(worker_loop(q, generator))
    asyncio.create_task(gc_loop())
    yield

app = FastAPI(lifespan=lifespan)


@app.post("/generate")
async def generate(
    image: UploadFile = File(...),
    product_name: str = Form(...),
    keywords: str = Form(...),   # "건강,스타일,혁신"
    tone: str = Form(...),
    size_str: str = Form("Creative_Ad"),
    layout : str = Form("vertical")
):
    task_id = uuid.uuid4().hex
    image_bytes = await image.read()
    kw_list = [k.strip() for k in keywords.split(",") if k.strip()]

    write_task(task_id, {
        "task_id": task_id,
        "status": "queued",
        "payload": {
            "image_hex": image_bytes.hex(),
            "product_name": product_name,
            "keywords": kw_list,
            "tone": tone,
            "layout": layout,
            "size_str": size_str,
        }
    })

    await q.put(task_id)
    return {"task_id": task_id}

@app.get("/status/{task_id}", response_model=StatusResponse)
async def status(task_id: str):
    if not task_exists(task_id):
        return StatusResponse(task_id=task_id, status="failed", error="unknown task_id")

    t = read_task(task_id)
    return StatusResponse(
        task_id=task_id,
        status=t["status"],
        error=t.get("error"),
        result=t.get("result"),
    )


@app.post("/ack/{task_id}")
async def ack(task_id: str):
    if not task_exists(task_id):
        return {"ok": False, "error": "unknown task_id"}

    delete_task(task_id)
    return {"ok": True}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)