"""음성 파일 유틸리티"""

from pathlib import Path
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.wave import WAVE


def get_audio_duration_ms(file_path: str) -> int:
    """
    음성 파일 길이 반환 (밀리초)

    Args:
        file_path: 음성 파일 경로

    Returns:
        duration_ms: 파일 길이 (밀리초)

    Raises:
        ValueError: 지원하지 않는 포맷 또는 분석 실패 시
    """
    ext = Path(file_path).suffix.lower()

    try:
        if ext == ".mp3":
            audio = MP3(file_path)
        elif ext == ".m4a":
            audio = MP4(file_path)
        elif ext == ".wav":
            audio = WAVE(file_path)
        else:
            raise ValueError(f"지원하지 않는 포맷: {ext}")

        # mutagen은 초 단위로 반환
        return int(audio.info.length * 1000)

    except Exception as e:
        raise ValueError(f"음성 파일 분석 실패: {e}")


def validate_audio_duration(file_path: str, max_minutes: int = 30) -> int:
    """
    음성 파일 길이 검증

    Args:
        file_path: 음성 파일 경로
        max_minutes: 최대 허용 길이 (분)

    Returns:
        duration_ms: 파일 길이 (밀리초)

    Raises:
        ValueError: 최대 길이 초과 시
    """
    duration_ms = get_audio_duration_ms(file_path)
    max_ms = max_minutes * 60 * 1000

    if duration_ms > max_ms:
        duration_min = duration_ms // 60000
        raise ValueError(
            f"파일이 너무 깁니다. ({duration_min}분 > 최대 {max_minutes}분)"
        )

    return duration_ms
