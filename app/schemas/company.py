"""Schemas for company/tenant management (SaaS)"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum


class PlanType(str, Enum):
    """구독 플랜"""
    FREE = "free"          # 무료 (일반 프롬프트만)
    BASIC = "basic"        # 기본 (PDF 1개)
    PRO = "pro"            # 프로 (PDF 5개 + 커스텀 프롬프트)
    ENTERPRISE = "enterprise"  # 엔터프라이즈 (무제한)


class IndustryType(str, Enum):
    """업종"""
    INSURANCE = "insurance"
    REAL_ESTATE = "real_estate"
    B2B = "b2b"
    TELECOM = "telecom"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    RETAIL = "retail"
    OTHER = "other"


class CompanyCreate(BaseModel):
    """회사 등록 요청"""
    name: str = Field(..., description="회사명")
    industry: IndustryType = Field(..., description="업종")
    plan: PlanType = Field(default=PlanType.FREE, description="구독 플랜")
    contact_email: str = Field(..., description="담당자 이메일")
    description: Optional[str] = Field(None, description="회사 설명")


class CompanyResponse(BaseModel):
    """회사 정보 응답"""
    id: str = Field(..., description="회사 ID")
    name: str
    industry: IndustryType
    plan: PlanType
    contact_email: str
    description: Optional[str] = None
    scripts_count: int = Field(default=0, description="업로드된 스크립트 수")
    created_at: datetime
    updated_at: datetime


class ScriptUpload(BaseModel):
    """스크립트 업로드 메타데이터"""
    name: str = Field(..., description="스크립트 이름 (예: 신규고객_상담_스크립트)")
    script_type: str = Field(..., description="스크립트 유형 (sales, support, objection_handling 등)")
    description: Optional[str] = Field(None, description="스크립트 설명")


class ScriptResponse(BaseModel):
    """스크립트 정보 응답"""
    id: str
    company_id: str
    name: str
    script_type: str
    description: Optional[str] = None
    file_path: str
    extracted_content: Optional[str] = Field(None, description="PDF에서 추출된 텍스트")
    key_phrases: List[str] = Field(default=[], description="핵심 문구/멘트")
    created_at: datetime


class CompanyPromptConfig(BaseModel):
    """회사별 프롬프트 설정"""
    company_id: str
    use_custom_prompt: bool = Field(default=False, description="커스텀 프롬프트 사용 여부")
    industry_context: str = Field(default="", description="업종별 맥락")
    tone_preference: str = Field(default="friendly", description="선호 톤 (friendly, professional, persuasive)")
    key_products: List[str] = Field(default=[], description="주요 상품/서비스")
    forbidden_phrases: List[str] = Field(default=[], description="금지 문구")
    must_include_phrases: List[str] = Field(default=[], description="필수 포함 문구")
    custom_instructions: Optional[str] = Field(None, description="추가 지시사항")
