import os
import shutil

import boto3
import botocore.exceptions
import textual.app
import textual.binding
import textual.containers
import textual.screen
import textual.widgets

from bucketman.constants import AWS_HEX_COLOR_CODE
from bucketman.events import StatusUpdate
from bucketman.modals import BucketSelectScreen, ConfirmationScreen
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
    TITLE = "BucketMan"
    SUB_TITLE = "Terminal S3 File Manager"
    CSS_PATH = "bucketman.tcss"
    BINDINGS = [
            textual.binding.Binding("escape,q,ctrl+c", "quit", "Quit", show=True, key_display="ESC", priority=True),
        ]

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

        self.status_log = StatusLog(id="status_log")
        self.footer = textual.widgets.Footer()
        self.header = textual.widgets.Header()

        super().__init__(*args, **kwargs)

    @property
    def selected_local_folder(self):
        """Return the selected local folder. If a file is selected, return the parent folder."""

        selected_node = self.query_one('#left').children[0].cursor_node
        if selected_node.allow_expand:
            return selected_node.data.path
        else:
            return selected_node.parent.data.path

    @property
    def selected_local_object(self):
        """Return the selected local folder or file."""

        selected_node = self.query_one('#left').children[0].cursor_node
        return selected_node.data.path

    @property
    def selected_key_or_prefix(self):
        """Return the selected S3 key or prefix."""
        selected_node = self.query_one('#right').children[0].cursor_node
        return selected_node.data.key

    async def action_delete(self) -> None:
        if self.left_widget == self.focused:
            path = self.left_widget.selected_object.path
            await self.dialog.do_prompt(
                f"Do you want to delete the path {path}?",
                self.do_local_delete,
                path=path,
            )

    def action_download(self) -> None:
        """Download the selected object to the selected local folder after confirmation."""
        def check_download(do_download: bool) -> None:
            if not do_download:
                return
            self.notify(f'Would download {self.selected_key_or_prefix} to {self.selected_local_folder}')

        self.push_screen(
            ConfirmationScreen(
                prompt=f"Do you want to download the object {self.selected_key_or_prefix} to {self.selected_local_folder}?",
            ),
            check_download
        )

    def action_upload(self) -> None:
        """Upload the selected local file to the selected S3 prefix after confirmation."""
        def check_upload(do_upload: bool) -> None:
            if not do_upload:
                return
            self.notify(f'Would upload {self.selected_local_object} to {self.selected_key_or_prefix}')

        self.push_screen(
            ConfirmationScreen(
                prompt=f"Do you want to upload the file {self.selected_local_object} to {self.bucket_name}/{self.selected_key_or_prefix}?",
            ),
            check_upload
        )

    def action_delete_local(self) -> None:
        """Delete the selected local file or folder after confirmation."""
        def check_delete(do_delete: bool) -> None:
            if not do_delete:
                return
            self.notify(f'Would delete {self.selected_local_object}')

        self.push_screen(
            ConfirmationScreen(
                prompt=f"Do you want to delete the path {self.selected_local_object}?",
            ),
            check_delete
        )

    def action_delete_s3(self) -> None:
        """Delete the selected S3 object or prefix after confirmation."""
        def check_delete(do_delete: bool) -> None:
            if not do_delete:
                return
            self.notify(f'Would delete {self.selected_key_or_prefix}')

        self.push_screen(
            ConfirmationScreen(
                prompt=f"Do you want to delete the object {self.selected_key_or_prefix}?",
            ),
            check_delete
        )

    def action_select_bucket(self) -> None:
        """Show the bucket select screen and change the bucket if a bucket is selected"""
        def select_bucket(new_bucket: str):
            right_pane = self.query_one('#right')
            right_pane.remove_children()
            right_pane.mount(S3Tree(new_bucket))
            right_pane.children[0].focus()
            self.notify(f'You are now connected to bucket [b]{new_bucket}[/b]', title='Changed Bucket')

        self.push_screen(
            BucketSelectScreen(),
            select_bucket
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

    #def on_status_update(self, message: StatusUpdate) -> None:
    #    self.status_log.add_status(message.message)

    def on_mount(self) -> None:
        if not self.bucket_name:
            self.action_select_bucket()


    def compose(self) -> textual.app.ComposeResult:
        directory = LocalTree(os.getcwd())

        if self.bucket_name:
            widget = S3Tree(self.bucket_name)
        else:
            widget = textual.containers.Center(
                textual.containers.Middle(
                    textual.widgets.Static("No bucket selected", id="no_bucket")
                )
            )

        yield self.header
        yield textual.containers.Horizontal(
            textual.containers.ScrollableContainer(directory, id="left"),
            textual.containers.ScrollableContainer(widget, id="right"),
            id="center"
        )
        #yield self.status_log
        yield self.footer
