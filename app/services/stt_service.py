"""Speech-to-Text service using Deepgram with speaker diarization"""

from typing import List, Dict
from deepgram import DeepgramClient, PrerecordedOptions, FileSource
from app.core.config import settings


class STTService:
    """Service for Speech-to-Text with speaker diarization using Deepgram"""

    def __init__(self):
        self.client = DeepgramClient(settings.DEEPGRAM_API_KEY.get_secret_value())

    def transcribe_with_speakers(
        self,
        audio_file_path: str,
        speaker_labels: bool = True,
        language_code: str = "ko"
    ) -> Dict:
        """
        Transcribe audio file with speaker diarization

        Args:
            audio_file_path: Path to audio file (mp3, wav, m4a)
            speaker_labels: Enable speaker diarization (default: True)
            language_code: Language code (default: "ko" for Korean)

        Returns:
            Dictionary containing:
            {
                "transcript_id": str,
                "full_text": str,
                "utterances": [
                    {
                        "speaker": str,  # "A", "B", "C", ...
                        "text": str,
                        "start": int,  # milliseconds
                        "end": int,    # milliseconds
                        "confidence": float
                    }
                ],
                "speakers": List[str],  # ["A", "B"]
                "duration": int  # milliseconds
            }

        Example:
            >>> service = STTService()
            >>> result = service.transcribe_with_speakers("call.mp3")
            >>> for utterance in result["utterances"]:
            ...     print(f"{utterance['speaker']}: {utterance['text']}")
        """
        # Read audio file
        with open(audio_file_path, "rb") as f:
            buffer_data = f.read()

        payload: FileSource = {
            "buffer": buffer_data,
        }

        # Configure options
        options = PrerecordedOptions(
            model="nova-2",
            language=language_code,
            smart_format=True,
            diarize=speaker_labels,
            punctuate=True,
            utterances=True,
        )

        # Transcribe
        response = self.client.listen.rest.v("1").transcribe_file(payload, options)

        # Process result
        return self._process_result(response)

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
        """
        Convert Deepgram speaker number to simple letter

        Args:
            speaker_num: Speaker number (0, 1, 2, ...)

        Returns:
            Simple letter (e.g., "A", "B", "C")
        """
        return chr(65 + speaker_num)  # 65 is ASCII for 'A'

    def get_speaker_segments(
        self,
        utterances: List[Dict],
        speaker: str
    ) -> List[Dict]:
        """
        Get all segments for a specific speaker

        Args:
            utterances: List of utterances from transcribe_with_speakers()
            speaker: Speaker label (e.g., "A", "B")

        Returns:
            List of utterances for that speaker

        Example:
            >>> result = service.transcribe_with_speakers("call.mp3")
            >>> speaker_a = service.get_speaker_segments(result["utterances"], "A")
            >>> for segment in speaker_a:
            ...     print(segment["text"])
        """
        return [
            utterance for utterance in utterances
            if utterance["speaker"] == speaker
        ]

    def format_conversation(
        self,
        utterances: List[Dict],
        format_type: str = "simple"
    ) -> str:
        """
        Format conversation for display

        Args:
            utterances: List of utterances
            format_type: "simple" or "detailed"

        Returns:
            Formatted conversation string

        Example:
            >>> result = service.transcribe_with_speakers("call.mp3")
            >>> conversation = service.format_conversation(result["utterances"])
            >>> print(conversation)
            A: 안녕하세요
            B: 네, 안녕하세요
            A: 보험 상담 받고 싶은데요
        """
        if format_type == "simple":
            lines = [
                f"{utterance['speaker']}: {utterance['text']}"
                for utterance in utterances
            ]
            return "\n".join(lines)

        elif format_type == "detailed":
            lines = []
            for utterance in utterances:
                start_sec = utterance['start'] / 1000
                end_sec = utterance['end'] / 1000
                lines.append(
                    f"[{start_sec:.1f}s - {end_sec:.1f}s] "
                    f"{utterance['speaker']}: {utterance['text']}"
                )
            return "\n".join(lines)

        return ""


# Global instance
stt_service = STTService()
