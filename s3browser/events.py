import textual.message

class StatusUpdate(textual.message.Message):
    def __init__(self, sender: textual.message.MessageTarget, message: str) -> None:
        self.message = message
        super().__init__(sender)

class MakeCopy(textual.message.Message):
    def __init__(self, sender: textual.message.MessageTarget,
    src_bucket: str,
    dst_bucket: str,
    src_path: str,
    dst_path: str,
    recursive: bool) -> None:
        self.src_bucket = src_bucket
        self.src_path = src_path
        self.dst_bucket = dst_bucket
        self.dst_path = dst_path
        self.recursive = recursive
        super().__init__(sender)