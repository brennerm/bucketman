import textual.message
import textual.types


class StatusUpdate(textual.message.Message):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__()
