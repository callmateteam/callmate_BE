from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import api_router
from app.mcp_server import mcp, mcp_app


# Combined lifespan to manage MCP session manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage MCP server lifespan along with FastAPI"""
    async with mcp.session_manager.run():
        yield

# API Documentation metadata
description = """
## CallMate AI Backend API

영업 통화를 분석하여 다음 대응 멘트를 추천하는 AI 백엔드 서비스입니다.

### 주요 기능

#### 📞 통화 전사 (Transcripts)
- 음성 파일 업로드 및 STT 처리
- **화자 분리** (Speaker Diarization)
- 시간순 대화 내용 제공
- 화자별 발화 내용 분리

#### 🧠 통화 분석 (Analysis)
- **화자별 감정 분석** (긍정/부정/중립 등)
- **말투 분석** (차분함, 급함, 설득적 등)
- **고객 상태 판단** (관심 있음, 고민 중, 망설임 등)
- **대화 흐름 분석** (턴별 분석, 반응 변화, 중요한 순간)
- **고객 니즈 추출** (전화 사유, 요구사항, 고민거리)
- **추천 멘트 생성** (다음 대응에 사용할 멘트 제안)

### 워크플로우

```
1. 음성 파일 업로드 (WebSocket)
   WS   /api/v1/transcripts/ws/transcribe (실시간 진행률)

2. 화자별 대화 조회
   GET /api/v1/transcripts/{id}/speakers

3. 종합 분석 조회
   GET /api/v1/analysis/{id}/comprehensive
```

---

### 🔌 WebSocket API (실시간 전사)

긴 음성 파일 처리 시 실시간 진행률을 받으려면 WebSocket을 사용하세요.

**엔드포인트:** `ws://host/api/v1/transcripts/ws/transcribe`

**사용 방법:**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/transcripts/ws/transcribe');

ws.onopen = () => {
    const fileData = btoa(audioFileContent); // base64 인코딩
    ws.send(JSON.stringify({
        action: 'upload',
        filename: 'call.mp3',
        data: fileData,
        language_code: 'ko'
    }));
};

ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.status === 'processing') {
        console.log(`진행률: ${msg.progress.percent}%`);
    } else if (msg.status === 'completed') {
        console.log('완료:', msg.data);
    }
};
```

**메시지 흐름:**
1. `{"status": "received", "data": {"file_id": "...", "duration_ms": 180000}}`
2. `{"status": "processing", "progress": {"percent": 10, "message": "업로드 중..."}}`
3. `{"status": "processing", "progress": {"percent": 50, "message": "전사 중..."}}`
4. `{"status": "completed", "data": {...전사 결과...}}`

---

### 기술 스택
- **STT & Speaker Diarization**: Deepgram Nova-2 (빠른 처리)
- **LLM 분석**: OpenAI GPT-4
- **실시간 통신**: WebSocket

### 문서
- Swagger UI: `/api/docs`
"""

tags_metadata = [
    {
        "name": "transcripts",
        "description": "**통화 전사 API** - 음성 파일을 업로드하고 화자별로 분리된 전사 결과를 조회합니다.",
    },
    {
        "name": "transcripts-ws",
        "description": "**실시간 전사 API (WebSocket)** - WebSocket을 통해 실시간 진행률과 함께 전사를 수행합니다.",
    },
    {
        "name": "analysis",
        "description": "**통화 분석 API** - 전사된 통화를 종합 분석하여 감정, 고객 상태, 니즈, 추천 멘트를 제공합니다.",
    },
    {
        "name": "scripts",
        "description": "**스크립트 API** - 영업 스크립트 폼 입력 및 PDF 업로드를 통해 AI 분석용 컨텍스트를 생성합니다.",
    },
]

app = FastAPI(
    title=settings.APP_NAME,
    description=description,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
    openapi_tags=tags_metadata,
    contact={
        "name": "CallMate Team",
        "email": "support@callmate.example.com",
    },
    license_info={
        "name": "MIT",
    },
    lifespan=lifespan,  # MCP lifespan 관리
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to CallMate API",
        "version": settings.APP_VERSION,
        "docs": "/api/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    }


# Include API routes
app.include_router(api_router, prefix="/api/v1")

# MCP Server 마운트 (카카오 PlayMCP 등록용 - Streamable HTTP)
# MCP 엔드포인트: /mcp (GET/POST 모두 지원)
app.mount("", mcp_app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
