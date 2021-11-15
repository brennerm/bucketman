from rich.console import RenderableType
from rich.text import Text
from textual.widget import Widget
import rich.repr

from s3browser.events import StatusUpdate


class StatusLog(Widget):
    name = 'status'

    def __init__(self) -> None:
        super().__init__()
        self.lines = ["test"]

    def __rich_repr__(self) -> rich.repr.Result:
        yield "name", self.name

    def add_status(self, message: str) -> None:
        self.lines.append(message)
        self.refresh(layout=True)

    def render(self) -> RenderableType:
        return '\n'.join(self.lines)