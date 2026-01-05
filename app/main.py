from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import api_router

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

#### 💬 통화 요약 (Calls)
- 통화 내용 자동 요약
- 핵심 포인트 추출
- 다음 액션 제안

### 워크플로우

**무료 사용자:**
```
1. 음성 파일 업로드
   POST /api/v1/transcripts/upload-and-transcribe

2. 화자별 대화 조회
   GET /api/v1/transcripts/{id}/speakers

3. 종합 분석 조회 (일반 프롬프트)
   GET /api/v1/analysis/{id}/comprehensive
```

**SaaS 고객 (회사별 맞춤 분석):**
```
1. 회사 등록
   POST /api/v1/companies

2. 영업 스크립트 PDF 업로드
   POST /api/v1/companies/{company_id}/scripts

3. 음성 파일 업로드
   POST /api/v1/transcripts/upload-and-transcribe

4. 종합 분석 조회 (회사 맞춤 프롬프트)
   GET /api/v1/analysis/{id}/comprehensive?company_id={company_id}
```

### 기술 스택
- **STT & Speaker Diarization**: AssemblyAI
- **LLM 분석**: OpenAI GPT-4
- **프롬프트 관리**: Markdown 기반 템플릿

### 문서
- Swagger UI: `/api/docs`
- ReDoc: `/api/redoc`
"""

tags_metadata = [
    {
        "name": "transcripts",
        "description": "**통화 전사 API** - 음성 파일을 업로드하고 화자별로 분리된 전사 결과를 조회합니다.",
    },
    {
        "name": "analysis",
        "description": "**통화 분석 API** - 전사된 통화를 종합 분석하여 감정, 고객 상태, 니즈, 추천 멘트를 제공합니다.",
    },
    {
        "name": "calls",
        "description": "**통화 관리 API** - 통화 업로드, 분석 요청, 결과 조회 등 통화 관련 기본 기능을 제공합니다.",
    },
    {
        "name": "Companies (SaaS)",
        "description": "**회사 관리 API (SaaS)** - 회사 등록, 영업 스크립트 PDF 업로드, 회사별 맞춤 분석을 제공합니다.",
    },
]

app = FastAPI(
    title=settings.APP_NAME,
    description=description,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    openapi_tags=tags_metadata,
    contact={
        "name": "CallMate Team",
        "email": "support@callmate.example.com",
    },
    license_info={
        "name": "MIT",
    },
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
