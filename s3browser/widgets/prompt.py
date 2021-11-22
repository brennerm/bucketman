import textual
import textual.reactive
from textual.widget import Widget
from textual.widgets import Button
import textual.events
from rich.console import RenderableType
import rich.panel
import rich.table

import inspect

class Prompt(Widget):
    def __init__(self, text: str, name: str = None) -> None:
        self.text = text
        self.__callback = None
        self.__callback_args = None
        self.__callback_kwargs = None
        super().__init__(name=name)

    yes = Button('Yes', style="dark_blue on white")
    no = Button('No', style="white on dark_blue")
    result = textual.reactive.Reactive(True)

    async def on_key(self, event: textual.events.Key) -> None:
        await self.dispatch_key(event)

    async def key_left(self, event: textual.events.Key) -> None:
        event.prevent_default().stop()
        self.result = True

    async def key_right(self, event: textual.events.Key) -> None:
        event.prevent_default().stop()
        self.result = False

    async def key_enter(self, event: textual.events.Key) -> None:
        event.prevent_default().stop()
        if self.result and self.__callback is not None:
            if inspect.iscoroutinefunction(self.__callback):
                await self.__callback(*self.__callback_args, **self.__callback_kwargs)
            else:
                self.__callback(*self.__callback_args, **self.__callback_kwargs)

        self.text = ""
        self.__callback = self.__callback_args = self.__callback_kwargs = None
        await self.app.toggle_dialog()

    async def watch_result(self, result):
        if result:
            self.yes.button_style = "dark_blue on white"
            self.no.button_style = "white on dark_blue"
        else:
            self.no.button_style = "dark_blue on white"
            self.yes.button_style = "white on dark_blue"

    def render(self) -> RenderableType:
        table = rich.table.Table.grid(padding=(0, 1), expand=True)
        table.add_column('left')
        table.add_column('right')
        table.add_row(self.text)
        table.add_row(self.yes, self.no)

        return rich.panel.Panel(table)

    async def do_prompt(self, prompt, callback, *args, **kwargs):
        self.text = prompt
        self.__callback = callback
        self.__callback_args = args
        self.__callback_kwargs = kwargs
        await self.app.toggle_dialog()