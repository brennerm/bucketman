import rich.console
import rich.panel
import rich.repr
import rich.style
import rich.table
import textual.reactive
import textual.widget
import textual.widgets

class Header(textual.widget.Widget):
    def __init__(self, style: rich.style.StyleType) -> None:
        super().__init__()
        self.title = ""
        self.style = style

    @property
    def full_title(self) -> str:
        return self.title

    def __rich_repr__(self) -> rich.repr.Result:
        yield self.title

    async def on_mount(self) -> None:
        async def set_title(title: str) -> None:
            self.title = title

        textual.reactive.watch(self.app, "title", set_title)

    def render(self) -> rich.console.RenderableType:
        header_table = rich.table.Table.grid(padding=(0, 1), expand=True)
        header_table.style = self.style
        header_table.add_column(justify="left", ratio=0, width=32)
        header_table.add_column("title", justify="center", ratio=1)
        header_table.add_column("built", justify="right", width=32)
        header_table.add_row(
            "🪣", self.full_title, "🔨 with 💗 by [link=https://brennerm.github.io/about.html]brennerm[/link]"
        )
        return header_table

