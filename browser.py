import os
import shutil
import warnings

import boto3
import botocore.exceptions

import textual.app
import textual.widgets
import textual.views
import textual.reactive

from s3browser.widgets.footer import Footer
from s3browser.widgets.prompt import Prompt
from s3browser.widgets.s3tree import S3Tree
from s3browser.widgets.statuslog import StatusLog
from s3browser.events import MakeCopy, StatusUpdate

class BucketManApp(textual.app.App):
    def __init__(self, *args, **kwargs):
        self.left_pane = None
        self.right_pane = None
        self.status_log = None
        self.directory = None
        self.s3tree = None
        self.bucket_name = 'openwifi-allure-reports'
        super().__init__(*args, **kwargs)

    show_dialog = textual.reactive.Reactive(False)

    async def on_load(self) -> None:
        await self.bind("escape", "quit", "Quit")
        await self.bind("ctrl+i", "cycle", "Cycle", key_display='TAB')
        await self.bind("o", "open", "Open")
        await self.bind("c", "copy", "Copy")
        await self.bind("r", "rename", "Rename")
        await self.bind("d", "delete", "Delete")

    async def action_cycle(self) -> None:
        if self.left_pane.window.widget.has_focus:
            await self.right_pane.window.widget.focus()
        elif self.right_pane.window.widget.has_focus:
            await self.left_pane.window.widget.focus()

    async def action_delete(self) -> None:
        if self.left_pane.window.widget.has_focus:
            path = [node.data.path for node_id, node in self.directory.nodes.items() if node_id == self.directory.cursor][0]
            await self.dialog.do_prompt(
                f"Do you want to delete the path {path}?",
                self.do_local_delete,
                path=path
            )
        else:
            await self.dialog.do_prompt(
                f"Do you want to delete the object {self.s3tree.selected_object.key}?",
                self.do_s3_delete,
                bucket=self.s3tree.bucket_name,
                key=self.s3tree.selected_object.key
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
            await self.reload_left_tree()

    async def do_s3_delete(self, bucket, key) -> None:
        client = boto3.client('s3')

        try:
            client.delete_object(Bucket=bucket, Key=key)
        except botocore.exceptions.ClientError as e:
            await self.handle_status_update(StatusUpdate(self, message=f'Failed to delete S3 object "{key}": {e.response["Error"]["Message"]}'))
        else:
            await self.handle_status_update(StatusUpdate(self, message=f'Successfully deleted S3 object "{key}"'))
            await self.s3tree.load_objects(self.s3tree.selected_node.parent)

    async def action_copy(self) -> None:
        if self.left_pane.window.widget.has_focus:
            message = MakeCopy(
                self,
                src_bucket=None,
                src_path=[node.data.path for node_id, node in self.directory.nodes.items() if node_id == self.directory.cursor][0],
                dst_bucket=self.s3tree.bucket_name,
                dst_path=os.path.dirname(self.s3tree.selected_object.key),
                recursive=True
            )
        else:
            message = MakeCopy(
                self,
                src_bucket=self.s3tree.bucket_name,
                src_path=self.s3tree.selected_object.key,
                dst_bucket=None,
                dst_path=self.directory.data.path,
                recursive=True
            )

        self.log(message.__dict__)

        client = boto3.client('s3')
        # local copy
        if message.src_bucket is None and message.dst_bucket is None:
            await self.handle_status_update(StatusUpdate(self, message='Copying from local to local is not yet supported!'))
        # upload
        elif message.src_bucket is None and message.dst_bucket is not None:
            client.upload_file(message.src_path, message.dst_bucket, os.path.join(message.dst_path, os.path.basename(message.src_path)) )
            await self.s3tree.load_objects(self.s3tree.selected_node)
            await self.handle_status_update(StatusUpdate(self, message=f'Uploaded file from {message.src_path} to {message.dst_bucket}/{message.dst_path}/{os.path.basename(message.src_path)}'))
        # download
        elif message.src_bucket is not None and message.dst_bucket is None:
            client.download_file(message.src_bucket, message.src_path, os.path.join(message.dst_path, os.path.basename(message.src_path)) )
            await self.reload_left_tree()
            await self.handle_status_update(StatusUpdate(self, message=f'Downloaded file from {message.src_bucket}/{message.src_path} to {message.dst_bucket}/{message.dst_path}/{message.src_path}'))
        # copy from one bucket to another
        else:
            await self.handle_status_update(StatusUpdate(self, message='Copying from S3 to S3 is not yet supported!'))

        self.refresh(layout=True)

    async def reload_left_tree(self):
        self.directory = textual.widgets.DirectoryTree(os.getcwd(), name="local")
        self.directory.show_cursor = True
        await self.left_pane.update(self.directory)
        self.refresh(layout=True)

    async def handle_status_update(self, message: StatusUpdate) -> None:
        await self.status_log.add_status(message.message)
        self.refresh()

    def watch_show_dialog(self, show_bar: bool) -> None:
        self.dialog.animate("layout_offset_y", -(self.view.size.height / 2) + 10 if show_bar else 20)

    async def toggle_dialog(self) -> None:
        self.show_dialog = not self.show_dialog
        if self.show_dialog:
            await self.dialog.focus()
        else:
            await self.right_pane.window.widget.focus()

    async def on_mount(self) -> None:
        self.dialog = Prompt("", name="prompt")
        await self.view.dock(self.dialog, edge="bottom", size=20, z=1)
        self.dialog.layout_offset_y = 20

        self.status_log = StatusLog()
        self.directory = textual.widgets.DirectoryTree(os.getcwd(), name="local")
        self.directory.show_cursor = True
        self.s3tree = S3Tree(self.bucket_name, name="s3")
        self.s3tree.show_cursor = True
        self.left_pane = textual.widgets.ScrollView(self.directory)
        self.right_pane = textual.widgets.ScrollView(self.s3tree)

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

        grid.place(header=textual.widgets.Header(tall=False, style="black on #FF9900"))
        grid.place(left=self.left_pane)
        grid.place(right=self.right_pane)
        grid.place(status=self.status_log)
        grid.place(footer=Footer())

        await self.right_pane.window.widget.focus()

        #await self.view.dock(textual.widgets.Header(tall=False, style="black on #FF9900"), edge="top")
        #await self.view.dock(Footer(), edge="bottom")
        #await self.view.dock(textual.widgets.ScrollView(self.status_log), edge="bottom", size=5)
        #await self.view.dock(
        #    textual.widgets.ScrollView(textual.widgets.DirectoryTree(os.getcwd(), name="local"), auto_width=True),
        #    textual.widgets.ScrollView(S3Tree('openwifi-allure-reports', name="s3"), auto_width=True),
        #    edge="left"
        #)

warnings.filterwarnings(action="ignore", message="unclosed", category=ResourceWarning)
BucketManApp.run(title="bucketman", log="textual.log")