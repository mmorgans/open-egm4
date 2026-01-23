"""Connect Screen - Serial port selection and connection."""

from dataclasses import dataclass

from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, OptionList, Static
from textual.widgets.option_list import Option
from serial.tools import list_ports


# ASCII art logo
LOGO = """
                                                    _  _   
   ___  _ __   ___ _ __         ___  __ _ _ __ ___ | || |  
  / _ \| '_ \ / _ \ '_ \ _____ / _ \/ _` | '_ ` _ \| || |_ 
 | (_) | |_) |  __/ | | |_____|  __/ (_| | | | | | |__   _|
  \___/| .__/ \___|_| |_|      \___|\__, |_| |_| |_|  |_|  
       |_|                          |___/                  

"""

AUTO_CONNECT_DELAY = 5  # seconds


def find_best_port() -> str | None:
    """
    Auto-detect the most likely EGM-4 port.
    
    Priority:
    1. USB serial devices (cu.usbserial, ttyUSB, etc.)
    2. COM1 on Windows
    3. First available port
    """
    ports = list_ports.comports()
    
    if not ports:
        return None
    
    # Priority 1: USB serial devices
    for port in ports:
        device_lower = port.device.lower()
        desc_lower = port.description.lower()
        
        if 'usbserial' in device_lower or 'ttyusb' in device_lower:
            return port.device
        if 'usb' in desc_lower and 'serial' in desc_lower:
            return port.device
        if any(chip in desc_lower for chip in ['ftdi', 'prolific', 'ch340', 'cp210']):
            return port.device
    
    # Priority 2: COM1 on Windows
    for port in ports:
        if port.device.upper() == 'COM1':
            return port.device
    
    # Priority 3: First available port
    return ports[0].device


class ConnectScreen(Screen):
    """Screen for selecting serial port."""

    DEFAULT_CSS = """
    ConnectScreen {
        align: center middle;
    }
    
    #logo {
        text-align: center;
        color: $primary;
        margin-bottom: 1;
    }
    
    #config-container {
        width: 70;
        height: auto;
        align: center middle;
    }
    
    #port-list {
        width: 100%;
        height: auto;
        max-height: 10;
        margin: 1 0;
    }
    
    #connect-btn {
        margin-top: 1;
        width: 100%;
    }
    
    #status {
        margin-top: 1;
        text-align: center;
        color: $text-muted;
    }
    
    #countdown {
        text-align: center;
        margin-top: 1;
        color: $warning;
    }
    """

    BINDINGS = [
        ("r", "refresh_ports", "Refresh"),
        ("q", "app.quit", "Quit"),
        ("enter", "connect_now", "Connect"),
    ]

    @dataclass
    class Connected(Message):
        """Message sent when a connection is established."""
        port: str

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._countdown = AUTO_CONNECT_DELAY
        self._timer_handle = None
        self._auto_connect_cancelled = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Center():
            with Vertical(id="config-container"):
                yield Static(LOGO, id="logo")
                yield Static("Select Serial Port", classes="config-label")
                yield OptionList(id="port-list")
                yield Static("", id="countdown")
                yield Button("Connect", id="connect-btn", variant="primary")
                yield Static("[dim]Probe type auto-detected from data[/dim]", id="status")
        yield Footer()

    def on_mount(self) -> None:
        """Populate port list and start auto-connect countdown."""
        self.refresh_ports()
        
        best_port = find_best_port()
        if best_port:
            self._start_countdown()
        else:
            self.query_one("#countdown", Static).update("")
            self.query_one("#status", Static).update(
                "No USB serial device detected - select a port manually"
            )

    def _start_countdown(self) -> None:
        """Start the auto-connect countdown."""
        self._countdown = AUTO_CONNECT_DELAY
        self._update_countdown_display()
        self._timer_handle = self.set_interval(1.0, self._tick_countdown)

    def _tick_countdown(self) -> None:
        """Called every second during countdown."""
        if self._auto_connect_cancelled:
            return
        
        self._countdown -= 1
        
        if self._countdown <= 0:
            self._stop_countdown()
            self._do_auto_connect()
        else:
            self._update_countdown_display()

    def _update_countdown_display(self) -> None:
        """Update the countdown display."""
        best_port = find_best_port()
        if best_port:
            port_short = best_port.split("/")[-1]
            self.query_one("#countdown", Static).update(
                f"Auto-connecting to {port_short} in {self._countdown}s...\n"
                f"[dim]Press any key to select manually[/dim]"
            )

    def _stop_countdown(self) -> None:
        """Stop the countdown timer."""
        if self._timer_handle:
            self._timer_handle.stop()
            self._timer_handle = None

    def _cancel_auto_connect(self) -> None:
        """Cancel the auto-connect and allow manual selection."""
        if not self._auto_connect_cancelled:
            self._auto_connect_cancelled = True
            self._stop_countdown()
            self.query_one("#countdown", Static).update("")
            self.query_one("#status", Static).update("[dim]Probe type auto-detected from data[/dim]")

    def _do_auto_connect(self) -> None:
        """Perform the auto-connect."""
        best_port = find_best_port()
        if best_port:
            self.query_one("#countdown", Static).update("")
            self.query_one("#status", Static).update(f"Connecting to {best_port}...")
            self.post_message(self.Connected(port=best_port))

    def on_key(self, event) -> None:
        """Cancel auto-connect on any keypress (except Enter which connects)."""
        if event.key not in ("enter", "q"):
            self._cancel_auto_connect()

    def refresh_ports(self) -> None:
        """Scan and display available serial ports."""
        option_list = self.query_one("#port-list", OptionList)
        option_list.clear_options()
        
        ports = list_ports.comports()
        
        if not ports:
            option_list.add_option(Option("No ports found", id="none", disabled=True))
            self.query_one("#status", Static).update("No serial ports detected")
            return
        
        best_port = find_best_port()
        
        for port in ports:
            if port.device == best_port:
                label = f"[*] {port.device} - {port.description}"
            elif 'usb' in port.device.lower() or 'serial' in port.description.lower():
                label = f"[+] {port.device} - {port.description}"
            else:
                label = f"[ ] {port.device} - {port.description}"
            option_list.add_option(Option(label, id=port.device))
        
        # Highlight the best port
        if best_port:
            for i in range(option_list.option_count):
                opt = option_list.get_option_at_index(i)
                if opt.id == best_port:
                    option_list.highlighted = i
                    break

    def action_refresh_ports(self) -> None:
        """Action to refresh port list."""
        self._cancel_auto_connect()
        self.refresh_ports()

    def action_connect_now(self) -> None:
        """Connect immediately."""
        self._stop_countdown()
        
        option_list = self.query_one("#port-list", OptionList)
        
        # Use highlighted port if available
        if option_list.highlighted is not None:
            selected_option = option_list.get_option_at_index(option_list.highlighted)
            if selected_option.id != "none":
                self.query_one("#countdown", Static).update("")
                self.query_one("#status", Static).update(f"Connecting to {selected_option.id}...")
                self.post_message(self.Connected(port=selected_option.id))
                return
        
        # Fall back to auto-detect
        self._do_auto_connect()

    @on(Button.Pressed, "#connect-btn")
    def handle_connect(self) -> None:
        """Handle connect button press."""
        self.action_connect_now()

    @on(OptionList.OptionSelected)
    def handle_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle port selection - connect immediately."""
        self._stop_countdown()
        if event.option_id != "none":
            self.query_one("#countdown", Static).update("")
            self.query_one("#status", Static).update(f"Connecting to {event.option_id}...")
            self.post_message(self.Connected(port=event.option_id))
