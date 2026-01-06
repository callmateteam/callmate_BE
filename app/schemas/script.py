"""Schemas for script extraction (MVP)"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum


class ScriptInputType(str, Enum):
    """스크립트 입력 방식"""
    PDF = "pdf"
    FORM = "form"


class ConsultationType(str, Enum):
    """상담 유형 (2단계)"""
    INFORMATION = "information"      # 안내/정보 제공
    SALES = "sales"                  # 판매/유지/설득
    COMPLAINT = "complaint"          # 불만/문제 해결


class ToneStyle(str, Enum):
    """말투 스타일 (4단계)"""
    FORMAL = "formal"           # 격식체
    FRIENDLY = "friendly"       # 친근체
    PROFESSIONAL = "professional"  # 전문가 스타일


class QAPair(BaseModel):
    """질문-답변 쌍"""
    question: str = Field(..., description="질문")
    answer: str = Field(..., description="답변")


class ProblemSolution(BaseModel):
    """문제-해결 쌍 (불만/문제 해결용)"""
    problem: str = Field(..., description="문제 유형")
    solution: str = Field(..., description="해결 절차")


class ObjectionResponse(BaseModel):
    """거절 사유-대응 멘트 쌍 (판매용)"""
    objection: str = Field(..., description="거절 사유")
    response: str = Field(..., description="대응 멘트")


# ============================================
# 3단계: 상담 유형별 세부 정보
# ============================================

class InformationDetails(BaseModel):
    """안내/정보 제공 - 세부 정보 (3단계)"""
    product_name: str = Field(..., description="제품/서비스명")
    key_features: List[str] = Field(
        default=[],
        description="주요 특장점 (최대 5개)",
        max_length=5
    )
    faq: List[QAPair] = Field(
        default=[],
        description="자주 묻는 질문",
        max_length=10
    )


class SalesDetails(BaseModel):
    """판매/유지/설득 - 세부 정보 (3단계)"""
    product_name: str = Field(..., description="제품/서비스명")
    key_features: List[str] = Field(
        default=[],
        description="주요 특장점",
        max_length=5
    )
    pricing_info: List[str] = Field(
        default=[],
        description="가격/혜택 정보",
        max_length=5
    )
    competitive_advantages: List[str] = Field(
        default=[],
        description="경쟁사 대비 장점",
        max_length=5
    )
    objection_responses: List[ObjectionResponse] = Field(
        default=[],
        description="자주 나오는 거절 사유 & 대응 멘트",
        max_length=10
    )


class ComplaintDetails(BaseModel):
    """불만/문제 해결 - 세부 정보 (3단계)"""
    common_problems: List[ProblemSolution] = Field(
        default=[],
        description="자주 발생하는 문제 유형 & 해결 절차",
        max_length=10
    )
    compensation_options: List[str] = Field(
        default=[],
        description="보상/대안 제시 가능 범위",
        max_length=5
    )
    escalation_criteria: List[str] = Field(
        default=[],
        description="에스컬레이션 기준 (상위 담당자 연결 조건)",
        max_length=5
    )


# ============================================
# 4단계: 톤 & 추가 설정 (선택)
# ============================================

class ToneSettings(BaseModel):
    """톤 & 추가 설정 (4단계 - 선택)"""
    tone_style: Optional[ToneStyle] = Field(
        default=ToneStyle.FRIENDLY,
        description="말투 스타일"
    )
    forbidden_phrases: List[str] = Field(
        default=[],
        description="금지 표현 (예: '안됩니다', '불가능합니다')",
        max_length=10
    )
    required_phrases: List[str] = Field(
        default=[],
        description="필수 포함 멘트 (예: '고객님', '감사합니다')",
        max_length=10
    )
    key_phrases: List[str] = Field(
        default=[],
        description="핵심 멘트 (강조하고 싶은 문구)",
        max_length=10
    )


# ============================================
# 폼 요청 스키마
# ============================================

class FormScriptRequest(BaseModel):
    """폼 입력 방식 스크립트 요청 (4단계)"""

    # 1단계: 기본 정보
    company_name: str = Field(
        ...,
        description="회사명 또는 이름",
        min_length=1,
        max_length=100
    )

    # 2단계: 상담 유형
    consultation_type: ConsultationType = Field(
        ...,
        description="상담 유형"
    )

    # 3단계: 유형별 세부 정보 (하나만 선택)
    information_details: Optional[InformationDetails] = Field(
        default=None,
        description="안내/정보 제공 세부 정보 (consultation_type=information일 때)"
    )
    sales_details: Optional[SalesDetails] = Field(
        default=None,
        description="판매/유지/설득 세부 정보 (consultation_type=sales일 때)"
    )
    complaint_details: Optional[ComplaintDetails] = Field(
        default=None,
        description="불만/문제 해결 세부 정보 (consultation_type=complaint일 때)"
    )

    # 4단계: 톤 & 추가 설정 (선택)
    tone_settings: Optional[ToneSettings] = Field(
        default=None,
        description="톤 & 추가 설정 (선택사항)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "ABC보험",
                "consultation_type": "sales",
                "sales_details": {
                    "product_name": "가족건강보험",
                    "key_features": [
                        "업계 최저 보험료",
                        "24시간 고객 상담",
                        "간편한 모바일 청구"
                    ],
                    "pricing_info": [
                        "월 19,900원부터",
                        "첫 달 무료 이벤트"
                    ],
                    "competitive_advantages": [
                        "보장 범위 1.5배",
                        "청구 후 24시간 내 지급"
                    ],
                    "objection_responses": [
                        {
                            "objection": "가격이 비싸요",
                            "response": "고객님, 가성비 측면에서 저희가 가장 합리적입니다."
                        },
                        {
                            "objection": "생각해볼게요",
                            "response": "네, 천천히 생각해보세요. 추가 궁금하신 점 있으실까요?"
                        }
                    ]
                },
                "tone_settings": {
                    "tone_style": "friendly",
                    "forbidden_phrases": ["안됩니다", "불가능합니다"],
                    "required_phrases": ["고객님", "감사합니다"],
                    "key_phrases": ["고객님께 딱 맞는 플랜", "부담 없이 상담받아보세요"]
                }
            }
        }


# ============================================
# 추출 결과 스키마
# ============================================

class ExtractedScript(BaseModel):
    """추출된 스크립트 정보"""
    company_name: str = Field("", description="회사명")
    consultation_type: Optional[ConsultationType] = Field(
        default=None,
        description="상담 유형"
    )

    # 공통
    product_name: str = Field(default="", description="제품/서비스명")
    key_features: List[str] = Field(default=[], description="주요 특장점")
    faq: List[QAPair] = Field(default=[], description="FAQ 목록")

    # 판매용
    pricing_info: List[str] = Field(default=[], description="가격/혜택 정보")
    competitive_advantages: List[str] = Field(default=[], description="경쟁사 대비 장점")
    objection_responses: List[ObjectionResponse] = Field(default=[], description="거절 대응")

    # 불만/문제 해결용
    common_problems: List[ProblemSolution] = Field(default=[], description="문제-해결")
    compensation_options: List[str] = Field(default=[], description="보상 옵션")
    escalation_criteria: List[str] = Field(default=[], description="에스컬레이션 기준")

    # 톤 설정
    tone_style: Optional[ToneStyle] = Field(default=None, description="말투 스타일")
    forbidden_phrases: List[str] = Field(default=[], description="금지 표현")
    required_phrases: List[str] = Field(default=[], description="필수 포함 멘트")
    key_phrases: List[str] = Field(default=[], description="핵심 멘트")


class ScriptExtractionResponse(BaseModel):
    """스크립트 추출 응답"""
    success: bool = Field(..., description="추출 성공 여부")
    input_type: ScriptInputType = Field(..., description="입력 방식")
    extracted: ExtractedScript = Field(..., description="추출된 스크립트 정보")
    prompt_context: str = Field(..., description="AI 프롬프트용 컨텍스트")
    metadata: Optional[Dict] = Field(
        default=None,
        description="추가 메타데이터 (PDF의 경우 페이지 수 등)"
    )
