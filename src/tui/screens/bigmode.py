"""Big Mode Screen - High visibility field display."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Static
from textual.reactive import reactive


class BigModeScreen(Screen):
    """Full-screen high-visibility CO2 display for field use."""

    DEFAULT_CSS = """
    BigModeScreen {
        background: $surface;
        layout: vertical;
        align: center middle;
    }
    
    #big-co2-value {
        text-align: center;
        text-style: bold;
        width: 100%;
        content-align: center middle;
        height: auto;
        margin: 2;
    }
    
    #big-co2-label {
        text-align: center;
        color: $text;
        width: 100%;
        content-align: center middle;
        height: 3;
    }
    
    #big-status {
        text-align: center;
        width: 100%;
        content-align: center middle;
        height: 3;
        margin-top: 2;
    }
    
    #big-record-count {
        text-align: center;
        color: $text-muted;
        width: 100%;
        content-align: center middle;
        height: 2;
    }
    """

    BINDINGS = [
        ("b", "exit_big_mode", "Exit Big Mode"),
        ("q", "exit_big_mode", "Exit"),
        ("escape", "exit_big_mode", "Back"),
    ]

    # Reactive properties
    current_co2: reactive[float | None] = reactive(None, init=False)
    record_count: reactive[int] = reactive(0, init=False)
    stability: reactive[str] = reactive("WAITING", init=False)

    def compose(self) -> ComposeResult:
        yield Static("---", id="big-co2-value")
        yield Static("ppm CO₂", id="big-co2-label")
        yield Static("○ WAITING", id="big-status")
        yield Static("Records: 0", id="big-record-count")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize display with current values after mount."""
        self._update_co2_display()
        self._update_record_display()
        self._update_stability_display()

    def watch_current_co2(self, value: float | None) -> None:
        """Update the display when CO2 changes."""
        if self.is_mounted:
            self._update_co2_display()

    def watch_record_count(self, value: int) -> None:
        """Update record count display."""
        if self.is_mounted:
            self._update_record_display()

    def watch_stability(self, value: str) -> None:
        """Update stability indicator."""
        if self.is_mounted:
            self._update_stability_display()

    def _update_co2_display(self) -> None:
        """Update the CO2 value widget."""
        try:
            co2_widget = self.query_one("#big-co2-value", Static)
        except Exception:
            return
        
        value = self.current_co2
        
        if value is None:
            co2_widget.update("---")
            co2_widget.styles.color = "white"
            return
        
        # Determine color based on CO2 level - use dark colors for contrast
        if value < 400:
            color = "#006400"  # Dark green
        elif value < 600:
            color = "#007000"  # Medium green
        elif value < 800:
            color = "#CC6600"  # Dark orange
        elif value < 1000:
            color = "#CC3300"  # Red-orange
        else:
            color = "#CC0000"  # Dark red
        
        # Use ASCII art style large numbers
        co2_widget.update(self._render_big_number(int(value)))
        co2_widget.styles.color = color

    def _update_record_display(self) -> None:
        """Update the record count widget."""
        try:
            self.query_one("#big-record-count", Static).update(f"Records: {self.record_count}")
        except Exception:
            pass

    def _update_stability_display(self) -> None:
        """Update the stability indicator widget."""
        try:
            status_widget = self.query_one("#big-status", Static)
        except Exception:
            return
        
        value = self.stability
        
        if value == "STABLE":
            status_widget.update("◆ STABLE")
            status_widget.styles.color = "green"
        elif value == "VARIABLE":
            status_widget.update("◇ VARIABLE")
            status_widget.styles.color = "yellow"
        elif value == "NOISY":
            status_widget.update("◈ NOISY")
            status_widget.styles.color = "red"
        else:
            status_widget.update("○ WAITING")
            status_widget.styles.color = "gray"

    def _render_big_number(self, value: int) -> str:
        """Render a large ASCII art number."""
        # Simple large digit rendering using Unicode block characters
        digits = {
            '0': ["█▀▀█", "█  █", "█▄▄█"],
            '1': ["  ▄█", "   █", "   █"],
            '2': ["█▀▀█", " ▄▄█", "█▄▄▄"],
            '3': ["█▀▀█", "  ▀█", "█▄▄█"],
            '4': ["█  █", "█▄▄█", "   █"],
            '5': ["█▀▀▀", "█▀▀█", "▄▄▄█"],
            '6': ["█▀▀▀", "█▀▀█", "█▄▄█"],
            '7': ["█▀▀█", "   █", "   █"],
            '8': ["█▀▀█", "█▀▀█", "█▄▄█"],
            '9': ["█▀▀█", "█▄▄█", "   █"],
        }
        
        value_str = str(value)
        lines = ["", "", ""]
        
        for char in value_str:
            if char in digits:
                for i, line in enumerate(digits[char]):
                    lines[i] += line + " "
        
        return "\n".join(lines)

    def action_exit_big_mode(self) -> None:
        """Exit big mode and return to normal monitor."""
        self.app.pop_screen()
