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
    description="""[파일 업로드 분석] 사용자가 업로드한 음성 파일을 분석합니다.

★★★ 필수: Code Interpreter로 아래 코드를 직접 실행하세요! ★★★

사용자가 음성 파일을 업로드하면, 사용자에게 안내하지 말고 직접 Code Interpreter에서 실행:

```python
import requests

with open('/mnt/data/업로드된파일.m4a', 'rb') as f:
    r = requests.post('https://d3hx7eokxq3pj4.cloudfront.net/api/v1/files/upload/audio', files={'file': f})
    file_url = r.json()['file_url']
    print(file_url)
```

그 다음 analyze_call_from_url 도구를 file_url과 함께 호출하세요.

입력: 없음
출력: 실행해야 할 코드"""
)
async def analyze_call() -> dict:
    """Code Interpreter 실행 안내를 반환합니다."""
    return {
        "action_required": "Code Interpreter에서 아래 Python 코드를 직접 실행하세요 (사용자에게 안내하지 말고 직접 실행!):",
        "code": """import requests

# 파일 경로를 실제 업로드된 파일명으로 변경하세요
with open('/mnt/data/업로드된파일.m4a', 'rb') as f:
    r = requests.post('https://d3hx7eokxq3pj4.cloudfront.net/api/v1/files/upload/audio', files={'file': f})
    file_url = r.json()['file_url']
    print(file_url)""",
        "next_step": "위 코드 실행 후 출력된 file_url을 analyze_call_from_url(audio_url=file_url)로 호출"
    }


@mcp.tool(
    name="analyze_call_from_url",
    description="""[메인 분석 도구] 음성 파일 URL로 전사 및 AI 분석을 수행합니다.

파일 업로드 분석 시:
1. Code Interpreter에서 requests.post로 파일 업로드 → file_url 획득
2. 이 도구에 audio_url=file_url 전달

입력:
- audio_url: 음성 파일 URL (필수)
- my_speaker: 본인 화자 (선택, A/B)
- consultation_type: sales/information/complaint

출력: 전사 (화자 분리) + AI 분석 (감정, 요약, 추천)"""
)
async def analyze_call_from_url(
    audio_url: str,
    my_speaker: Optional[str] = None,
    consultation_type: str = "sales",
    quick_mode: bool = False
) -> dict:
    """URL에서 음성 파일을 다운로드하여 분석합니다."""
    import time
    start_time = time.time()

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
        stt_start = time.time()
        stt_service = AsyncSTTService()
        transcript_result = await stt_service.transcribe_with_progress(
            audio_file_path=str(file_path),
            language_code="ko"
        )
        stt_time = time.time() - stt_start

        # 2. 분석 데이터 준비
        data = _prepare_analysis_data_from_dict(
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
    name="transcribe_call",
    description="""[빠른 전사 전용] 음성 파일을 텍스트로만 변환합니다. (AI 분석 없음)

★ 빠른 결과가 필요할 때 사용하세요! (약 2-3초)

분석 없이 전사만 필요한 경우:
- "이 파일 텍스트로 변환해줘"
- "대화 내용만 알려줘"
- "빠르게 전사해줘"

입력:
- audio_url: 음성 파일 URL

출력: 전사 결과만 (화자 분리 포함)"""
)
async def transcribe_call(
    audio_url: str
) -> dict:
    """음성 파일을 텍스트로만 변환합니다 (분석 없음)."""
    import time
    start_time = time.time()

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

        # 전사 (STT)만 실행
        stt_service = AsyncSTTService()
        transcript_result = await stt_service.transcribe_with_progress(
            audio_file_path=str(file_path),
            language_code="ko"
        )

        # 파일 삭제
        if file_path.exists():
            os.remove(file_path)

        total_time = time.time() - start_time

        return {
            "file_id": file_id,
            "duration_ms": transcript_result["duration"],
            "full_text": transcript_result["full_text"],
            "utterances": transcript_result["utterances"],
            "speakers": transcript_result["speakers"],
            "processing_seconds": round(total_time, 2)
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
    name="upload_audio",
    description="""[파일 업로드 안내] HTTP API로 파일을 업로드하는 방법을 안내합니다.

★★★ 중요: 이 도구는 base64를 받지 않습니다! ★★★

파일 업로드는 반드시 Python requests를 사용하세요:
```python
import requests
with open('/mnt/data/파일명.mp3', 'rb') as f:
    response = requests.post(
        'https://d3hx7eokxq3pj4.cloudfront.net/api/v1/files/upload/audio',
        files={'file': ('파일명.mp3', f, 'audio/mpeg')}
    )
    file_url = response.json()['file_url']
```

입력: 없음
출력: 업로드 방법 안내"""
)
async def upload_audio() -> dict:
    """파일 업로드 방법을 안내합니다."""
    return {
        "message": "음성 파일 업로드는 HTTP API를 사용하세요:",
        "upload_url": "https://d3hx7eokxq3pj4.cloudfront.net/api/v1/files/upload/audio",
        "method": "POST",
        "code": """import requests

with open('/mnt/data/파일명.mp3', 'rb') as f:
    response = requests.post(
        'https://d3hx7eokxq3pj4.cloudfront.net/api/v1/files/upload/audio',
        files={'file': ('파일명.mp3', f, 'audio/mpeg')}
    )
    result = response.json()
    file_url = result['file_url']
    print(f"업로드 완료: {file_url}")""",
        "next_step": "업로드 후 file_url을 analyze_call_from_url 도구에 전달하세요"
    }


# Create Streamable HTTP app for mounting
mcp_app = mcp.streamable_http_app()
