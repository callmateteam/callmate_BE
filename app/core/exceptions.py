"""
CallMate API 에러 관리 모듈
모든 에러 메시지는 한국어로 통일
"""

from fastapi import HTTPException, status
from typing import Optional


# ============================================
# 에러 코드 정의
# ============================================

class ErrorCode:
    """에러 코드 상수"""
    # 파일 관련
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    FILE_SIZE_EXCEEDED = "FILE_SIZE_EXCEEDED"
    FILE_SAVE_FAILED = "FILE_SAVE_FAILED"

    # 전사 관련
    TRANSCRIPT_NOT_FOUND = "TRANSCRIPT_NOT_FOUND"
    STT_PROCESSING_ERROR = "STT_PROCESSING_ERROR"

    # 분석 관련
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    SUMMARY_FAILED = "SUMMARY_FAILED"
    FEEDBACK_FAILED = "FEEDBACK_FAILED"

    # 스크립트 관련
    PDF_PARSING_ERROR = "PDF_PARSING_ERROR"
    SCRIPT_EXTRACTION_ERROR = "SCRIPT_EXTRACTION_ERROR"

    # 일반
    INVALID_REQUEST = "INVALID_REQUEST"
    SERVER_ERROR = "SERVER_ERROR"

    # 사용량 제한
    AUDIO_DURATION_EXCEEDED = "AUDIO_DURATION_EXCEEDED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"


# ============================================
# 에러 메시지 정의 (한국어)
# ============================================

class ErrorMessage:
    """에러 메시지 상수 (한국어)"""

    # 파일 관련
    INVALID_AUDIO_TYPE = "지원하지 않는 음성 파일 형식입니다. (mp3, wav, m4a만 가능)"
    INVALID_PDF_TYPE = "PDF 파일만 지원합니다."
    FILE_SIZE_EXCEEDED = "파일 크기가 너무 큽니다. (최대 {max_size}MB)"
    FILE_SAVE_FAILED = "파일 저장에 실패했습니다."

    # 전사 관련
    TRANSCRIPT_NOT_FOUND = "전사 결과를 찾을 수 없습니다."
    STT_PROCESSING_ERROR = "음성 변환 중 오류가 발생했습니다."
    STT_TIMEOUT = "음성 변환 시간이 초과되었습니다. 다시 시도해주세요."

    # 분석 관련
    ANALYSIS_FAILED = "통화 분석에 실패했습니다."
    SUMMARY_FAILED = "요약 생성에 실패했습니다."
    FEEDBACK_FAILED = "피드백 생성에 실패했습니다."
    INVALID_CONSULTATION_TYPE = "유효하지 않은 상담 유형입니다. (sales, information, complaint 중 선택)"

    # 스크립트 관련
    PDF_PARSING_ERROR = "PDF 파싱에 실패했습니다."
    SCRIPT_EXTRACTION_ERROR = "스크립트 추출에 실패했습니다."

    # 일반
    SERVER_ERROR = "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
    INVALID_REQUEST = "잘못된 요청입니다."

    # 사용량 제한
    AUDIO_DURATION_EXCEEDED = "음성 파일이 너무 깁니다. (최대 {max_minutes}분)"
    RATE_LIMIT_EXCEEDED = "일일 사용량을 초과했습니다. (남은 시간: {remaining}분)"


# ============================================
# 커스텀 예외 클래스
# ============================================

class CallMateException(Exception):
    """CallMate 기본 예외"""

    def __init__(
        self,
        message: str,
        code: str = ErrorCode.SERVER_ERROR,
        status_code: int = 500
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)

    def to_http_exception(self) -> HTTPException:
        """HTTPException으로 변환"""
        return HTTPException(
            status_code=self.status_code,
            detail={
                "code": self.code,
                "message": self.message
            }
        )


# 파일 관련 예외
class InvalidFileTypeError(CallMateException):
    """지원하지 않는 파일 형식"""

    def __init__(self, file_type: str = "audio"):
        if file_type == "audio":
            message = ErrorMessage.INVALID_AUDIO_TYPE
        elif file_type == "pdf":
            message = ErrorMessage.INVALID_PDF_TYPE
        else:
            message = f"지원하지 않는 파일 형식입니다."

        super().__init__(
            message=message,
            code=ErrorCode.INVALID_FILE_TYPE,
            status_code=400
        )


class FileSizeExceededError(CallMateException):
    """파일 크기 초과"""

    def __init__(self, max_size_mb: int = 50):
        super().__init__(
            message=ErrorMessage.FILE_SIZE_EXCEEDED.format(max_size=max_size_mb),
            code=ErrorCode.FILE_SIZE_EXCEEDED,
            status_code=400
        )


