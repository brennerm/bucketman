import os
import shutil

import boto3
import botocore.exceptions
import textual.app

from bucketman.constants import AWS_HEX_COLOR_CODE
from bucketman.events import MakeCopy, StatusUpdate
from bucketman.widgets import (Footer, LocalTree, Prompt, S3BucketSelect,
                               S3Tree, StatusLog, Header)


class BucketManApp(textual.app.App):
    def __init__(self, *args, bucket: str=None, **kwargs):
        self.left_pane = None
        self.right_pane = None
        self.focused_pane = None
        self.status_log = None
        self.directory = None
        self.bucket_name = bucket
        super().__init__(*args, **kwargs)

    show_dialog = textual.reactive.Reactive(False)

    async def on_load(self) -> None:
        await self.bind("escape", "quit", "Quit")
        await self.bind("ctrl+i", "cycle", "Cycle", key_display='TAB')
        await self.bind("b", "select_bucket", "Select Bucket", key_display='b')
        await self.bind("R", "reload", "Reload")
        #await self.bind("c", "copy", "Copy", key_display='c')
        #await self.bind("r", "rename", "Rename", key_display='r')
        #await self.bind("d", "delete", "Delete", key_display='d')

    async def action_reload(self) -> None:
        if self.left_pane.window.widget == self.focused:
            await self.left_pane.window.widget.load_objects(self.left_pane.window.widget.selected_node)
        elif self.right_pane.window.widget == self.focused:
            await self.right_pane.window.widget.load_objects(self.right_pane.window.widget.selected_node)

    async def action_cycle(self) -> None:
        if self.left_pane.window.widget == self.focused:
            await self.right_pane.window.widget.focus()
            self.focused_pane = self.right_pane
        elif self.right_pane.window.widget == self.focused:
            await self.left_pane.window.widget.focus()
            self.focused_pane = self.left_pane

    async def action_select_bucket(self) -> None:
        if self.left_pane.window.widget == self.focused:
            pass
        elif self.right_pane.window.widget == self.focused:
            await self.right_pane.update(
                S3BucketSelect(self.bucket_selected)
            )
            await self.right_pane.window.widget.focus()

    async def action_delete(self) -> None:
        if self.left_pane.window.widget == self.focused:
            path = self.directory.selected_object.path
            await self.dialog.do_prompt(
                f"Do you want to delete the path {path}?",
                self.do_local_delete,
                path=path
            )
        else:
            if self.right_pane.window.widget.selected_object.key:
                prompt = f"Do you want to delete the object {self.right_pane.window.widget.selected_object.key}?"
            else:
                prompt = f"Do you want to empty the bucket {self.right_pane.window.widget.bucket_name}?"

            await self.dialog.do_prompt(
                prompt,
                self.do_s3_delete,
                bucket=self.right_pane.window.widget.bucket_name,
                key=self.right_pane.window.widget.selected_object.key
            )

    async def do_local_delete(self, path) -> None:
        try:
            if os.path.isfile(path):
                os.remove(path)
            else:
                shutil.rmtree(path)
        except OSError as e:
            await self.handle_status_update(StatusUpdate(self, message=f'Failed to delete path "{path}": {e.strerror}'))
        else:
            await self.handle_status_update(StatusUpdate(self, message=f'Successfully deleted path "{path}"'))
            await self.directory.load_objects(self.directory.selected_node.parent)

    async def do_s3_delete(self, bucket, key) -> None:
        s3 = boto3.resource('s3')
        bucket = s3.Bucket(bucket)

        try:
            bucket.objects.filter(Prefix=key).delete()
            await self.handle_status_update(StatusUpdate(self, message=f'Deleted S3 object(s) "{bucket}:{key}"'))

        except botocore.exceptions.ClientError as e:
            await self.handle_status_update(StatusUpdate(self, message=f'Failed to delete S3 object(s) "{bucket}:{key}": {e.response["Error"]["Message"]}'))
        else:
            await self.right_pane.window.widget.load_objects(self.right_pane.window.widget.selected_node.parent)

    async def action_copy(self) -> None:
        if self.left_pane.window.widget == self.focused:
            message = MakeCopy(
                self,
                src_bucket=None,
                src_path=self.directory.selected_object.path,
                dst_bucket=self.right_pane.window.widget.bucket_name,
                dst_path=os.path.dirname(self.right_pane.window.widget.selected_object.key),
                recursive=True
            )
        else:
            message = MakeCopy(
                self,
                src_bucket=self.right_pane.window.widget.bucket_name,
                src_path=self.right_pane.window.widget.selected_object.key,
                dst_bucket=None,
                dst_path=self.directory.data.path,
                recursive=True
            )

        # local copy
        if message.src_bucket is None and message.dst_bucket is None:
            await self.handle_status_update(StatusUpdate(self, message='Copying from local to local is not yet supported!'))
        # upload
        elif message.src_bucket is None and message.dst_bucket is not None:
            key = os.path.join(message.dst_path, os.path.basename(message.src_path))
            await self.dialog.do_prompt(
                f"Do you want to upload the file {message.src_path} to {self.right_pane.window.widget.bucket_name}/{key}?",
                self.do_upload,
                path=message.src_path,
                bucket=self.right_pane.window.widget.bucket_name,
                key=key
            )
        # download
        elif message.src_bucket is not None and message.dst_bucket is None:
            path = os.path.join(message.dst_path, os.path.basename(message.src_path))
            await self.dialog.do_prompt(
                f"Do you want to download the object {self.right_pane.window.widget.bucket_name}/{self.right_pane.window.widget.selected_object.key} to {path}?",
                self.do_download,
                bucket=self.right_pane.window.widget.bucket_name,
                key=self.right_pane.window.widget.selected_object.key,
                path=path
            )
        # copy from one bucket to another
        else:
            await self.handle_status_update(StatusUpdate(self, message='Copying from S3 to S3 is not yet supported!'))

    async def do_upload(self, path, bucket, key) -> None:
        client = boto3.client('s3')

        try:
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for file in files:
                        src = os.path.join(root, file)
                        dst = os.path.normpath(os.path.join(key, os.path.relpath(root, path),file))
                        client.upload_file(src, bucket, dst)
                        await self.handle_status_update(StatusUpdate(self, message=f'Uploaded file {src} to {bucket}/{dst}'))
            else:
                client.upload_file(path, bucket, key)
        except botocore.exceptions.ClientError as e:
            await self.handle_status_update(StatusUpdate(self, message=f'Failed to upload file {path} to {bucket}/{key}: {e.response["Error"]["Message"]}'))
        else:
            node_to_reload = self.right_pane.window.widget.selected_node.parent if self.right_pane.window.widget.selected_node.parent else self.right_pane.window.widget.selected_node
            await self.right_pane.window.widget.load_objects(node_to_reload)

    async def do_download(self, bucket, key, path) -> None:
        client = boto3.client('s3')

        try:
            client.download_file(bucket, key, path)
        except botocore.exceptions.ClientError as e:
            await self.handle_status_update(StatusUpdate(self, message=f'Failed to download object {bucket}/{key} to {path}: {e.response["Error"]["Message"]}'))
        else:
            await self.directory.load_objects(self.directory.selected_node.parent)
            await self.handle_status_update(StatusUpdate(self, message=f'Downloaded object {bucket}/{key} to {path}'))

    async def handle_status_update(self, message: StatusUpdate) -> None:
        await self.status_log.add_status(message.message)

    def watch_show_dialog(self, show_bar: bool) -> None:
        self.dialog.animate("layout_offset_y", -(self.view.size.height / 2) + 10 if show_bar else 20)

    async def toggle_dialog(self) -> None:
        self.show_dialog = not self.show_dialog
        if self.show_dialog:
            await self.dialog.focus()
        else:
            await self.focused_pane.window.widget.focus()

    async def bucket_selected(self):
        bucket_name = self.focused_pane.window.widget.selected_bucket
        s3tree = S3Tree(bucket_name, name="s3")
        await self.focused_pane.update(s3tree)
        await self.focused_pane.window.widget.focus()

    async def on_mount(self) -> None:
        self.dialog = Prompt("", name="prompt")
        await self.view.dock(self.dialog, edge="bottom", size=20, z=1)
        self.dialog.layout_offset_y = 20

        self.status_log = StatusLog()
        self.directory = LocalTree(os.getcwd())
        self.directory.show_cursor = True
        self.left_pane = textual.widgets.ScrollView(self.directory, name="left_pane")
        if self.bucket_name:
            widget = S3Tree(self.bucket_name, name="s3")
        else:
            widget = S3BucketSelect(self.bucket_selected)
        self.right_pane = textual.widgets.ScrollView(widget, name="right_pane")

        grid = await self.view.dock_grid()

        grid.add_column("left")
        grid.add_column("right")
        grid.add_row("header", size=1)
        grid.add_row("pane")
        grid.add_row("status", size=6)
        grid.add_row("footer", size=1)
        grid.add_areas(
            left="left,pane",
            right="right,pane",
            status="left-start|right-end,status",
            footer="left-start|right-end,footer",
            header="left-start|right-end,header",
        )

        grid.place(header=Header(style=f"black on {AWS_HEX_COLOR_CODE}"))
        grid.place(left=self.left_pane)
        grid.place(right=self.right_pane)
        grid.place(status=self.status_log)
        grid.place(footer=Footer())

        await self.right_pane.window.widget.focus()
        self.focused_pane = self.right_pane

