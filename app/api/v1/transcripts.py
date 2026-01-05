"""API endpoints for call transcripts with speaker diarization"""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import Optional
import os
import uuid
import aiofiles
from pathlib import Path

from app.schemas.transcript import (
    TranscriptResponse,
    SpeakerSeparatedResponse,
    SpeakerSegment,
    Utterance
)
from app.services.stt_service import stt_service
from app.core.config import settings
from app.api.v1.examples import TRANSCRIPT_EXAMPLE, SPEAKER_SEPARATED_EXAMPLE

router = APIRouter()

# In-memory storage for demo (replace with DB later)
transcripts_store = {}


@router.post(
    "/upload-and-transcribe",
    response_model=TranscriptResponse,
    summary="음성 파일 업로드 및 전사",
    description="""
    음성 파일을 업로드하고 화자 분리(Speaker Diarization)가 적용된 전사 결과를 받습니다.

    **처리 과정:**
    1. 음성 파일 업로드 (mp3, wav, m4a)
    2. AssemblyAI STT 처리
    3. 화자 분리 (SPEAKER_00 → A, SPEAKER_01 → B)
    4. 시간순 발화 목록 생성

    **처리 시간:** 1분 통화 기준 약 10-20초

    **비용:** 분당 $0.00025
    """,
    responses={
        200: {
            "description": "전사 성공",
            "content": {
                "application/json": {
                    "example": TRANSCRIPT_EXAMPLE
                }
            }
        },
        400: {
            "description": "잘못된 파일 형식",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid file type. Allowed: audio/mpeg, audio/wav, audio/mp4, audio/x-m4a"}
                }
            }
        },
        500: {
            "description": "전사 실패",
            "content": {
                "application/json": {
                    "example": {"detail": "Transcription failed: [error message]"}
                }
            }
        }
    }
)
async def upload_and_transcribe(
    file: UploadFile = File(..., description="음성 파일 (mp3, wav, m4a)"),
    language_code: str = "ko"
):
    """
    음성 파일 업로드 및 전사
    """
    # Validate file type
    allowed_types = ["audio/mpeg", "audio/wav", "audio/mp4", "audio/x-m4a"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )

    # Create upload directory if not exists
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix
    file_path = upload_dir / f"{file_id}{file_extension}"

    # Save uploaded file
    try:
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Transcribe with speaker diarization
    try:
        result = stt_service.transcribe_with_speakers(
            audio_file_path=str(file_path),
            language_code=language_code
        )
    except Exception as e:
        # Clean up uploaded file
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

    # Store result (in-memory for now)
    transcript_id = result["transcript_id"]
    transcripts_store[transcript_id] = {
        "file_path": str(file_path),
        "result": result
    }

    # Convert to response model
    utterances = [Utterance(**u) for u in result["utterances"]]

    return TranscriptResponse(
        transcript_id=transcript_id,
        full_text=result["full_text"],
        utterances=utterances,
        speakers=result["speakers"],
        duration=result["duration"]
    )


