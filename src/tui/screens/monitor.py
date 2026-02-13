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
from src.tui.screens.confirm import ConfirmScreen
from src.database import DatabaseHandler
from src.analysis import FluxCalculator
import time
from src.tui.screens.note import NoteInputScreen


class MonitorScreen(Screen):
    """Main monitoring dashboard screen."""

    SAMPLE_STEP_IDLE = "idle"
    SAMPLE_STEP_INJECT = "inject"
    SAMPLE_STEP_SETTLE = "settle"
    SAMPLE_STEP_FLUSH = "flush"

    # Defer to styles.tcss or use simple layout
    DEFAULT_CSS = """
    MonitorScreen {
        layout: vertical;
        padding: 0;
    }
    """

    BINDINGS = [
        ("q", "quit_app", "Quit"),  # Screen-specific quit
        ("c", "clear", "Clear"),
        ("e", "export", "Export"),
        ("n", "add_note", "Note"),
        ("m", "toggle_static_mode", "Static"),
        ("x", "reset_static_cycle", "Reset Static"),
        ("p", "pause", "Pause"),
        ("b", "big_mode", "Big"),
        ("d", "app.toggle_dark", "Theme"),
        # Channel selection - hidden from footer (shown in legend)
        ("1", "select_slot('1')", None),
        ("2", "select_slot('2')", None),
        ("3", "select_slot('3')", None),
        ("4", "select_slot('4')", None),
        ("5", "select_slot('5')", None),
        ("6", "select_slot('6')", None),
        ("7", "select_slot('7')", None),
        ("8", "select_slot('8')", None),
        ("9", "select_slot('9')", None),

        # Plot cycling - hidden from footer
        ("comma", "prev_plot", None),
        ("full_stop", "next_plot", None),
        ("less_than_sign", "prev_plot", None),
        ("greater_than_sign", "next_plot", None),
        # Data cursor - arrow keys to navigate, 'i' to toggle inspect mode
        ("i", "toggle_cursor", "Inspect"),
        ("left", "cursor_left", None),
        ("right", "cursor_right", None),
        ("home", "cursor_home", None),
        ("end", "cursor_end", None),
        ("?", "help", "Help"),
    ]

    @dataclass
    class Disconnected(Message):
        """Message sent when disconnecting."""
        pass

    def __init__(
        self,
        port: str | None,  # None for offline mode
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        db_handler: DatabaseHandler | None = None,
        resume_session_id: int | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self.port = port
        self.serial = EGM4Serial() if port else None
        self.is_paused = False
        self.recorded_data: list[dict] = []
        self.raw_log_file = None
        self._warmup_logged = False  # Track if warmup message was shown
        self._zero_logged = False  # Track if zero check message was shown
        self._disconnect_logged = False  # Track if disconnect was already logged
        self.db = db_handler
        self.session_id: int | None = resume_session_id
        self._is_resuming = resume_session_id is not None
        self.flux_calc = FluxCalculator(window_size=30)  # 30s window for Flux
        self._plot_base_times = {} # Track base time for each plot to synthesize timestamps from DT
        self.static_sampling_mode = False
        self._sample_counter = 0
        self._last_measurement: dict | None = None
        self._sample_capture_active = False
        self._sample_peak_ppm: float | None = None
        self._sample_flow_step = self.SAMPLE_STEP_IDLE

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
        log = self.query_one("#log", LogWidget)
        stats = self.query_one("#stats", StatsWidget)
        
        # Offline mode: skip serial connection
        if not self.port:
            stats.port_name = "Offline"
            stats.is_connected = False
            log.log_info("Offline mode - viewing saved session")
        else:
            self.start_serial_reading()
            
            # Update stats widget with connection info
            stats.port_name = self.port
            stats.is_connected = True
            
            # Log connection
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
            
        # Create DB Session
        if self.db:
            try:
                if self._is_resuming and self.session_id:
                    self._restore_session(self.session_id)
                else:
                    self.session_id = self.db.create_session(notes=f"Monitor session started on {self.port}")
                    self.query_one("#log", LogWidget).log_success(f"New session #{self.session_id} started")
            except Exception as e:
                self.query_one("#log", LogWidget).log_error(f"DB Error: {e}")

    def _restore_session(self, session_id: int) -> None:
        """Restore data from a previous session."""
        try:
            log = self.query_one("#log", LogWidget)
            chart = self.query_one("#chart", CO2PlotWidget)
            stats = self.query_one("#stats", StatsWidget)
            legend = self.query_one("#legend", ChannelLegend)

            # Clear existing data to prevent overlap/duplicates
            chart.clear_data()

            log.log_info(f"Restoring session #{session_id}...")

            # Fetch all readings
            readings = self.db.get_session_readings(session_id)

            if not readings:
                log.log_warning("Session empty")
                return

            # CRITICAL: Sort readings by (plot_id, elapsed_time) to ensure
            # DT values are monotonically increasing within each plot
            # Memory dumps from the EGM may have out-of-order records
            readings.sort(key=lambda r: (r['plot_id'], r['elapsed_time'] or 0))

            count = 0

            # Use batch mode to avoid replotting on every data point
            for row in readings:
                # Use stored elapsed_time directly if available (new behavior)
                # This is the actual DT from the EGM device
                stored_dt = row.get('elapsed_time')

                if stored_dt is not None:
                    dt_val = stored_dt
                else:
                    # Fallback for old data without elapsed_time column
                    # Parse timestamp and calculate
                    try:
                        ts_str = row['timestamp']
                        if isinstance(ts_str, str):
                            ts = datetime.datetime.fromisoformat(ts_str)
                        else:
                            ts = ts_str
                    except (ValueError, TypeError, AttributeError):
                        ts = datetime.datetime.now()

                    # Need to track first timestamp per plot for calculation
                    pid = row['plot_id']
                    if not hasattr(self, '_fallback_plot_starts'):
                        self._fallback_plot_starts = {}
                    if pid not in self._fallback_plot_starts:
                        self._fallback_plot_starts[pid] = ts
                    dt_val = (ts - self._fallback_plot_starts[pid]).total_seconds()

                # Reconstruct parsed dict format expected by widgets
                parsed = {
                    'timestamp': row['timestamp'],
                    'type': row['record_type'],
                    'plot': row['plot_id'],
                    'record': row['record_num'],
                    'co2': row['co2'],  # Internal key
                    'co2_ppm': row['co2'],
                    'h2o': row['h2o'],
                    'h2o_mb': row['h2o'],
                    'temp': row['temp_c'],
                    'temp_c': row['temp_c'], # Export key
                    'atmp': row['pressure'],
                    'atmp_mb': row['pressure'], # Export key
                    'par': row['par'],
                    'rh': row['humidity'],
                    'rh_pct': row['humidity'], # Export key
                    'dc': row['delta_co2'],
                    'dc_ppm': row['delta_co2'], # Export key
                    'sr': row['soil_resp_rate'],
                    'sr_rate': row['soil_resp_rate'], # Export key
                    'probe_type': row['probe_type'],
                    'dt': dt_val,         # Calculated DT
                    'dt_s': dt_val,
                    'note': '',
                    'sample_id': '',
                    'sample_label': '',
                    'sample_ppm': '',
                    'sample_peak_ppm': ''
                }

                # Add to local cache for export
                self.recorded_data.append(parsed)

                # Update widgets in batch mode (no replot per item)
                chart.add_data(parsed, batch_mode=True)
                stats.add_reading(row['co2'], record=row['record_num'])
                count += 1

            # Replot once after all data is loaded
            chart.replot()

            # Update legend with restored plots
            legend.set_plot_info(chart.filter_plot, chart.get_known_plots())
            log.log_success(f"Restored {count} readings")

        except Exception as e:
            self.query_one("#log", LogWidget).log_error(f"Restore Failed: {e}")

    def _write_raw_line(self, row_type: str, text: str) -> None:
        if self.raw_log_file:
            try:
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                self.raw_log_file.write(f"{row_type} [{timestamp}] {text}\n")
                self.raw_log_file.flush()
            except (IOError, OSError):
                pass

    def _sample_step_message(self, step: str) -> str:
        if step == self.SAMPLE_STEP_INJECT:
            return "STEP 1: INJECT SAMPLE (N)"
        if step == self.SAMPLE_STEP_SETTLE:
            return "STEP 2: WAIT TO SETTLE, CAPTURE (N)"
        if step == self.SAMPLE_STEP_FLUSH:
            return "STEP 3: INJECT AMBIENT AIR (N)"
        return ""

    def _set_sample_step(self, step: str) -> None:
        self._sample_flow_step = step
        stats = self.query_one("#stats", StatsWidget)
        stats.static_sampling_step = self._sample_step_message(step) if self.static_sampling_mode else ""

    def _reset_sample_cycle(self) -> None:
        self._sample_capture_active = False
        self._sample_peak_ppm = None
        self._set_sample_step(self.SAMPLE_STEP_INJECT)

    def _check_usb_port(self) -> None:
        """Check if the USB port is still present."""
        from serial.tools import list_ports
        
        available_ports = [p.device for p in list_ports.comports()]
        stats = self.query_one("#stats", StatsWidget)
        
        if self.port not in available_ports:
            # Port disappeared - USB unplugged
            if stats.is_connected:
                stats.is_connected = False
                # Only log disconnect once
                if not self._disconnect_logged:
                    log = self.query_one("#log", LogWidget)
                    log.log_error(f"USB disconnected: {self.port}")
                    self._disconnect_logged = True
        else:
            # Port present
            if not stats.is_connected:
                stats.is_connected = True
                stats.reconnect_count += 1
                log = self.query_one("#log", LogWidget)
                log.log_success(f"USB reconnected: {self.port}")
                # Reset disconnect flag for next time
                self._disconnect_logged = False
                
                # Check if the reader loop died (expected behavior now on disconnect)
                # If so, restart it
                if self.serial and not getattr(self.serial, 'running', False):
                    log.log_info("Restarting data stream...")
                    self.start_serial_reading()

    async def on_unmount(self) -> None:
        """Clean up when screen unmounts."""
        if self.serial:
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

        # Track malformed/unknown records for quick quality checks.
        if parsed.get('error') or rec_type == 'unknown':
            stats.parse_errors += 1
        
        if rec_type in ('R', 'M'):
            stats.parsed_records += 1
            # Try to synthesize timestamp from DT (if available) for better consistency
            # This is crucial for Memory Dumps where arrival time != measurement time
            dt_val = parsed.get('dt')
            plot_id = parsed.get('plot', 0)
            
            if dt_val is not None:
                # Type 8 (SRC) and others with DT
                
                # Check for new measurement cycle (DT reset)
                reset_base = False
                if not hasattr(self, '_last_dt_per_plot'):
                    self._last_dt_per_plot = {}
                
                last = self._last_dt_per_plot.get(plot_id)
                if last is not None and dt_val < last:
                    reset_base = True
                self._last_dt_per_plot[plot_id] = dt_val

                if plot_id not in self._plot_base_times or reset_base:
                    # Initialize/Reset base time: current time minus elapsed dt
                    # This aligns 'now' with the correct relative position in the timeline
                    self._plot_base_times[plot_id] = datetime.datetime.now() - datetime.timedelta(seconds=dt_val)
                
                # Calculate absolute timestamp from base + dt
                new_ts = self._plot_base_times[plot_id] + datetime.timedelta(seconds=dt_val)
                timestamp = new_ts.isoformat()
            
            # Inject timestamp for DB consistency (and for Resume restoration)
            parsed['timestamp'] = timestamp
            
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
                'note': '',
                'sample_id': '',
                'sample_label': '',
                'sample_ppm': '',
                'sample_peak_ppm': '',
            }
            self.recorded_data.append(export_row)
            self._last_measurement = export_row
            if self._sample_capture_active:
                if self._sample_peak_ppm is None or co2 > self._sample_peak_ppm:
                    self._sample_peak_ppm = co2
            
            # DB Insert (Async Worker)
            if self.db and self.session_id:
                self.save_reading_worker(self.session_id, parsed)
            
            chart.add_data(parsed)
            stats.add_reading(co2, record=parsed.get('record'))
            
            # Real-time Flux Calc
            self.flux_calc.add_point(time.time(), co2)
            res = self.flux_calc.calculate()
            stats.flux_slope = res.slope
            stats.flux_r2 = res.r_squared
            
            stats.record_count += 1
            stats.data_mode = rec_type  # Update mode indicator (M=Real-Time, R=Memory)
            stats.device_status = ""  # Clear warmup/zero status when data arrives
            
            # Use compact counter for memory dumps (R), individual logs for real-time (M)
            if rec_type == 'R':
                if not log.is_downloading:
                    log.start_download()
                log.log_download_record(plot, record, co2)
            else:
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
            # Log once at warmup start
            if not self._warmup_logged:
                log.log_info("EGM warming up - ready at ~55C (see status panel)")
                self._warmup_logged = True
            
        elif rec_type == 'Z':
            # Zero check in progress
            countdown = parsed.get('zero_countdown', 0)
            stats.device_status = f"ZERO CHECK: {countdown:.0f}/15s"
            stats.data_mode = ""  # Clear data mode during zero check
            # Log once at zero check start
            if not self._zero_logged:
                log.log_info("Zero checking in progress (15 seconds)")
                self._zero_logged = True
            
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
        # Debug log 
        log = self.query_one("#log", LogWidget)
        log.log_event(f"Probe type detected: {event.probe_type}", "warning")

    @on(Message)
    def handle_serial_error(self, event: Message) -> None:
        """Handle serial errors - log only, no notification."""
        if not isinstance(event, SerialError):
            return
        
        # Log the error but don't show annoying notification
        log = self.query_one("#log", LogWidget)
        log.log_error(event.message)
        stats = self.query_one("#stats", StatsWidget)
        stats.serial_errors += 1
        
        # If it's a device error, mark as disconnected
        if "device" in event.message.lower() or "disconnected" in event.message.lower():
            stats.is_connected = False

    async def action_quit_app(self) -> None:
        """Save work and quit the application."""
        # Immediate feedback that we're quitting
        log = self.query_one("#log", LogWidget)
        log.log_info("Saving and quitting...")
        stats = self.query_one("#stats", StatsWidget)
        stats.device_status = "QUITTING..."
        
        # Clear callbacks to prevent error messages during shutdown
        if self.serial:
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
                    # Get fieldnames from first record
                    fieldnames = list(self.recorded_data[0].keys())
                    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                    writer.writeheader()
                    writer.writerows(self.recorded_data)
            except Exception:
                pass
        
        # Exit the app
        self.app.exit()

    def action_clear(self) -> None:
        """Clear all data after confirmation."""
        def handle_clear_confirmation(confirmed: bool) -> None:
            if confirmed:
                self.query_one("#chart", CO2PlotWidget).clear_data()
                self.query_one("#stats", StatsWidget).clear_history()
                self.query_one("#log", LogWidget).clear()
                self.recorded_data.clear()
                self.flux_calc.clear()
                self._plot_base_times.clear()
                self._sample_capture_active = False
                self._sample_peak_ppm = None
                if self.static_sampling_mode:
                    self._reset_sample_cycle()
                if hasattr(self, '_last_dt_per_plot'):
                    self._last_dt_per_plot.clear()
                # Update legend to reflect cleared plots
                legend = self.query_one("#legend", ChannelLegend)
                chart = self.query_one("#chart", CO2PlotWidget)
                legend.set_plot_info(chart.filter_plot, chart.get_known_plots())
                self.app.notify("Data cleared", severity="information")
        
        self.app.push_screen(
            ConfirmScreen(
                title="Clear All Data?",
                message="This will clear all chart data, statistics, and logs.\nThis action cannot be undone."
            ),
            handle_clear_confirmation
        )


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
        """Open the Export Wizard."""
        if not self.recorded_data:
            self.notify("No data to export", severity="warning")
            return
            
        from src.tui.screens.export import ExportScreen
        self.app.push_screen(ExportScreen(self.recorded_data))

    def action_big_mode(self) -> None:
        """Toggle high-visibility field mode."""
        stats = self.query_one("#stats", StatsWidget)
        big_screen = BigModeScreen()
        big_screen.current_co2 = stats.current_co2
        big_screen.record_count = stats.record_count
        # Store reference so we can update it
        self._big_screen = big_screen
        self.app.push_screen(big_screen)

    def _save_event_row(
        self,
        row_type: str,
        note_text: str,
        sample_id: int | str = "",
        sample_label: str = "",
        sample_ppm: float | str = "",
        sample_peak_ppm: float | str = "",
    ) -> None:
        chart = self.query_one("#chart", CO2PlotWidget)
        stats = self.query_one("#stats", StatsWidget)
        plot = chart.current_plot
        dt_val = chart.current_dt
        current_ppm = stats.current_co2 if stats.current_co2 is not None else ""

        event_row = {
            'timestamp': datetime.datetime.now().isoformat(),
            'type': row_type,
            'plot': plot,
            'record': stats.hw_record or '',
            'day': '',
            'month': '',
            'hour': '',
            'minute': '',
            'co2_ppm': current_ppm,
            'h2o_mb': '',
            'rht_c': '',
            'par': '',
            'rh_pct': '',
            'temp_c': '',
            'dc_ppm': '',
            'dt_s': dt_val,
            'sr_rate': '',
            'atmp_mb': '',
            'probe_type': '',
            'note': note_text,
            'sample_id': sample_id,
            'sample_label': sample_label,
            'sample_ppm': sample_ppm,
            'sample_peak_ppm': sample_peak_ppm,
        }
        self.recorded_data.append(event_row)

        if current_ppm != "":
            chart.add_marker(plot, dt_val, float(current_ppm), note_text)

    async def action_add_note(self) -> None:
        """Add a note, or advance static sampling workflow when static mode is enabled."""
        if not self.static_sampling_mode:
            def handle_note(note: str | None) -> None:
                if not note:
                    return
                self._save_event_row("NOTE", note.strip())
                self.query_one("#log", LogWidget).log_info(f"NOTE: {note}")
                self._write_raw_line("NOTE", note)

            self.app.push_screen(NoteInputScreen(), handle_note)
            return

        log = self.query_one("#log", LogWidget)
        stats = self.query_one("#stats", StatsWidget)

        if self._sample_flow_step == self.SAMPLE_STEP_IDLE:
            self._reset_sample_cycle()
            return

        if self._sample_flow_step == self.SAMPLE_STEP_INJECT:
            self._sample_capture_active = True
            self._sample_peak_ppm = stats.current_co2 if stats.current_co2 is not None else None
            log.log_info("STATIC: Injection acknowledged; tracking peak ppm.")
            self._write_raw_line("SAMPLE", "Injection acknowledged; peak tracking started")
            self._set_sample_step(self.SAMPLE_STEP_SETTLE)
            return

        if self._sample_flow_step == self.SAMPLE_STEP_SETTLE:
            def handle_sample_label(note: str | None) -> None:
                if note is None:
                    log.log_info("STATIC: Capture cancelled. Still waiting to capture settled value.")
                    return

                settled_ppm = stats.current_co2 if stats.current_co2 is not None else ""
                self._sample_counter += 1
                sample_label = note.strip() or f"Sample {self._sample_counter}"
                sample_id = self._sample_counter
                peak_ppm = self._sample_peak_ppm if self._sample_peak_ppm is not None else settled_ppm

                self._save_event_row(
                    "SAMPLE",
                    f"[{sample_label}]",
                    sample_id=sample_id,
                    sample_label=sample_label,
                    sample_ppm=settled_ppm,
                    sample_peak_ppm=peak_ppm,
                )

                settled_disp = f"{settled_ppm:.0f}" if isinstance(settled_ppm, (int, float)) else "n/a"
                peak_disp = f"{peak_ppm:.0f}" if isinstance(peak_ppm, (int, float)) else "n/a"
                log.log_success(
                    f"SAMPLE #{sample_id}: {sample_label} settled={settled_disp} ppm peak={peak_disp} ppm"
                )
                self._write_raw_line("SAMPLE", f"{sample_label}; settled={settled_disp}; peak={peak_disp}")

                self._sample_capture_active = False
                self._sample_peak_ppm = None
                self._set_sample_step(self.SAMPLE_STEP_FLUSH)

            self.app.push_screen(
                NoteInputScreen(
                    title="Capture Settled Sample",
                    placeholder="Sample label (optional)...",
                    save_label="Capture",
                ),
                handle_sample_label,
            )
            return

        if self._sample_flow_step == self.SAMPLE_STEP_FLUSH:
            log.log_info("STATIC: Ambient air flush confirmed.")
            self._write_raw_line("SAMPLE", "Ambient air flush confirmed")
            self._reset_sample_cycle()
            return

    def action_toggle_static_mode(self) -> None:
        """Toggle static sampling mode."""
        stats = self.query_one("#stats", StatsWidget)
        self.static_sampling_mode = not self.static_sampling_mode
        log = self.query_one("#log", LogWidget)
        if self.static_sampling_mode:
            stats.static_sampling_mode = True
            self._reset_sample_cycle()
            log.log_info("Static sampling mode ON")
        else:
            stats.static_sampling_mode = False
            stats.static_sampling_step = ""
            self._sample_flow_step = self.SAMPLE_STEP_IDLE
            self._sample_capture_active = False
            self._sample_peak_ppm = None
            log.log_info("Static sampling mode OFF")

    def action_reset_static_cycle(self) -> None:
        """Reset the static sampling step sequence."""
        if not self.static_sampling_mode:
            return
        self.query_one("#log", LogWidget).log_info("STATIC: Cycle reset.")
        self._reset_sample_cycle()

    @work(thread=True)
    def save_reading_worker(self, session_id: int, data: dict) -> None:
        """Background worker to save data to DB without blocking UI."""
        try:
            if self.db:
                self.db.insert_reading(session_id, data)
        except Exception:
            pass

    # Channel selection actions (Dynamic)
    def action_select_slot(self, slot_idx: str) -> None:
        """Select a channel by its slot index (1-9)."""
        chart = self.query_one("#chart", CO2PlotWidget)
        legend = self.query_one("#legend", ChannelLegend)
        
        # Chart finds the key for this slot based on current config (SRC/CPY/etc)
        active_key = chart.set_active_by_slot_index(slot_idx)
        
        if active_key:
            legend.set_active(active_key)

    def action_select_atmp(self) -> None:
        self._select_channel("atmp")

    def action_select_dt(self) -> None:
        self._select_channel("dt")

    # Span control actions


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

    def action_toggle_cursor(self) -> None:
        """Toggle data cursor mode."""
        chart = self.query_one("#chart", CO2PlotWidget)
        chart.toggle_cursor()

    def action_cursor_left(self) -> None:
        """Move cursor left."""
        chart = self.query_one("#chart", CO2PlotWidget)
        chart.cursor_left()

    def action_cursor_right(self) -> None:
        """Move cursor right."""
        chart = self.query_one("#chart", CO2PlotWidget)
        chart.cursor_right()

    def action_cursor_home(self) -> None:
        """Move cursor to start."""
        chart = self.query_one("#chart", CO2PlotWidget)
        chart.cursor_home()

    def action_cursor_end(self) -> None:
        """Move cursor to end."""
        chart = self.query_one("#chart", CO2PlotWidget)
        chart.cursor_end()


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
