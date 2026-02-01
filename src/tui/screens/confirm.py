"""Confirmation dialog for destructive actions."""

from textual.app import ComposeResult
from textual.containers import Grid, Container
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class ConfirmScreen(ModalScreen[bool]):
    """Modal confirmation dialog for destructive actions."""
    
    CSS = """
    ConfirmScreen {
        align: center middle;
        background: rgba(0,0,0,0.7);
    }
    
    #confirm-dialog {
        width: 60;
        height: auto;
        background: $surface;
        padding: 1 2;
        border: thick $error;
    }
    
    .confirm-header {
        text-style: bold;
        color: $error;
        margin-bottom: 1;
        text-align: center;
        width: 100%;
        border-bottom: solid $primary;
        padding-bottom: 1;
    }
    
    .confirm-message {
        margin-bottom: 1;
        text-align: center;
    }
    
    #confirm-dialog Grid {
        grid-size: 2;
        grid-gutter: 1;
        height: 3;
    }
    
    #confirm-dialog Button {
        width: 100%;
        min-width: 10;
    }
    """

    BINDINGS = [
        ("y", "confirm", "Yes"),
        ("n", "cancel", "No"),
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, title: str, message: str):
        super().__init__()
        self.title = title
        self.message = message

    def compose(self) -> ComposeResult:
        with Container(id="confirm-dialog"):
            yield Label(self.title, classes="confirm-header")
            yield Label(self.message, classes="confirm-message")
            with Grid():
                yield Button("No (n)", variant="default", id="no")
                yield Button("Yes (y)", variant="error", id="yes")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            self.dismiss(True)
        else:
            self.dismiss(False)
