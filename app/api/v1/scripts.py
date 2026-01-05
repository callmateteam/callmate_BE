"""
Script extraction API endpoints for MVP.
Supports markdown text and PDF file inputs.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
import tempfile
import os

from app.schemas.script import (
    MarkdownScriptRequest,
    ScriptExtractionResponse,
    ExtractedScript,
    ScriptInputType,
    QAPair
)
from app.services.script_extractor_service import script_extractor_service

router = APIRouter(prefix="/scripts", tags=["scripts"])


@router.post(
    "/extract/markdown",
    response_model=ScriptExtractionResponse,
    summary="마크다운에서 스크립트 추출",
    description="프론트엔드에서 전달한 마크다운 텍스트에서 영업 스크립트 정보를 추출합니다."
)
async def extract_from_markdown(request: MarkdownScriptRequest):
    """
    마크다운 텍스트에서 스크립트 정보 추출

    ## 지원하는 마크다운 형식

    ```markdown
    # 회사명

    ## 인사말
    - "인사말 1"
    - "인사말 2"

    ## 상품 소개
    - 특장점 1
    - 특장점 2

    ## 자주 묻는 질문
    ### Q: 질문 내용
    A: 답변 내용

    ## 클로징 멘트
    - "마무리 멘트"
    ```

    ## 반환값
    - `extracted`: 섹션별로 파싱된 스크립트 정보
    - `prompt_context`: AI 분석 시 사용할 컨텍스트 문자열
    """
    try:
        # 마크다운에서 추출
        extracted_data = script_extractor_service.extract_from_markdown(
            request.markdown_text
        )

        # 회사명 오버라이드
        if request.company_name:
            extracted_data["company_name"] = request.company_name

        # 프롬프트 컨텍스트 생성
        prompt_context = script_extractor_service.generate_prompt_context(
            extracted_data,
            request.company_name
        )

        # FAQ 형식 변환
        faq_list = []
        for qa in extracted_data.get("faq", []):
            if isinstance(qa, dict):
                faq_list.append(QAPair(
                    question=qa.get("question", ""),
                    answer=qa.get("answer", "")
                ))

        return ScriptExtractionResponse(
            success=True,
            input_type=ScriptInputType.MARKDOWN,
            extracted=ExtractedScript(
                company_name=extracted_data.get("company_name", ""),
                greeting=extracted_data.get("greeting", []),
                product_info=extracted_data.get("product_info", []),
                faq=faq_list,
                closing=extracted_data.get("closing", []),
                key_phrases=extracted_data.get("key_phrases", []),
                objection_handling=extracted_data.get("objection_handling", [])
            ),
            prompt_context=prompt_context,
            metadata={
                "char_count": len(request.markdown_text),
                "sections_found": len([
                    k for k in ["greeting", "product_info", "faq", "closing"]
                    if extracted_data.get(k)
                ])
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"마크다운 파싱 실패: {str(e)}"
        )


@router.post(
    "/extract/pdf",
    response_model=ScriptExtractionResponse,
    summary="PDF에서 스크립트 추출",
    description="업로드된 PDF 파일에서 영업 스크립트 정보를 추출합니다."
)
async def extract_from_pdf(
    file: UploadFile = File(..., description="PDF 스크립트 파일"),
    company_name: Optional[str] = Form(None, description="회사명")
):
    """
    PDF 파일에서 스크립트 정보 추출

    ## 지원 파일
    - PDF 형식 (.pdf)
    - 최대 10MB

    ## 추출 방식
    - pdfplumber로 텍스트 추출
    - 따옴표 안의 멘트 자동 인식
    - 섹션 헤더 기반 분류

    ## 반환값
    - `extracted`: 섹션별로 파싱된 스크립트 정보
    - `prompt_context`: AI 분석 시 사용할 컨텍스트 문자열
    - `metadata.page_count`: PDF 페이지 수
    """
    # 파일 유효성 검사
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="PDF 파일만 지원합니다."
        )

    # 파일 크기 검사 (10MB)
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="파일 크기는 10MB를 초과할 수 없습니다."
        )

    try:
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        try:
            # PDF에서 추출
            extracted_data = script_extractor_service.extract_from_pdf(tmp_path)

            # 회사명 오버라이드
            if company_name:
                extracted_data["company_name"] = company_name

            # 프롬프트 컨텍스트 생성
            prompt_context = script_extractor_service.generate_prompt_context(
                extracted_data,
                company_name
            )

            # FAQ 형식 변환
            faq_list = []
            for qa in extracted_data.get("faq", []):
                if isinstance(qa, dict):
                    faq_list.append(QAPair(
                        question=qa.get("question", ""),
                        answer=qa.get("answer", "")
                    ))

            return ScriptExtractionResponse(
                success=True,
                input_type=ScriptInputType.PDF,
                extracted=ExtractedScript(
                    company_name=extracted_data.get("company_name", ""),
                    greeting=extracted_data.get("greeting", []),
                    product_info=extracted_data.get("product_info", []),
                    faq=faq_list,
                    closing=extracted_data.get("closing", []),
                    key_phrases=extracted_data.get("key_phrases", []),
                    objection_handling=extracted_data.get("objection_handling", [])
                ),
                prompt_context=prompt_context,
                metadata={
                    "filename": file.filename,
                    "page_count": extracted_data.get("page_count", 0),
                    "char_count": len(extracted_data.get("raw_text", ""))
                }
            )

        finally:
            # 임시 파일 삭제
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"PDF 파싱 실패: {str(e)}"
        )


@router.get(
    "/template/markdown",
    summary="마크다운 템플릿 반환",
    description="프론트엔드에서 사용할 마크다운 스크립트 템플릿을 반환합니다."
)
async def get_markdown_template():
    """
    마크다운 스크립트 작성 템플릿 반환

    프론트엔드에서 이 템플릿을 보여주고,
    사용자가 채워서 /extract/markdown API로 전송
    """
    template = """# 회사명을 입력하세요

## 인사말
- "안녕하세요, [회사명] [담당자명]입니다."
- "전화 주셔서 감사합니다."

## 상품 소개
- 핵심 특장점 1
- 핵심 특장점 2
- 핵심 특장점 3

## 자주 묻는 질문
### Q: 가격이 얼마인가요?
A: [가격 정보를 입력하세요]

### Q: 배송은 얼마나 걸리나요?
A: [배송 정보를 입력하세요]

## 반대 처리
- 가격이 비싸다고 할 때: "고객님, 가성비 측면에서 보시면..."
- 생각해보겠다고 할 때: "네, 천천히 생각해보세요. 혹시 추가로 궁금하신 점 있으실까요?"

## 클로징 멘트
- "감사합니다. 좋은 하루 되세요."
- "추가 문의사항 있으시면 언제든 연락주세요."
"""

    return {
        "template": template,
        "sections": [
            {"name": "인사말", "description": "전화 시작 시 사용하는 인사말"},
            {"name": "상품 소개", "description": "상품/서비스의 핵심 특장점"},
            {"name": "자주 묻는 질문", "description": "고객이 자주 묻는 질문과 모범 답변"},
            {"name": "반대 처리", "description": "고객이 거절/반대할 때 응대 방법"},
            {"name": "클로징 멘트", "description": "통화 종료 시 사용하는 마무리 멘트"}
        ],
        "tips": [
            "따옴표(\"\")로 감싼 문구는 핵심 멘트로 자동 인식됩니다",
            "각 섹션은 ## 으로 시작합니다",
            "리스트는 - 또는 숫자로 시작합니다",
            "Q&A는 ### Q: 와 A: 형식을 사용합니다"
        ]
    }
