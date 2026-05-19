class DomainError(Exception):
    def __init__(self, *, context: dict[str, object] | None = None):
        super().__init__()
        self.context: dict[str, object] = context if context is not None else {}
