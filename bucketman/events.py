import textual.message


class StatusUpdate(textual.message.Message):
    def __init__(self, sender: textual.message.MessageTarget, message: str) -> None:
        self.message = message
        super().__init__(sender)
