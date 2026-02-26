# AdWidget Project 🎯

제품 이미지를 기반으로 광고 배너(세로/가로)를 생성하는 FastAPI + Streamlit 프로젝트입니다.  
LLM 카피 생성, SDXL 기반 이미지 생성, 텍스트/레이아웃 합성을 결합해 최종 배너를 만듭니다.

## 한눈에 보는 흐름 🧭
1. 프론트엔드에서 이미지/상품명/키워드/톤/레이아웃을 입력합니다.
2. `POST /generate` 요청이 들어오면 백엔드는 작업 파일을 생성하고 큐에 등록합니다.
3. 워커가 Vision 분석 → 카피 생성 → SDXL 이미지 생성 → 레이아웃 합성을 수행합니다.
4. 결과는 작업 파일에 저장되고 `GET /status/{task_id}`로 조회됩니다.
5. 프론트가 폴링하여 결과를 표시하고, 필요 시 `POST /ack/{task_id}`로 정리합니다.

```
[Frontend] → /generate → [Task 저장] → [Worker]
             └── Vision/LLM/SDXL → Layout 합성 → /status → [Frontend]
```

## 이미지 자리 🖼️
아래 경로에 이미지를 넣으면 README에 표시됩니다.

![UI Screenshot](/opt/AdWidget_Project/시연영상.gif)

## 주요 기능 ✨
- 제품 이미지 + 키워드 + 톤 입력으로 광고 배너 생성
- Vision 기반 시나리오 생성 → 카피 생성 → 이미지 생성 → 레이아웃 합성
- 세로형/가로형 템플릿 제공
- 프론트에서 결과 미리보기, 다운로드 및 간단한 오버레이 편집

## 기술 스택 🧰
- Backend: FastAPI, Uvicorn
- Frontend: Streamlit
- AI/ML: OpenAI API, Diffusers(SDXL), PyTorch
- 이미지 처리: Pillow, rembg

## 디렉터리 구조 📁
```
.
├─ backend/
│  ├─ app.py                 # FastAPI 엔드포인트
│  ├─ worker_true.py         # 비동기 워커 (실제 생성)
│  ├─ worker_dummy.py        # 더미 워커 (테스트용)
│  ├─ task_gc.py             # 작업 파일 정리(GC)
│  ├─ storage.py             # 작업 파일 저장/조회
│  ├─ schemas.py             # API 응답 스키마
│  └─ model/
│     ├─ llm_service.py      # 카피/시나리오 생성 (OpenAI)
│     ├─ image_gen_service.py# SDXL 이미지 생성
│     ├─ image_edit_service.py# 배경 제거/합성/레이아웃
│     └─ workflow_manager.py # 전체 워크플로우
├─ frontend/
│  ├─ app.py                 # Streamlit UI
│  ├─ api.py                 # 백엔드 호출/폴링
│  ├─ config.py              # API URL/옵션
│  └─ utils/
│     ├─ text.py             # 키워드 정규화
│     └─ image.py            # 이미지 변환/오버레이
└─ requirements.txt
```

## 실행 방법 🚀
### 1) 환경 변수 설정
`.env` 또는 셸 환경변수로 OpenAI 키를 설정합니다.
```
OPENAI_API_KEY=your_key_here
```

### 2) 의존성 설치
```
pip install -r requirements.txt
```

### 3) 백엔드 실행
```
cd backend
python app.py
```
또는
```
cd backend
uvicorn app:app --host 0.0.0.0 --port 8000
```

### 4) 프론트엔드 실행
```
streamlit run frontend/app.py
```

> `frontend/config.py`의 `API_URL`이 백엔드 주소와 맞는지 확인하세요.

## API 요약 📡
- `POST /generate`
  - Form-data: `image`(파일), `product_name`, `keywords`, `tone`, `layout`
  - 응답: `{ "task_id": "..." }`
- `GET /status/{task_id}`
  - 응답: `{ task_id, status, result?, error? }`
- `POST /ack/{task_id}`
  - 완료된 작업 결과 정리

## 메모 📝
- 폰트 파일: `backend/assets/NanumGothicBold.ttf`
- 작업 결과는 `backend/tasks/*.json`에 저장되며, 일정 시간이 지나면 GC가 삭제합니다.
- GPU가 없으면 SDXL 생성이 느릴 수 있습니다.
- 현재 `requirements.txt`는 CUDA 12.8(`cu128`) 기준입니다. CPU 환경이라면 Torch 버전을 조정하세요.


## 협업일지
정예진 - https://www.notion.so/2f8fce412ebd801b856fd5483b93e4ab

최지혁 - https://www.notion.so/2f8b65ba18c680a8be58c2a3a3505009