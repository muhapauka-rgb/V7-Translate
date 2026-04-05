from datetime import datetime
from pathlib import Path
from traceback import format_exc
from typing import Optional

from PySide6.QtCore import QThread, Signal

from app.config import STATE_DIR
from app.core.cancellation import CancellationToken
from app.core.errors import ProcessingCancelledError, UserFacingError
from app.core.pipeline import ProcessingPipeline
from app.models import ProcessingRequest, ProcessingResult


class ProcessingWorker(QThread):
    progress_changed = Signal(int)
    status_changed = Signal(str)
    log_message = Signal(str)
    completed = Signal(object)
    failed = Signal(str)
    cancelled = Signal(str)

    def __init__(self, request: ProcessingRequest, parent: Optional[object] = None) -> None:
        super().__init__(parent)
        self.request = request
        self.cancellation_token = CancellationToken()
        self.pipeline = ProcessingPipeline()

    def cancel(self) -> None:
        self.cancellation_token.cancel()

    def run(self) -> None:
        try:
            result = self.pipeline.run(
                request=self.request,
                cancellation_token=self.cancellation_token,
                progress_callback=self._handle_progress,
                log_callback=self.log_message.emit,
            )
        except ProcessingCancelledError as exc:
            self.cancelled.emit(str(exc))
        except UserFacingError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # pragma: no cover - defensive fallback for UI.
            self._write_crash_log(exc)
            self.failed.emit(f"Произошла непредвиденная ошибка: {exc}")
        else:
            self.completed.emit(result)

    def _handle_progress(self, value: int, message: str) -> None:
        self.progress_changed.emit(value)
        self.status_changed.emit(message)

    def _write_crash_log(self, exc: Exception) -> None:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        log_path = STATE_DIR / "runtime_errors.log"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with log_path.open("a", encoding="utf-8") as file:
            file.write(f"[{timestamp}] {type(exc).__name__}: {exc}\n")
            file.write(format_exc())
            file.write("\n\n")
