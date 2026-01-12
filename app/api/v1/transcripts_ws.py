"""WebSocket endpoint for real-time transcription with progress updates"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import asyncio
import json
import uuid
import os
import aiofiles
from pathlib import Path
from typing import Optional
import base64

from app.core.config import settings
from app.core.rate_limiter import rate_limiter
from app.utils.audio import get_audio_duration_ms
from app.services.stt_service_async import AsyncSTTService

router = APIRouter()


# ============================================
# WebSocket 문서화용 엔드포인트 (Swagger 표시용)
# ============================================

@router.get(
    "/ws/transcribe",
    summary="🔌 실시간 전사 (WebSocket)",
    description="""
## WebSocket 엔드포인트

**이 API는 WebSocket으로만 사용 가능합니다. HTTP GET은 지원하지 않습니다.**

### 연결 URL
```
ws://host/api/v1/transcripts/ws/transcribe
```

### 프로토콜

**1. 클라이언트 → 서버 (파일 업로드)**
```json
{
    "action": "upload",
    "filename": "call.mp3",
    "data": "<base64 인코딩된 파일>",
    "language_code": "ko"
}
```

**2. 서버 → 클라이언트 (진행률)**
```json
{"status": "received", "data": {"file_id": "uuid", "duration_ms": 180000}}
{"status": "processing", "progress": {"percent": 10, "message": "업로드 중..."}}
{"status": "processing", "progress": {"percent": 50, "message": "전사 중..."}}
{"status": "completed", "data": {"transcript_id": "...", "utterances": [...]}}
```

**3. 에러 발생 시**
```json
{"status": "error", "error": {"code": "ERROR_CODE", "message": "에러 메시지"}}
```

### JavaScript 예제
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/transcripts/ws/transcribe');

// 파일을 base64로 인코딩하여 전송
const reader = new FileReader();
reader.onload = () => {
    const base64 = reader.result.split(',')[1];
    ws.send(JSON.stringify({
        action: 'upload',
        filename: file.name,
        data: base64,
        language_code: 'ko'
    }));
};
reader.readAsDataURL(file);

