from datetime import datetime
from pathlib import Path
from time import perf_counter
from traceback import format_exc
from typing import Callable, Optional

from app.config import STATE_DIR
from app.core.cancellation import CancellationToken
from app.core.errors import UserFacingError
from app.models import ProcessingRequest, ProcessingResult
from services.audio_service import AudioService
from services.estimate_service import EstimateService
from services.export_service import ExportService
from services.transcription_service import TranscriptionService
from services.translation_service import TranslationService

ProgressCallback = Callable[[int, str], None]
LogCallback = Callable[[str], None]


class ProcessingPipeline:
    def __init__(self, estimate_service: Optional[EstimateService] = None) -> None:
        self.estimate_service = estimate_service or EstimateService()

    def run(
        self,
        request: ProcessingRequest,
        cancellation_token: Optional[CancellationToken] = None,
        progress_callback: Optional[ProgressCallback] = None,
        log_callback: Optional[LogCallback] = None,
    ) -> ProcessingResult:
        token = cancellation_token or CancellationToken()
        started_at = perf_counter()
        warnings: list[str] = []

        def report_progress(value: int, message: str) -> None:
            if progress_callback:
                progress_callback(value, message)

        def report_log(message: str) -> None:
            if log_callback:
                log_callback(message)

        output_dir = Path(request.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        report_progress(5, "Анализ файла")
        report_log("Проверяю выбранный файл и определяю его параметры.")
        audio_info = AudioService.analyze_file(request.input_path)
        if audio_info.analysis_note:
            report_log(audio_info.analysis_note)
        token.check_cancelled()

        report_progress(12, "Подготовка")
        report_log(f"Качество распознавания: {request.quality_label}.")

        transcription_payload = TranscriptionService.transcribe(
            audio_info=audio_info,
            quality_label=request.quality_label,
            cancellation_token=token,
            progress_callback=lambda part: report_progress(12 + int(part * 48), "Распознавание"),
            log_callback=report_log,
        )
        token.check_cancelled()
        report_log(f"Распознавание завершено. Получено сегментов: {len(transcription_payload.segments)}.")

        segments = transcription_payload.segments
        if request.export_options.translate_to_ru:
            report_progress(64, "Перевод")
            report_log("Запускаю локальный перевод на русский.")
            try:
                segments = TranslationService.translate_segments(
                    segments=segments,
                    cancellation_token=token,
                    progress_callback=lambda part: report_progress(64 + int(part * 18), "Перевод"),
                    log_callback=report_log,
                )
                token.check_cancelled()
                report_log("Перевод завершён.")
            except UserFacingError as exc:
                warning = (
                    "Перевод не выполнен. Продолжаю без русского текста. "
                    f"Причина: {exc}"
                )
                warnings.append(warning)
                report_log(warning)
                self._write_warning_log(exc)
            except Exception as exc:
                warning = (
                    "Во время перевода произошла непредвиденная ошибка. "
                    "Продолжаю без русского текста."
                )
                warnings.append(f"{warning} Причина: {exc}")
                report_log(f"{warning} Причина: {exc}")
                self._write_warning_log(exc)
        else:
            report_log("Перевод отключён пользователем.")

        report_progress(84, "Сохранение")
        report_log(f"Сохраняю результаты в папку: {output_dir}.")
        generated_files = ExportService.export_outputs(
            output_dir=output_dir,
            audio_info=audio_info,
            segments=segments,
            model_name=transcription_payload.model_name,
            export_options=request.export_options,
            base_name=request.input_path.stem,
        )

        actual_processing_seconds = perf_counter() - started_at
        self.estimate_service.record_run(
            audio_duration_seconds=audio_info.duration_seconds,
            quality_label=request.quality_label,
            actual_processing_seconds=actual_processing_seconds,
        )

        report_progress(100, "Готово")
        report_log("Обработка завершена успешно.")

        return ProcessingResult(
            success=True,
            audio_info=audio_info,
            segments=segments,
            generated_files=generated_files,
            warnings=warnings,
            model_name=transcription_payload.model_name,
            actual_processing_seconds=actual_processing_seconds,
        )

    def _write_warning_log(self, exc: Exception) -> None:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        log_path = STATE_DIR / "runtime_errors.log"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with log_path.open("a", encoding="utf-8") as file:
            file.write(f"[{timestamp}] Translation warning {type(exc).__name__}: {exc}\n")
            file.write(format_exc())
            file.write("\n\n")
