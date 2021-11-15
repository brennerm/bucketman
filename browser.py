import os
import warnings

import textual.app
import textual.widgets
import textual.views

from s3browser.widgets.footer import Footer
from s3browser.widgets.s3tree import S3Tree
from s3browser.widgets.statuslog import StatusLog
from s3browser.events import StatusUpdate

#class S3Browser(textual.views.GridView):
#    def on_mount(self) -> None:
        #self.grid.add_column("left", max_size=120)
        #self.grid.add_column("right", max_size=120)
        #self.grid.add_row("pane", fraction=21)
        #self.grid.add_row("status", fraction=3)
        #self.grid.add_row("keys", fraction=1)
        #self.grid.add_row("footer", fraction=1)
        #self.grid.add_areas(
        #    left="left,pane",
        #    right="right,pane",
        #    status="left-start|right-end,status",
        #    keys="left-start|right-end,keys",
        #    footer="left-start|right-end,footer",
        #)

        #self.grid.place(left=textual.widgets.ScrollView(textual.widgets.DirectoryTree(os.getcwd(), "local")))
        #self.grid.place(right=textual.widgets.Placeholder(name="right"))
        #self.grid.place(status=textual.widgets.ScrollView())
        #self.grid.place(keys=textual.widgets.Placeholder(name="keys"))
        #self.grid.place(footer=textual.widgets.Footer())



class S3BrowserApp(textual.app.App):
    def __init__(self, *args, **kwargs):
        self.status_log = None
        super().__init__(*args, **kwargs)

    async def on_load(self) -> None:
        """Sent before going in to application mode."""

        await self.bind("q", "quit", "Quit")
        await self.bind("tab", "cycle", "Cycle")
        await self.bind("c", "copy", "Copy")
        await self.bind("d", "delete", "Delete")


    async def handle_status_update(self, message: StatusUpdate) -> None:
        self.status_log.add_status(message.message)

    async def on_mount(self) -> None:
        self.status_log = StatusLog()

        await self.view.dock(textual.widgets.Header(tall=False, style="black on #FF9900"), edge="top")
        await self.view.dock(Footer(), edge="bottom")
        await self.view.dock(textual.widgets.ScrollView(self.status_log), edge="bottom", size=5)
        await self.view.dock(
            textual.widgets.ScrollView(textual.widgets.DirectoryTree(os.getcwd(), name="local"), auto_width=True),
            textual.widgets.ScrollView(S3Tree('openwifi-allure-reports', name="s3"), auto_width=True),
            edge="left"
        )

warnings.filterwarnings(action="ignore", message="unclosed", category=ResourceWarning)
S3BrowserApp.run(title="S3Browser", log="textual.log")