import shutil
import subprocess
import wave
from pathlib import Path

from app.config import SUPPORTED_EXTENSIONS
from app.core.errors import UserFacingError
from app.models import AudioFileInfo


class AudioService:
    @staticmethod
    def analyze_file(file_path: Path) -> AudioFileInfo:
        if not file_path.exists():
            raise UserFacingError("Файл не найден.")

        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise UserFacingError("Неподдерживаемый формат файла.")

        size_bytes = file_path.stat().st_size
        duration_seconds, note = AudioService._detect_duration(file_path, size_bytes)

        return AudioFileInfo(
            file_path=file_path,
            file_name=file_path.name,
            extension=file_path.suffix.lower(),
            size_bytes=size_bytes,
            duration_seconds=duration_seconds,
            analysis_note=note,
        )

    @staticmethod
    def _detect_duration(file_path: Path, size_bytes: int) -> tuple[float, str]:
        ffprobe_path = shutil.which("ffprobe")
        if ffprobe_path:
            command = [
                ffprobe_path,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(file_path),
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                output = result.stdout.strip()
                try:
                    return float(output), "Длительность определена точно через ffprobe."
                except ValueError:
                    pass

        if file_path.suffix.lower() == ".wav":
            try:
                with wave.open(str(file_path), "rb") as wav_file:
                    frames = wav_file.getnframes()
                    frame_rate = wav_file.getframerate() or 1
                    return frames / frame_rate, "Длительность определена по WAV-метаданным."
            except wave.Error:
                pass

        estimated_duration_seconds = max(45.0, size_bytes / 180000)
        return (
            estimated_duration_seconds,
            "Точная длительность недоступна. Для лучшего анализа установите ffmpeg/ffprobe.",
        )
