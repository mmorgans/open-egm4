"""Monitor Screen - Live data monitoring dashboard."""

import csv
import datetime
from dataclasses import dataclass
from pathlib import Path

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from src.tui.widgets.co2_chart import CO2PlotWidget
from src.tui.widgets.stats import StatsWidget
from src.tui.widgets.log import LogWidget
from src.tui.widgets.legend import ChannelLegend
from src.egm_interface import EGM4Serial
from src.tui.screens.bigmode import BigModeScreen
from src.tui.screens.help import HelpScreen


class MonitorScreen(Screen):
    """Main monitoring dashboard screen."""

    # Defer to styles.tcss or use simple layout
    DEFAULT_CSS = """
    MonitorScreen {
        layout: vertical;
        padding: 0;
    }
    """

    BINDINGS = [
        ("q", "quit_app", "Quit"),
        ("c", "clear", "Clear"),
        ("e", "export", "Export"),
        ("p", "pause", "Pause"),
        ("b", "big_mode", "Big"),
        ("d", "app.toggle_dark", "Theme"),
        # Channel selection - hidden from footer (shown in legend)
        ("1", "select_cr", None),
        ("2", "select_hr", None),
        ("3", "select_par", None),
        ("4", "select_rh", None),
        ("5", "select_temp", None),
        ("6", "select_dc", None),
        ("7", "select_sr", None),
        ("8", "select_atmp", None),
        ("9", "select_dt", None),
        # Span control - hidden from footer (shown in legend)
        ("=", "increase_span", None),
        ("+", "increase_span", None),
        ("-", "decrease_span", None),
        ("_", "decrease_span", None),
        # Plot cycling - hidden from footer
        ("comma", "prev_plot", None),
        ("full_stop", "next_plot", None),
        ("less_than_sign", "prev_plot", None),
        ("greater_than_sign", "next_plot", None),
        ("?", "help", "Help"),
    ]

    @dataclass
    class Disconnected(Message):
        """Message sent when disconnecting."""
        pass

    def __init__(
        self,
        port: str,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self.port = port
        self.serial = EGM4Serial()
        self.is_paused = False
        self.recorded_data: list[dict] = []
        self.raw_log_file = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main"):
            with Vertical(id="left"):
                yield CO2PlotWidget(id="chart")
                yield ChannelLegend(id="legend")
            with Vertical(id="right"):
                yield StatsWidget(id="stats")
                log_widget = LogWidget(id="log")
                log_widget.border_title = "Event Log"
                yield log_widget
        yield Footer()

    def on_mount(self) -> None:
        """Start serial connection when screen mounts."""

        self.start_serial_reading()
        
        # Update stats widget with connection info
        stats = self.query_one("#stats", StatsWidget)
        stats.port_name = self.port
        stats.is_connected = True
        
        # Log connection
        log = self.query_one("#log", LogWidget)
        log.log_success(f"USB attached: {self.port}")
        
        # Start periodic USB port monitoring
        self._usb_monitor = self.set_interval(2.0, self._check_usb_port)
        
        # Open raw log file
        log_filename = f"raw_dump_{datetime.datetime.now().strftime('%Y-%m-%d')}.log"
        try:
            self.raw_log_file = open(log_filename, 'a')
            self.raw_log_file.write(f"\n--- Session started {datetime.datetime.now().isoformat()} ---\n")
        except Exception:
            pass

    def _check_usb_port(self) -> None:
        """Check if the USB port is still present."""
        from serial.tools import list_ports
        
        available_ports = [p.device for p in list_ports.comports()]
        stats = self.query_one("#stats", StatsWidget)
        
        if self.port not in available_ports:
            # Port disappeared - USB unplugged
            if stats.is_connected:
                stats.is_connected = False
                log = self.query_one("#log", LogWidget)
                log.log_error(f"USB disconnected: {self.port}")
        else:
            # Port present
            if not stats.is_connected:
                stats.is_connected = True
                log = self.query_one("#log", LogWidget)
                log.log_success(f"USB reconnected: {self.port}")

    async def on_unmount(self) -> None:
        """Clean up when screen unmounts."""
        await self.serial.disconnect()
        if self.raw_log_file:
            try:
                self.raw_log_file.write(f"--- Session ended {datetime.datetime.now().isoformat()} ---\n")
                self.raw_log_file.close()
            except Exception:
                pass

    @work(exclusive=True)
    async def start_serial_reading(self) -> None:
        """Background worker for reading serial data."""
        # Callback wrapper to bridge to UI thread
        def on_data(raw_line: str, parsed_data: dict) -> None:
            # We are in an async worker, so we should be careful.
            # EGM4Serial.process_loop awaits things, so it runs in event loop.
            # We can directly post message or use call_from_others.
            # But wait, EGM4Serial calls this callback synchronously from its await loop.
            # So we are in the main thread's event loop.
            
            # Save to raw log immediately
            if self.raw_log_file:
                try:
                    self.raw_log_file.write(raw_line + '\n')
                    self.raw_log_file.flush()
                except Exception:
                    pass
            
            self.post_message(DataReceived(raw_line=raw_line, parsed=parsed_data))

        def on_error(msg: str) -> None:
            self.post_message(SerialError(message=msg))

        self.serial.data_callback = on_data
        self.serial.error_callback = on_error
        
        # Connect asynchronously
        success = await self.serial.connect(self.port)
        if not success:
            self.post_message(SerialError(message=f"Failed to connect to {self.port}"))
            return

        # Start processing loop (this blocks the worker, which is fine for async worker)
        await self.serial.process_loop()

    @on(Message)
    def handle_data_received(self, event: Message) -> None:
        """Handle incoming serial data."""
        if not isinstance(event, DataReceived):
            return
        
        if self.is_paused:
            return
        
        parsed = event.parsed
        rec_type = parsed.get('type', 'unknown')
        
        chart = self.query_one("#chart", CO2PlotWidget)
        stats = self.query_one("#stats", StatsWidget)
        log = self.query_one("#log", LogWidget)
        
        timestamp = datetime.datetime.now().isoformat()
        
        if rec_type in ('R', 'M'):
            co2 = parsed.get('co2_ppm', 0)
            record = parsed.get('record', 0)
            plot = parsed.get('plot', 0)
            
            # Store parsed data for CSV export (all fields from manual)
            export_row = {
                'timestamp': timestamp,
                'type': rec_type,
                'plot': plot,
                'record': record,
                'day': parsed.get('day', 0),
                'month': parsed.get('month', 0),
                'hour': parsed.get('hour', 0),
                'minute': parsed.get('minute', 0),
                'co2_ppm': co2,
                'h2o_mb': parsed.get('h2o', 0),
                'rht_c': parsed.get('rht', 0),
                'par': parsed.get('par', ''),
                'rh_pct': parsed.get('rh', ''),
                'temp_c': parsed.get('temp', ''),
                'dc_ppm': parsed.get('dc', ''),
                'dt_s': parsed.get('dt', ''),
                'sr_rate': parsed.get('sr', ''),
                'atmp_mb': parsed.get('atmp', ''),
                'probe_type': parsed.get('probe_type', ''),
            }
            self.recorded_data.append(export_row)
            
            chart.add_data(parsed)
            stats.add_reading(co2)
            stats.record_count += 1
            stats.data_mode = rec_type  # Update mode indicator (M=Real-Time, R=Memory)
            stats.device_status = ""  # Clear warmup/zero status when data arrives
            log.log_data(plot, record, co2)
            
            # Update legend with current plot info
            legend = self.query_one("#legend", ChannelLegend)
            legend.set_plot_info(chart.filter_plot, chart.get_known_plots())
            
            # Update big mode screen if it's active
            if hasattr(self, '_big_screen') and self._big_screen.is_current:
                self._big_screen.current_co2 = co2
                self._big_screen.record_count = stats.record_count
                # Calculate stability
                history = list(stats._history)
                if len(history) >= 10:
                    import statistics
                    stdev = statistics.stdev(history[-10:])
                    if stdev < 5:
                        self._big_screen.stability = "STABLE"
                    elif stdev < 20:
                        self._big_screen.stability = "VARIABLE"
                    else:
                        self._big_screen.stability = "NOISY"
            
        elif rec_type == 'B':
            co2 = parsed.get('co2_ppm', 0)
            log.log_info(f"Device startup: EGM4, CO2: {co2:.1f}")
            
        elif rec_type == 'W':
            # Warmup - device heating up
            temp = parsed.get('warmup_temp', 0)
            stats.device_status = f"WARMUP: {temp:.0f}C"
            stats.data_mode = ""  # Clear data mode during warmup
            
        elif rec_type == 'Z':
            # Zero check in progress
            countdown = parsed.get('zero_countdown', 0)
            stats.device_status = f"ZERO CHECK: {countdown:.0f}/14s"
            stats.data_mode = ""  # Clear data mode during zero check
            
        elif rec_type == 'Z_END':
            # End of memory dump (plain "Z" without value)
            log.log_complete()
            self.notify("Download Complete!", severity="information", timeout=5)
            stats.device_status = ""  # Clear status
            # Audible beep
            self.app.bell()
            
        else:
            log.log_event(event.raw_line[:60], "dim")

    @on(CO2PlotWidget.ProbeTypeChanged)
    def handle_probe_change(self, event: CO2PlotWidget.ProbeTypeChanged) -> None:
        """Handle probe type change detection."""
        legend = self.query_one("#legend", ChannelLegend)
        legend.set_probe_type(event.probe_type)
        # Maybe show an unobtrusive indicator if needed, but the legend update is clear

    @on(Message)
    def handle_serial_error(self, event: Message) -> None:
        """Handle serial errors - log only, no notification."""
        if not isinstance(event, SerialError):
            return
        
        # Log the error but don't show annoying notification
        log = self.query_one("#log", LogWidget)
        log.log_error(event.message)
        
        # If it's a device error, mark as disconnected
        if "device" in event.message.lower() or "disconnected" in event.message.lower():
            stats = self.query_one("#stats", StatsWidget)
            stats.is_connected = False

    async def action_quit_app(self) -> None:
        """Save work and quit the application."""
        # Immediate feedback that we're quitting
        log = self.query_one("#log", LogWidget)
        log.log_info("Saving and quitting...")
        stats = self.query_one("#stats", StatsWidget)
        stats.device_status = "QUITTING..."
        
        # Clear callbacks to prevent error messages during shutdown
        self.serial.error_callback = None
        self.serial.data_callback = None
        
        # Close serial connection
        await self.serial.disconnect()
        
        # Close log file
        if self.raw_log_file:
            try:
                self.raw_log_file.write(f"--- Session ended {datetime.datetime.now().isoformat()} ---\n")
                self.raw_log_file.close()
            except Exception:
                pass
        
        # Auto-export if there's data
        if self.recorded_data:
            filename = f"egm4_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            try:
                with open(filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Timestamp", "Raw_Data"])
                    writer.writerows(self.recorded_data)
            except Exception:
                pass
        
        # Exit the app
        self.app.exit()

    def action_clear(self) -> None:
        """Clear all data."""
        self.query_one("#chart", CO2PlotWidget).clear_data()
        self.query_one("#stats", StatsWidget).clear_history()
        self.query_one("#log", LogWidget).clear()
        # Update legend to reflect cleared plots
        legend = self.query_one("#legend", ChannelLegend)
        chart = self.query_one("#chart", CO2PlotWidget)
        legend.set_plot_info(chart.filter_plot, chart.get_known_plots())

    def action_pause(self) -> None:
        """Toggle pause state."""
        self.is_paused = not self.is_paused
        stats = self.query_one("#stats", StatsWidget)
        stats.is_paused = self.is_paused
        
        if self.is_paused:
            self.notify("⏸ Data stream paused", severity="warning")
        else:
            self.notify("▶ Data stream resumed", severity="information")

    def action_export(self) -> None:
        """Export data to CSV with proper headers matching EGM-4 manual."""
        if not self.recorded_data:
            self.notify("No data to export", severity="warning")
            return
        
        filename = f"egm4_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Headers matching EGM-4 manual record structure
        headers = [
            'timestamp',      # Local timestamp when received
            'type',           # M=Real Time, R=Memory
            'plot',           # Plot No (0-99)
            'record',         # Record No (1-9999)
            'day',            # Day (1-31)
            'month',          # Month (1-12)
            'hour',           # Hour (1-24)
            'minute',         # Minute (0-59)
            'co2_ppm',        # CO2 Ref (ppm)
            'h2o_mb',         # H2O Ref (mb)
            'rht_c',          # RH Sensor Temp (°C)
            'par',            # PAR (µmol m⁻² s⁻¹) - SRC-1
            'rh_pct',         # %RH - SRC-1
            'temp_c',         # Soil Temp (°C) - SRC-1
            'dc_ppm',         # Delta CO2 (ppm) - SRC-1
            'dt_s',           # Delta Time (s) - SRC-1
            'sr_rate',        # Soil Resp Rate (g CO2/m²/hr) - SRC-1
            'atmp_mb',        # Atmospheric Pressure (mb)
            'probe_type',     # Probe Type code
        ]
        
        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(self.recorded_data)
            
            self.notify(f"✓ Exported to {filename}", severity="information", timeout=5)
            self.query_one("#log", LogWidget).log_success(f"Exported {len(self.recorded_data)} records to {filename}")
        except Exception as e:
            self.notify(f"Export failed: {e}", severity="error")

    def action_big_mode(self) -> None:
        """Toggle high-visibility field mode."""
        stats = self.query_one("#stats", StatsWidget)
        big_screen = BigModeScreen()
        big_screen.current_co2 = stats.current_co2
        big_screen.record_count = stats.record_count
        # Store reference so we can update it
        self._big_screen = big_screen
        self.app.push_screen(big_screen)

    # Channel selection actions (SRC mode: 8 channels)
    def _select_channel(self, channel: str) -> None:
        """Select a channel to display on the chart."""
        chart = self.query_one("#chart", CO2PlotWidget)
        legend = self.query_one("#legend", ChannelLegend)
        chart.set_active_channel(channel)
        legend.set_active(channel)

    def action_select_cr(self) -> None:
        self._select_channel("cr")

    def action_select_hr(self) -> None:
        self._select_channel("hr")

    def action_select_par(self) -> None:
        self._select_channel("par")

    def action_select_rh(self) -> None:
        self._select_channel("rh")

    def action_select_temp(self) -> None:
        self._select_channel("temp")

    def action_select_dc(self) -> None:
        self._select_channel("dc")

    def action_select_sr(self) -> None:
        self._select_channel("sr")

    def action_select_atmp(self) -> None:
        self._select_channel("atmp")

    def action_select_dt(self) -> None:
        self._select_channel("dt")

    # Span control actions
    def action_increase_span(self) -> None:
        """Double the chart history span (max 600)."""
        chart = self.query_one("#chart", CO2PlotWidget)
        new_span = min(600, chart.max_points * 2)
        if new_span != chart.max_points:
            chart.max_points = new_span

    def action_decrease_span(self) -> None:
        """Halve the chart history span (min 30)."""
        chart = self.query_one("#chart", CO2PlotWidget)
        new_span = max(30, chart.max_points // 2)
        if new_span != chart.max_points:
            chart.max_points = new_span

    def action_help(self) -> None:
        """Show the help screen."""
        self.app.push_screen(HelpScreen())

    def action_next_plot(self) -> None:
        """Switch to next plot."""
        chart = self.query_one("#chart", CO2PlotWidget)
        legend = self.query_one("#legend", ChannelLegend)
        chart.next_plot()
        legend.set_plot_info(chart.filter_plot, chart.get_known_plots())

    def action_prev_plot(self) -> None:
        """Switch to previous plot."""
        chart = self.query_one("#chart", CO2PlotWidget)
        legend = self.query_one("#legend", ChannelLegend)
        chart.prev_plot()
        legend.set_plot_info(chart.filter_plot, chart.get_known_plots())


# Custom message types
@dataclass
class DataReceived(Message):
    """Message for received serial data."""
    raw_line: str
    parsed: dict


@dataclass
class SerialError(Message):
    """Message for serial errors."""
    message: str
