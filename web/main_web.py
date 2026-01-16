import asyncio
from textual.app import App
from src.tui.app import EGM4App
from src.tui.screens.connect import ConnectScreen
from src.tui.screens.monitor import MonitorScreen
from src.web_bridge import WebSerialTransport
from src.egm_interface import EGM4Serial

# Monkey patch EGM4App to inject Web Serial if needed
# Or better, we subclass it or configure it.
# EGM4App currently hardcodes EGM4Serial() with default transport in MonitorScreen.
# We need to inject the transport.

# Implementation Strategy:
# We will subclass MonitorScreen or modify EGM4App to accept a factory/transport.
# For now, let's monkeypatch EGM4Serial default init or pass it in.

# Actually, MonitorScreen creates `self.serial = EGM4Serial()`.
# EGM4Serial() uses `DesktopSerialTransport` by default.
# We can overwrite the default argument in EGM4Serial if we are in web mode, 
# but we are in the same codebase.

# Let's modify EGM4Serial in memory before the app starts?
# Or clearer: Update MonitorScreen to accept a transport/serial instance.
# But MonitorScreen is created by ConnectScreen event...

# Refactor Step (Pre-requisite logic):
# We need to tell the App to use WebSerialTransport.
# The ConnectScreen usually asks for a COM port (User input).
# In Web Serial, the "Connect" button action triggers the browser picker.
# So ConnectScreen needs to behave differently on Web.

import js

class WebEGM4App(EGM4App):
    """Web-specific version of the App."""
    
    def on_mount(self) -> None:
        """
        On web, we can skip the standard 'Select Port' dropdown 
        and just have a big 'Connect USB' button because 
        the browser handles the selection UI.
        """
        # We can still use ConnectScreen but maybe we should modify it 
        # to just have a "Connect" button that triggers the Web Serial request.
        self.push_screen("connect")

# We also need to patch ConnectScreen or MonitorScreen behavior
# MonitorScreen instantiates EGM4Serial. 
# We should arguably make EGM4Serial smart enough to detect environment?
# Or inject it.

from src import egm_interface

# Force the default transport to be WebSerialTransport in this environment
egm_interface.DesktopSerialTransport = WebSerialTransport

if __name__ == "__main__":
    app = WebEGM4App()
    app.run()
