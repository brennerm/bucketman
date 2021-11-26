import inspect

import boto3

import textual
from textual.layouts.grid import GridLayout
import textual.reactive
from textual.widget import Widget
from textual.widgets import Button, ScrollView, Placeholder
import textual.events
from rich.console import RenderableType
import rich.panel
import rich.table
import rich.text
import rich.align
import rich.layout


class S3BucketSelect(Widget):
    selected_style = "bold black on #FF9900"
    unselected_style = "#FF9900 on black"

    def __init__(self, callback, callback_args=[], callback_kwargs={}) -> None:
        client = boto3.client('s3')
        self.buckets = [bucket['Name'] for bucket in client.list_buckets()['Buckets']]
        self.selected_index = 0
        self.__callback = callback
        self.__callback_args = callback_args
        self.__callback_kwargs = callback_kwargs
        super().__init__(name='S3 bucket select')

    has_focus: textual.reactive.Reactive[bool] = textual.reactive.Reactive(False)

    async def on_focus(self) -> None:
        self.has_focus = True

    def on_blur(self) -> None:
        self.has_focus = False

    @property
    def selected_bucket(self):
        try:
            return self.buckets[self.selected_index]
        except IndexError:
            return None

    async def on_key(self, event: textual.events.Key) -> None:
        await self.dispatch_key(event)

    async def key_up(self, event: textual.events.Key) -> None:
        if self.selected_index > 0:
            self.selected_index -= 1
        self.refresh()

    async def key_down(self, event: textual.events.Key) -> None:
        if self.selected_index < len(self.buckets) - 1:
            self.selected_index += 1
        self.refresh()

    async def key_enter(self, event: textual.events.Key) -> None:
        event.prevent_default().stop()
        pass
        if self.selected_bucket and self.__callback is not None:
            if inspect.iscoroutinefunction(self.__callback):
                await self.__callback(*self.__callback_args, **self.__callback_kwargs)
            else:
                self.__callback(*self.__callback_args, **self.__callback_kwargs)

    def render(self) -> RenderableType:
        buttons = [Button(rich.align.Align(bucket, vertical='middle'), style=S3BucketSelect.selected_style if index == self.selected_index and self.has_focus else S3BucketSelect.unselected_style) for index, bucket in enumerate(self.buckets)]
        layout = rich.layout.Layout()
        layout.split_column(
            *buttons
        )

        return rich.panel.Panel(layout, title='Select S3 bucket')
