"""
Script extraction API endpoints for MVP.
Supports form input (4-step wizard) and PDF file inputs.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
import tempfile
import os

from app.schemas.script import (
    FormScriptRequest,
    ScriptExtractionResponse,
    ExtractedScript,
    ScriptInputType,
    ConsultationType,
    ToneStyle,
    QAPair,
    ObjectionResponse,
    ProblemSolution
)
from app.services.script_extractor_service import script_extractor_service

router = APIRouter(prefix="/scripts", tags=["scripts"])


@router.post(
    "/extract/form",
    response_model=ScriptExtractionResponse,
    summary="폼 입력으로 스크립트 생성 (4단계)",
    description="프론트엔드 4단계 폼에서 입력받은 데이터로 스크립트 컨텍스트를 생성합니다."
)
async def extract_from_form(request: FormScriptRequest):
    """
    폼 입력 방식으로 스크립트 컨텍스트 생성 (4단계 위자드)

    ## 입력 단계
    1. **기본 정보**: company_name (회사명 또는 이름)
    2. **상담 유형**: consultation_type (information/sales/complaint)
    3. **세부 정보**: 유형에 따라 다른 필드
       - information: information_details
       - sales: sales_details
       - complaint: complaint_details
    4. **톤 & 설정** (선택): tone_settings

    ## 반환값
    - `extracted`: 입력한 스크립트 정보
    - `prompt_context`: AI 분석 시 사용할 컨텍스트 문자열
    """
    # 폼 데이터에서 추출
    extracted_data = script_extractor_service.extract_from_form(request)

    # 프롬프트 컨텍스트 생성
    prompt_context = script_extractor_service.generate_prompt_context(
        extracted_data,
        request.company_name
    )

    # ExtractedScript 객체 생성
    extracted = ExtractedScript(
        company_name=extracted_data["company_name"],
        consultation_type=ConsultationType(extracted_data["consultation_type"]) if extracted_data.get("consultation_type") else None,
        product_name=extracted_data.get("product_name", ""),
        key_features=extracted_data.get("key_features", []),
        faq=[QAPair(**qa) for qa in extracted_data.get("faq", [])],
        pricing_info=extracted_data.get("pricing_info", []),
        competitive_advantages=extracted_data.get("competitive_advantages", []),
        objection_responses=[ObjectionResponse(**obj) for obj in extracted_data.get("objection_responses", [])],
        common_problems=[ProblemSolution(**ps) for ps in extracted_data.get("common_problems", [])],
        compensation_options=extracted_data.get("compensation_options", []),
        escalation_criteria=extracted_data.get("escalation_criteria", []),
        tone_style=ToneStyle(extracted_data["tone_style"]) if extracted_data.get("tone_style") else None,
        forbidden_phrases=extracted_data.get("forbidden_phrases", []),
        required_phrases=extracted_data.get("required_phrases", []),
        key_phrases=extracted_data.get("key_phrases", [])
    )

    # 메타데이터 계산
    total_items = (
        len(extracted_data.get("key_features", [])) +
        len(extracted_data.get("faq", [])) +
        len(extracted_data.get("pricing_info", [])) +
        len(extracted_data.get("objection_responses", [])) +
        len(extracted_data.get("common_problems", [])) +
        len(extracted_data.get("key_phrases", []))
    )

    return ScriptExtractionResponse(
        success=True,
        input_type=ScriptInputType.FORM,
        extracted=extracted,
        prompt_context=prompt_context,
        metadata={
            "consultation_type": extracted_data.get("consultation_type"),
            "total_items": total_items,
            "has_tone_settings": request.tone_settings is not None
        }
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

            # ExtractedScript 객체 생성
            extracted = ExtractedScript(
                company_name=extracted_data.get("company_name", ""),
                consultation_type=ConsultationType(extracted_data["consultation_type"]) if extracted_data.get("consultation_type") else None,
                product_name=extracted_data.get("product_name", ""),
                key_features=extracted_data.get("key_features", []),
                faq=[QAPair(**qa) for qa in extracted_data.get("faq", []) if isinstance(qa, dict)],
                pricing_info=extracted_data.get("pricing_info", []),
                competitive_advantages=extracted_data.get("competitive_advantages", []),
                objection_responses=[ObjectionResponse(**obj) for obj in extracted_data.get("objection_responses", []) if isinstance(obj, dict)],
                common_problems=[ProblemSolution(**ps) for ps in extracted_data.get("common_problems", []) if isinstance(ps, dict)],
                compensation_options=extracted_data.get("compensation_options", []),
                escalation_criteria=extracted_data.get("escalation_criteria", []),
                tone_style=ToneStyle(extracted_data["tone_style"]) if extracted_data.get("tone_style") else None,
                forbidden_phrases=extracted_data.get("forbidden_phrases", []),
                required_phrases=extracted_data.get("required_phrases", []),
                key_phrases=extracted_data.get("key_phrases", [])
            )

            return ScriptExtractionResponse(
                success=True,
                input_type=ScriptInputType.PDF,
                extracted=extracted,
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
