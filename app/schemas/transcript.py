"""Schemas for speaker-separated transcripts"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class Utterance(BaseModel):
    """Single utterance by a speaker"""
    speaker: str = Field(..., description="화자 레이블 (A, B, C, ...)")
    text: str = Field(..., description="발화 내용")
    start: int = Field(..., description="시작 시간 (밀리초)")
    end: int = Field(..., description="종료 시간 (밀리초)")
    confidence: float = Field(default=0.0, description="신뢰도 (0.0 ~ 1.0)")


class SpeakerSegment(BaseModel):
    """화자별 전체 발화 내용"""
    speaker: str = Field(..., description="화자 레이블 (A, B, C, ...)")
    total_utterances: int = Field(..., description="총 발화 횟수")
    total_duration: int = Field(..., description="총 발화 시간 (밀리초)")
    utterances: List[Utterance] = Field(..., description="발화 목록")
    full_text: str = Field(..., description="전체 발화 내용 (합친 텍스트)")


class TranscriptResponse(BaseModel):
    """전사 결과 응답"""
    transcript_id: str = Field(..., description="전사 ID")
    full_text: str = Field(..., description="전체 대화 내용")
    utterances: List[Utterance] = Field(..., description="시간순 발화 목록")
    speakers: List[str] = Field(..., description="화자 목록 (A, B, C, ...)")
    duration: int = Field(..., description="총 통화 시간 (밀리초)")


class SpeakerSeparatedResponse(BaseModel):
    """화자별 분리된 대화 내용 응답"""
    transcript_id: str = Field(..., description="전사 ID")
    speakers: List[str] = Field(..., description="화자 목록")
    duration: int = Field(..., description="총 통화 시간 (밀리초)")
    speaker_segments: List[SpeakerSegment] = Field(
        ...,
        description="화자별 발화 세그먼트"
    )
    conversation_formatted: str = Field(
        ...,
        description="대화 형식 텍스트 (A: ... B: ...)"
    )


class TranscriptWithAnalysis(BaseModel):
    """전사 결과 + 분석"""
    transcript_id: str
    full_text: str
    utterances: List[Utterance]
    speakers: List[str]
    duration: int
    # Analysis will be added later
    analysis: Optional[dict] = None
