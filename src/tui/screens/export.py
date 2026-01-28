import csv
import os
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Set

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, Static, SelectionList
from textual.reactive import reactive


class ExportScreen(ModalScreen):
    """
    Simple Export Screen with plot and date filtering.

    Keys:
    - e: Export with current filters
    - p: Toggle plot selection
    - d: Toggle date selection
    - q/ESC: Cancel
    """

    CSS = """
    ExportScreen {
        align: center middle;
        background: rgba(0,0,0,0.8);
    }

    #export-container {
        width: 70;
        height: auto;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }

    .export-header {
        text-style: bold;
        color: $accent;
        border-bottom: solid $primary;
        margin-bottom: 1;
        padding-bottom: 1;
    }

    .section {
        margin-top: 1;
        color: $text-muted;
        text-style: bold;
    }

    .info {
        color: $text;
        padding-left: 2;
        margin-bottom: 1;
    }

    #plot-container, #date-container {
        display: none;
        height: 12;
        background: $surface-darken-1;
        border: round $primary;
        margin-top: 1;
        padding: 1;
    }

    SelectionList {
        height: 100%;
        border: none;
    }

    #helper {
        margin-top: 1;
        padding-top: 1;
        border-top: solid $primary;
        color: $text-muted;
        text-align: center;
    }
    """

    # State
    selected_plots: Set[int] = set()
    selected_dates: Set[date] = set()
    mode = reactive("MENU")  # MENU, PLOT, DATE

    def __init__(self, recorded_data: List[dict]):
        super().__init__()
        self.recorded_data = recorded_data

        # Analyze data
        self.available_plots = sorted(list(set(r.get('plot', 0) for r in recorded_data)))
        self.available_dates = set()
        for r in recorded_data:
            try:
                ts = r.get('timestamp')
                if isinstance(ts, str):
                    dt = datetime.fromisoformat(ts).date()
                    self.available_dates.add(dt)
            except (ValueError, TypeError, AttributeError):
                pass

        # Defaults - select all
        self.selected_plots = set(self.available_plots)
        self.selected_dates = set()  # Empty = ALL

    def compose(self) -> ComposeResult:
        with Container(id="export-container"):
            yield Static("Export Data", classes="export-header")

            # Status area
            yield Static("", id="preview", classes="section")
            yield Static("", id="filename-info", classes="info")

            # Filters section
            yield Static("Filters", classes="section")
            yield Static("", id="plot-status", classes="info")
            yield Static("", id="date-status", classes="info")

            # Instructions section
            yield Static("Instructions", classes="section")
            yield Static("  Press [b]p[/] to select/deselect plots", classes="info")
            yield Static("  Press [b]d[/] to select/deselect dates", classes="info")
            yield Static("  Press [b]e[/] to export with current filters", classes="info")
            yield Static("  Press [b]q[/] to cancel", classes="info")

            # Selection containers
            with Vertical(id="plot-container"):
                yield SelectionList(id="plot-list")

            with Vertical(id="date-container"):
                yield SelectionList(id="date-list")

            # Helper text
            yield Static("", id="helper")


    def on_mount(self) -> None:
        # Initialize Plot List
        plot_list = self.query_one("#plot-list", SelectionList)
        for p in self.available_plots:
            plot_list.add_option((f"Plot {p}", p, True))

        # Initialize Date List
        date_list = self.query_one("#date-list", SelectionList)
        for d in sorted(self.available_dates):
            date_list.add_option((d.isoformat(), d, False))

        self.refresh_display()

    def refresh_display(self) -> None:
        """Update all display elements."""
        # Calculate filtered count
        filtered_count = sum(1 for row in self.recorded_data if self._should_include(row))
        total = len(self.recorded_data)

        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        plot_part = ""
        if len(self.selected_plots) == 1:
            plot_part = f"_plot{list(self.selected_plots)[0]}"
        elif len(self.selected_plots) != len(self.available_plots):
            plot_part = f"_{len(self.selected_plots)}plots"

        date_part = ""
        if self.selected_dates:
            if len(self.selected_dates) == 1:
                date_part = f"_{list(self.selected_dates)[0].isoformat()}"
            else:
                dates = sorted(self.selected_dates)
                date_part = f"_{dates[0].isoformat()}to{dates[-1].isoformat()}"

        filename = f"egm4{plot_part}{date_part}_{timestamp}.csv"

        # Update preview
        if filtered_count == total:
            preview = f"[bold cyan]{filtered_count}[/bold cyan] records (all data)"
        elif filtered_count == 0:
            preview = "[yellow]⚠ No records match filters[/yellow]"
        else:
            preview = f"[bold cyan]{filtered_count}[/bold cyan] of {total} records"
        self.query_one("#preview").update(preview)

        # Update filename info
        self.query_one("#filename-info").update(f"→ {filename}")

        # Update plot status
        if len(self.selected_plots) == len(self.available_plots):
            plot_str = "ALL"
        elif not self.selected_plots:
            plot_str = "[red]NONE[/red]"
        else:
            plot_str = ", ".join(str(p) for p in sorted(self.selected_plots))
        self.query_one("#plot-status").update(f"  [b]p[/]  Plots: {plot_str}")

        # Update date status
        if not self.selected_dates:
            date_str = "ALL"
        else:
            dates = sorted(self.selected_dates)
            if len(dates) == 1:
                date_str = dates[0].isoformat()
            elif len(dates) <= 3:
                date_str = ", ".join(d.isoformat() for d in dates)
            else:
                date_str = f"{dates[0].isoformat()}..{dates[-1].isoformat()} ({len(dates)} days)"
        self.query_one("#date-status").update(f"  [b]d[/]  Dates: {date_str}")

        # Update visibility and helper text
        plot_cont = self.query_one("#plot-container")
        date_cont = self.query_one("#date-container")
        helper = self.query_one("#helper")

        if self.mode == "MENU":
            plot_cont.display = False
            date_cont.display = False
            helper.update("[dim]Press [b]p[/b] for plots, [b]d[/b] for dates, [b]e[/b] to export[/dim]")
        elif self.mode == "PLOT":
            plot_cont.display = True
            date_cont.display = False
            self.query_one("#plot-list").focus()
            helper.update("[dim][b]SPACE[/b]: Toggle  [b]a[/b]: All  [b]n[/b]: None  [b]p[/b]/[b]ESC[/b]: Done[/dim]")
        elif self.mode == "DATE":
            plot_cont.display = False
            date_cont.display = True
            self.query_one("#date-list").focus()
            helper.update("[dim][b]SPACE[/b]: Toggle  [b]a[/b]: All  [b]n[/b]: None  [b]c[/b]: Clear  [b]d[/b]/[b]ESC[/b]: Done[/dim]")

    def _should_include(self, row: dict) -> bool:
        """Check if row matches current filters."""
        if row.get('plot') not in self.selected_plots:
            return False
        if self.selected_dates:
            try:
                ts = row.get('timestamp')
                if isinstance(ts, str):
                    row_date = datetime.fromisoformat(ts).date()
                    if row_date not in self.selected_dates:
                        return False
            except (ValueError, TypeError, AttributeError):
                return False
        return True

    def on_key(self, event) -> None:
        """Handle keyboard shortcuts."""
        if self.mode == "MENU":
            if event.key in ("q", "escape"):
                event.stop()  # Prevent propagation to parent (which would quit app)
                self.dismiss()
            elif event.key == "e":
                self.export_data()
            elif event.key == "p":
                self.mode = "PLOT"
                self.refresh_display()
            elif event.key == "d":
                self.mode = "DATE"
                self.refresh_display()

        elif self.mode == "PLOT":
            if event.key in ("p", "escape"):
                # Save and exit
                self.selected_plots = set(self.query_one("#plot-list", SelectionList).selected)
                self.mode = "MENU"
                self.refresh_display()
            elif event.key == "a":
                self.query_one("#plot-list", SelectionList).select_all()
            elif event.key == "n":
                self.query_one("#plot-list", SelectionList).deselect_all()

        elif self.mode == "DATE":
            if event.key in ("d", "escape"):
                # Save and exit
                selected = self.query_one("#date-list", SelectionList).selected
                self.selected_dates = set(selected) if selected else set()
                self.mode = "MENU"
                self.refresh_display()
            elif event.key == "a":
                self.query_one("#date-list", SelectionList).select_all()
            elif event.key == "n":
                self.query_one("#date-list", SelectionList).deselect_all()
            elif event.key == "c":
                # Clear all = show ALL dates
                self.query_one("#date-list", SelectionList).deselect_all()
                self.selected_dates = set()
                self.mode = "MENU"
                self.refresh_display()

    def export_data(self) -> None:
        """Export filtered data to CSV."""
        # Log export for debugging spurious export reports
        import logging
        logging.info(f"Export initiated: {len(self.recorded_data)} total records")
        
        # Filter data
        filtered_data = [row for row in self.recorded_data if self._should_include(row)]

        if not filtered_data:
            self.app.notify("No records match filters!", severity="warning")
            return

        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        plot_part = ""
        if len(self.selected_plots) == 1:
            plot_part = f"_plot{list(self.selected_plots)[0]}"
        elif len(self.selected_plots) != len(self.available_plots):
            plot_part = f"_{len(self.selected_plots)}plots"

        date_part = ""
        if self.selected_dates:
            if len(self.selected_dates) == 1:
                date_part = f"_{list(self.selected_dates)[0].isoformat()}"
            else:
                dates = sorted(self.selected_dates)
                date_part = f"_{dates[0].isoformat()}to{dates[-1].isoformat()}"

        filename = f"egm4{plot_part}{date_part}_{timestamp}.csv"
        
        # Determine export directory: Downloads folder or current directory
        downloads_dir = Path.home() / "Downloads"
        if downloads_dir.exists() and downloads_dir.is_dir():
            export_path = downloads_dir / filename
            location_note = "Downloads"
        else:
            export_path = Path(filename)
            location_note = "current directory"

        try:
            headers = [
                'timestamp', 'type', 'plot', 'record',
                'day', 'month', 'hour', 'minute',
                'co2_ppm', 'h2o_mb', 'temp_c', 'atmp_mb',
                'rh_pct', 'par', 'probe_type',
                'dc_ppm', 'dt_s', 'sr_rate'
            ]

            with open(export_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(filtered_data)

            # Success
            file_size = os.path.getsize(export_path)
            size_str = f"{file_size / 1024:.1f} KB" if file_size >= 1024 else f"{file_size} bytes"
            self.app.notify(
                f"✓ Exported {len(filtered_data)} records to {location_note}/{filename} ({size_str})",
                severity="information",
                timeout=5
            )
            self.dismiss()

        except Exception as e:
            self.app.notify(f"Export failed: {str(e)}", severity="error", timeout=10)
