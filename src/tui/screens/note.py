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

    def __init__(
        self,
        title: str = "Add Field Note",
        placeholder: str = "Type note here...",
        save_label: str = "Save",
    ) -> None:
        super().__init__()
        self.title = title
        self.placeholder = placeholder
        self.save_label = save_label

    def compose(self) -> ComposeResult:
        with Container():
            yield Label(self.title, classes="header")
            yield Input(placeholder=self.placeholder, id="note-input")
            with Grid():
                yield Button("Cancel", variant="error", id="cancel")
                yield Button(self.save_label, variant="success", id="save")

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
    
    def on_key(self, event) -> None:
        """Handle 'q' to dismiss without quitting app."""
        if event.key == "q":
            event.stop()  # Prevent propagation
            self.dismiss(None)
