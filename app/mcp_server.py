"""MCP Server for Kakao PlayMCP integration using official MCP SDK"""

import os
import uuid
import base64
import json
from pathlib import Path
from typing import Optional, Any
from contextlib import asynccontextmanager

from mcp.server import Server
from mcp.server.streamable_http import StreamableHTTPServerTransport
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.responses import JSONResponse

from app.core.config import settings
from app.utils.audio import get_audio_duration_ms
from app.services.stt_service_async import AsyncSTTService
from app.services.analysis_service import analysis_service


# Create MCP server instance
mcp_server = Server(name="CallMate 통화분석")


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


async def analyze_call_impl(
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


# Register tools
@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="analyze_call",
            description="""음성 파일(base64)을 분석하여 통화 내용을 전사하고 AI로 종합 분석합니다.

입력:
- audio_base64: 음성 파일의 base64 인코딩 문자열 (mp3, wav, m4a 지원)
- filename: 파일명 (확장자 포함, 예: "call.mp3")
- my_speaker: (선택) 본인 화자 (A 또는 B) - 미지정 시 자동 감지
- consultation_type: 상담 유형 (sales/information/complaint), 기본값: sales

출력:
- transcript: 전사 결과 (full_text, utterances, speakers)
- analysis: 종합 분석 결과 (감정, 고객 상태, 요약, 추천 멘트 등)""",
            inputSchema={
                "type": "object",
                "properties": {
                    "audio_base64": {
                        "type": "string",
                        "description": "음성 파일의 base64 인코딩 문자열"
                    },
                    "filename": {
                        "type": "string",
                        "description": "파일명 (확장자 포함)",
                        "default": "audio.mp3"
                    },
                    "my_speaker": {
                        "type": "string",
                        "description": "본인 화자 (A 또는 B)"
                    },
                    "consultation_type": {
                        "type": "string",
                        "description": "상담 유형",
                        "enum": ["sales", "information", "complaint"],
                        "default": "sales"
                    }
                },
                "required": ["audio_base64"]
            }
        )
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    if name == "analyze_call":
        result = await analyze_call_impl(
            audio_base64=arguments.get("audio_base64", ""),
            filename=arguments.get("filename", "audio.mp3"),
            my_speaker=arguments.get("my_speaker"),
            consultation_type=arguments.get("consultation_type", "sales")
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, default=str))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


# Create Streamable HTTP transport and app
transport = StreamableHTTPServerTransport(
    mcp_endpoint="/mcp",
    messages_endpoint="/mcp/messages",
)


async def handle_mcp(request):
    """Handle MCP protocol requests"""
    return await transport.handle_request(request, mcp_server)


# Create Starlette app for MCP
mcp_app = Starlette(
    routes=[
        Route("/mcp", handle_mcp, methods=["GET", "POST"]),
        Route("/mcp/messages", handle_mcp, methods=["GET", "POST"]),
        Route("/mcp/messages/", handle_mcp, methods=["GET", "POST"]),
    ]
)
