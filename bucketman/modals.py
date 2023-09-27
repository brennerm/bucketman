import time
import botocore.exceptions
import textual.app
from textual.app import ComposeResult
import textual.containers
import textual.screen
import textual.widgets

class ConfirmationScreen(textual.screen.ModalScreen[bool]):
    """A screen that displays a prompt and two buttons, Yes and No, to confirm or cancel an action."""

    CSS = """
    ConfirmationScreen {
        align: center middle;
    }

    #dialog {
        grid-size: 2;
        grid-gutter: 1 2;
        grid-rows: 1fr 3;
        padding: 0 1;
        width: 60;
        height: 11;
        border: thick $background 80%;
        background: $surface;
    }

    #prompt {
        column-span: 2;
        height: 1fr;
        width: 1fr;
        content-align: center middle;
    }

    Button {
        width: 100%;
    }
    """

    BINDINGS = [
        textual.binding.Binding("left", "select_left", "Focus previous", show=False),
        textual.binding.Binding("right", "select_right", "Focus next", show=False),
    ]

    def __init__(
        self,
        *args,
        prompt: str,
        **kwargs,
    ):
        self.prompt = prompt
        super().__init__(*args, **kwargs)

    def compose(self) -> textual.app.ComposeResult:
        yield textual.containers.Grid(
            textual.widgets.Label(self.prompt, id="prompt"),
            textual.widgets.Button("Yes", variant="success", id="yes"),
            textual.widgets.Button("No", variant="error", id="no"),
            id="dialog",
        )

    def on_mount(self) -> None:
        self.query_one("#no").focus()

    def action_select_left(self) -> None:
        self.focus_next()

    def action_select_right(self) -> None:
        self.focus_next()

    def on_button_pressed(self, event: textual.widgets.Button.Pressed) -> None:
        if event.button.id == "yes":
            self.dismiss(True)
        else:
            self.dismiss(False)


class BucketSelectScreen(textual.screen.ModalScreen[str]):
    """A screen that displays a list of S3 buckets to select from."""

    CSS = """
    BucketSelectScreen, Vertical {
        align: center middle;
        height: auto;
        width: auto;
    }
    
    Static {
        width: auto;
        height: auto;
    }

    LoadingIndicator {
        height: 1;
    }

    #buckets {
        width: 50%;
        max-height: 50%;
    }
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.__buckets = []

    async def on_mount(self):
        self.query_one("#buckets").display = False
        self.run_worker(self.load_buckets(), exclusive=True, thread=True)

    async def load_buckets(self):
        try:
            self.__buckets = [
                bucket["Name"]
                for bucket in self.app.s3_client.list_buckets()["Buckets"]
            ]
        except botocore.exceptions.ClientError:
            self.app.panic(
                "Bucketman is unable to list your S3 buckets. Please check your credentials and make sure your user has the required permissions or pass a bucket name using the --bucket option."
            )

        self.query_one("#buckets").add_options(self.__buckets)
        self.query_one("#buckets").action_first()
        self.query_one("#buckets").display = True
        self.query_one('#loading').display = False

    def on_option_list_option_selected(self, event: textual.widgets.OptionList.OptionSelected):
        self.dismiss(event.option.prompt)

    def compose(self) -> ComposeResult:
        yield textual.containers.Vertical(
            textual.widgets.Static("Loading S3 buckets..."),
            textual.widgets.LoadingIndicator(),
            id="loading"
        )
        yield textual.widgets.OptionList(id='buckets')