import os
import pathlib
import shutil

import boto3
import botocore.exceptions
import textual.app
import textual.binding
import textual.notifications
import textual.containers
import textual.screen
import textual.widgets

from bucketman.constants import AWS_HEX_COLOR_CODE
from bucketman.modals import BucketSelectScreen, ConfirmationScreen
from bucketman.widgets import (
    LocalTree,
    S3Tree,
)
from bucketman.widgets.common import ObjectType

class BucketManApp(textual.app.App):
    TITLE = "BucketMan"
    SUB_TITLE = "A Terminal S3 File Browser, 🔨 with 💗 by brennerm"
    CSS_PATH = "bucketman.tcss"
    BINDINGS = [
            textual.binding.Binding("escape,q,ctrl+c", "quit", "Quit", show=True, key_display="ESC", priority=True),
        ]
    ENABLE_COMMAND_PALETTE = False

    def __init__(
        self,
        *args,
        bucket: str = None,
        endpoint_url: str = None,
        access_key_id: str = None,
        secret_access_key: str = None,
        dry_run: bool = False,
        **kwargs,
    ):

        self.bucket_name = bucket
        self.dry_run = dry_run

        session = boto3.Session(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )

        self.s3_client = session.client("s3", endpoint_url=endpoint_url)
        self.s3_resource = session.resource("s3", endpoint_url=endpoint_url)

        self.footer = textual.widgets.Footer()
        self.header = textual.widgets.Header()

        super().__init__(*args, **kwargs)

    @property
    def selected_local_folder(self) -> pathlib.PosixPath:
        """Return the selected local folder. If a file is selected, return the parent folder."""

        selected_node = self.query_one('#left LocalTree', LocalTree).cursor_node
        if selected_node.allow_expand:
            return selected_node.data.path
        else:
            return selected_node.parent.data.path

    @property
    def selected_local_object(self) -> pathlib.PosixPath:
        """Return the selected local folder or file."""
        selected_node = self.query_one('#left LocalTree', LocalTree).cursor_node
        return selected_node.data.path

    @property
    def selected_s3_key_or_prefix(self):
        """Return the selected S3 key or prefix."""
        selected_node = self.query_one('#right S3Tree', S3Tree).cursor_node
        return selected_node.data.key

    @property
    def selected_s3_prefix(self):
        """Return the selected S3 prefix. If an object is selected, return the parent prefix."""
        selected_node = self.query_one('#right S3Tree', S3Tree).cursor_node
        if selected_node.allow_expand:
            return selected_node.data.key
        else:
            return selected_node.parent.data.key

    def action_download(self) -> None:
        """Download the selected object to the selected local folder after confirmation."""
        bucket = self.bucket_name
        key = self.selected_s3_key_or_prefix
        path = str(self.selected_local_folder.joinpath(os.path.basename(key)))

        def check_download(do_download: bool) -> None:
            if not do_download:
                return

            if self.dry_run:
                self.notify(f'Would download {bucket}/{key} to {path}', title='Dry Run')
                return

            self.run_worker(self.do_download(self.bucket_name, key, path), thread=True)

        self.push_screen(
            ConfirmationScreen(
                prompt=f"Do you want to download the object {bucket}/{key} to {path}?",
            ),
            check_download
        )

    async def do_download(self, bucket, key, path) -> None:
        try:
            self.s3_client.download_file(bucket, key, path)
        except botocore.exceptions.ClientError as e:
            self.notify(
                f'Failed to download object {bucket}/{key} to {path}: {e.response["Error"]["Message"]}',
                title='Error',
                severity='error'
            )
        else:
            self.query_one('#left LocalTree', LocalTree).reload_selected_directory()

            self.notify(
                f'Successfully downloaded object {bucket}/{key} to {path}',
                title='Success',
            )

    def action_upload(self) -> None:
        """Upload the selected local folder/file to the selected S3 prefix after confirmation."""

        bucket = self.bucket_name
        path = str(self.selected_local_object)
        key = os.path.join(self.selected_s3_prefix, os.path.basename(path))

        def check_upload(do_upload: bool) -> None:
            if not do_upload:
                return

            if self.dry_run:
                self.notify(f'Would upload {path} to {key}', title='Dry Run')
                return

            self.run_worker(self.do_upload(path, bucket, key), thread=True)

        self.push_screen(
            ConfirmationScreen(
                prompt=f"Do you want to upload the path {path} to {bucket}/{key}?",
            ),
            check_upload
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
            else:
                self.s3_client.upload_file(path, bucket, key)
        except botocore.exceptions.ClientError as e:
            self.notify(
                f'Failed to upload file {path} to {bucket}/{key}: {e.response["Error"]["Message"]}',
                title='Error',
                severity='error'
            )
        else:
            self.query_one('#right S3Tree', S3Tree).reload_selected_prefix()
            self.notify(
                f'Successfully uploaded path {path} to {bucket}/{key}',
                title='Success',
            )

    def action_local_delete(self) -> None:
        """Delete the selected local file or folder after confirmation."""
        path = str(self.selected_local_object.absolute())

        def check_delete(do_delete: bool) -> None:
            if not do_delete:
                return

            if self.dry_run:
                self.notify(f'Would delete {path}', title='Dry Run')
                return

            self.run_worker(self.do_local_delete(path), thread=True)

        self.push_screen(
            ConfirmationScreen(
                prompt=f"Do you want to delete the path {path}?",
            ),
            check_delete
        )

    async def do_local_delete(self, path: str) -> None:
        """Delete the given local file or folder."""
        try:
            if os.path.isfile(path):
                os.remove(path)
            else:
                shutil.rmtree(path)
        except OSError as e:
            self.notify(
                f'Failed to delete path "{path}": {e.strerror}',
                title='Error',
                severity='error'
            )
        else:
            self.notify(
                f'Successfully deleted path "{path}"',
                title='Success',
            )
            self.query_one('#left LocalTree', LocalTree).reload_parent_of_selected_node()

    def action_s3_delete(self) -> None:
        """Delete the selected S3 object or prefix after confirmation."""
        bucket = self.bucket_name
        key_or_prefix = self.selected_s3_key_or_prefix

        def check_delete(do_delete: bool) -> None:
            if not do_delete:
                return

            if self.dry_run:
                self.notify(f'Would delete {bucket}/{key_or_prefix}', title='Dry Run')
                return

            self.run_worker(self.do_s3_delete(bucket, key_or_prefix), thread=True)

        self.push_screen(
            ConfirmationScreen(
                prompt=f"Do you want to delete the object {bucket}/{key_or_prefix}?",
            ),
            check_delete
        )

    async def do_s3_delete(self, bucket: str, key_or_prefix: str) -> None:
        """Delete the given S3 object or prefix."""

        try:
            self.s3_resource.Bucket(bucket).objects.filter(Prefix=key_or_prefix).delete()
        except botocore.exceptions.ClientError as e:
            self.notify(
                f'Failed to delete S3 object(s) "{bucket}/{key_or_prefix}": {e.response["Error"]["Message"]}',
                title='Error',
                severity='error'
            )
        else:
            self.notify(
                f'Successfully deleted S3 object(s) "{bucket}/{key_or_prefix}"',
                title='Success',
            )
            self.query_one('#right S3Tree', S3Tree).reload_selected_prefix()

    def action_select_bucket(self) -> None:
        """Show the bucket select screen and change the bucket if a bucket is selected"""
        def select_bucket(new_bucket: str):
            self.bucket_name = new_bucket
            right_pane = self.query_one('#right', textual.containers.ScrollableContainer)
            right_pane.remove_children()
            right_pane.mount(S3Tree(new_bucket))
            right_pane.children[0].focus()
            self.notify(f'You are now connected to bucket [b]{new_bucket}[/b]', title='Changed Bucket')

        self.push_screen(
            BucketSelectScreen(),
            select_bucket
        )

    def on_mount(self) -> None:
        # open bucket select screen if no bucket has been provided
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
        yield self.footer
