from __future__ import annotations
import dataclasses
import enum
import functools
import os

import textual.widgets
import textual.widgets.tree
import textual.reactive
import rich.console
import rich.text

from bucketman.constants import AWS_HEX_COLOR_CODE
from bucketman.events import StatusUpdate
from bucketman.widgets.common import ObjectType


@dataclasses.dataclass
class FileObject:
    path: str
    size: float
    type: ObjectType
    loaded: bool

    @property
    def is_dir(self):
        return self.type == ObjectType.FOLDER


class LocalTree(textual.widgets.DirectoryTree):
    name = "LocalTree"
    BINDINGS = [
        textual.binding.Binding("r", "reload", "Reload", show=True),
        textual.binding.Binding("u", "upload", "Upload", show=True),
        textual.binding.Binding("D", "delete_local", "Delete", show=True, key_display="Shift+d"),
    ]

    @property
    def selected_object(self) -> FileObject:
        return self.cursor_node.data
