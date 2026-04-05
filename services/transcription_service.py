from typing import Callable, Dict, Optional

from app.config import MODEL_PRESETS
from app.core.cancellation import CancellationToken
from app.core.errors import UserFacingError
from app.models import AudioFileInfo, Segment, TranscriptionPayload

ProgressCallback = Callable[[float], None]
LogCallback = Callable[[str], None]


class TranscriptionService:
    _model_cache: Dict[str, object] = {}

    @classmethod
    def transcribe(
        cls,
        audio_info: AudioFileInfo,
        quality_label: str,
        cancellation_token: Optional[CancellationToken] = None,
        progress_callback: Optional[ProgressCallback] = None,
        log_callback: Optional[LogCallback] = None,
    ) -> TranscriptionPayload:
        token = cancellation_token or CancellationToken()
        preset = MODEL_PRESETS.get(quality_label, MODEL_PRESETS["Баланс"])

        model_name, model = cls._load_model(
            model_candidates=preset["model_candidates"],
            log_callback=log_callback,
        )
        token.check_cancelled()

        if log_callback:
            log_callback(f"Использую модель распознавания: {model_name}.")

        try:
            segments_iter, _ = model.transcribe(
                str(audio_info.file_path),
                language="en",
                vad_filter=True,
                beam_size=preset["beam_size"],
            )
        except MemoryError as exc:
            raise UserFacingError("Недостаточно памяти для выбранной модели распознавания.") from exc
        except Exception as exc:
            raise UserFacingError(f"Не удалось запустить распознавание: {exc}") from exc

        segments = []
        total_duration = max(audio_info.duration_seconds, 1.0)
        for raw_segment in segments_iter:
            token.check_cancelled()
            text = raw_segment.text.strip()
            if not text:
                continue

            segments.append(
                Segment(
                    start=float(raw_segment.start),
                    end=float(raw_segment.end),
                    text_en=text,
                )
            )

            if progress_callback:
                progress_callback(min(1.0, float(raw_segment.end) / total_duration))

        if not segments:
            raise UserFacingError("Распознавание завершилось без текста. Проверьте, что в файле есть речь.")

        return TranscriptionPayload(
            segments=segments,
            model_name=model_name,
            backend_name="faster-whisper",
        )

    @classmethod
    def _load_model(
        cls,
        model_candidates: list[str],
        log_callback: Optional[LogCallback] = None,
    ) -> tuple[str, object]:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise UserFacingError(
                "Для распознавания не установлен faster-whisper. Установите зависимости из requirements.txt."
            ) from exc

        last_error = None
        for model_name in model_candidates:
            if model_name in cls._model_cache:
                return model_name, cls._model_cache[model_name]

            try:
                if log_callback:
                    log_callback(f"Подготавливаю модель Whisper: {model_name}.")
                model = WhisperModel(model_name, device="cpu", compute_type="int8")
                cls._model_cache[model_name] = model
                return model_name, model
            except Exception as exc:
                last_error = exc
                if log_callback:
                    log_callback(f"Не удалось подготовить модель {model_name}: {exc}")

        raise UserFacingError(
            "Не удалось загрузить модель распознавания. Проверьте интернет для первой загрузки "
            "или выберите более лёгкий режим качества."
        ) from last_error
