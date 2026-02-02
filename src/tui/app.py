#!/usr/bin/env python3
"""
Open EGM-4 TUI - Professional Textual Application
A modern terminal interface for the PP Systems EGM-4 Environmental Gas Monitor.

Features:
- Real-time CO₂ charting with textual-plotext
- Multi-screen navigation (Connect → Monitor)
- Thread-safe serial communication
- Professional keyboard bindings and theming
"""

import argparse
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from src.tui.screens.connect import ConnectScreen
from src.tui.screens.monitor import MonitorScreen
from src.database import DatabaseHandler


class EGM4App(App):
    """Main EGM-4 Terminal User Interface Application."""

    TITLE = "Open EGM-4"
    SUB_TITLE = "Environmental Gas Monitor Interface"
    
    def __init__(self, force_unicode: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.force_unicode = force_unicode
    
    CSS_PATH = Path(__file__).parent / "styles.tcss"
    
    SCREENS = {
        "connect": ConnectScreen,
    }
    
    BINDINGS = [
        ("d", "toggle_dark", "Dark/Light"),
        ("ctrl+c", "quit", None),  # Always quit, even in modals
        ("?", "help", "Help"),
    ]

    def on_mount(self) -> None:
        """Show connect screen on startup."""
        try:
            self.db = DatabaseHandler()
        except Exception as e:
            self.notify(f"Database Init Failed: {e}", severity="error")
            self.db = None
            
        self.push_screen("connect")

    @on(ConnectScreen.Connected)
    def handle_connection(self, event: ConnectScreen.Connected) -> None:
        """Handle successful connection from connect screen."""
        # Create monitor screen with the selected port and DB handler
        monitor = MonitorScreen(
            port=event.port, 
            db_handler=self.db,
            resume_session_id=event.resume_session_id,
        )
        self.push_screen(monitor)

    @on(MonitorScreen.Disconnected)
    def handle_disconnection(self, event: MonitorScreen.Disconnected) -> None:
        """Handle disconnection from monitor screen."""
        self.pop_screen()
        self.notify("Disconnected from device", severity="information")

    def action_toggle_dark(self) -> None:
        """Toggle dark/light mode."""
        self.theme = "textual-light" if self.theme == "textual-dark" else "textual-dark"

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    def action_help(self) -> None:
        """Show help information."""
        self.notify(
            "Q: Quit | D: Dark Mode | E: Export | C: Clear | P: Pause",
            title="Keyboard Shortcuts",
            timeout=5,
        )


def main() -> None:
    """Entry point for the EGM-4 TUI application."""
    # Parse arguments here so it works when installed as a CLI tool
    parser = argparse.ArgumentParser(description="Open EGM-4 TUI")
    parser.add_argument("--force-unicode", action="store_true", help="Force usage of Unicode symbols even on Windows")
    
    # Use parse_known_args to avoid conflict if Textual consumes args (though usually safe)
    args, _ = parser.parse_known_args()
    
    app = EGM4App(force_unicode=args.force_unicode)
    app.run()


if __name__ == "__main__":
    main()