// 메시지 수신
ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.status === 'processing') {
        updateProgressBar(msg.progress.percent);
    } else if (msg.status === 'completed') {
        showResult(msg.data);
    }
};
```

### 제한사항
- 최대 파일 길이: 30분
- 지원 형식: mp3, wav, m4a
- 일일 사용량: IP당 30분

### 중요: 프론트엔드 저장 필요
WebSocket 응답으로 전사 결과를 한 번만 전송합니다.
**서버에서 결과를 저장하지 않으므로**, 프론트엔드에서 `completed` 응답의 데이터를 반드시 저장해야 합니다.

```javascript
ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.status === 'completed') {
        // 반드시 프론트엔드에서 저장!
        localStorage.setItem('transcript', JSON.stringify(msg.data));
        // 또는 상태관리 (Redux, Zustand 등)에 저장
    }
};
```
""",
    responses={
        200: {
            "description": "WebSocket 연결 정보",
            "content": {
                "application/json": {
                    "example": {
                        "message": "이 엔드포인트는 WebSocket 전용입니다.",
                        "websocket_url": "ws://host/api/v1/transcripts/ws/transcribe",
                        "protocol": {
                            "send": {
                                "action": "upload",
                                "filename": "call.mp3",
                                "data": "<base64>",
                                "language_code": "ko"
                            },
                            "receive": [
                                {"status": "processing", "progress": {"percent": 50, "message": "전사 중..."}},
                                {"status": "completed", "data": {"transcript_id": "..."}}
                            ]
                        }
                    }
                }
            }
        }
    },
    tags=["transcripts-ws"]
)
async def websocket_transcribe_docs():
    """WebSocket 전사 API 문서 (실제 연결은 WebSocket 사용)"""
    return JSONResponse({
        "message": "이 엔드포인트는 WebSocket 전용입니다. HTTP GET은 지원하지 않습니다.",
        "websocket_url": "ws://{host}/api/v1/transcripts/ws/transcribe",
        "documentation": "/api/docs#/transcripts-ws"
    })

class TranscriptionWebSocket:
    """WebSocket handler for real-time transcription"""

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.stt_service = AsyncSTTService()

    async def send_status(self, status: str, data: dict = None):
        """Send status message to client"""
        message = {"status": status}
        if data:
            message["data"] = data
        await self.websocket.send_json(message)

    async def send_error(self, code: str, message: str):
        """Send error message to client"""
        await self.websocket.send_json({
            "status": "error",
            "error": {
                "code": code,
                "message": message
            }
        })

    async def send_progress(self, percent: int, message: str):
        """Send progress update to client"""
        await self.websocket.send_json({
            "status": "processing",
            "progress": {
                "percent": percent,
                "message": message
            }
        })


@router.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    """
    WebSocket endpoint for real-time transcription

    ## Protocol:
    1. Client connects to ws://host/api/v1/transcripts/ws/transcribe
    2. Client sends: {"action": "upload", "filename": "test.mp3", "data": "<base64>", "language_code": "ko"}
    3. Server sends progress updates:
       - {"status": "received", "data": {"file_id": "...", "duration_ms": 180000}}
       - {"status": "processing", "progress": {"percent": 10, "message": "파일 읽는 중..."}}
       - {"status": "processing", "progress": {"percent": 30, "message": "Deepgram 전사 처리 중..."}}
       - {"status": "processing", "progress": {"percent": 90, "message": "결과 처리 중..."}}
       - {"status": "completed", "data": {"transcript_id": "...", ...}}
    4. On error:
       - {"status": "error", "error": {"code": "...", "message": "..."}}

    ## Example client (JavaScript):
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/api/v1/transcripts/ws/transcribe');

    ws.onopen = () => {
        const fileData = btoa(audioFileContent); // base64 encode
        ws.send(JSON.stringify({
            action: 'upload',
            filename: 'call.mp3',
            data: fileData,
            language_code: 'ko'
        }));
    };

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.status === 'processing') {
            console.log(`Progress: ${msg.progress.percent}% - ${msg.progress.message}`);
        } else if (msg.status === 'completed') {
            console.log('Transcription completed:', msg.data);
        } else if (msg.status === 'error') {
            console.error('Error:', msg.error.message);
        }
    };
    ```
    """
    await websocket.accept()
    handler = TranscriptionWebSocket(websocket)

    try:
        # Wait for upload message
        data = await websocket.receive_json()

        if data.get("action") != "upload":
            await handler.send_error("INVALID_ACTION", "Expected action: upload")
            await websocket.close()
            return

        # Extract file info
        filename = data.get("filename", "audio.mp3")
        file_data_b64 = data.get("data")
        language_code = data.get("language_code", "ko")

        if not file_data_b64:
            await handler.send_error("MISSING_DATA", "파일 데이터가 없습니다.")
            await websocket.close()
            return

        # Validate file extension
        allowed_extensions = {".mp3", ".wav", ".m4a"}
        file_ext = Path(filename).suffix.lower()
        if file_ext not in allowed_extensions:
            await handler.send_error(
                "INVALID_FILE_TYPE",
                "지원하지 않는 음성 파일 형식입니다. (mp3, wav, m4a만 가능)"
            )
            await websocket.close()
            return

        # Decode base64
        try:
            file_content = base64.b64decode(file_data_b64)
        except Exception:
            await handler.send_error("INVALID_DATA", "잘못된 파일 데이터입니다.")
            await websocket.close()
            return

        await handler.send_progress(5, "파일 저장 중...")

        # Save file
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_id = str(uuid.uuid4())
        file_path = upload_dir / f"{file_id}{file_ext}"

        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)

        # Check audio duration
        try:
            duration_ms = get_audio_duration_ms(str(file_path))
            max_duration_ms = 30 * 60 * 1000  # 30분

            if duration_ms > max_duration_ms:
                os.remove(file_path)
                await handler.send_error(
                    "AUDIO_DURATION_EXCEEDED",
                    "음성 파일이 너무 깁니다. (최대 30분)"
                )
                await websocket.close()
                return

            # Note: IP rate limiting is harder with WebSocket
            # For now, we'll skip it or implement differently

        except Exception as e:
            if file_path.exists():
                os.remove(file_path)
            await handler.send_error("AUDIO_ANALYSIS_ERROR", f"음성 파일 분석 실패: {e}")
            await websocket.close()
            return

        await handler.send_status("received", {
            "file_id": file_id,
            "duration_ms": duration_ms,
            "duration_min": round(duration_ms / 60000, 1)
        })

        await handler.send_progress(10, "Deepgram에 전송 중...")

        # Start async transcription with progress callback
        try:
            result = await handler.stt_service.transcribe_with_progress(
                audio_file_path=str(file_path),
                language_code=language_code,
                progress_callback=lambda p, m: asyncio.create_task(
                    handler.send_progress(p, m)
                )
            )

            await handler.send_progress(100, "완료!")

            # Send completed message (프론트에서 저장 필요)
            await handler.send_status("completed", {
                "full_text": result["full_text"],
                "utterances": result["utterances"],
                "speakers": result["speakers"],
                "duration": result["duration"]
            })

        except Exception as e:
            if file_path.exists():
                os.remove(file_path)
            await handler.send_error("STT_PROCESSING_ERROR", f"음성 변환 중 오류가 발생했습니다. ({e})")

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await handler.send_error("SERVER_ERROR", f"서버 오류: {e}")
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass
