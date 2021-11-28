import dataclasses
import enum
import functools
import os

import textual.widgets
import textual.reactive
import rich.console
import rich.text

from bucketman.constants import AWS_HEX_COLOR_CODE
from bucketman.events import StatusUpdate

class ObjectType(enum.Enum):
    FILE = 0
    FOLDER = 1

@dataclasses.dataclass
class FileObject:
    path: str
    size: float
    type: ObjectType

    @property
    def is_dir(self):
        return self.type == ObjectType.FOLDER

class LocalTree(textual.widgets.TreeControl[FileObject]):
    name="LocalTree"

    def __init__(self, root_path: str, name: str = None):
        self.root_path = root_path
        label = os.path.basename(root_path)
        data = FileObject(path=root_path, size=0, type=ObjectType.FOLDER)
        super().__init__(label, name=name, data=data)

    has_focus: textual.reactive.Reactive[bool] = textual.reactive.Reactive(False)

    async def on_focus(self) -> None:
        self.has_focus = True

    def on_blur(self) -> None:
        self.has_focus = False

    @property
    def selected_node(self) -> textual.widgets.TreeNode[FileObject]:
        for node in self.nodes.values():
            if node.is_cursor:
                return node

    @selected_node.setter
    def selected_node(self, node: textual.widgets.TreeNode[FileObject]):
        self.cursor = node.id
    
    @property
    def selected_object(self) -> FileObject:
        return self.selected_node.data

    async def watch_hover_node(self, hover_node: textual.widgets.NodeID) -> None:
        for node in self.nodes.values():
            node.tree.guide_style = (
                f"bold not dim {AWS_HEX_COLOR_CODE}" if node.id == hover_node else "black"
            )
        self.refresh(layout=True)

    async def on_mount(self) -> None:
        await self.load_objects(self.root)

    def render_node(self, node: textual.widgets.TreeNode[FileObject]) -> rich.console.RenderableType:
        return self.render_tree_label(
            node,
            node.data.is_dir,
            node.expanded,
            node.is_cursor,
            node.id == self.hover_node,
            self.has_focus,
        )

    @functools.lru_cache(maxsize=1024 * 32)
    def render_tree_label(
        self,
        node: textual.widgets.TreeNode[FileObject],
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
            icon = "📄"

        if label.plain.startswith("."):
            label.stylize("dim")

        if is_cursor and has_focus:
            label.stylize("reverse")

        icon_label = rich.text.Text(f"{icon} ", no_wrap=True, overflow="ellipsis") + label
        icon_label.apply_meta(meta)
        return icon_label

    async def load_objects(self, node: textual.widgets.TreeNode[FileObject]):
        await node.expand(False)
        self.app.refresh(layout=True)
        node.loaded = False
        node.children = []
        node.tree.children = []

        folder = node.data.path

        path = os.path.join(self.root_path, folder)
        for _, dirs, files in os.walk(path):
            for dir in sorted(dirs, key=str.casefold):
                await node.add(dir, FileObject(os.path.join(path, dir), 0, ObjectType.FOLDER))

            for file in sorted(files, key=str.casefold):
                await node.add(file, FileObject(os.path.join(path, file), 0, ObjectType.FILE))

            break

        node.loaded = True
        if node.data.is_dir:
            await node.expand()
            await self.emit(StatusUpdate(self, message=f'Loaded files in {folder}'))
        else:
            await self.emit(StatusUpdate(self, message=f'Loaded file {folder}'))

        self.app.refresh(layout=True)

    async def handle_tree_click(self, message: textual.widgets.TreeClick[FileObject]) -> None:
        if message.node.data.is_dir:
            if not message.node.loaded:
                await self.load_objects(message.node)
            else:
                await message.node.toggle()
