"""MCP Server for Kakao PlayMCP integration using official MCP SDK FastMCP"""

import os
import uuid
import base64
import json
from pathlib import Path
from typing import Optional
import httpx

from mcp.server.fastmcp import FastMCP

from app.core.config import settings
from app.utils.audio import get_audio_duration_ms
from app.services.stt_service_async import AsyncSTTService
from app.services.analysis_service import analysis_service


# Create MCP server instance using official SDK's FastMCP
mcp = FastMCP(
    name="CallMate 통화분석",
    instructions="""영업/상담 통화를 AI로 분석하고 최적의 응대 방법을 추천하는 서비스입니다.

[분석 기능]
• 음성→텍스트 전사 (화자 분리 포함)
• 고객 감정 분석 (긍정/부정/걱정/화남 등)
• 고객 상태 파악 (관심있음, 고민중, 망설임, 구매준비됨, 불만족 등)

[요약 기능]
• 대화 핵심 요약 (주요 주제, 질문, 답변)
• 고객 니즈 분석 (전화 사유, 요구사항, 고민거리)
• 대화 흐름 및 전환점 파악

[추천 기능]
• 상담 유형별 맞춤 응대 멘트 3가지 제공
• 다음 액션 제안 (추가 상담 예정, 견적 발송 등)""",
    stateless_http=True  # Required for Streamable HTTP
)


def _prepare_analysis_data_from_dict(utterances: list, speakers: list, my_speaker: Optional[str] = None):
    """전사 결과 dict에서 분석 데이터 전처리"""
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


@mcp.tool(
    name="analyze_call",
    description="""음성 파일(base64)을 분석하여 통화 내용을 전사하고 AI로 종합 분석합니다.

입력:
- audio_base64: 음성 파일의 base64 인코딩 문자열 (mp3, wav, m4a 지원)
- filename: 파일명 (확장자 포함, 예: "call.mp3")
- my_speaker: (선택) 본인 화자 (A 또는 B) - 미지정 시 자동 감지
- consultation_type: 상담 유형 (sales/information/complaint), 기본값: sales

출력:
- transcript: 전사 결과 (full_text, utterances, speakers)
- analysis: 종합 분석 결과 (감정, 고객 상태, 요약, 추천 멘트 등)"""
)
async def analyze_call(
    audio_base64: str,
    filename: str = "audio.mp3",
    my_speaker: Optional[str] = None,
    consultation_type: str = "sales"
) -> dict:
    """음성 파일을 분석하여 전사 및 종합 분석 결과를 반환합니다."""

    # 파일 확장자 검증
    allowed_extensions = {".mp3", ".wav", ".m4a"}
    file_ext = Path(filename).suffix.lower()
    if file_ext not in allowed_extensions:
        return {"error": "지원하지 않는 파일 형식입니다. (mp3, wav, m4a만 가능)"}

    # Base64 디코딩
    try:
        file_content = base64.b64decode(audio_base64)
    except Exception:
        return {"error": "잘못된 base64 데이터입니다."}

    # 파일 저장
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid.uuid4())
    file_path = upload_dir / f"{file_id}{file_ext}"

    try:
        with open(file_path, "wb") as f:
            f.write(file_content)

        # 오디오 길이 확인 (최대 30분)
        duration_ms = get_audio_duration_ms(str(file_path))
        max_duration_ms = 30 * 60 * 1000
        if duration_ms > max_duration_ms:
            os.remove(file_path)
            return {"error": "음성 파일이 너무 깁니다. (최대 30분)"}

        # 1. 전사 (STT)
        stt_service = AsyncSTTService()
        transcript_result = await stt_service.transcribe_with_progress(
            audio_file_path=str(file_path),
            language_code="ko"
        )

        # 2. 분석 데이터 준비
        data = _prepare_analysis_data_from_dict(
            utterances=transcript_result["utterances"],
            speakers=transcript_result["speakers"],
            my_speaker=my_speaker
        )

        # 3. 종합 분석
        analysis = await analysis_service.analyze_call(
            transcript_id=file_id,
            conversation_formatted=data["conversation_formatted"],
            speaker_segments=data["speaker_segments"],
            utterances=data["utterances"],
            agent_speaker=data["agent_speaker"],
            other_speakers=data["other_speakers"],
            script_context=None
        )

        # 파일 삭제
        if file_path.exists():
            os.remove(file_path)

        return {
            "transcript": {
                "file_id": file_id,
                "duration_ms": transcript_result["duration"],
                "full_text": transcript_result["full_text"],
                "utterances": transcript_result["utterances"],
                "speakers": transcript_result["speakers"]
            },
            "analysis": analysis
        }

    except Exception as e:
        if file_path.exists():
            os.remove(file_path)
        return {"error": f"처리 중 오류 발생: {str(e)}"}


