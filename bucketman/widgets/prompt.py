import inspect

import textual
import textual.reactive
from textual.widget import Widget
from textual.widgets import Button
import textual.events
from rich.console import RenderableType
import rich.panel
import rich.table
import rich.text
import rich.align
import rich.layout

from bucketman.constants import AWS_HEX_COLOR_CODE

class Prompt(Widget):
    selected_style = f"bold black on {AWS_HEX_COLOR_CODE}"
    unselected_style = f"{AWS_HEX_COLOR_CODE} on black"

    def __init__(self, text: str, name: str = None) -> None:
        self.text = text
        self.__callback = None
        self.__callback_args = None
        self.__callback_kwargs = None
        super().__init__(name=name)

    yes = Button('Yes', style=unselected_style)
    no = Button('No', style=selected_style)
    result = textual.reactive.Reactive(False)

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
        self.result = False
        await self.app.toggle_dialog()

    async def watch_result(self, result):
        if result:
            self.yes.button_style = self.selected_style
            self.no.button_style = self.unselected_style
        else:
            self.no.button_style = self.selected_style
            self.yes.button_style = self.unselected_style

    def render(self) -> RenderableType:
        layout = rich.layout.Layout()
        layout.split_column(
            rich.align.Align(rich.text.Text(self.text, style="bold"), align="center", vertical="middle"),
            rich.layout.Layout(name="bottom")
        )

        layout["bottom"].split_row(
            self.yes,
            self.no,
        )

        return rich.panel.Panel(layout)

    async def do_prompt(self, prompt, callback, *args, **kwargs):
        self.text = prompt
        self.__callback = callback
        self.__callback_args = args
        self.__callback_kwargs = kwargs
        await self.app.toggle_dialog()