@router.get(
    "/{transcript_id}/speakers",
    response_model=SpeakerSeparatedResponse,
    summary="화자별 분리된 대화 조회",
    description="""
    화자별로 분리된 통화 내용을 조회합니다.

    **주요 기능:**
    - 화자별(A, B, C) 전체 발화 내용
    - 각 화자의 총 발화 횟수 및 시간
    - 대화 형식으로 포맷팅된 텍스트 (A: ... B: ...)

    **사용 시나리오:**
    - 화자별 발화 내용 확인
    - 대화 흐름 파악
    - LLM 분석 전 데이터 준비
    """,
    responses={
        200: {
            "description": "조회 성공",
            "content": {
                "application/json": {
                    "example": SPEAKER_SEPARATED_EXAMPLE
                }
            }
        },
        404: {
            "description": "전사 결과를 찾을 수 없음",
            "content": {
                "application/json": {
                    "example": {"detail": "Transcript not found"}
                }
            }
        }
    }
)
async def get_speaker_separated_transcript(
    transcript_id: str,
    format_type: str = "simple"
):
    """
    화자별 분리된 대화 조회
    """

    Returns:
        Speaker-separated conversation with each speaker's utterances grouped

    Example response:
        ```json
        {
          "speakers": ["A", "B"],
          "speaker_segments": [
            {
              "speaker": "A",
              "total_utterances": 5,
              "utterances": [...],
              "full_text": "안녕하세요... 보험 상담..."
            },
            {
              "speaker": "B",
              "total_utterances": 4,
              "utterances": [...],
              "full_text": "네, 안녕하세요... 어떤 상품..."
            }
          ],
          "conversation_formatted": "A: 안녕하세요\\nB: 네, 안녕하세요..."
        }
        ```
    """
    # Get stored transcript
    if transcript_id not in transcripts_store:
        raise HTTPException(status_code=404, detail="Transcript not found")

    stored = transcripts_store[transcript_id]
    result = stored["result"]

    # Build speaker segments
    speaker_segments = []
    for speaker in result["speakers"]:
        # Get all utterances for this speaker
        speaker_utterances = stt_service.get_speaker_segments(
            result["utterances"],
            speaker
        )

        # Calculate total duration
        total_duration = sum(
            u["end"] - u["start"] for u in speaker_utterances
        )

        # Combine all text
        full_text = " ".join(u["text"] for u in speaker_utterances)

        # Convert to Utterance models
        utterances = [Utterance(**u) for u in speaker_utterances]

        speaker_segments.append(
            SpeakerSegment(
                speaker=speaker,
                total_utterances=len(speaker_utterances),
                total_duration=total_duration,
                utterances=utterances,
                full_text=full_text
            )
        )

    # Format conversation
    conversation_formatted = stt_service.format_conversation(
        result["utterances"],
        format_type=format_type
    )

    return SpeakerSeparatedResponse(
        transcript_id=transcript_id,
        speakers=result["speakers"],
        duration=result["duration"],
        speaker_segments=speaker_segments,
        conversation_formatted=conversation_formatted
    )


@router.get("/{transcript_id}", response_model=TranscriptResponse)
async def get_transcript(transcript_id: str):
    """
    Get full transcript by ID

    - **transcript_id**: Transcript ID
    """
    if transcript_id not in transcripts_store:
        raise HTTPException(status_code=404, detail="Transcript not found")

    stored = transcripts_store[transcript_id]
    result = stored["result"]

    utterances = [Utterance(**u) for u in result["utterances"]]

    return TranscriptResponse(
        transcript_id=transcript_id,
        full_text=result["full_text"],
        utterances=utterances,
        speakers=result["speakers"],
        duration=result["duration"]
    )


@router.delete("/{transcript_id}")
async def delete_transcript(transcript_id: str):
    """
    Delete transcript and associated file

    - **transcript_id**: Transcript ID
    """
    if transcript_id not in transcripts_store:
        raise HTTPException(status_code=404, detail="Transcript not found")

    stored = transcripts_store[transcript_id]

    # Delete file
    file_path = Path(stored["file_path"])
    if file_path.exists():
        os.remove(file_path)

    # Delete from store
    del transcripts_store[transcript_id]

    return {"message": "Transcript deleted successfully"}


@router.get("/{transcript_id}/conversation")
async def get_formatted_conversation(
    transcript_id: str,
    format_type: str = "simple"
):
    """
    Get formatted conversation text

    - **transcript_id**: Transcript ID
    - **format_type**: "simple" or "detailed"

    Returns:
        Plain text formatted conversation

    Example (simple):
        ```
        A: 안녕하세요
        B: 네, 안녕하세요
        A: 보험 상담 받고 싶은데요
        ```

    Example (detailed):
        ```
        [0.0s - 2.5s] A: 안녕하세요
        [2.6s - 5.1s] B: 네, 안녕하세요
        [5.2s - 8.3s] A: 보험 상담 받고 싶은데요
        ```
    """
    if transcript_id not in transcripts_store:
        raise HTTPException(status_code=404, detail="Transcript not found")

    stored = transcripts_store[transcript_id]
    result = stored["result"]

    conversation = stt_service.format_conversation(
        result["utterances"],
        format_type=format_type
    )

    return {"conversation": conversation}