@mcp.tool(
    name="analyze_call_from_url",
    description="""공개 URL의 음성 파일을 다운로드하여 분석합니다.

사용 예시:
- analyze_call_from_url("https://callmate-uploads.s3.ap-northeast-2.amazonaws.com/samples/sample1.mp3")

입력:
- audio_url: 음성 파일의 공개 URL (mp3, wav, m4a 지원)
- my_speaker: (선택) 본인 화자 (A 또는 B) - 미지정 시 자동 감지
- consultation_type: 상담 유형 (sales/information/complaint), 기본값: sales

출력:
- transcript: 전사 결과 (full_text, utterances, speakers)
- analysis: 종합 분석 결과 (감정, 고객 상태, 요약, 추천 멘트 등)"""
)
async def analyze_call_from_url(
    audio_url: str,
    my_speaker: Optional[str] = None,
    consultation_type: str = "sales"
) -> dict:
    """URL에서 음성 파일을 다운로드하여 분석합니다."""

    # URL에서 파일명 추출
    try:
        filename = audio_url.split("/")[-1].split("?")[0]
        if not filename:
            filename = "audio.mp3"
    except:
        filename = "audio.mp3"

    file_ext = Path(filename).suffix.lower()
    allowed_extensions = {".mp3", ".wav", ".m4a"}
    if file_ext not in allowed_extensions:
        return {"error": "지원하지 않는 파일 형식입니다. (mp3, wav, m4a만 가능)"}

    # 파일 다운로드
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid.uuid4())
    file_path = upload_dir / f"{file_id}{file_ext}"

    try:
        # httpx로 파일 다운로드
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
            return {"error": "음성 파일이 너무 깁니다. (최대 30분)"}

        # 1. 전사 (STT)
        stt_service = AsyncSTTService()
        transcript_result = await stt_service.transcribe_with_progress(
            audio_file_path=str(file_path),
            language_code="ko"
        )

        # 2. 분석 데이터 준비
        data = _prepare_analysis_data_from_dict(
            utterances=transcript_result["utterances"],
            speakers=transcript_result["speakers"],
            my_speaker=my_speaker
        )

        # 3. 종합 분석
        analysis = await analysis_service.analyze_call(
            transcript_id=file_id,
            conversation_formatted=data["conversation_formatted"],
            speaker_segments=data["speaker_segments"],
            utterances=data["utterances"],
            agent_speaker=data["agent_speaker"],
            other_speakers=data["other_speakers"],
            script_context=None
        )

        # 파일 삭제
        if file_path.exists():
            os.remove(file_path)

        return {
            "transcript": {
                "file_id": file_id,
                "duration_ms": transcript_result["duration"],
                "full_text": transcript_result["full_text"],
                "utterances": transcript_result["utterances"],
                "speakers": transcript_result["speakers"]
            },
            "analysis": analysis
        }

    except httpx.HTTPError as e:
        if file_path.exists():
            os.remove(file_path)
        return {"error": f"URL에서 파일을 다운로드할 수 없습니다: {str(e)}"}
    except Exception as e:
        if file_path.exists():
            os.remove(file_path)
        return {"error": f"처리 중 오류 발생: {str(e)}"}


@mcp.tool(
    name="analyze_sample_call",
    description="""샘플 통화 녹음을 분석합니다. 테스트용으로 미리 준비된 샘플 파일을 사용합니다.

사용 예시:
- analyze_sample_call("sample1") - 영업 통화 샘플
- analyze_sample_call("sample2") - 고객 상담 샘플

입력:
- sample_id: 샘플 파일 ID (sample1, sample2 등)
- my_speaker: (선택) 본인 화자 (A 또는 B) - 미지정 시 자동 감지
- consultation_type: 상담 유형 (sales/information/complaint), 기본값: sales

출력:
- transcript: 전사 결과
- analysis: 종합 분석 결과"""
)
async def analyze_sample_call(
    sample_id: str = "sample1",
    my_speaker: Optional[str] = None,
    consultation_type: str = "sales"
) -> dict:
    """샘플 파일을 분석합니다."""

    # S3 샘플 URL 생성
    sample_url = f"https://callmate-uploads.s3.ap-northeast-2.amazonaws.com/samples/{sample_id}.mp3"

    # URL 기반 분석 재사용
    return await analyze_call_from_url(
        audio_url=sample_url,
        my_speaker=my_speaker,
        consultation_type=consultation_type
    )


# Create Streamable HTTP app for mounting
mcp_app = mcp.streamable_http_app()
