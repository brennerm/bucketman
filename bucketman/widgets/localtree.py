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


class LocalTree(textual.widgets.DirectoryTree):
    name = "LocalTree"
    BINDINGS = [
        textual.binding.Binding("r", "reload", "Reload", show=True),
        textual.binding.Binding("u", "upload", "Upload", show=True),
        textual.binding.Binding("D", "local_delete", "Delete", show=True, key_display="Shift+d"),
    ]

    @property
    def selected_object(self):
        return self.cursor_node.data

    def reload_parent_of_selected_node(self):
        """Reload the parent of the cursor node."""
        self.reload_node(
            self.cursor_node.parent
        )

    def reload_selected_directory(self) -> str:
        if self.cursor_node.data.path.is_dir():
            node_to_reload = self.cursor_node
        else:
            node_to_reload = self.cursor_node.parent

        self.reload_node(node_to_reload)
        return str(node_to_reload.data.path)

