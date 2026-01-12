"""
Async Speech-to-Text service using Deepgram with progress tracking.
Designed for WebSocket real-time progress updates.

Deepgram is much faster than AssemblyAI:
- 10min audio: ~30 seconds (vs ~3 minutes with AssemblyAI)
- Near real-time processing
"""

from typing import Dict, Callable, Optional
import asyncio
from deepgram import DeepgramClient, PrerecordedOptions, FileSource
from app.core.config import settings


class AsyncSTTService:
    """
    Async STT Service with progress callbacks using Deepgram.

    Deepgram processes audio much faster than AssemblyAI:
    - No upload step needed (direct file processing)
    - Near real-time transcription
    - Single API call (no polling required)
    """

    def __init__(self):
        self.client = DeepgramClient(settings.DEEPGRAM_API_KEY.get_secret_value())

    async def transcribe_with_progress(
        self,
        audio_file_path: str,
        language_code: str = "ko",
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Dict:
        """
        Transcribe audio with progress updates.

        Args:
            audio_file_path: Path to audio file
            language_code: Language code (default: "ko")
            progress_callback: Callback function(percent, message)

        Returns:
            Transcription result dictionary
        """
        # Step 1: Read file (10%)
        if progress_callback:
            await self._call_callback(progress_callback, 10, "파일 읽는 중...")

        with open(audio_file_path, "rb") as f:
            buffer_data = f.read()

        payload: FileSource = {
            "buffer": buffer_data,
        }

        # Step 2: Configure and start transcription (20%)
        if progress_callback:
            await self._call_callback(progress_callback, 20, "Deepgram 전사 시작...")

        options = PrerecordedOptions(
            model="nova-2",
            language=language_code,
            smart_format=True,
            diarize=True,
            punctuate=True,
            utterances=True,
        )

        # Step 3: Transcribe (30-80%)
        if progress_callback:
            await self._call_callback(progress_callback, 30, "전사 처리 중...")

        # Deepgram is synchronous but very fast, run in executor
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.listen.rest.v("1").transcribe_file(payload, options)
        )

        if progress_callback:
            await self._call_callback(progress_callback, 80, "전사 완료, 결과 처리 중...")

        # Step 4: Process result (90%)
        if progress_callback:
            await self._call_callback(progress_callback, 90, "결과 처리 중...")

        result = self._process_result(response)

        return result

    async def _call_callback(
        self,
        callback: Callable[[int, str], None],
        percent: int,
        message: str
    ):
        """Safely call progress callback"""
        try:
            result = callback(percent, message)
            if asyncio.iscoroutine(result):
                await result
        except Exception:
            pass

    def _process_result(self, response) -> Dict:
        """Process Deepgram response into our format"""
        result = response.to_dict()

        utterances = []
        speakers_set = set()

        # Get utterances from Deepgram response
        if result.get("results", {}).get("utterances"):
            for utterance in result["results"]["utterances"]:
                speaker = self._convert_speaker_label(utterance.get("speaker", 0))
                speakers_set.add(speaker)

                # Deepgram returns seconds, convert to milliseconds
                start_ms = int(utterance["start"] * 1000)
                end_ms = int(utterance["end"] * 1000)

                utterances.append({
                    "speaker": speaker,
                    "text": utterance["transcript"],
                    "start": start_ms,
                    "end": end_ms,
                    "confidence": utterance.get("confidence", 0.0)
                })

        # Sort speakers alphabetically
        speakers = sorted(list(speakers_set))

        # Get full text
        full_text = ""
        if result.get("results", {}).get("channels"):
            channels = result["results"]["channels"]
            if channels and channels[0].get("alternatives"):
                full_text = channels[0]["alternatives"][0].get("transcript", "")

        return {
            "full_text": full_text,
            "utterances": utterances,
            "speakers": speakers,
            "duration": utterances[-1]["end"] if utterances else 0
        }

    def _convert_speaker_label(self, speaker_num: int) -> str:
        """Convert Deepgram speaker number to simple letter (0->A, 1->B, etc.)"""
        return chr(65 + speaker_num)  # 65 is ASCII for 'A'
