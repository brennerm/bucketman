import asyncio
import dataclasses
import enum
import functools

import boto3
from textual import layout
import textual.widgets
import textual.reactive
import rich.console
import rich.text

from s3browser.events import StatusUpdate

class ObjectType(enum.Enum):
    FILE = 0
    FOLDER = 1

@dataclasses.dataclass
class S3Object:
    """Represents the data"""

    key: str
    size: float
    type: ObjectType

class S3Tree(textual.widgets.TreeControl[S3Object]):
    name="S3Tree"

    def __init__(self, bucket_name: str, name: str = None):
        self.bucket_name = bucket_name
        label = bucket_name
        data = S3Object(key="", size=0, type=ObjectType.FOLDER)
        super().__init__(label, name=name, data=data)

    has_focus: textual.reactive.Reactive[bool] = textual.reactive.Reactive(False)

    async def on_focus(self) -> None:
        self.has_focus = True

    def on_blur(self) -> None:
        self.has_focus = False

    @property
    def selected_node(self) -> textual.widgets.TreeNode[S3Object]:
        for node in self.nodes.values():
            if node.is_cursor:
                return node
    @property
    def selected_object(self) -> S3Object:
        return self.selected_node.data

    async def watch_hover_node(self, hover_node: textual.widgets.NodeID) -> None:
        for node in self.nodes.values():
            node.tree.guide_style = (
                "bold not dim #FF9900" if node.id == hover_node else "black"
            )
        self.refresh(layout=True)

    async def on_mount(self) -> None:
        await self.emit(StatusUpdate(self, message=f'Loaded objects in bucket {self.bucket_name}'))
        await self.load_objects(self.root)

    def render_node(self, node: textual.widgets.TreeNode[S3Object]) -> rich.console.RenderableType:
        return self.render_tree_label(
            node,
            node.data.type == ObjectType.FOLDER,
            node.expanded,
            node.is_cursor,
            node.id == self.hover_node,
            self.has_focus,
        )

    @functools.lru_cache(maxsize=1024 * 32)
    def render_tree_label(
        self,
        node: textual.widgets.TreeNode[S3Object],
        is_dir: bool,
        expanded: bool=False,
        is_cursor: bool=False,
        is_hover: bool=False,
        has_focus: bool=False,
    ) -> rich.console.RenderableType:
        meta = {
            "@click": f"click_label({node.id})",
            "tree_node": node.id,
            "cursor": node.is_cursor,
        }
        label = rich.text.Text(node.label) if isinstance(node.label, str) else node.label
        if is_hover:
            label.stylize("underline")
        if is_dir:
            label.stylize("bold blue")
            icon = "📂" if expanded else "📁"
        else:
            label.stylize("bright_green")
            icon = "📄"
            label.highlight_regex(r"\..*$", "green")

        if label.plain.startswith("."):
            label.stylize("dim")

        if is_cursor and has_focus:
            label.stylize("reverse")

        icon_label = rich.text.Text(f"{icon} ", no_wrap=True, overflow="ellipsis") + label
        icon_label.apply_meta(meta)
        return icon_label

    async def load_objects(self, node: textual.widgets.TreeNode[S3Object]):
        node.loaded = False
        node.children = []
        node.tree.children = []

        folder = node.data.key

        client = boto3.client('s3')
        paginator = client.get_paginator('list_objects_v2')
        result = paginator.paginate(Bucket=self.bucket_name, Delimiter='/', Prefix=folder)

        for prefix in result.search('CommonPrefixes'):
            if not prefix: continue
            key = prefix.get('Prefix')
            await node.add(key.replace(folder, '', 1), S3Object(key, 0, ObjectType.FOLDER))

        for obj in result.search('Contents'):
            if not obj: continue
            key = obj.get('Key')
            await node.add(key.replace(folder, '', 1), S3Object(key, obj.get('Size'), ObjectType.FILE))

        node.loaded = True
        await node.expand()
        self.refresh(layout=True)

    async def handle_tree_click(self, message: textual.widgets.TreeClick[S3Object]) -> None:
        dir_entry = message.node.data
        if dir_entry.type == ObjectType.FOLDER:
            if not message.node.loaded:
                await self.emit(StatusUpdate(self, message=f'Loaded objects in folder {message.node.data.key}'))
                await self.load_objects(message.node)
                await message.node.expand()
            else:
                await message.node.toggle()
