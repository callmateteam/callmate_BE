"""API endpoints for call analysis (MVP)"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.schemas.analysis import (
    ComprehensiveAnalysis,
    AISummaryResponse,
    ResponseFeedbackResponse,
    ConversationResponse
)
from app.services.analysis_service import analysis_service
from app.api.v1.transcripts import transcripts_store

router = APIRouter()

# In-memory storage for analysis results
analysis_store = {}
summary_store = {}
feedback_store = {}


def _get_transcript_data(transcript_id: str):
    """전사 데이터 조회 및 전처리"""
    if transcript_id not in transcripts_store:
        raise HTTPException(status_code=404, detail="전사 결과를 찾을 수 없습니다")

    stored = transcripts_store[transcript_id]
    result = stored["result"]

    from app.services.stt_service import stt_service

    # 화자별 데이터 준비
    speaker_segments = []
    for speaker in result["speakers"]:
        speaker_utterances = stt_service.get_speaker_segments(
            result["utterances"],
            speaker
        )
        full_text = " ".join(u["text"] for u in speaker_utterances)
        speaker_segments.append({
            "speaker": speaker,
            "full_text": full_text,
            "utterances": speaker_utterances
        })

    # 대화 포맷
    conversation_formatted = stt_service.format_conversation(
        result["utterances"],
        format_type="simple"
    )

    # 고객 텍스트 추출
    customer_speaker = analysis_service._detect_customer_speaker(
        speaker_segments, result["utterances"]
    )
    customer_text = ""
    for seg in speaker_segments:
        if seg["speaker"] == customer_speaker:
            customer_text = seg["full_text"]
            break

    return {
        "result": result,
        "speaker_segments": speaker_segments,
        "conversation_formatted": conversation_formatted,
        "customer_text": customer_text
    }


# ============================================
# 1. AI 요약 API
# ============================================

@router.get(
    "/{transcript_id}/summary",
    response_model=AISummaryResponse,
    summary="AI 요약",
    description="고객 니즈와 대화 핵심을 90자 이내로 요약합니다."
)
async def get_summary(transcript_id: str):
    """
    AI 요약 (500px × 3줄, 16px 폰트 = 최대 90자)

    - **transcript_id**: 전사 ID

    ## 반환값
    - `summary`: 90자 이내 요약
    - `customer_state`: 고객 현재 상태
    """
    # 캐시 확인
    if transcript_id in summary_store:
        return summary_store[transcript_id]

    # 데이터 조회
    data = _get_transcript_data(transcript_id)

    # 요약 생성
    try:
        summary = analysis_service.generate_summary(
            transcript_id=transcript_id,
            conversation_formatted=data["conversation_formatted"],
            customer_text=data["customer_text"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"요약 생성 실패: {str(e)}")

    # 캐시 저장
    summary_store[transcript_id] = summary

    return summary


# ============================================
# 2. 전체 대화 내용 API
# ============================================

@router.get(
    "/{transcript_id}/conversation",
    response_model=ConversationResponse,
    summary="전체 대화 내용",
    description="화자 분리된 전체 대화 내용을 반환합니다."
)
async def get_conversation(transcript_id: str):
    """
    전체 대화 내용 조회

    - **transcript_id**: 전사 ID

    ## 반환값
    - `duration`: 통화 시간 (ms)
    - `speakers`: 화자 목록
    - `utterances`: 시간순 발화 목록 [{speaker, text, start, end, confidence}]
    """
    if transcript_id not in transcripts_store:
        raise HTTPException(status_code=404, detail="전사 결과를 찾을 수 없습니다")

    stored = transcripts_store[transcript_id]
    result = stored["result"]

    return ConversationResponse(
        transcript_id=transcript_id,
        duration=result.get("duration", 0),
        speakers=result.get("speakers", []),
        utterances=result.get("utterances", [])
    )


# ============================================
# 3. 응대 피드백 API
# ============================================

@router.get(
    "/{transcript_id}/feedback",
    response_model=ResponseFeedbackResponse,
    summary="응대 피드백",
    description="상담 유형별 3가지 추천 멘트를 제공합니다."
)
async def get_feedback(
    transcript_id: str,
    consultation_type: str = Query(
        "sales",
        description="상담 유형 (sales/information/complaint)"
    ),
    script_context: Optional[str] = Query(
        None,
        description="스크립트 컨텍스트 (POST /scripts/extract/form 응답의 prompt_context)"
    )
):
    """
    응대 피드백 (상담 유형별 3가지 추천)

    - **transcript_id**: 전사 ID
    - **consultation_type**: 상담 유형
      - `sales`: 판매/유지/설득 → 손실 강조, 대안 제시, 마무리
      - `information`: 안내/정보 제공 → 핵심 포인트, 추가 안내, 마무리
      - `complaint`: 불만/문제 해결 → 공감 표현, 해결 방안, 마무리
    - **script_context**: (선택) 회사 스크립트

    ## 반환값
    - `feedbacks`: 3가지 피드백 [{type, title, content}]
    """
    # 유효한 상담 유형 확인
    valid_types = ["sales", "information", "complaint"]
    if consultation_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"유효하지 않은 상담 유형입니다. ({', '.join(valid_types)})"
        )

    # 캐시 키
    cache_key = f"{transcript_id}:{consultation_type}:{hash(script_context or '')}"
    if cache_key in feedback_store:
        return feedback_store[cache_key]

    # 데이터 조회
    data = _get_transcript_data(transcript_id)

    # 피드백 생성
    try:
        feedback = analysis_service.generate_feedback(
            transcript_id=transcript_id,
            conversation_formatted=data["conversation_formatted"],
            customer_text=data["customer_text"],
            consultation_type=consultation_type,
            script_context=script_context
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"피드백 생성 실패: {str(e)}")

    # 캐시 저장
    feedback_store[cache_key] = feedback

    return feedback


# ============================================
# 4. 종합 분석 API (기존)
# ============================================

@router.get(
    "/{transcript_id}",
    response_model=ComprehensiveAnalysis,
    summary="통화 종합 분석",
    description="음성 통화를 AI로 종합 분석합니다."
)
async def analyze_call(
    transcript_id: str,
    script_context: Optional[str] = Query(
        None,
        description="스크립트 컨텍스트 (POST /scripts/extract/form 응답의 prompt_context)"
    )
):
    """
    통화 종합 분석

    - **transcript_id**: 전사 ID (POST /transcripts/upload 응답)
    - **script_context**: (선택) 스크립트 컨텍스트 - 맞춤 추천 멘트 생성에 사용

    ## 분석 결과
    - 화자별 감정 분석
    - 고객 상태 (관심 있음, 고민 중, 망설임 등)
    - 대화 요약
    - 고객 니즈 (전화 사유, 요구사항, 고민거리)
    - 대화 흐름 (턴별 분석, 전환점)
    - 추천 액션 및 멘트
    """
    # 캐시 확인
    cache_key = f"{transcript_id}:{hash(script_context or '')}"
    if cache_key in analysis_store:
        return analysis_store[cache_key]

    # 데이터 조회
    data = _get_transcript_data(transcript_id)

    # 분석 수행
    try:
        analysis = analysis_service.analyze_call(
            transcript_id=transcript_id,
            conversation_formatted=data["conversation_formatted"],
            speaker_segments=data["speaker_segments"],
            utterances=data["result"]["utterances"],
            script_context=script_context
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"분석 실패: {str(e)}"
        )

    # 캐시 저장
    analysis_store[cache_key] = analysis

    return analysis


@router.post(
    "/{transcript_id}/reanalyze",
    response_model=ComprehensiveAnalysis,
    summary="재분석",
    description="캐시를 무시하고 새로 분석합니다."
)
async def reanalyze_call(
    transcript_id: str,
    script_context: Optional[str] = Query(None, description="스크립트 컨텍스트")
):
    """재분석 (캐시 무시)"""
    # 캐시 삭제
    cache_key = f"{transcript_id}:{hash(script_context or '')}"
    if cache_key in analysis_store:
        del analysis_store[cache_key]

    return await analyze_call(transcript_id, script_context)
