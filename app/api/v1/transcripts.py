"""API endpoints for transcripts - 사용량 조회만"""

from fastapi import APIRouter, Request
from app.core.rate_limiter import rate_limiter

router = APIRouter()


@router.get(
    "/usage/remaining",
    summary="남은 사용량 조회",
    description="현재 IP의 일일 남은 사용량을 조회합니다."
)
async def get_remaining_usage(request: Request):
    """
    남은 사용량 조회

    ## 반환값
    - `used_duration_ms`: 오늘 사용한 시간 (밀리초)
    - `used_duration_min`: 오늘 사용한 시간 (분)
    - `remaining_duration_ms`: 남은 시간 (밀리초)
    - `remaining_duration_min`: 남은 시간 (분)
    - `max_duration_min`: 일일 최대 사용 시간 (분)
    """
    return rate_limiter.get_remaining(request)
