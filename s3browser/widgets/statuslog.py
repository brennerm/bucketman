from rich.console import RenderableType
from textual.widget import Widget
import rich.repr
import rich.panel
import rich.align


class StatusLog(Widget):
    name = 'status'

    def __init__(self) -> None:
        super().__init__()
        self.lines = []

    def __rich_repr__(self) -> rich.repr.Result:
        yield "name", self.name

    async def add_status(self, message: str) -> None:
        self.lines.append(message)
        self.refresh()

    def render(self) -> RenderableType:
        visible_lines = self.lines[-(self.size.height - 2):]

        return rich.panel.Panel(
            rich.align.Align('\n'.join(visible_lines), vertical="bottom")
            , title="Status"
            )