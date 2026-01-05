"""Schemas for script extraction (MVP)"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum


class ScriptInputType(str, Enum):
    """스크립트 입력 방식"""
    MARKDOWN = "markdown"
    PDF = "pdf"


class QAPair(BaseModel):
    """질문-답변 쌍"""
    question: str = Field(..., description="질문")
    answer: str = Field(..., description="답변")


class MarkdownScriptRequest(BaseModel):
    """마크다운 스크립트 입력 요청"""
    markdown_text: str = Field(
        ...,
        description="마크다운 형식의 스크립트 텍스트",
        min_length=10
    )
    company_name: Optional[str] = Field(
        None,
        description="회사명 (없으면 마크다운에서 추출)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "markdown_text": """# ABC보험

## 인사말
- "안녕하세요, ABC보험 OOO입니다."
- "소중한 시간 내주셔서 감사합니다."

## 상품 소개
- 업계 최저 보험료
- 24시간 고객 상담
- 간편한 모바일 청구

## 자주 묻는 질문
### Q: 가격이 얼마인가요?
A: 월 19,900원부터 시작합니다.

### Q: 해지 시 위약금이 있나요?
A: 1년 이후 해지 시 위약금이 없습니다.

## 클로징 멘트
- "고객님께 맞는 플랜 안내드릴게요"
- "좋은 하루 되세요"
""",
                "company_name": "ABC보험"
            }
        }


class ExtractedScript(BaseModel):
    """추출된 스크립트 정보"""
    company_name: str = Field("", description="회사명")
    greeting: List[str] = Field(default=[], description="인사말 목록")
    product_info: List[str] = Field(default=[], description="상품/서비스 특장점")
    faq: List[QAPair] = Field(default=[], description="FAQ 목록")
    closing: List[str] = Field(default=[], description="마무리 멘트")
    key_phrases: List[str] = Field(default=[], description="핵심 멘트/스크립트")
    objection_handling: List[str] = Field(default=[], description="반대/거절 처리 멘트")


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


class ScriptAnalysisRequest(BaseModel):
    """스크립트 기반 분석 요청"""
    transcript_id: str = Field(..., description="분석할 전사 ID")
    script_context: str = Field(
        ...,
        description="스크립트 추출 API에서 받은 prompt_context"
    )
    company_name: Optional[str] = Field(None, description="회사명")
