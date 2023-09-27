from __future__ import annotations
import dataclasses
import enum
import functools

import botocore.exceptions
from rich.style import Style
from rich.text import Text
import textual.binding
import textual.widgets
import textual.reactive
import rich.console
import rich.text
from textual.widgets._tree import TreeNode

from bucketman.constants import AWS_HEX_COLOR_CODE
from bucketman.events import StatusUpdate
from bucketman.widgets.common import ObjectType


@dataclasses.dataclass
class S3Object:
    key: str
    size: float
    type: ObjectType
    loaded: bool = False

    @property
    def is_dir(self):
        return self.type == ObjectType.FOLDER


class S3Tree(textual.widgets.Tree[S3Object]):
    name = "S3Tree"
    BINDINGS = [
        textual.binding.Binding("r", "reload", "Reload", show=True),
        textual.binding.Binding("d", "download", "Download", show=True, key_display='d'),
        textual.binding.Binding("D", "delete_s3", "Delete", show=True, key_display="Shift+d"),
        textual.binding.Binding("b", "select_bucket", "Select Bucket", show=True),
    ]

    def __init__(self, bucket_name: str, *args, **kwargs):
        self.bucket_name = bucket_name
        label = bucket_name
        data = S3Object(key="", size=0, type=ObjectType.FOLDER)
        super().__init__(label, *args, data=data, **kwargs)
        self.root.expand()

    @property
    def selected_object(self) -> S3Object:
        return self.cursor_node.data

    async def on_mount(self) -> None:
        self.load_objects(self.root)

    def action_reload(self) -> None:
        if self.cursor_node.data.is_dir:
            node_to_reload = self.cursor_node
        else:
            node_to_reload = self.cursor_node.parent

        node_to_reload.remove_children()
        self.load_objects(node_to_reload)
        node_to_reload.expand()
        self.notify(f'Reloaded objects in {self.bucket_name}/{node_to_reload.data.key}')

    async def action_delete(self):
        if self.selected_object.key:
            if self.selected_object.type == ObjectType.FOLDER:
                prompt = f"Do you want to delete all objects with the prefix {self.selected_object.key}?"
            elif self.selected_object.type == ObjectType.FILE:
                prompt = f"Do you want to delete the object {self.selected_object.key}?"
        else:
            prompt = f"Do you want to empty the bucket {self.bucket_name}?"

        await self.app.dialog.do_prompt(
            prompt, self.delete_prefix_or_object, prefix_or_key=self.selected_object.key
        )

    async def delete_prefix_or_object(self, prefix_or_key):
        bucket = self.app.s3_resource.Bucket(self.bucket_name)

        try:
            bucket.objects.filter(Prefix=prefix_or_key).delete()
        except botocore.exceptions.ClientError as e:
            await self.app.handle_status_update(
                StatusUpdate(
                    message=f'Failed to delete S3 object(s) "{self.bucket_name}/{prefix_or_key}": {e.response["Error"]["Message"]}',
                )
            )

        await self.app.handle_status_update(
            StatusUpdate(
                message=f'Deleted S3 object(s) "{self.bucket_name}/{prefix_or_key}"',
            )
        )
        self.load_objects(self.selected_node.parent)

    def render_label(self, node: TreeNode[S3Object], base_style: Style, style: Style) -> Text:
        node_label = node._label.copy()
        node_label.stylize(style)

        if node.is_root:
            prefix = ("🪣  ", base_style)
        elif node.data.is_dir:
            prefix = (
                "📂 " if node.is_expanded else "📁 ",
                base_style + rich.style.Style.from_meta({"toggle": True}),
            )
        else:
            prefix = ("📄 ", base_style)

        text = Text.assemble(prefix, node_label)
        return text

    def load_objects(self, node: textual.widgets.TreeNode[S3Object]):
        if node is None:
            node = self.root

        prefix = node.data.key

        paginator = self.app.s3_client.get_paginator("list_objects_v2")
        result = paginator.paginate(
            Bucket=self.bucket_name, Delimiter="/", Prefix=prefix
        )

        try:
            for common_prefix in result.search("CommonPrefixes"):
                if not common_prefix:
                    continue
                key = common_prefix.get("Prefix")
                node.add(
                    key.replace(prefix, "", 1), S3Object(key, 0, ObjectType.FOLDER)
                )

            for obj in result.search("Contents"):
                if not obj:
                    continue
                key = obj.get("Key")
                node.add(
                    key.replace(prefix, "", 1),
                    S3Object(key, obj.get("Size"), ObjectType.FILE),
                    allow_expand=False
                )
        except botocore.exceptions.ClientError:
            self.notify(
                f'Failed to load contents of bucket "{self.bucket_name}". Please check your credentials and make sure the bucket exists and you have permission to access it.',
                title="Error",
                severity="error"
            )
            self.app.action_change_bucket()
            #self.app.panic(
            #    f'Failed to load contents of bucket "{self.bucket_name}". Please check your credentials and make sure the bucket exists and you have permission to access it.'
            #)

        node.data.loaded = True
        if node.data.is_dir:
            self.post_message(
                StatusUpdate(
                    message=f"Loaded objects in {self.bucket_name}/{prefix}"
                )
            )
        else:
            self.post_message(
                StatusUpdate(message=f"Loaded object {self.bucket_name}/{prefix}")
            )

    def load_and_toggle_selected_node(self):
        node = self.cursor_node
        if node.data.is_dir:
            if not node.data.loaded:
                self.load_objects(node)

        node.toggle()

    def action_toggle_node(self):
        self.load_and_toggle_selected_node()

    def action_select_cursor(self):
        self.load_and_toggle_selected_node()

