class UserFacingError(RuntimeError):
    """Error that can be shown to the user without technical details."""


class ProcessingCancelledError(UserFacingError):
    def __init__(self) -> None:
        super().__init__("Обработка отменена пользователем.")
