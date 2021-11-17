import collections

from rich.console import RenderableType
from textual.widget import Widget, watch
import rich.repr
import rich.panel

from s3browser.events import StatusUpdate


class StatusLog(Widget):
    name = 'status'

    def __init__(self) -> None:
        super().__init__()
        self.lines = collections.deque([])

    def __rich_repr__(self) -> rich.repr.Result:
        yield "name", self.name

    async def add_status(self, message: str) -> None:
        self.lines.appendleft(message)
        self.refresh()

    def render(self) -> RenderableType:
        return rich.panel.Panel('\n'.join(list(self.lines)), title="Status")