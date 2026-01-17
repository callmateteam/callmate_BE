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
from app.services.s3_service import s3_service


# Create MCP server instance using official SDK's FastMCP
mcp = FastMCP(
    name="CallMate 통화분석",
    instructions="""영업/상담 통화를 AI로 분석하고 최적의 응대 방법을 추천하는 서비스입니다.

🌐 홈페이지: https://callmate-fe.vercel.app/

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
  - 판매/설득: 손실 강조, 대안 제시, 마무리 멘트
  - 안내/정보: 핵심 포인트, 추가 안내, 마무리 멘트
  - 불만/문제: 공감 표현, 해결 방안, 마무리 멘트
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


def _convert_to_wav(input_path: str, output_path: str) -> bool:
    """ffmpeg를 사용해 오디오를 WAV로 변환"""
    import subprocess
    try:
        result = subprocess.run(
            ['ffmpeg', '-y', '-i', input_path, '-ar', '16000', '-ac', '1', output_path],
            capture_output=True,
            timeout=60
        )
        return result.returncode == 0
    except Exception:
        return False


@mcp.tool(
    name="analyze_call",
    description="""[파일 업로드용] 사용자가 업로드한 음성 파일을 분석합니다.

★★★ 중요: 사용자가 음성 파일을 업로드하면 반드시 이 도구를 사용하세요! ★★★

사용 방법 (필수):
1. 업로드된 파일을 Python 코드로 읽어서 base64 인코딩
2. 인코딩된 문자열을 audio_base64 파라미터에 전달

Python 코드 예시:
```python
import base64
with open('/mnt/data/파일명.mp3', 'rb') as f:
    audio_base64 = base64.b64encode(f.read()).decode('utf-8')
```

지원 포맷: mp3, wav, m4a, ogg, webm, opus, aac, flac
최대 파일 크기: 25MB / 최대 길이: 30분

입력:
- audio_base64: base64 인코딩된 음성 데이터 (필수)
- filename: 원본 파일명 (예: "call.mp3")

출력: 전사 결과 + AI 종합 분석 (감정, 요약, 추천 멘트)"""
)
async def analyze_call(
    audio_base64: str,
    filename: str = "audio.mp3",
    my_speaker: Optional[str] = None,
    consultation_type: str = "sales"
) -> dict:
    """음성 파일을 분석하여 전사 및 종합 분석 결과를 반환합니다."""

    # 파일 확장자 검증
    allowed_extensions = {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".oga", ".opus", ".aac", ".flac"}
    file_ext = Path(filename).suffix.lower()
    if not file_ext or file_ext not in allowed_extensions:
        file_ext = ".mp3"  # 확장자 없으면 mp3로 가정

    # Base64 디코딩 (다양한 포맷 지원)
    try:
        # 공백 및 줄바꿈 제거
        audio_base64 = audio_base64.strip().replace("\n", "").replace("\r", "").replace(" ", "")

        # data:audio/... 형식 처리
        if "," in audio_base64 and "base64" in audio_base64.lower():
            audio_base64 = audio_base64.split(",", 1)[1]

        # URL-safe base64 변환
        audio_base64 = audio_base64.replace("-", "+").replace("_", "/")

        # 패딩 처리
        missing_padding = len(audio_base64) % 4
        if missing_padding:
            audio_base64 += "=" * (4 - missing_padding)

        file_content = base64.b64decode(audio_base64, validate=True)

        # 파일 크기 검증
        if len(file_content) < 1000:
            return {"error": "파일이 너무 작습니다. 유효한 음성 파일인지 확인해주세요."}
        if len(file_content) > 25 * 1024 * 1024:  # 25MB
            return {"error": "파일이 너무 큽니다. 최대 25MB까지 지원합니다."}

    except Exception as e:
        return {"error": f"base64 디코딩 실패: {str(e)}. 파일이 올바르게 인코딩되었는지 확인해주세요."}

    # 파일 저장
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid.uuid4())
    file_path = upload_dir / f"{file_id}{file_ext}"

    wav_path = None
    try:
        with open(file_path, "wb") as f:
            f.write(file_content)

        # 오디오 포맷 검증 및 변환
        wav_path = upload_dir / f"{file_id}_converted.wav"
        if not _convert_to_wav(str(file_path), str(wav_path)):
            # 변환 실패 시 원본 파일 사용 시도
            wav_path = None
            actual_path = str(file_path)
        else:
            actual_path = str(wav_path)

        # 오디오 길이 확인 (최대 30분)
        try:
            duration_ms = get_audio_duration_ms(actual_path)
        except Exception:
            duration_ms = get_audio_duration_ms(str(file_path))
        max_duration_ms = 30 * 60 * 1000
        if duration_ms > max_duration_ms:
            if file_path.exists():
                os.remove(file_path)
            if wav_path and wav_path.exists():
                os.remove(wav_path)
            return {"error": "음성 파일이 너무 깁니다. (최대 30분)"}

        # 1. 전사 (STT) - 변환된 WAV 또는 원본 사용
        stt_service = AsyncSTTService()
        transcript_result = await stt_service.transcribe_with_progress(
            audio_file_path=actual_path,
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
        if wav_path and wav_path.exists():
            os.remove(wav_path)

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
        if wav_path and wav_path.exists():
            os.remove(wav_path)
        return {"error": f"처리 중 오류 발생: {str(e)}"}


@mcp.tool(
    name="analyze_call_from_url",
    description="""[파일 업로드 및 URL용 - 권장] 음성 파일 URL을 받아서 분석합니다.

★★★ 중요: 사용자가 음성 파일을 업로드하면 이 도구를 사용하세요! ★★★

이 도구를 사용해야 하는 경우:
1. 사용자가 음성 파일을 업로드했을 때 → 파일의 sandbox URL 사용
2. 사용자가 음성 파일 URL/링크를 제공했을 때
3. "이 파일 분석해줘", "녹음 분석", "통화 분석" 요청

사용자가 파일 업로드 시:
- ChatGPT sandbox의 파일 경로(예: /mnt/data/파일명.mp3)가 아닌
- 파일의 다운로드 가능한 URL을 audio_url에 전달하세요

입력:
- audio_url: 음성 파일 URL (mp3, wav, m4a, ogg, webm)
- my_speaker: 본인 화자 (선택, A/B)
- consultation_type: sales/information/complaint

출력: 전사 결과 + AI 종합 분석"""
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
    allowed_extensions = {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".oga", ".opus"}
    if not file_ext or file_ext not in allowed_extensions:
        # 확장자 없으면 mp3로 가정
        file_ext = ".mp3"

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
    description="""[테스트용 필수 도구] 미리 준비된 샘플 통화를 분석합니다. 파일 업로드 없이 바로 테스트할 수 있습니다.

★ 이 도구를 사용해야 하는 경우:
- "sample1 분석", "sample2 분석", "샘플 분석", "샘플 통화 분석"
- "테스트", "데모", "체험", "시연"이라는 단어가 포함된 요청
- 사용자가 파일을 제공하지 않고 분석을 요청할 때

사용 가능한 샘플:
- sample1: 스마트홈 영업 통화 (약 5분, 상담사가 고객에게 제품 설명)
- sample2: 고객 상담 통화 (약 5분, 고객 문의 응대)

입력:
- sample_id: "sample1" 또는 "sample2" (기본값: sample1)
- my_speaker: 본인 화자 지정 (선택, A/B)
- consultation_type: sales/information/complaint (기본값: sales)

출력: 전사 결과 + AI 종합 분석 (감정, 요약, 추천 멘트)"""
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


@mcp.tool(
    name="upload_audio",
    description="""[파일 업로드 1단계] 음성 파일을 서버에 업로드하고 URL을 반환합니다.

★★★ 대용량 파일 분석 시 이 도구를 먼저 사용하세요! ★★★

사용 시나리오:
1. 사용자가 음성 파일을 업로드함
2. upload_audio로 파일을 서버에 업로드 → URL 반환
3. analyze_call_from_url로 반환된 URL 분석

사용 방법:
```python
import base64
with open('/mnt/data/파일명.mp3', 'rb') as f:
    audio_base64 = base64.b64encode(f.read()).decode('utf-8')
```

입력:
- audio_base64: base64 인코딩된 음성 데이터
- filename: 파일명 (예: "call.mp3")

출력:
- file_url: 분석에 사용할 URL (analyze_call_from_url에 전달)
- file_key: 파일 식별자"""
)
async def upload_audio(
    audio_base64: str,
    filename: str = "audio.mp3"
) -> dict:
    """음성 파일을 S3에 업로드하고 URL을 반환합니다."""

    # 파일 확장자 검증
    allowed_extensions = {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".oga", ".opus", ".aac", ".flac"}
    file_ext = Path(filename).suffix.lower()
    if not file_ext or file_ext not in allowed_extensions:
        file_ext = ".mp3"
        filename = f"audio{file_ext}"

    # Base64 디코딩
    try:
        audio_base64 = audio_base64.strip().replace("\n", "").replace("\r", "").replace(" ", "")

        if "," in audio_base64 and "base64" in audio_base64.lower():
            audio_base64 = audio_base64.split(",", 1)[1]

        audio_base64 = audio_base64.replace("-", "+").replace("_", "/")

        missing_padding = len(audio_base64) % 4
        if missing_padding:
            audio_base64 += "=" * (4 - missing_padding)

        file_content = base64.b64decode(audio_base64, validate=True)

        if len(file_content) < 1000:
            return {"error": "파일이 너무 작습니다. base64 데이터가 잘렸을 수 있습니다. analyze_sample_call을 사용하거나 공개 URL을 제공해주세요."}
        if len(file_content) > 50 * 1024 * 1024:
            return {"error": "파일이 너무 큽니다. 최대 50MB까지 지원합니다."}

    except Exception as e:
        return {"error": f"base64 디코딩 실패: {str(e)}. 파일이 잘렸을 수 있습니다."}

    # S3 업로드
    try:
        content_types = {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".m4a": "audio/mp4",
            ".ogg": "audio/ogg",
            ".webm": "audio/webm"
        }

        file_key, file_url = await s3_service.upload_file(
            file_content=file_content,
            filename=filename,
            folder="mcp-uploads",
            content_type=content_types.get(file_ext, "audio/mpeg")
        )

        return {
            "success": True,
            "file_url": file_url,
            "file_key": file_key,
            "size_bytes": len(file_content),
            "message": "업로드 완료. 이제 analyze_call_from_url 도구에 file_url을 전달하여 분석하세요."
        }

    except Exception as e:
        return {"error": f"업로드 실패: {str(e)}"}


# Create Streamable HTTP app for mounting
mcp_app = mcp.streamable_http_app()
