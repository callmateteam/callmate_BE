"""
Custom exceptions for CallMate API.
"""

from fastapi import HTTPException, status


class CallMateException(Exception):
    """Base exception for CallMate"""

    def __init__(self, message: str, code: str = "UNKNOWN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class TranscriptNotFoundError(CallMateException):
    """Raised when transcript is not found"""

    def __init__(self, transcript_id: str):
        super().__init__(
            message=f"전사 결과를 찾을 수 없습니다: {transcript_id}",
            code="TRANSCRIPT_NOT_FOUND"
        )
        self.transcript_id = transcript_id


class CompanyNotFoundError(CallMateException):
    """Raised when company is not found"""

    def __init__(self, company_id: str):
        super().__init__(
            message=f"회사를 찾을 수 없습니다: {company_id}",
            code="COMPANY_NOT_FOUND"
        )
        self.company_id = company_id


class STTProcessingError(CallMateException):
    """Raised when STT processing fails"""

    def __init__(self, message: str = "음성 변환 처리 중 오류가 발생했습니다"):
        super().__init__(message=message, code="STT_PROCESSING_ERROR")


class LLMServiceError(CallMateException):
    """Raised when LLM API call fails"""

    def __init__(self, provider: str, message: str = "AI 분석 중 오류가 발생했습니다"):
        super().__init__(message=message, code="LLM_SERVICE_ERROR")
        self.provider = provider


class PDFParsingError(CallMateException):
    """Raised when PDF parsing fails"""

    def __init__(self, message: str = "PDF 파싱 중 오류가 발생했습니다"):
        super().__init__(message=message, code="PDF_PARSING_ERROR")


class ScriptExtractionError(CallMateException):
    """Raised when script extraction fails"""

    def __init__(self, message: str = "스크립트 추출 중 오류가 발생했습니다"):
        super().__init__(message=message, code="SCRIPT_EXTRACTION_ERROR")


class FileSizeExceededError(CallMateException):
    """Raised when file size exceeds limit"""

    def __init__(self, max_size_mb: int = 10):
        super().__init__(
            message=f"파일 크기는 {max_size_mb}MB를 초과할 수 없습니다",
            code="FILE_SIZE_EXCEEDED"
        )


class InvalidFileTypeError(CallMateException):
    """Raised when file type is not supported"""

    def __init__(self, expected_type: str):
        super().__init__(
            message=f"{expected_type} 파일만 지원합니다",
            code="INVALID_FILE_TYPE"
        )


class PlanLimitExceededError(CallMateException):
    """Raised when plan limit is exceeded"""

    def __init__(self, limit_type: str, current_plan: str):
        super().__init__(
            message=f"{current_plan} 플랜의 {limit_type} 한도를 초과했습니다. 업그레이드가 필요합니다.",
            code="PLAN_LIMIT_EXCEEDED"
        )


# HTTP Exception helpers
def raise_not_found(resource: str, resource_id: str):
    """Raise 404 Not Found"""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{resource}을(를) 찾을 수 없습니다: {resource_id}"
    )


def raise_bad_request(message: str):
    """Raise 400 Bad Request"""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=message
    )


def raise_server_error(message: str = "서버 오류가 발생했습니다"):
    """Raise 500 Internal Server Error"""
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=message
    )


def raise_forbidden(message: str = "접근이 거부되었습니다"):
    """Raise 403 Forbidden"""
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=message
    )
