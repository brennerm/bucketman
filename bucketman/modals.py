import textual.app
import textual.containers
import textual.screen
import textual.widgets

class ConfirmationScreen(textual.screen.ModalScreen[bool]):
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
            textual.widgets.Button("Yes", variant="error", id="yes"),
            textual.widgets.Button("No", variant="primary", id="no"),
            id="dialog",
        )

    def on_button_pressed(self, event: textual.widgets.Button.Pressed) -> None:
        if event.button.id == "yes":
            self.dismiss(True)
        else:
            self.dismiss(False)

