"""Speech-to-Text service using AssemblyAI with speaker diarization"""

from typing import List, Dict, Optional
import assemblyai as aai
from app.core.config import settings


class STTService:
    """Service for Speech-to-Text with speaker diarization using AssemblyAI"""

    def __init__(self):
        aai.settings.api_key = settings.ASSEMBLYAI_API_KEY

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
        # Configure transcription
        config = aai.TranscriptionConfig(
            speaker_labels=speaker_labels,
            language_code=language_code
        )

        # Create transcriber
        transcriber = aai.Transcriber()

        # Transcribe
        transcript = transcriber.transcribe(audio_file_path, config=config)

        # Wait for completion
        if transcript.status == aai.TranscriptStatus.error:
            raise Exception(f"Transcription failed: {transcript.error}")

        # Process utterances
        utterances = []
        speakers_set = set()

        if transcript.utterances:
            for utterance in transcript.utterances:
                # Convert speaker label (e.g., "SPEAKER_00" -> "A")
                speaker = self._convert_speaker_label(utterance.speaker)
                speakers_set.add(speaker)

                utterances.append({
                    "speaker": speaker,
                    "text": utterance.text,
                    "start": utterance.start,
                    "end": utterance.end,
                    "confidence": utterance.confidence if hasattr(utterance, 'confidence') else 0.0
                })

        # Sort speakers alphabetically
        speakers = sorted(list(speakers_set))

        return {
            "transcript_id": transcript.id,
            "full_text": transcript.text,
            "utterances": utterances,
            "speakers": speakers,
            "duration": utterances[-1]["end"] if utterances else 0
        }

    def _convert_speaker_label(self, speaker_label: str) -> str:
        """
        Convert AssemblyAI speaker label to simple letter

        Args:
            speaker_label: Original label (e.g., "SPEAKER_00", "SPEAKER_01")

        Returns:
            Simple letter (e.g., "A", "B", "C")
        """
        # Extract number from "SPEAKER_00"
        if speaker_label.startswith("SPEAKER_"):
            try:
                speaker_num = int(speaker_label.split("_")[1])
                # Convert to letter: 0->A, 1->B, 2->C, etc.
                return chr(65 + speaker_num)  # 65 is ASCII for 'A'
            except (IndexError, ValueError):
                return speaker_label

        return speaker_label

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
