"""
File upload API endpoints

[향후 확장용] 파일 영구 저장이 필요할 때 사용하는 API입니다.
현재 MVP에서는 WebSocket 전사 시 임시 파일 처리 후 삭제하며,
프론트엔드에서 결과를 저장하는 방식입니다.

추후 다음 기능 구현 시 사용:
- 통화 녹음 파일 보관
- 전사 결과 서버 저장
- 스크립트 PDF 관리
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Optional

from app.services.s3_service import s3_service
from app.core.config import settings

router = APIRouter(prefix="/files", tags=["files (향후 확장용)"])


@router.post(
    "/upload/audio",
    summary="음성 파일 업로드",
    description="음성 파일을 S3(배포) 또는 로컬(개발)에 업로드합니다."
)
async def upload_audio(
    file: UploadFile = File(..., description="음성 파일 (mp3, wav, m4a)")
):
    """
    음성 파일 업로드

    ## 지원 형식
    - mp3, wav, m4a

    ## 최대 크기
    - 50MB

    ## 반환값
    - `file_key`: 파일 식별자 (나중에 조회/삭제 시 사용)
    - `file_url`: 파일 URL (S3) 또는 경로 (로컬)
    - `storage`: 저장소 타입 (s3 / local)
    """
    # 확장자 검증
    allowed_extensions = {".mp3", ".wav", ".m4a"}
    filename = file.filename or "audio.mp3"
    ext = filename.lower().split(".")[-1] if "." in filename else ""

    if f".{ext}" not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_FILE_TYPE",
                "message": "지원하지 않는 음성 형식입니다. (mp3, wav, m4a만 가능)"
            }
        )

    # 파일 읽기
    content = await file.read()

    # 크기 검증 (50MB)
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": f"파일이 너무 큽니다. (최대 {settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB)"
            }
        )

    # Content-Type 매핑
    content_types = {
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "m4a": "audio/mp4"
    }

    # 업로드
    file_key, file_url = await s3_service.upload_file(
        file_content=content,
        filename=filename,
        folder="audio",
        content_type=content_types.get(ext, "audio/mpeg")
    )

    return {
        "file_key": file_key,
        "file_url": file_url,
        "storage": "s3" if settings.use_s3 else "local",
        "filename": filename,
        "size_bytes": len(content)
    }


@router.post(
    "/upload/pdf",
    summary="PDF 파일 업로드",
    description="PDF 파일을 S3(배포) 또는 로컬(개발)에 업로드합니다."
)
async def upload_pdf(
    file: UploadFile = File(..., description="PDF 파일")
):
    """
    PDF 파일 업로드 (스크립트 등)

    ## 지원 형식
    - pdf

    ## 최대 크기
    - 10MB

    ## 반환값
    - `file_key`: 파일 식별자
    - `file_url`: 파일 URL
    - `storage`: 저장소 타입
    """
    # 확장자 검증
    filename = file.filename or "document.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_FILE_TYPE",
                "message": "PDF 파일만 업로드 가능합니다."
            }
        )

    # 파일 읽기
    content = await file.read()

    # 크기 검증 (10MB)
    max_pdf_size = 10 * 1024 * 1024
    if len(content) > max_pdf_size:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": "PDF 파일이 너무 큽니다. (최대 10MB)"
            }
        )

    # 업로드
    file_key, file_url = await s3_service.upload_file(
        file_content=content,
        filename=filename,
        folder="pdf",
        content_type="application/pdf"
    )

    return {
        "file_key": file_key,
        "file_url": file_url,
        "storage": "s3" if settings.use_s3 else "local",
        "filename": filename,
        "size_bytes": len(content)
    }


@router.delete(
    "/{file_key:path}",
    summary="파일 삭제",
    description="업로드된 파일을 삭제합니다."
)
async def delete_file(file_key: str):
    """
    파일 삭제

    ## 파라미터
    - `file_key`: 업로드 시 반환받은 file_key

    ## 반환값
    - `success`: 삭제 성공 여부
    """
    success = await s3_service.delete_file(file_key)

    if not success:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "FILE_NOT_FOUND",
                "message": "파일을 찾을 수 없습니다."
            }
        )

    return {"success": True, "file_key": file_key}


@router.get(
    "/download-url/{file_key:path}",
    summary="다운로드 URL 생성",
    description="S3 Presigned URL을 생성합니다. (S3 사용 시에만 동작)"
)
async def get_download_url(file_key: str, expiration: int = 3600):
    """
    S3 Presigned URL 생성 (다운로드용)

    ## 파라미터
    - `file_key`: 파일 키
    - `expiration`: URL 만료 시간 (초, 기본 1시간)

    ## 반환값
    - `download_url`: 임시 다운로드 URL
    """
    if not settings.use_s3:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "S3_NOT_CONFIGURED",
                "message": "S3가 설정되지 않았습니다. 로컬 환경에서는 사용할 수 없습니다."
            }
        )

    url = s3_service.generate_presigned_url(file_key, expiration)

    if not url:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "FILE_NOT_FOUND",
                "message": "파일을 찾을 수 없습니다."
            }
        )

    return {
        "file_key": file_key,
        "download_url": url,
        "expires_in_seconds": expiration
    }
