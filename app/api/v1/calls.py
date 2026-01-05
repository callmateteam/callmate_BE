from fastapi import APIRouter, UploadFile, File, HTTPException
from app.schemas.call import CallAnalysisResponse, CallUploadResponse

router = APIRouter()


@router.post("/upload", response_model=CallUploadResponse)
async def upload_call(file: UploadFile = File(...)):
    """
    Upload a call recording for analysis

    - **file**: Audio file (mp3, wav, m4a)
    """
    # Validate file type
    allowed_types = ["audio/mpeg", "audio/wav", "audio/mp4", "audio/x-m4a"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )

    # TODO: Implement file upload logic
    return CallUploadResponse(
        call_id="temp_call_id",
        filename=file.filename,
        status="uploaded",
        message="File uploaded successfully. Processing will be implemented."
    )


@router.post("/analyze", response_model=CallAnalysisResponse)
async def analyze_call(call_id: str):
    """
    Analyze a call and get summary + recommended replies

    - **call_id**: ID of the uploaded call
    """
    # TODO: Implement STT + LLM analysis
    return CallAnalysisResponse(
        call_id=call_id,
        call_summary={
            "customer_needs": "예시: 보험 상품 비교 관심",
            "objections": ["가격 부담", "결정 보류"],
            "decision_stage": "검토 단계"
        },
        next_action="후속 전화 제안",
        recommended_replies=[
            "안녕하세요, 지난번 말씀하신 보험 상품 비교 자료 준비했습니다.",
            "가격 관련해서 더 나은 옵션을 찾아봤어요.",
            "천천히 검토하시고 궁금한 점 있으시면 언제든 연락주세요."
        ]
    )


@router.get("/{call_id}", response_model=CallAnalysisResponse)
async def get_call_analysis(call_id: str):
    """
    Get analysis result for a specific call

    - **call_id**: ID of the call
    """
    # TODO: Implement database lookup
    raise HTTPException(status_code=404, detail="Call not found")
