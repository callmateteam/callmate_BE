"""Schemas for call analysis including sentiment and conversation flow"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


# ============================================
# 상담 유형별 피드백 타이틀
# ============================================

class FeedbackType(str, Enum):
    """피드백 유형 (상담 유형별로 다름)"""
    # 판매/설득 (sales)
    LOSS_EMPHASIS = "loss_emphasis"      # 손실 강조
    ALTERNATIVE = "alternative"          # 대안 제시
    CLOSING = "closing"                  # 마무리

    # 안내/정보 (information)
    KEY_POINT = "key_point"              # 핵심 포인트
    ADDITIONAL_INFO = "additional_info"  # 추가 안내

    # 불만/문제 (complaint)
    EMPATHY = "empathy"                  # 공감 표현
    SOLUTION = "solution"                # 해결 방안


class SentimentType(str, Enum):
    """감정 유형"""
    POSITIVE = "긍정"
    NEUTRAL = "중립"
    NEGATIVE = "부정"
    EXCITED = "흥분/기대"
    WORRIED = "걱정/우려"
    ANGRY = "화남"
    SATISFIED = "만족"


class CustomerState(str, Enum):
    """고객 상태"""
    INTERESTED = "관심 있음"
    CONSIDERING = "고민 중"
    HESITANT = "망설임"
    SATISFIED = "만족"
    DISSATISFIED = "불만족"
    READY_TO_BUY = "구매 준비됨"
    NOT_INTERESTED = "관심 없음"


class SpeakerSentiment(BaseModel):
    """화자별 감정 분석"""
    speaker: str = Field(..., description="화자 레이블 (A, B)")
    overall_sentiment: SentimentType = Field(..., description="전반적인 감정")
    sentiment_score: float = Field(..., ge=-1.0, le=1.0, description="감정 점수 (-1: 부정 ~ 1: 긍정)")
    tone_analysis: str = Field(..., description="말투 분석 (예: 차분함, 급함, 설득적)")
    engagement_level: str = Field(..., description="참여도 (높음/보통/낮음)")
    key_emotions: List[str] = Field(default=[], description="주요 감정 키워드")


class ConversationTurn(BaseModel):
    """대화 턴 (주고받음 단위)"""
    turn_number: int = Field(..., description="턴 번호")
    speaker: str = Field(..., description="화자")
    message: str = Field(..., description="발화 내용")
    customer_reaction: Optional[str] = Field(None, description="고객 반응 (다음 턴 기준)")
    key_point: Optional[str] = Field(None, description="핵심 포인트")


class CustomerNeed(BaseModel):
    """고객 니즈 분석"""
    primary_reason: str = Field(..., description="전화한 주요 사유")
    specific_needs: List[str] = Field(..., description="구체적인 요구사항")
    pain_points: List[str] = Field(default=[], description="고객의 고민/문제점")
    urgency_level: str = Field(..., description="긴급도 (높음/보통/낮음)")


class ConversationSummary(BaseModel):
    """대화 요약"""
    overview: str = Field(..., description="전체 대화 요약 (2-3문장)")
    main_topics: List[str] = Field(..., description="주요 대화 주제")
    key_questions: List[str] = Field(default=[], description="고객의 주요 질문")
    key_answers: List[str] = Field(default=[], description="상담사의 주요 답변")
    outcome: str = Field(..., description="대화 결과 (예: 추가 상담 예정, 견적 발송 예정 등)")


class CallFlowAnalysis(BaseModel):
    """통화 흐름 분석"""
    conversation_turns: List[ConversationTurn] = Field(..., description="대화 턴별 분석")
    customer_journey: List[str] = Field(..., description="고객 반응 변화 과정")
    critical_moments: List[str] = Field(default=[], description="중요한 순간/전환점")


class ComprehensiveAnalysis(BaseModel):
    """종합 분석 결과"""
    transcript_id: str = Field(..., description="전사 ID")

    # 감정 분석
    speaker_sentiments: List[SpeakerSentiment] = Field(..., description="화자별 감정 분석")
    customer_state: CustomerState = Field(..., description="고객 현재 상태")

    # 대화 요약
    conversation_summary: ConversationSummary = Field(..., description="대화 요약")

    # 고객 니즈
    customer_need: CustomerNeed = Field(..., description="고객 니즈 분석")

    # 통화 흐름
    call_flow: CallFlowAnalysis = Field(..., description="통화 흐름 분석")

    # 추천 액션
    next_action: str = Field(..., description="다음 액션 제안")
    recommended_replies: List[str] = Field(..., description="추천 멘트")

    # 메타 정보
    analysis_timestamp: str = Field(..., description="분석 시간")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="분석 신뢰도")


# ============================================
# 프론트엔드용 API 스키마
# ============================================

class AISummaryResponse(BaseModel):
    """AI 요약 응답 (500px × 3줄, 16px 폰트 = 75~90자)"""
    transcript_id: str = Field(..., description="전사 ID")
    summary: str = Field(
        ...,
        description="고객 니즈 + 대화 핵심 요약 (최대 90자)",
        max_length=90
    )
    customer_state: CustomerState = Field(..., description="고객 현재 상태")


class FeedbackItem(BaseModel):
    """개별 피드백 항목"""
    type: FeedbackType = Field(..., description="피드백 유형")
    title: str = Field(..., description="타이틀 (한글)")
    content: str = Field(..., description="추천 멘트")


class ResponseFeedbackResponse(BaseModel):
    """응대 피드백 응답 (3가지 추천)"""
    transcript_id: str = Field(..., description="전사 ID")
    consultation_type: str = Field(..., description="상담 유형 (sales/information/complaint)")
    feedbacks: List[FeedbackItem] = Field(
        ...,
        description="3가지 피드백",
        min_length=3,
        max_length=3
    )


class ConversationResponse(BaseModel):
    """전체 대화 내용 응답"""
    transcript_id: str = Field(..., description="전사 ID")
    duration: int = Field(..., description="통화 시간 (ms)")
    speakers: List[str] = Field(..., description="화자 목록")
    utterances: List[dict] = Field(..., description="시간순 발화 목록")