class FileSaveError(CallMateException):
    """파일 저장 실패"""

    def __init__(self, detail: Optional[str] = None):
        message = ErrorMessage.FILE_SAVE_FAILED
        if detail:
            message = f"{message} ({detail})"
        super().__init__(
            message=message,
            code=ErrorCode.FILE_SAVE_FAILED,
            status_code=500
        )


# 전사 관련 예외
class TranscriptNotFoundError(CallMateException):
    """전사 결과 없음"""

    def __init__(self, transcript_id: Optional[str] = None):
        message = ErrorMessage.TRANSCRIPT_NOT_FOUND
        if transcript_id:
            message = f"{message} (ID: {transcript_id})"
        super().__init__(
            message=message,
            code=ErrorCode.TRANSCRIPT_NOT_FOUND,
            status_code=404
        )


class STTProcessingError(CallMateException):
    """STT 처리 오류"""

    def __init__(self, detail: Optional[str] = None):
        message = ErrorMessage.STT_PROCESSING_ERROR
        if detail:
            message = f"{message} ({detail})"
        super().__init__(
            message=message,
            code=ErrorCode.STT_PROCESSING_ERROR,
            status_code=500
        )


# 분석 관련 예외
class AnalysisError(CallMateException):
    """분석 실패"""

    def __init__(self, detail: Optional[str] = None):
        message = ErrorMessage.ANALYSIS_FAILED
        if detail:
            message = f"{message} ({detail})"
        super().__init__(
            message=message,
            code=ErrorCode.ANALYSIS_FAILED,
            status_code=500
        )


class SummaryError(CallMateException):
    """요약 생성 실패"""

    def __init__(self, detail: Optional[str] = None):
        message = ErrorMessage.SUMMARY_FAILED
        if detail:
            message = f"{message} ({detail})"
        super().__init__(
            message=message,
            code=ErrorCode.SUMMARY_FAILED,
            status_code=500
        )


class FeedbackError(CallMateException):
    """피드백 생성 실패"""

    def __init__(self, detail: Optional[str] = None):
        message = ErrorMessage.FEEDBACK_FAILED
        if detail:
            message = f"{message} ({detail})"
        super().__init__(
            message=message,
            code=ErrorCode.FEEDBACK_FAILED,
            status_code=500
        )


class InvalidConsultationTypeError(CallMateException):
    """유효하지 않은 상담 유형"""

    def __init__(self):
        super().__init__(
            message=ErrorMessage.INVALID_CONSULTATION_TYPE,
            code=ErrorCode.INVALID_REQUEST,
            status_code=400
        )


# 스크립트 관련 예외
class PDFParsingError(CallMateException):
    """PDF 파싱 실패"""

    def __init__(self, detail: Optional[str] = None):
        message = ErrorMessage.PDF_PARSING_ERROR
        if detail:
            message = f"{message} ({detail})"
        super().__init__(
            message=message,
            code=ErrorCode.PDF_PARSING_ERROR,
            status_code=400
        )


class ScriptExtractionError(CallMateException):
    """스크립트 추출 실패"""

    def __init__(self, detail: Optional[str] = None):
        message = ErrorMessage.SCRIPT_EXTRACTION_ERROR
        if detail:
            message = f"{message} ({detail})"
        super().__init__(
            message=message,
            code=ErrorCode.SCRIPT_EXTRACTION_ERROR,
            status_code=500
        )


# 사용량 제한 예외
class AudioDurationExceededError(CallMateException):
    """음성 파일 길이 초과"""

    def __init__(self, max_minutes: int = 30):
        super().__init__(
            message=ErrorMessage.AUDIO_DURATION_EXCEEDED.format(max_minutes=max_minutes),
            code=ErrorCode.AUDIO_DURATION_EXCEEDED,
            status_code=400
        )


class RateLimitExceededError(CallMateException):
    """일일 사용량 초과"""

    def __init__(self, remaining_minutes: int = 0):
        super().__init__(
            message=ErrorMessage.RATE_LIMIT_EXCEEDED.format(remaining=remaining_minutes),
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            status_code=429
        )


# ============================================
# 헬퍼 함수
# ============================================

def raise_http_error(
    status_code: int,
    code: str,
    message: str
) -> None:
    """HTTPException 발생"""
    raise HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "message": message
        }
    )


def raise_not_found(message: str = ErrorMessage.TRANSCRIPT_NOT_FOUND) -> None:
    """404 에러 발생"""
    raise_http_error(404, ErrorCode.TRANSCRIPT_NOT_FOUND, message)


def raise_bad_request(message: str = ErrorMessage.INVALID_REQUEST) -> None:
    """400 에러 발생"""
    raise_http_error(400, ErrorCode.INVALID_REQUEST, message)


def raise_server_error(message: str = ErrorMessage.SERVER_ERROR) -> None:
    """500 에러 발생"""
    raise_http_error(500, ErrorCode.SERVER_ERROR, message)
