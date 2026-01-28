"""Help Screen - Shows usage instructions for the EGM-4."""

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static, Footer


HELP_TEXT = """
[bold cyan]══════════════════════════════════════════════════════════════[/bold cyan]
[bold white]                    Open EGM-4 Help[/bold white]
[bold cyan]══════════════════════════════════════════════════════════════[/bold cyan]

[bold yellow]▶ GETTING DATA FROM THE EGM-4[/bold yellow]

[bold]Dump data from the EGM-4:[/bold]
[italic]This will transfer all records stored on the EGM to the application at once.[/italic]
  1. Connect the EGM-4 to your computer via the serial port (RS232 on the EGM chassis).
  2. On the EGM-4 keypad, press 4 to select DMP.
  3. Press 2 to select DATA DUMP. Press any key to start the transfer.
  4. All records should stream to the chart :)

[bold]Get live readings from the EGM-4:[/bold]
  1. Connect the EGM-4 to your computer via the serial port (RS232 on the EGM chassis).
  2. On the EGM-4 keypad, press 1 to select REC.
  3. You can take measurements as you would ordinarily, and the EGM will send the data.

[bold yellow]▶ KEYBOARD SHORTCUTS[/bold yellow]

[bold cyan]1-9[/bold cyan]     Select channel to display (Cr, Hr, PAR, etc.)
[bold cyan]p[/bold cyan]       Pause/Resume data stream
[bold cyan]c[/bold cyan]       Clear chart data
[bold cyan]e[/bold cyan]       Export data to CSV file
[bold cyan]b[/bold cyan]       Big mode (use this in a field? I guess. I thought it was a good idea)
[bold cyan]d[/bold cyan]       Toggle dark/light theme
[bold cyan]q[/bold cyan]       Quit application

[bold yellow]▶ CHANNELS[/bold yellow]

[italic]Generally, refer to the manual here. The channels change definition depending on the probe connected.[/italic]

[bold cyan]1[/bold cyan] Cr    CO2 concentration (ppm)
[bold cyan]2[/bold cyan] Hr    H2O (mb)
[bold cyan]3[/bold cyan] PAR   Light intensity (μmol/m²/s)
[bold cyan]4[/bold cyan] %RH   Chamber relative humidity (%)
[bold cyan]5[/bold cyan] Temp  Soil temperature (°C)
[bold cyan]6[/bold cyan] DC    Delta concentration (ppm)
[bold cyan]7[/bold cyan] SR    Soil Respiration (gCO2/m²/hr)
[bold cyan]8[/bold cyan] ATMP  Atmospheric pressure (mb)
[bold cyan]9[/bold cyan] DT    Delta Time (seconds)

[bold cyan]══════════════════════════════════════════════════════════════[/bold cyan]
[dim]Press Escape to close this help screen[/dim]
[dim]Press ? to open the real help screen[/dim]
"""


SECRET_HELP_TEXT = """
[#D4A574]
  .--~~--._.--~~--._.--~~--._.--~~--._.--~~--._.--~~--._.--~~--._
 /                                                               \\
|                                                                 |
|  [bold #5C4033]Help for Plants and Zombies Game[/bold #5C4033]                               |
|                                                                 |
|  [#5C4033]When the Zombies show up, just sit[/#5C4033]                             |
|  [#5C4033]there and don't do anything. You[/#5C4033]                               |
|  [#5C4033]win the game when the Zombies get[/#5C4033]                              |
|  [#5C4033]to your houze.[/#5C4033]                                                 |
|                                                                 |
|                                                                 |
|              [dim #5C4033]- this help section brought to you[/dim #5C4033]                 |
|                              [dim #5C4033]by Morgan[/dim #5C4033]                          |
|                                                                 |
 \\__.-~~--.__.-~~--.__.-~~--.__.-~~--.__.-~~--.__.-~~--.__.-~~--._/
[/#D4A574]
"""


class SecretHelpScreen(ModalScreen):
    """The real help screen (easter egg)."""

    BINDINGS = [
        ("escape", "dismiss", "Back"),
        ("?", "dismiss", "Back"),
    ]

    DEFAULT_CSS = """
    SecretHelpScreen {
        align: center middle;
    }
    
    SecretHelpScreen > VerticalScroll {
        width: 80;
        height: 90%;
        border: double green;
        background: $surface;
        padding: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static(SECRET_HELP_TEXT, markup=True)
        yield Footer()

    def on_key(self, event) -> None:
        """Any key dismisses this screen."""
        self.dismiss()


class HelpScreen(ModalScreen):
    """Modal help screen with EGM-4 instructions."""

    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("?", "secret_help", "???"),
    ]

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }
    
    HelpScreen > VerticalScroll {
        width: 70;
        height: 80%;
        border: solid $primary;
        background: $surface;
        padding: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static(HELP_TEXT, markup=True)
        yield Footer()

    def action_secret_help(self) -> None:
        """Open the secret help screen."""
        self.app.push_screen(SecretHelpScreen())
    
    def on_key(self, event) -> None:
        """Handle 'q' to dismiss without quitting app."""
        if event.key == "q":
            event.stop()  # Prevent propagation
            self.dismiss()

