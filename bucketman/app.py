import os
import shutil

import boto3
import botocore.exceptions
import textual.app
import textual.binding
import textual.widgets

from bucketman.constants import AWS_HEX_COLOR_CODE
from bucketman.events import StatusUpdate
from bucketman.widgets import (
    Footer,
    LocalTree,
    Prompt,
    S3BucketSelect,
    S3Tree,
    StatusLog,
    Header,
    VerticalDivider,
)
from bucketman.widgets.common import ObjectType


class BucketManApp(textual.app.App):
    def __init__(
        self,
        *args,
        bucket: str = None,
        endpoint_url: str = None,
        access_key_id: str = None,
        secret_access_key: str = None,
        **kwargs,
    ):

        self.bucket_name = bucket

        session = boto3.Session(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )

        self.s3_client = session.client("s3", endpoint_url=endpoint_url)
        self.s3_resource = session.resource("s3", endpoint_url=endpoint_url)

        self.left_pane = None
        self.right_pane = None
        self.focused_pane = None
        self.status_log = StatusLog()
        self.footer = Footer()
        self.header = Header(style=f"black on {AWS_HEX_COLOR_CODE}")

        self.default_bindings = [
            textual.binding.Binding("ctrl+c", "quit", "", allow_forward=False),
            textual.binding.Binding("escape", "quit", "Quit", show=True),
            textual.binding.Binding(
                "ctrl+i", "cycle", "Cycle", show=True, key_display="TAB"
            ),
        ]
        super().__init__(*args, **kwargs)

    show_dialog = textual.reactive.Reactive(False)

    @property
    def left_widget(self):
        return self.left_pane.window.widget

    @property
    def right_widget(self):
        return self.right_pane.window.widget

    @property
    def focused_widget(self):
        return self.focused_pane.window.widget

    async def load_bindings(self):
        new_bindings = list(self.default_bindings)

        try:
            new_bindings += self.focused.bindings
        except AttributeError:
            pass

        self.bindings = textual.binding.Bindings()
        for binding in new_bindings:
            self.bindings.keys[binding.key] = binding

        self.footer.refresh(layout=True)

    async def on_load(self) -> None:
        await self.load_bindings()

    async def action_cycle(self) -> None:
        if self.left_widget == self.focused:
            await self.right_widget.focus()
            await self.load_bindings()
            self.focused_pane = self.right_pane
        elif self.right_widget == self.focused:
            await self.left_widget.focus()
            await self.load_bindings()
            self.focused_pane = self.left_pane

    async def action_delete(self) -> None:
        if self.left_widget == self.focused:
            path = self.left_widget.selected_object.path
            await self.dialog.do_prompt(
                f"Do you want to delete the path {path}?",
                self.do_local_delete,
                path=path,
            )

    async def do_local_delete(self, path) -> None:
        try:
            if os.path.isfile(path):
                os.remove(path)
            else:
                shutil.rmtree(path)
        except OSError as e:
            await self.handle_status_update(
                StatusUpdate(
                    self, message=f'Failed to delete path "{path}": {e.strerror}'
                )
            )
        else:
            await self.handle_status_update(
                StatusUpdate(self, message=f'Successfully deleted path "{path}"')
            )
            await self.left_widget.load_objects(self.left_widget.selected_node.parent)

    async def action_copy(self) -> None:
        if self.left_widget == self.focused:
            message = MakeCopy(
                self,
                src_bucket=None,
                src_path=self.left_widget.selected_object.path,
                dst_bucket=self.right_widget.bucket_name,
                dst_path=os.path.dirname(self.right_widget.selected_object.key),
                recursive=True,
            )
        else:
            message = MakeCopy(
                self,
                src_bucket=self.right_widget.bucket_name,
                src_path=self.right_widget.selected_object.key,
                dst_bucket=None,
                dst_path=self.left_widget.data.path,
                recursive=True,
            )

        # local copy
        if message.src_bucket is None and message.dst_bucket is None:
            await self.handle_status_update(
                StatusUpdate(
                    self, message="Copying from local to local is not yet supported!"
                )
            )
        # upload
        elif message.src_bucket is None and message.dst_bucket is not None:
            key = os.path.join(message.dst_path, os.path.basename(message.src_path))
            await self.dialog.do_prompt(
                f"Do you want to upload the file {message.src_path} to {self.right_widget.bucket_name}/{key}?",
                self.do_upload,
                path=message.src_path,
                bucket=self.right_widget.bucket_name,
                key=key,
            )
        # download
        elif message.src_bucket is not None and message.dst_bucket is None:
            path = os.path.join(message.dst_path, os.path.basename(message.src_path))
            await self.dialog.do_prompt(
                f"Do you want to download the object {self.right_widget.bucket_name}/{self.right_widget.selected_object.key} to {path}?",
                self.do_download,
                bucket=self.right_widget.bucket_name,
                key=self.right_widget.selected_object.key,
                path=path,
            )
        # copy from one bucket to another
        else:
            await self.handle_status_update(
                StatusUpdate(
                    self, message="Copying from S3 to S3 is not yet supported!"
                )
            )

    async def do_upload(self, path, bucket, key) -> None:
        try:
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for file in files:
                        src = os.path.join(root, file)
                        dst = os.path.normpath(
                            os.path.join(key, os.path.relpath(root, path), file)
                        )
                        self.s3_client.upload_file(src, bucket, dst)
                        await self.handle_status_update(
                            StatusUpdate(
                                self, message=f"Uploaded file {src} to {bucket}/{dst}"
                            )
                        )
            else:
                self.s3_client.upload_file(path, bucket, key)
        except botocore.exceptions.ClientError as e:
            await self.handle_status_update(
                StatusUpdate(
                    self,
                    message=f'Failed to upload file {path} to {bucket}/{key}: {e.response["Error"]["Message"]}',
                )
            )
        else:
            node_to_reload = (
                self.right_widget.selected_node.parent
                if self.right_widget.selected_node.parent
                else self.right_widget.selected_node
            )
            await self.right_widget.load_objects(node_to_reload)

    async def do_download(self, bucket, key, path) -> None:
        try:
            self.s3_client.download_file(bucket, key, path)
        except botocore.exceptions.ClientError as e:
            await self.handle_status_update(
                StatusUpdate(
                    self,
                    message=f'Failed to download object {bucket}/{key} to {path}: {e.response["Error"]["Message"]}',
                )
            )
        else:
            node_to_reload = (
                self.left_widget.selected_node.parent
                if self.left_widget.selected_node.parent
                else self.left_widget.selected_node
            )
            await self.left_widget.load_objects(node_to_reload)
            await self.handle_status_update(
                StatusUpdate(
                    self, message=f"Downloaded object {bucket}/{key} to {path}"
                )
            )

    async def handle_status_update(self, message: StatusUpdate) -> None:
        await self.status_log.add_status(message.message)

    def watch_show_dialog(self, show_bar: bool) -> None:
        self.dialog.animate(
            "layout_offset_y", -(self.view.size.height / 2) + 10 if show_bar else 20
        )

    async def toggle_dialog(self) -> None:
        self.show_dialog = not self.show_dialog
        if self.show_dialog:
            await self.dialog.focus()
        else:
            await self.focused_widget.focus()

    async def show_select_bucket(self) -> None:
        await self.focused_pane.update(S3BucketSelect(self.bucket_selected))
        await self.focused_widget.focus()
        await self.load_bindings()

    async def bucket_selected(self):
        bucket_name = self.focused_widget.selected_bucket
        s3tree = S3Tree(bucket_name, name="s3")
        await self.focused_pane.update(s3tree)
        await self.focused_widget.focus()
        await self.load_bindings()

    async def on_mount(self) -> None:
        self.dialog = Prompt("", name="prompt")
        await self.view.dock(self.dialog, edge="bottom", size=20, z=1)
        self.dialog.layout_offset_y = 20

        directory = LocalTree(os.getcwd())
        directory.show_cursor = True
        self.left_pane = textual.widgets.ScrollView(directory, name="left_pane")
        if self.bucket_name:
            widget = S3Tree(self.bucket_name, name="s3")
        else:
            widget = S3BucketSelect(self.bucket_selected)
        self.right_pane = textual.widgets.ScrollView(widget, name="right_pane")

        await self.right_pane.window.widget.focus()
        self.focused_pane = self.right_pane

        grid = await self.view.dock_grid(name="grid")

        grid.add_column("left")
        grid.add_column("middle", size=1)
        grid.add_column("right")
        grid.add_row("header", size=1)
        grid.add_row("pane")
        grid.add_row("status", size=6)
        grid.add_row("footer", size=1)
        grid.add_areas(
            header="left-start|right-end,header",
            left="left,pane",
            middle="middle,pane",
            right="right,pane",
            status="left-start|right-end,status",
            footer="left-start|right-end,footer",
        )

        grid.place(header=self.header)
        grid.place(left=self.left_pane)
        grid.place(middle=VerticalDivider())
        grid.place(right=self.right_pane)
        grid.place(status=self.status_log)
        grid.place(footer=self.footer)
