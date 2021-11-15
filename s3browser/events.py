import textual.message

class StatusUpdate(textual.message.Message, bubble=True, verbosity=3):
    def __init__(self, sender: textual.message.MessageTarget, message: str) -> None:
        self.message = message
        super().__init__(sender)