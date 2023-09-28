from __future__ import annotations
import dataclasses

import botocore.exceptions
from rich.style import Style
from rich.text import Text
import textual.binding
import textual.widgets
import textual.reactive
import textual.events
import rich.console
import rich.text
from textual.widgets._tree import TreeNode

from bucketman.constants import AWS_HEX_COLOR_CODE
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
        textual.binding.Binding("D", "s3_delete", "Delete", show=True, key_display="Shift+d"),
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

    def on_paste(self, event: textual.events.Paste) -> None:
        """Handle pasting a path from the clipboard or file drop."""
        # TODO support pasting multiple paths without erroring
        paths = event.text.splitlines()

        for path in paths:
            self.log(f"Would upload {path}")
            #self.app.action_upload(path.strip())

    def reload_node(self, node: TreeNode[S3Object]):
        """Reload the given node. If the node is a file or a prefix with no children, reload the parent."""
        node.remove_children()
        self.load_objects(node)
        if not node.children and self.root != node:
            self.reload_node(node.parent)
        else:
            node.expand()

    def reload_selected_prefix(self) -> str:
        if self.cursor_node.data.is_dir:
            node_to_reload = self.cursor_node
        else:
            node_to_reload = self.cursor_node.parent

        self.reload_node(node_to_reload)
        return node_to_reload.data.key

    def action_reload(self) -> None:
        reloaded_key = self.reload_selected_prefix()
        self.notify(f'Reloaded objects in {self.bucket_name}/{reloaded_key}')

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

