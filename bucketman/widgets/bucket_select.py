import inspect

import boto3
import botocore.exceptions
import textual
import textual.reactive
import textual.widget
import textual.events
import rich.console
import rich.panel
import rich.table
import rich.text
import rich.align
import rich.layout

from bucketman.constants import AWS_HEX_COLOR_CODE


class S3BucketSelect(textual.widget.Widget):
    selected_style = f"bold black on {AWS_HEX_COLOR_CODE}"
    unselected_style = f"{AWS_HEX_COLOR_CODE} on black"

    def __init__(self, callback, callback_args=[], callback_kwargs={}) -> None:
        super().__init__(name='S3 bucket select')

        self.buckets = None
        self.selected_index = 0
        self.__callback = callback
        self.__callback_args = callback_args
        self.__callback_kwargs = callback_kwargs

    has_focus: textual.reactive.Reactive[bool] = textual.reactive.Reactive(False)

    async def on_focus(self) -> None:
        self.has_focus = True

    def on_blur(self) -> None:
        self.has_focus = False

    @property
    def selected_bucket(self):
        try:
            return self.buckets[self.selected_index]
        except (IndexError, TypeError):
            return None

    async def on_mount(self) -> None:
        client = boto3.client('s3')
        try:
            self.buckets = [bucket['Name'] for bucket in client.list_buckets()['Buckets']]
        except botocore.exceptions.ClientError:
            self.app.panic("Bucketman is unable to list your S3 buckets. Make sure your user has the required permissions or pass a bucket name using the --bucket option.")


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

    def render(self) -> rich.console.RenderableType:
        layout = rich.layout.Layout()

        if self.buckets is None:
            layout.split_column(
                rich.align.Align("Loading S3 buckets...", vertical='middle', align='center', height=3, style=S3BucketSelect.selected_style),
            )
        elif self.buckets == []:
            layout.split_column(
                rich.align.Align("No S3 buckets found.", vertical='middle', align='center', height=3, style=S3BucketSelect.selected_style)
            )
        else:
            buttons = [
                rich.align.Align(
                    bucket,
                    vertical='middle',
                    align='center',
                    height=3,
                    style=S3BucketSelect.selected_style if index == self.selected_index and self.has_focus else S3BucketSelect.unselected_style
                ) for index, bucket in enumerate(self.buckets)
            ]
            layout.split_column(
                rich.console.Group(*buttons)
            )

        return rich.panel.Panel(
            layout,
            title='Select S3 bucket'
        )
