"""API endpoints for call analysis (MVP)"""

from typing import Optional, List
from fastapi import APIRouter, Query, Body
from pydantic import BaseModel
from app.schemas.analysis import (
    ComprehensiveAnalysis,
    AISummaryResponse,
    ResponseFeedbackResponse
)
from app.services.analysis_service import analysis_service
from app.core.exceptions import (
    AnalysisError,
    SummaryError,
    FeedbackError,
    InvalidConsultationTypeError
)

router = APIRouter()

# In-memory cache
summary_cache = {}
feedback_cache = {}
analysis_cache = {}


# ============================================
# Request Models (프론트에서 전사 데이터 전달)
# ============================================

class Utterance(BaseModel):
    speaker: str
    text: str
    start: int
    end: int
    confidence: float = 0.0


class AnalysisRequest(BaseModel):
    """분석 요청 (프론트에서 저장한 전사 데이터 전달)"""
    utterances: List[Utterance]
    speakers: List[str]
    script_context: Optional[str] = None
    consultation_type: str = "sales"


def _prepare_analysis_data(request: AnalysisRequest):
    """분석을 위한 데이터 전처리"""
    utterances_dict = [u.model_dump() for u in request.utterances]

    # 대화 포맷 생성
    conversation_formatted = "\n".join(
        f"{u['speaker']}: {u['text']}" for u in utterances_dict
    )

    # 화자별 세그먼트
    speaker_segments = []
    for speaker in request.speakers:
        speaker_utterances = [u for u in utterances_dict if u["speaker"] == speaker]
        full_text = " ".join(u["text"] for u in speaker_utterances)
        speaker_segments.append({
            "speaker": speaker,
            "full_text": full_text,
            "utterances": speaker_utterances
        })

    # 고객 텍스트 추출
    customer_speaker = analysis_service._detect_customer_speaker(
        speaker_segments, utterances_dict
    )
    customer_text = ""
    for seg in speaker_segments:
        if seg["speaker"] == customer_speaker:
            customer_text = seg["full_text"]
            break

    return {
        "utterances": utterances_dict,
        "speaker_segments": speaker_segments,
        "conversation_formatted": conversation_formatted,
        "customer_text": customer_text
    }


# ============================================
# 1. AI 요약 API
# ============================================

@router.post(
    "/summary",
    response_model=AISummaryResponse,
    summary="AI 요약",
    description="고객 니즈와 대화 핵심을 90자 이내로 요약합니다."
)
async def get_summary(request: AnalysisRequest):
    """
    AI 요약 (500px × 3줄, 16px 폰트 = 최대 90자)

    ## 요청 Body
    - `utterances`: 전사 결과의 utterances 배열
    - `speakers`: 화자 목록 ["A", "B"]

    ## 반환값
    - `summary`: 90자 이내 요약
    - `customer_state`: 고객 현재 상태
    """
    data = _prepare_analysis_data(request)

    try:
        summary = analysis_service.generate_summary(
            transcript_id="from_request",
            conversation_formatted=data["conversation_formatted"],
            customer_text=data["customer_text"]
        )
    except Exception as e:
        raise SummaryError(str(e)).to_http_exception()

    return summary


# ============================================
# 2. 응대 피드백 API
# ============================================

@router.post(
    "/feedback",
    response_model=ResponseFeedbackResponse,
    summary="응대 피드백",
    description="상담 유형별 3가지 추천 멘트를 제공합니다."
)
async def get_feedback(request: AnalysisRequest):
    """
    응대 피드백 (상담 유형별 3가지 추천)

    ## 요청 Body
    - `utterances`: 전사 결과의 utterances 배열
    - `speakers`: 화자 목록
    - `consultation_type`: 상담 유형
      - `sales`: 판매/유지/설득 → 손실 강조, 대안 제시, 마무리
      - `information`: 안내/정보 제공 → 핵심 포인트, 추가 안내, 마무리
      - `complaint`: 불만/문제 해결 → 공감 표현, 해결 방안, 마무리
    - `script_context`: (선택) 회사 스크립트

    ## 반환값
    - `feedbacks`: 3가지 피드백 [{type, title, content}]
    """
    valid_types = ["sales", "information", "complaint"]
    if request.consultation_type not in valid_types:
        raise InvalidConsultationTypeError().to_http_exception()

    data = _prepare_analysis_data(request)

    try:
        feedback = analysis_service.generate_feedback(
            transcript_id="from_request",
            conversation_formatted=data["conversation_formatted"],
            customer_text=data["customer_text"],
            consultation_type=request.consultation_type,
            script_context=request.script_context
        )
    except Exception as e:
        raise FeedbackError(str(e)).to_http_exception()

    return feedback


# ============================================
# 3. 종합 분석 API
# ============================================

@router.post(
    "/comprehensive",
    response_model=ComprehensiveAnalysis,
    summary="통화 종합 분석",
    description="음성 통화를 AI로 종합 분석합니다."
)
async def analyze_call(request: AnalysisRequest):
    """
    통화 종합 분석

    ## 요청 Body
    - `utterances`: 전사 결과의 utterances 배열
    - `speakers`: 화자 목록
    - `script_context`: (선택) 스크립트 컨텍스트 - 맞춤 추천 멘트 생성에 사용

    ## 분석 결과
    - 화자별 감정 분석
    - 고객 상태 (관심 있음, 고민 중, 망설임 등)
    - 대화 요약
    - 고객 니즈 (전화 사유, 요구사항, 고민거리)
    - 대화 흐름 (턴별 분석, 전환점)
    - 추천 액션 및 멘트
    """
    data = _prepare_analysis_data(request)

    try:
        analysis = analysis_service.analyze_call(
            transcript_id="from_request",
            conversation_formatted=data["conversation_formatted"],
            speaker_segments=data["speaker_segments"],
            utterances=data["utterances"],
            script_context=request.script_context
        )
    except Exception as e:
        raise AnalysisError(str(e)).to_http_exception()

    return analysis
