import flet as ft
from serial.tools import list_ports
import datetime

class PortSelector(ft.Row):
    def __init__(self, on_refresh=None, on_change=None):
        super().__init__()
        self.on_refresh_callback = on_refresh
        self.on_change_callback = on_change
        self.dd = ft.Dropdown(
            label="Select Serial Port",
            width=300,
            options=[],
        )
        self.dd.on_change = self.on_port_change
        
        refresh_btn = ft.ElevatedButton("Refresh")
        refresh_btn.on_click = lambda _: self.refresh_ports()
        
        self.controls = [
            self.dd,
            refresh_btn
        ]
        self.refresh_ports()

    def refresh_ports(self):
        ports = list_ports.comports()
        self.dd.options = [ft.dropdown.Option(port.device) for port in ports]
        self.dd.value = None
        try:
            self.dd.update() 
        except RuntimeError:
            pass
        if self.on_refresh_callback:
            self.on_refresh_callback()

    def on_port_change(self, e):
        if self.on_change_callback:
            self.on_change_callback(e.control.value)
    
    def get_selected_port(self):
        return self.dd.value


class TerminalView(ft.Column):
    def __init__(self):
        super().__init__()
        self.text_field = ft.TextField(
            multiline=True,
            read_only=True,
            min_lines=10,
            max_lines=20,
        )
        self.controls = [
            ft.Text("Terminal Output:"),
            self.text_field
        ]

    def log(self, message: str):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        current = self.text_field.value or ""
        self.text_field.value = current + f"[{now}] {message}\n"
        try:
            self.text_field.update()
        except RuntimeError:
            pass


class LiveChart(ft.Container):
    def __init__(self):
        super().__init__()
        self.content = ft.Text("(Chart disabled)")
        
    def add_point(self, value):
        pass
