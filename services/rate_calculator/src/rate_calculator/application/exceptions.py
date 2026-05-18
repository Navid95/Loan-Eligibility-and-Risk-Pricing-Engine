class ApplicationError(Exception):
    def __init__(self, *, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class NotFoundError(ApplicationError):
    pass


class ConflictError(ApplicationError):
    pass


class ValidationError(ApplicationError):
    pass
