import flet as ft
from src.egm_interface import EGM4Serial
from src.ui.components import PortSelector, TerminalView, LiveChart
import datetime
import csv
import logging

class EGMApp:
    def __init__(self, page: ft.Page):
        self.page_ref = page 
        self.serial_interface = EGM4Serial()
        self.serial_interface.data_callback = self.on_data_received
        self.serial_interface.error_callback = self.on_error
        
        self.port_selector = PortSelector(on_change=self.on_port_change)
        self.terminal = TerminalView()
        self.chart = LiveChart()
        
        self.connect_btn = ft.ElevatedButton("Connect")
        self.connect_btn.on_click = self.toggle_connection
        
        self.export_btn = ft.ElevatedButton("Export CSV")
        self.export_btn.on_click = self.export_data
        
        self.is_connected = False
        self.recorded_data = [] 

    def build(self):
        return ft.Column(
            controls=[
                ft.Text("Open EGM-4 Interface", size=20),
                ft.Divider(),
                self.port_selector,
                ft.Row([self.connect_btn, self.export_btn]),
                ft.Divider(),
                ft.Text("Chart:"),
                self.chart,
                ft.Divider(),
                self.terminal,
            ],
            scroll=ft.ScrollMode.AUTO,
        )

    def on_port_change(self, port):
        logging.info(f"Port selected: {port}")

    def toggle_connection(self, e):
        if not self.is_connected:
            port = self.port_selector.get_selected_port()
            if not port:
                self.terminal.log("Error: No port selected.")
                return

            self.terminal.log(f"System: Connecting to {port}...")
            if self.serial_interface.connect(port):
                self.is_connected = True
                self.connect_btn.text = "Disconnect"
                self.terminal.log("System: Connected.")
            else:
                self.terminal.log("System: Connection Failed.")
        else:
            self.serial_interface.disconnect()
            self.is_connected = False
            self.connect_btn.text = "Connect"
            self.terminal.log("System: Disconnected.")
        
        self.connect_btn.update()

    def on_data_received(self, raw_line, parsed_data):
        self.terminal.log(raw_line)
        self.recorded_data.append([datetime.datetime.now().isoformat(), raw_line])

    def on_error(self, msg):
        self.terminal.log(f"Error: {msg}")

    def export_data(self, e):
        if not self.recorded_data:
            self.terminal.log("System: No data to export.")
            return

        filename = f"egm4_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Raw Data"])
                writer.writerows(self.recorded_data)
            self.terminal.log(f"System: Exported to {filename}")
        except Exception as ex:
            self.terminal.log(f"System: Export Failed: {ex}")
