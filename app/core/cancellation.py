from threading import Event

from app.core.errors import ProcessingCancelledError


class CancellationToken:
    def __init__(self) -> None:
        self._event = Event()

    def cancel(self) -> None:
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def check_cancelled(self) -> None:
        if self.is_cancelled():
            raise ProcessingCancelledError()
