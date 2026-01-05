"""Schemas for call analysis including sentiment and conversation flow"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum


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


class ModelUsageInfo(BaseModel):
    """사용된 모델 정보"""
    task: str = Field(..., description="작업 유형 (quick_summary, sentiment_analysis 등)")
    model: str = Field(..., description="사용된 모델명")


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
    models_used: Optional[List[ModelUsageInfo]] = Field(
        default=None,
        description="작업별 사용된 LLM 모델 (멀티 모델 분석 시)"
    )


class QuickAnalysis(BaseModel):
    """간단한 분석 결과 (빠른 조회용)"""
    transcript_id: str
    summary: str = Field(..., description="한 줄 요약")
    customer_state: CustomerState
    overall_sentiment: SentimentType
    key_needs: List[str]
    next_action: str
