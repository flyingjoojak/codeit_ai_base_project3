import requests
import time

from config import API_URL, GENERATE_ENDPOINT, JOB_ENDPOINT

def post_generate(image_name:str, image_bytes:bytes, image_type: str,product_name:str,keywords_str:str,tone_ko:str,layout:str):
    url = f"{API_URL}{GENERATE_ENDPOINT}"

    files = {
        "image": (
            image_name,
            image_bytes,
            image_type
        )
    }
    data = {
        "product_name":product_name,
        "keywords":keywords_str,
        "tone":tone_ko,
        "layout":layout
    }
    res = requests.post(url, files=files, data=data, timeout=60)
    res.raise_for_status()
    return res.json()

def poll_job(task_id:str,progress_bar, status_holder, max_wait_sec: int=120, interval_sec:float=1.5):
    url = f"{API_URL}{JOB_ENDPOINT}".format(task_id=task_id)
    start = time.time()

    status_msg = {
        "queued": "대기 중..",
        "running": "생성 중.."
    }

    progress_bar.progress(0)
    status_holder.info("요청이 접수됐어요. 광고 위젯 생성 중입니다..")

    while True:
        try:
            res = requests.get(url, timeout=30)
            res.raise_for_status()
            payload = res.json()
        except requests.Timeout:
            status_holder.warning("서버 응답이 지연되고 있어요. 다시 시도 중..")
            time.sleep(interval_sec)
            continue
        status = payload.get("status")
        progress = payload.get("progress")

        if status == "done":
            progress_bar.progress(100)
            status_holder.success("생성 완료")
            return payload

        elif status == "failed":
            raise RuntimeError(payload.get("error","생성 실패"))

        if isinstance(progress, int):
            progress_bar.progress(max(0,min(100, progress)))
            status_holder.info(f"{status_msg.get(status)}{progress}%")
        else:
            status_holder.info(status_msg.get(status,f"진행 중..(status:{status})"))

        if time.time() - start > max_wait_sec:
            raise TimeoutError("생성 시간이 오래 걸립니다")

        time.sleep(interval_sec)