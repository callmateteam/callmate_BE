from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime


class CallUploadResponse(BaseModel):
    """Response for call upload"""
    call_id: str
    filename: str
    status: str
    message: str


class CallSummary(BaseModel):
    """Call summary structure"""
    customer_needs: str = Field(..., description="고객의 핵심 니즈")
    objections: List[str] = Field(..., description="고객의 반대 의견")
    decision_stage: str = Field(..., description="결정 단계 (관심/검토/보류)")


class CallAnalysisResponse(BaseModel):
    """Response for call analysis"""
    call_id: str
    call_summary: CallSummary
    next_action: str = Field(..., description="권장 다음 액션")
    recommended_replies: List[str] = Field(
        ...,
        min_items=1,
        max_items=5,
        description="추천 대응 멘트"
    )


class CallAnalysisRequest(BaseModel):
    """Request for call analysis"""
    call_transcript: str = Field(..., description="통화 전사 텍스트")
    sales_type: Optional[str] = Field(
        None,
        description="영업 유형 (insurance, real_estate, b2b, etc)"
    )
    conversation_goal: Optional[str] = Field(
        None,
        description="대화 목표 (follow_up, objection_handling, close)"
    )
    tone: Optional[str] = Field(
        None,
        description="톤 (friendly, professional, persuasive)"
    )


class CallRecord(BaseModel):
    """Call record from database"""
    id: str
    filename: str
    transcript: Optional[str] = None
    analysis: Optional[CallAnalysisResponse] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
