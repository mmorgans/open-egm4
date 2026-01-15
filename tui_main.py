#!/usr/bin/env python3
"""
Open EGM-4 TUI - Terminal User Interface
A clean, terminal-based interface for the EGM-4 Gas Monitor

Modes:
- Live Monitoring: Watch real-time CO2 readings
- Data Dump: Download stored records from device memory
"""

import sys
import os
import time
import datetime
import csv
import threading
import statistics
from collections import deque

from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich import box
from serial.tools import list_ports

from src.egm_interface import EGM4Serial


class EGM4TUI:
    def __init__(self):
        self.console = Console()
        self.serial = EGM4Serial()
        self.serial.data_callback = self.on_data_received
        self.serial.error_callback = self.on_error
        
        self.is_connected = False
        self.current_port = None
        self.terminal_lines = deque(maxlen=15)
        self.data_lock = threading.Lock()
        self.recorded_data = []
        self.latest_co2 = None
        self.record_count = 0
        self.dump_complete = False
        self.last_activity = None
        
        # Phase 1 features
        self.raw_log_file = None
        self.co2_history = deque(maxlen=40)  # For sparkline
        self.session_notes = ""  # User metadata
        
    def on_data_received(self, raw_line, parsed_data):
        """Callback when serial data is received"""
        # Auto-save to raw log (crash-proof backup)
        if self.raw_log_file:
            try:
                self.raw_log_file.write(raw_line + '\n')
                self.raw_log_file.flush()  # Immediate write
            except:
                pass
        
        with self.data_lock:
            timestamp = datetime.datetime.now()
            self.last_activity = timestamp
            
            # Format display based on record type
            rec_type = parsed_data.get('type', 'unknown')
            
            if rec_type == 'R':
                co2 = parsed_data.get('co2_ppm', 0)
                record_num = parsed_data.get('record', 0)
                plot_num = parsed_data.get('plot', 0)
                self.latest_co2 = co2
                self.co2_history.append(co2)  # For sparkline
                self.record_count += 1
                display_msg = f"[P{plot_num:02d}-R{record_num:04d}] CO2: {co2} ppm"
            elif rec_type == 'B':
                co2 = parsed_data.get('co2_ppm', 0)
                self.latest_co2 = co2
                display_msg = f"[Startup] Device: EGM4, CO2: {co2:.1f}"
            elif rec_type == 'Z':
                self.dump_complete = True
                display_msg = "━━━ DOWNLOAD COMPLETE ━━━"
                # Audible beep on complete!
                print('\a', end='', flush=True)
            else:
                display_msg = raw_line[:50]
            
            self.terminal_lines.append((timestamp, display_msg))
            self.recorded_data.append([timestamp.isoformat(), raw_line])
    
    def on_error(self, msg):
        """Callback for serial errors"""
        with self.data_lock:
            self.terminal_lines.append((datetime.datetime.now(), f"⚠ ERROR: {msg}"))
    
    def list_ports(self):
        """Get list of available serial ports"""
        ports = list_ports.comports()
        return [(p.device, p.description) for p in ports]
    
    def select_port(self):
        """Interactive port selection"""
        ports = self.list_ports()
        
        if not ports:
            self.console.print("[red]✗ No serial ports found![/red]")
            return None
        
        self.console.print("\n[bold cyan]📡 Available Serial Ports:[/bold cyan]\n")
        for i, (device, desc) in enumerate(ports, 1):
            # Highlight USB serial devices
            if 'usb' in device.lower() or 'serial' in desc.lower():
                self.console.print(f"  [green]{i}.[/green] [bold]{device}[/bold] - {desc}")
            else:
                self.console.print(f"  [dim]{i}. {device} - {desc}[/dim]")
        
        choice = Prompt.ask(
            "\n[cyan]Select port number[/cyan]",
            choices=[str(i) for i in range(1, len(ports) + 1)]
        )
        
        return ports[int(choice) - 1][0]
    
    def connect(self, port):
        """Connect to serial port"""
        if self.serial.connect(port):
            self.is_connected = True
            self.current_port = port
            self.last_activity = datetime.datetime.now()
            
            # Open raw log file for crash-proof backup
            log_filename = f"raw_dump_{datetime.datetime.now().strftime('%Y-%m-%d')}.log"
            try:
                self.raw_log_file = open(log_filename, 'a')
                self.raw_log_file.write(f"\n--- Session started {datetime.datetime.now().isoformat()} ---\n")
            except Exception as e:
                pass  # Non-critical
            
            with self.data_lock:
                self.terminal_lines.append(
                    (datetime.datetime.now(), f"✓ Connected to {port}")
                )
            return True
        return False
    
    def disconnect(self):
        """Disconnect from serial port"""
        self.serial.disconnect()
        self.is_connected = False
        
        # Close raw log file
        if self.raw_log_file:
            try:
                self.raw_log_file.write(f"--- Session ended {datetime.datetime.now().isoformat()} ---\n")
                self.raw_log_file.close()
            except:
                pass
            self.raw_log_file = None
        
        with self.data_lock:
            self.terminal_lines.append(
                (datetime.datetime.now(), "✓ Disconnected")
            )
    
    def render_sparkline(self, width=20):
        """Render ASCII sparkline from co2_history"""
        if len(self.co2_history) < 2:
            return "[dim]── no data ──[/dim]"
        
        values = list(self.co2_history)
        min_val = min(values)
        max_val = max(values)
        
        # Show flat line if no variation
        if max_val == min_val:
            return "▄" * min(len(values), width)
        
        # Unicode block characters for sparkline (full height chars for visibility)
        blocks = "▁▂▃▄▅▆▇█"
        
        # Sample values to fit width
        result = []
        step = max(1, len(values) // width)
        for i in range(0, min(len(values), width * step), step):
            v = values[i]
            normalized = (v - min_val) / (max_val - min_val)
            idx = int(normalized * (len(blocks) - 1))
            result.append(blocks[idx])
        
        return '[green]' + ''.join(result) + '[/green]'
    
    def calculate_stability(self):
        """Calculate signal stability from recent CO2 readings"""
        if len(self.co2_history) < 5:
            return None, "WAITING"
        
        recent = list(self.co2_history)[-10:]
        try:
            stdev = statistics.stdev(recent)
            if stdev < 5:
                return stdev, "STABLE"
            elif stdev < 20:
                return stdev, "VARIABLE"
            else:
                return stdev, "NOISY"
        except:
            return None, "ERROR"
    
    def export_csv(self):
        """Export recorded data to CSV with parsed columns"""
        if not self.recorded_data:
            return None
        
        filename = f"egm4_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header row with all parsed fields
            writer.writerow([
                "PC_Timestamp",
                "Type",
                "Plot",
                "Record",
                "Day",
                "Month", 
                "Hour",
                "Minute",
                "CO2_ppm",
                "H2O_Ref",
                "RHT",
                "Sensor_A",
                "Sensor_B",
                "Sensor_C",
                "Sensor_D",
                "Pressure_mb",
                "Probe_Type",
                "User_Notes",
                "Raw_Data"
            ])
            
            for timestamp, raw_line in self.recorded_data:
                # Skip non-R records in parsed output
                if not raw_line.startswith('R') or len(raw_line) < 60:
                    # Write B/Z records with minimal parsing
                    if raw_line.startswith('B'):
                        writer.writerow([timestamp, 'B', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', self.session_notes, raw_line])
                    elif raw_line.startswith('Z'):
                        writer.writerow([timestamp, 'Z', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', self.session_notes, raw_line])
                    continue
                
                try:
                    # Parse R-type record (60 characters)
                    rec_type = raw_line[0]
                    plot = int(raw_line[1:3])
                    record = int(raw_line[3:7])
                    day = int(raw_line[7:9])
                    month = int(raw_line[9:11])
                    hour = int(raw_line[11:13])
                    minute = int(raw_line[13:15])
                    co2_ppm = int(raw_line[15:20])
                    h2o_ref = int(raw_line[20:25]) if len(raw_line) > 25 else ''
                    rht = int(raw_line[25:30]) if len(raw_line) > 30 else ''
                    sensor_a = int(raw_line[30:34]) if len(raw_line) > 34 else ''
                    sensor_b = int(raw_line[34:38]) if len(raw_line) > 38 else ''
                    sensor_c = int(raw_line[38:42]) if len(raw_line) > 42 else ''
                    sensor_d = int(raw_line[42:46]) if len(raw_line) > 46 else ''
                    pressure = int(raw_line[54:58]) if len(raw_line) > 58 else ''
                    probe_type = int(raw_line[58:60]) if len(raw_line) >= 60 else ''
                    
                    writer.writerow([
                        timestamp,
                        rec_type,
                        plot,
                        record,
                        day,
                        month,
                        hour,
                        minute,
                        co2_ppm,
                        h2o_ref,
                        rht,
                        sensor_a,
                        sensor_b,
                        sensor_c,
                        sensor_d,
                        pressure,
                        probe_type,
                        self.session_notes,
                        raw_line
                    ])
                except (ValueError, IndexError) as e:
                    # If parsing fails, write raw line
                    writer.writerow([timestamp, '?', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', raw_line])
        
        return filename
    
    def build_layout(self):
        """Build the TUI layout"""
        layout = Layout()
        
        # Header, main content, footer
        layout.split_column(
            Layout(name="header", size=5),
            Layout(name="main"),
            Layout(name="footer", size=4)
        )
        
        # Split main into terminal and stats
        layout["main"].split_row(
            Layout(name="terminal", ratio=3),
            Layout(name="stats", ratio=1)
        )
        
        # === HEADER ===
        # Traffic light connection indicator with timeout detection
        with self.data_lock:
            now = datetime.datetime.now()
            if not self.is_connected:
                status = "[red][ ] DISCONNECTED[/red]"
            elif self.last_activity and (now - self.last_activity).total_seconds() > 2:
                status = "[yellow][~] IDLE[/yellow]"
            else:
                status = "[green][*] ACTIVE[/green]"
        
        port_info = f" → {self.current_port}" if self.current_port else ""
        
        header_table = Table(show_header=False, box=None, padding=0)
        header_table.add_column(ratio=1)
        header_table.add_column(ratio=1, justify="right")
        header_table.add_row(
            "[bold cyan]Open EGM-4 Interface[/bold cyan]",
            f"{status}{port_info}"
        )
        header_table.add_row(
            f"[dim]Records: {self.record_count}[/dim]",
            f"[dim]{datetime.datetime.now().strftime('%H:%M:%S')}[/dim]"
        )
        
        layout["header"].update(Panel(header_table, border_style="cyan"))
        
        # === TERMINAL ===
        with self.data_lock:
            terminal_table = Table(
                show_header=True,
                header_style="bold",
                box=box.SIMPLE,
                padding=(0, 1),
                expand=True
            )
            terminal_table.add_column("Time", style="dim", width=10)
            terminal_table.add_column("Data", ratio=1, overflow="fold")
            
            for timestamp, line in list(self.terminal_lines):
                terminal_table.add_row(
                    timestamp.strftime("%H:%M:%S"),
                    line
                )
        
        layout["terminal"].update(Panel(
            terminal_table, 
            title="[bold]Data Stream[/bold]", 
            border_style="blue"
        ))
        
        # === STATS ===
        with self.data_lock:
            stats = Text()
            
            # CO2 reading
            stats.append("━━━ CO₂ Level ━━━\n", style="cyan")
            
            if self.latest_co2 is not None:
                co2 = self.latest_co2
                if co2 < 400:
                    color = "green"
                elif co2 < 1000:
                    color = "yellow"
                else:
                    color = "red"
                stats.append(f"  {co2:.0f} ", style=f"bold {color}")
                stats.append("ppm\n\n", style=color)
            else:
                stats.append("  --- ppm\n\n", style="dim")
            
            # Sparkline graph
            stats.append("━━━ Trend ━━━\n", style="cyan")
            sparkline = self.render_sparkline(15)
            stats.append(f"  {sparkline}\n\n", style="green")
            
            # Stability indicator
            stdev, stability = self.calculate_stability()
            stats.append("━━━ Signal ━━━\n", style="cyan")
            if stability == "STABLE":
                stats.append(f"  [+] {stability}\n", style="green")
            elif stability == "VARIABLE":
                stats.append(f"  [~] {stability}\n", style="yellow")
            elif stability == "NOISY":
                stats.append(f"  [!] {stability}\n", style="red")
            else:
                stats.append(f"  [ ] {stability}\n", style="dim")
            
            if stdev is not None:
                stats.append(f"  (σ={stdev:.1f})\n", style="dim")
            
            # Session notes if set
            if self.session_notes:
                stats.append(f"\n[dim]Note: {self.session_notes[:15]}...[/dim]\n")
        
        layout["stats"].update(Panel(stats, title="[bold]Status[/bold]", border_style="green"))
        
        # === FOOTER ===
        footer = Text()
        with self.data_lock:
            if self.dump_complete:
                footer.append("  [+] ", style="green")
                footer.append("DOWNLOAD COMPLETE", style="bold green")
                footer.append(f" - {self.record_count} records received\n", style="green")
                footer.append("  Press Ctrl+C to export and exit", style="dim")
            else:
                footer.append("  Press ", style="dim")
                footer.append("Ctrl+C", style="bold cyan")
                footer.append(" to stop and export data\n", style="dim")
                if self.record_count > 0:
                    footer.append(f"  Receiving data... ({self.record_count} records)", style="yellow")
                else:
                    footer.append("  Waiting for data from EGM-4...", style="dim")
        
        layout["footer"].update(Panel(footer, border_style="dim" if not self.dump_complete else "green"))
        
        return layout
    
    def monitor_mode(self):
        """Live monitoring mode - displays real-time data"""
        self.console.print("\n[green]✓ Starting live monitoring...[/green]")
        self.console.print("[dim]The EGM-4 will send data when in Measurement Mode (1REC)[/dim]")
        self.console.print("[dim]Press Ctrl+C to stop[/dim]\n")
        
        time.sleep(1)
        
        try:
            with Live(self.build_layout(), console=self.console, refresh_per_second=4) as live:
                while True:
                    time.sleep(0.25)
                    live.update(self.build_layout())
        except KeyboardInterrupt:
            pass
    
    def run(self):
        """Main TUI entry point"""
        self.console.clear()
        self.console.print(Panel(
            "[bold cyan]Open EGM-4 Terminal Interface[/bold cyan]\n\n"
            "This tool connects to your PP Systems EGM-4 Environmental Gas Monitor\n"
            "and displays CO2 readings in real-time.\n\n"
            "[dim]Serial: 9600 baud, 8N2[/dim]",
            title="Welcome",
            border_style="cyan"
        ))
        
        # Port selection
        port = self.select_port()
        if not port:
            return
        
        # Connect
        self.console.print(f"\n[yellow]⏳ Connecting to {port}...[/yellow]")
        if not self.connect(port):
            self.console.print("[red]✗ Connection failed![/red]")
            return
        
        self.console.print("[green]✓ Connected successfully![/green]\n")
        
        # Show instructions
        self.console.print(Panel(
            "[bold]To see data:[/bold]\n\n"
            "1. On the EGM-4, press [cyan]4[/cyan] (4DMP - Data Dump)\n"
            "2. Then press [cyan]2[/cyan] (Data Dump)\n"
            "3. Press any key on EGM-4 to send data\n\n"
            "[bold]Or for live readings:[/bold]\n\n"
            "1. On the EGM-4, press [cyan]1[/cyan] (1REC - Measurement Mode)\n"
            "2. Data will stream as measurements are taken",
            title="EGM-4 Instructions",
            border_style="yellow"
        ))
        
        # Session notes prompt (optional metadata)
        notes = Prompt.ask(
            "\n[cyan]Session notes[/cyan] [dim](optional, press Enter to skip)[/dim]",
            default=""
        )
        self.session_notes = notes.strip()
        if self.session_notes:
            self.console.print(f"[dim]Notes set: {self.session_notes}[/dim]")
        
        input("\n[Press Enter to start monitoring...]")
        
        # Run monitoring
        self.monitor_mode()
        
        # Cleanup
        self.console.print("\n[yellow]⏳ Stopping...[/yellow]")
        self.disconnect()
        
        # Offer export
        if self.recorded_data:
            self.console.print(f"\n[green]📊 Received {len(self.recorded_data)} data records[/green]")
            if Confirm.ask("Export to CSV?", default=True):
                filename = self.export_csv()
                self.console.print(f"[green]✓ Saved to {filename}[/green]")
        
        self.console.print("\n[cyan]Goodbye![/cyan]")


if __name__ == "__main__":
    tui = EGM4TUI()
    tui.run()
