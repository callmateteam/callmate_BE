"""
IP 기반 일일 사용량 제한
- 하루 총 30분까지 사용 가능
- 1회 업로드 최대 30분
- 한국 시간(KST) 자정 기준으로 초기화
"""

from datetime import datetime, timezone, timedelta
from typing import Dict
from fastapi import Request

from app.core.exceptions import RateLimitExceededError

# 한국 시간대 (UTC+9)
KST = timezone(timedelta(hours=9))


class IPRateLimiter:
    """IP별 일일 사용량 제한 (한국 시간 기준)"""

    def __init__(self):
        # {ip: {"date": "2024-01-15", "total_duration_ms": 1200000}}
        self.usage: Dict[str, dict] = {}

        # 제한 설정
        self.MAX_DURATION_PER_DAY_MS = 30 * 60 * 1000  # 하루 총 30분 (ms)

    def _get_client_ip(self, request: Request) -> str:
        """클라이언트 IP 추출"""
        # 프록시/로드밸런서 뒤에 있을 경우
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host

    def _get_kst_date(self) -> str:
        """한국 시간 기준 오늘 날짜 반환"""
        return datetime.now(KST).date().isoformat()

    def _reset_if_new_day(self, ip: str):
        """날짜가 바뀌면 초기화 (한국 시간 기준)"""
        today_kst = self._get_kst_date()
        if ip not in self.usage or self.usage[ip]["date"] != today_kst:
            self.usage[ip] = {
                "date": today_kst,
                "total_duration_ms": 0
            }

    def check_limit(self, request: Request, duration_ms: int = 0):
        """
        제한 확인 (초과 시 RateLimitExceededError 발생)

        Args:
            request: FastAPI Request 객체
            duration_ms: 추가할 음성 파일 길이 (밀리초)
        """
        ip = self._get_client_ip(request)
        self._reset_if_new_day(ip)

        usage = self.usage[ip]
        remaining_ms = self.MAX_DURATION_PER_DAY_MS - usage["total_duration_ms"]

        # 남은 시간보다 큰 파일 업로드 시도
        if duration_ms > remaining_ms:
            remaining_min = remaining_ms // 60000
            raise RateLimitExceededError(remaining_minutes=remaining_min).to_http_exception()

    def record_usage(self, request: Request, duration_ms: int):
        """사용량 기록"""
        ip = self._get_client_ip(request)
        self._reset_if_new_day(ip)

        self.usage[ip]["total_duration_ms"] += duration_ms

    def get_remaining(self, request: Request) -> dict:
        """남은 사용량 조회"""
        ip = self._get_client_ip(request)
        self._reset_if_new_day(ip)

        usage = self.usage[ip]
        remaining_ms = self.MAX_DURATION_PER_DAY_MS - usage["total_duration_ms"]

        return {
            "used_duration_ms": usage["total_duration_ms"],
            "used_duration_min": usage["total_duration_ms"] // 60000,
            "remaining_duration_ms": max(0, remaining_ms),
            "remaining_duration_min": max(0, remaining_ms // 60000),
            "max_duration_min": self.MAX_DURATION_PER_DAY_MS // 60000
        }


# 전역 인스턴스
rate_limiter = IPRateLimiter()
