"""
GPT Actions용 통화 분석 API 엔드포인트
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
import os
import time
from pathlib import Path
import httpx

from app.core.config import settings
from app.utils.audio import get_audio_duration_ms
from app.services.stt_service_async import AsyncSTTService
from app.services.analysis_service import analysis_service

router = APIRouter(prefix="/calls", tags=["calls"])


class AnalyzeUrlRequest(BaseModel):
    audio_url: str
    my_speaker: Optional[str] = None
    consultation_type: str = "sales"


class AnalyzeSampleRequest(BaseModel):
    sample_id: str = "sample1"
    my_speaker: Optional[str] = None
    consultation_type: str = "sales"


def _prepare_analysis_data(utterances: list, speakers: list, my_speaker: Optional[str] = None):
    """전사 결과에서 분석 데이터 전처리"""
    conversation_formatted = "\n".join(
        f"{u['speaker']}: {u['text']}" for u in utterances
    )

    speaker_segments = []
    for speaker in speakers:
        speaker_utterances = [u for u in utterances if u["speaker"] == speaker]
        full_text = " ".join(u["text"] for u in speaker_utterances)
        speaker_segments.append({
            "speaker": speaker,
            "full_text": full_text,
            "utterances": speaker_utterances
        })

    if my_speaker and my_speaker in speakers:
        agent_speaker = my_speaker
        other_speakers = [s for s in speakers if s != agent_speaker]
    else:
        customer_speaker = analysis_service._detect_customer_speaker(
            speaker_segments, utterances
        )
        agent_speaker = [s for s in speakers if s != customer_speaker][0] if len(speakers) > 1 else speakers[0]
        other_speakers = [s for s in speakers if s != agent_speaker]

    other_text = ""
    for seg in speaker_segments:
        if seg["speaker"] in other_speakers:
            other_text += seg["full_text"] + " "

    agent_text = ""
    for seg in speaker_segments:
        if seg["speaker"] == agent_speaker:
            agent_text = seg["full_text"]
            break

    return {
        "utterances": utterances,
        "speaker_segments": speaker_segments,
        "conversation_formatted": conversation_formatted,
        "agent_speaker": agent_speaker,
        "other_speakers": other_speakers,
        "agent_text": agent_text,
        "other_text": other_text.strip()
    }


@router.post(
    "/analyze-url",
    summary="URL로 통화 분석",
    description="음성 파일 URL을 받아 전사 및 AI 분석을 수행합니다."
)
async def analyze_call_from_url(request: AnalyzeUrlRequest):
    """
    음성 파일 URL을 받아 분석합니다.

    1. uploadAudioFile API로 파일 업로드 후 받은 file_url 사용
    2. 또는 공개 접근 가능한 음성 파일 URL 사용
    """
    start_time = time.time()

    audio_url = request.audio_url
    my_speaker = request.my_speaker

    # URL에서 파일명 추출
    try:
        filename = audio_url.split("/")[-1].split("?")[0]
        if not filename:
            filename = "audio.mp3"
    except:
        filename = "audio.mp3"

    file_ext = Path(filename).suffix.lower()
    allowed_extensions = {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".oga", ".opus"}
    if not file_ext or file_ext not in allowed_extensions:
        file_ext = ".mp3"

    # 파일 다운로드
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid.uuid4())
    file_path = upload_dir / f"{file_id}{file_ext}"

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(audio_url)
            response.raise_for_status()
            file_content = response.content

        with open(file_path, "wb") as f:
            f.write(file_content)

        # 오디오 길이 확인 (최대 30분)
        duration_ms = get_audio_duration_ms(str(file_path))
        max_duration_ms = 30 * 60 * 1000
        if duration_ms > max_duration_ms:
            os.remove(file_path)
            raise HTTPException(
                status_code=400,
                detail={"code": "FILE_TOO_LONG", "message": "음성 파일이 너무 깁니다. (최대 30분)"}
            )

        # 1. 전사 (STT)
        stt_start = time.time()
        stt_service = AsyncSTTService()
        transcript_result = await stt_service.transcribe_with_progress(
            audio_file_path=str(file_path),
            language_code="ko"
        )
        stt_time = time.time() - stt_start

        # 2. 분석 데이터 준비
        data = _prepare_analysis_data(
            utterances=transcript_result["utterances"],
            speakers=transcript_result["speakers"],
            my_speaker=my_speaker
        )

        # 3. 종합 분석
        analysis_start = time.time()
        analysis = await analysis_service.analyze_call(
            transcript_id=file_id,
            conversation_formatted=data["conversation_formatted"],
            speaker_segments=data["speaker_segments"],
            utterances=data["utterances"],
            agent_speaker=data["agent_speaker"],
            other_speakers=data["other_speakers"],
            script_context=None
        )
        analysis_time = time.time() - analysis_start

        # 파일 삭제
        if file_path.exists():
            os.remove(file_path)

        total_time = time.time() - start_time

        return {
            "transcript": {
                "file_id": file_id,
                "duration_ms": transcript_result["duration"],
                "full_text": transcript_result["full_text"],
                "utterances": transcript_result["utterances"],
                "speakers": transcript_result["speakers"]
            },
            "analysis": analysis,
            "processing_time": {
                "stt_seconds": round(stt_time, 2),
                "analysis_seconds": round(analysis_time, 2),
                "total_seconds": round(total_time, 2)
            }
        }

    except httpx.HTTPError as e:
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(
            status_code=400,
            detail={"code": "DOWNLOAD_ERROR", "message": f"URL에서 파일을 다운로드할 수 없습니다: {str(e)}"}
        )
    except Exception as e:
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(
            status_code=500,
            detail={"code": "PROCESSING_ERROR", "message": f"처리 중 오류 발생: {str(e)}"}
        )


@router.post(
    "/analyze-sample",
    summary="샘플 통화 분석",
    description="미리 준비된 샘플 통화를 분석합니다. 테스트용으로 사용하세요."
)
async def analyze_sample_call(request: AnalyzeSampleRequest):
    """
    샘플 통화를 분석합니다.

    사용 가능한 샘플:
    - sample1: 스마트홈 영업 통화 (약 5분)
    - sample2: 고객 상담 통화 (약 5분)
    """
    sample_url = f"https://callmate-uploads.s3.ap-northeast-2.amazonaws.com/samples/{request.sample_id}.mp3"

    return await analyze_call_from_url(AnalyzeUrlRequest(
        audio_url=sample_url,
        my_speaker=request.my_speaker,
        consultation_type=request.consultation_type
    ))
