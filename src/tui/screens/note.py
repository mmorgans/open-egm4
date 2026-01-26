from textual.app import ComposeResult
from textual.containers import Grid, Container
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

class NoteInputScreen(ModalScreen[str]):
    """Modal to enter a note."""
    
    CSS = """
    NoteInputScreen {
        align: center middle;
        background: rgba(0,0,0,0.5);
    }
    
    Container {
        width: 60;
        height: auto;
        background: $surface;
        padding: 1 2;
        border: thick $accent;
    }
    
    .header {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
        text-align: center;
        width: 100%;
        border-bottom: solid $primary;
        padding-bottom: 1;
    }
    
    Input {
        margin-bottom: 2;
    }
    
    Grid {
        grid-size: 2;
        grid-gutter: 1;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        with Container():
            yield Label("Add Field Note", classes="header")
            yield Input(placeholder="Type note here...", id="note-input")
            with Grid():
                yield Button("Cancel", variant="error", id="cancel")
                yield Button("Save", variant="success", id="save")

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            note = self.query_one(Input).value
            self.dismiss(note)
        else:
            self.dismiss(None)
            
    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)
