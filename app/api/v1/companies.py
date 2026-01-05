"""Company management API endpoints (SaaS)"""

import os
import uuid
import shutil
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query

from app.schemas.company import (
    CompanyCreate,
    CompanyResponse,
    ScriptUpload,
    ScriptResponse,
    PlanType,
    IndustryType
)
from app.services.company_prompt_service import company_prompt_service


router = APIRouter(prefix="/companies", tags=["Companies (SaaS)"])

# Upload directory
UPLOAD_DIR = "uploads/scripts"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post(
    "",
    response_model=CompanyResponse,
    summary="회사 등록",
    description="""
새로운 회사(테넌트)를 등록합니다.

**플랜별 기능:**
- **free**: 일반 분석만 가능 (스크립트 업로드 불가)
- **basic**: PDF 스크립트 1개 업로드 가능
- **pro**: PDF 스크립트 5개 + 커스텀 프롬프트
- **enterprise**: 무제한 스크립트 + 전용 지원
"""
)
async def register_company(company: CompanyCreate) -> CompanyResponse:
    """Register a new company"""
    company_id = str(uuid.uuid4())[:8]

    result = company_prompt_service.register_company(
        company_id=company_id,
        name=company.name,
        industry=company.industry.value,
        config={
            "plan": company.plan.value,
            "contact_email": company.contact_email,
            "description": company.description
        }
    )

    return CompanyResponse(
        id=result["id"],
        name=result["name"],
        industry=IndustryType(result["industry"]),
        plan=PlanType(result["config"]["plan"]),
        contact_email=result["config"]["contact_email"],
        description=result["config"].get("description"),
        scripts_count=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@router.get(
    "/{company_id}",
    response_model=CompanyResponse,
    summary="회사 정보 조회",
    description="회사 ID로 회사 정보를 조회합니다."
)
async def get_company(company_id: str) -> CompanyResponse:
    """Get company by ID"""
    company = company_prompt_service.get_company(company_id)

    if not company:
        raise HTTPException(status_code=404, detail=f"Company {company_id} not found")

    scripts = company_prompt_service.get_company_scripts(company_id)

    return CompanyResponse(
        id=company["id"],
        name=company["name"],
        industry=IndustryType(company["industry"]),
        plan=PlanType(company["config"]["plan"]),
        contact_email=company["config"]["contact_email"],
        description=company["config"].get("description"),
        scripts_count=len(scripts),
        created_at=datetime.utcnow(),  # TODO: Store actual timestamp
        updated_at=datetime.utcnow()
    )


@router.post(
    "/{company_id}/scripts",
    response_model=ScriptResponse,
    summary="스크립트 PDF 업로드",
    description="""
회사의 영업 스크립트 PDF를 업로드합니다.

**플랜별 제한:**
- free: 업로드 불가
- basic: 1개
- pro: 5개
- enterprise: 무제한

PDF에서 자동으로 다음을 추출합니다:
- 핵심 멘트/문구
- 섹션별 내용 (인사, 상품소개, 마무리 등)
- 권장 응대 스크립트
"""
)
async def upload_script(
    company_id: str,
    file: UploadFile = File(..., description="PDF 파일"),
    name: str = Form(..., description="스크립트 이름"),
    script_type: str = Form(..., description="스크립트 유형 (sales, support, objection_handling)"),
    description: Optional[str] = Form(None, description="스크립트 설명")
) -> ScriptResponse:
    """Upload a script PDF for a company"""
    # Verify company exists
    company = company_prompt_service.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail=f"Company {company_id} not found")

    # Check plan limits
    plan = company["config"].get("plan", "free")
    scripts = company_prompt_service.get_company_scripts(company_id)

    plan_limits = {
        "free": 0,
        "basic": 1,
        "pro": 5,
        "enterprise": float("inf")
    }

    if len(scripts) >= plan_limits.get(plan, 0):
        raise HTTPException(
            status_code=403,
            detail=f"Plan '{plan}' allows maximum {plan_limits[plan]} scripts. "
                   f"Current: {len(scripts)}. Please upgrade your plan."
        )

    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Save file
    script_id = str(uuid.uuid4())[:8]
    file_path = os.path.join(UPLOAD_DIR, company_id, f"{script_id}.pdf")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Parse and store
    try:
        script_data = company_prompt_service.add_script(
            company_id=company_id,
            script_id=script_id,
            name=name,
            script_type=script_type,
            file_path=file_path,
            description=description
        )
    except Exception as e:
        # Clean up file on failure
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")

    return ScriptResponse(
        id=script_data["id"],
        company_id=script_data["company_id"],
        name=script_data["name"],
        script_type=script_data["script_type"],
        description=script_data.get("description"),
        file_path=script_data["file_path"],
        key_phrases=script_data.get("key_phrases", []),
        created_at=datetime.utcnow()
    )


@router.get(
    "/{company_id}/scripts",
    response_model=List[ScriptResponse],
    summary="회사 스크립트 목록",
    description="회사에 등록된 모든 스크립트를 조회합니다."
)
async def get_company_scripts(company_id: str) -> List[ScriptResponse]:
    """Get all scripts for a company"""
    company = company_prompt_service.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail=f"Company {company_id} not found")

    scripts = company_prompt_service.get_company_scripts(company_id)

    return [
        ScriptResponse(
            id=s["id"],
            company_id=s["company_id"],
            name=s["name"],
            script_type=s["script_type"],
            description=s.get("description"),
            file_path=s["file_path"],
            key_phrases=s.get("key_phrases", []),
            created_at=datetime.utcnow()
        )
        for s in scripts
    ]


@router.delete(
    "/{company_id}/scripts/{script_id}",
    summary="스크립트 삭제",
    description="회사의 스크립트를 삭제합니다."
)
async def delete_script(company_id: str, script_id: str):
    """Delete a script"""
    company = company_prompt_service.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail=f"Company {company_id} not found")

    success = company_prompt_service.delete_script(company_id, script_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Script {script_id} not found")

    # Delete file
    file_path = os.path.join(UPLOAD_DIR, company_id, f"{script_id}.pdf")
    if os.path.exists(file_path):
        os.remove(file_path)

    return {"message": "Script deleted successfully"}


@router.get(
    "/{company_id}/prompt-preview",
    summary="프롬프트 미리보기",
    description="""
회사의 스크립트를 기반으로 생성되는 프롬프트 컨텍스트를 미리봅니다.
실제 분석 시 이 컨텍스트가 기본 분석 프롬프트에 추가됩니다.
"""
)
async def preview_prompt_context(company_id: str):
    """Preview the generated prompt context for a company"""
    company = company_prompt_service.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail=f"Company {company_id} not found")

    context = company_prompt_service.get_prompt_context(company_id)

    return {
        "company_id": company_id,
        "company_name": company["name"],
        "scripts_count": len(company_prompt_service.get_company_scripts(company_id)),
        "prompt_context": context,
        "context_length": len(context)
    }
