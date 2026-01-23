import csv
import os
from datetime import datetime, date
from typing import List, Set, Optional

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.screen import ModalScreen
from textual.widgets import Label, Static, Input, SelectionList
from textual.reactive import reactive

from src.tui.widgets.calendar import CalendarWidget


class ExportScreen(ModalScreen):
    """
    Keyboard-driven Export Menu (Magit-style).
    
    Modes:
    - MENU: Main menu (e, p, d, f, q)
    - CALENDAR: Date selection (Arrows, Space, Enter)
    - PLOT: Plot selection (1-9, a, n, Enter)
    - FILENAME: Editing filename (Input widget focused)
    """

    CSS = """
    ExportScreen {
        align: center middle;
        background: rgba(0,0,0,0.8);
    }

    #menu-container {
        width: 95;
        height: auto;
        border: rounded $accent;
        background: $surface;
        padding: 1 2;
    }

    .menu-header {
        text-style: bold;
        color: $accent;
        border-bottom: solid $primary;
        margin-bottom: 1;
        padding-bottom: 1;
    }
    
    .menu-section {
        margin-top: 1;
        color: $text-muted;
        text-style: bold;
    }

    .menu-item {
        color: $text;
        padding-left: 2;
    }

    /* Sub-mode container styles */
    #calendar-container, #plot-container, #filename-input, #location-input, #date-input {
        display: none;
        margin-top: 1;
        border-top: solid $primary;
        padding-top: 1;
    }
    
    #plot-container {
        height: 10;
        background: $surface-darken-1;
        border: rounded $primary;
    }
    
    SelectionList {
        height: auto;
        border: none;
    }

    /* Active states handle visibility */
    .dimmed { opacity: 0.5; }
    """
    
    # Selection State
    selected_plots: Set[int] = set()
    selected_dates: Set[date] = set()
    filename: str = ""
    location: str = ""
    
    # UI State
    mode = reactive("MENU")  # MENU, DATE_MENU, CALENDAR, PLOT, FILENAME, LOCATION, DATE_INPUT
    date_input_mode = "RANGE" # RANGE, BEFORE, AFTER used when in DATE_INPUT mode

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
            except:
                pass
                
        # Defaults
        self.selected_plots = set(self.available_plots)
        self.filename = f"egm4_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self.location = os.getcwd()

    def compose(self) -> ComposeResult:
        with Container(id="menu-container"):
            yield Static("Export Menu", classes="menu-header")
            
            # Main Menu Area
            with Vertical(id="main-menu"):
                yield Static("Actions", classes="menu-section")
                yield Static("  [b $accent]e[/]   Export Now", classes="menu-item")
                yield Static("  [b $accent]q[/]   Cancel", classes="menu-item")
                
                yield Static("Filters", classes="menu-section")
                yield Static("", id="plot-status", classes="menu-item")
                yield Static("", id="date-status", classes="menu-item")
                
                yield Static("Configuration", classes="menu-section")
                yield Static("", id="file-status", classes="menu-item")
                yield Static("", id="location-status", classes="menu-item")
            
            # Sub-mode areas
            with Vertical(id="calendar-container"):
                yield CalendarWidget(id="calendar")
            
            with Vertical(id="plot-container"):
                yield SelectionList(id="plot-list")
                
            yield Input(id="filename-input")
            yield Input(id="location-input")
            yield Input(id="date-input")
            
            # Helper text
            yield Static("", id="helper-text", classes="menu-item dimmed")

    def on_mount(self) -> None:
        # Initialize Calendar
        cal = self.query_one("#calendar", CalendarWidget)
        cal.set_data_dates(self.available_dates)
        
        # Initialize Plot List
        plot_list = self.query_one("#plot-list", SelectionList)
        for p in self.available_plots:
            plot_list.add_option((f"Plot {p}", p, True))
            
        self.refresh_menu()

    def refresh_menu(self) -> None:
        """Update menu text based on state."""
        # Update Status Lines
        self._update_status_lines()
        
        # Visibility Logic
        widgets = {
            "menu": self.query_one("#main-menu"),
            "cal": self.query_one("#calendar-container"),
            "plot": self.query_one("#plot-container"),
            "file": self.query_one("#filename-input"),
            "loc": self.query_one("#location-input"),
            "date_in": self.query_one("#date-input"),
        }
        helper = self.query_one("#helper-text", Static)
        
        # Reset all
        widgets["menu"].remove_class("dimmed")
        for w in list(widgets.values())[1:]: w.display = False
        helper.update("")
        
        if self.mode == "MENU":
            helper.update("\n[dim]Select an option to configure export parameters.[/dim]")
            
        elif self.mode == "DATE_MENU":
            widgets["menu"].add_class("dimmed")
            # Show options in helper
            helper.update("\n[b]Date Menu:[/b]  [b $accent]c[/] Calendar  [b $accent]r[/] Range  [b $accent]b[/] Before  [b $accent]a[/] After  [b $accent]q[/] Back")
            
        elif self.mode == "CALENDAR":
            widgets["menu"].add_class("dimmed")
            widgets["cal"].display = True
            self.query_one("#calendar").focus()
            helper.update("\n[dim][b]ARROWS[/]: Move  [b]SPACE[/]: Toggle  [b]d[/]: Done[/dim]")
            
        elif self.mode == "PLOT":
            widgets["menu"].add_class("dimmed")
            widgets["plot"].display = True
            self.query_one("#plot-list").focus()
            helper.update("\n[dim][b]SPACE[/]: Toggle  [b $accent]a[/]: All  [b $accent]n[/]: None  [b]p[/]: Done[/dim]")
            
        elif self.mode == "FILENAME":
            widgets["menu"].add_class("dimmed")
            widgets["file"].display = True
            widgets["file"].value = self.filename
            widgets["file"].focus()
            helper.update("\n[dim]Enter filename. [b]ENTER[/]: Save  [b]ESC[/]: Cancel[/dim]")

        elif self.mode == "LOCATION":
            widgets["menu"].add_class("dimmed")
            widgets["loc"].display = True
            widgets["loc"].value = self.location
            widgets["loc"].focus()
            helper.update("\n[dim]Enter directory path. [b]ENTER[/]: Save  [b]ESC[/]: Cancel[/dim]")
            
        elif self.mode == "DATE_INPUT":
            widgets["menu"].add_class("dimmed")
            widgets["date_in"].display = True
            widgets["date_in"].focus()
            prefix = ""
            if self.date_input_mode == "BEFORE": prefix = "<"
            elif self.date_input_mode == "AFTER": prefix = ">"
            helper.update(f"\n[dim]Enter date ({prefix}YYYY-MM-DD). [b]ENTER[/]: Save  [b]ESC[/]: Cancel[/dim]")

    def _update_status_lines(self):
        # Plots
        if len(self.selected_plots) == len(self.available_plots): p_str = "ALL"
        elif not self.selected_plots: p_str = "NONE"
        else: p_str = ",".join(str(p) for p in sorted(self.selected_plots))
        self.query_one("#plot-status", Static).update(f"  [b $accent]p[/]   Plots: [b]{p_str}[/b]")
        
        # Dates
        if not self.selected_dates: d_str = "ALL"
        else: d_str = f"{len(self.selected_dates)} selected"
        self.query_one("#date-status", Static).update(f"  [b $accent]d[/]   Dates: [b]{d_str}[/b]")
        
        # File & Location
        self.query_one("#file-status", Static).update(f"  [b $accent]f[/]   File:  [b]{self.filename}[/b]")
        self.query_one("#location-status", Static).update(f"  [b $accent]l[/]   Loc:   [b]{self.location}[/b]")

    def on_key(self, event) -> None:
        """Handle global keys."""
        if self.mode == "MENU":
            if event.key in ("q", "escape"): self.dismiss()
            elif event.key == "e": self.export_data()
            elif event.key == "p": self.mode = "PLOT"; self.refresh_menu()
            elif event.key == "d": self.mode = "DATE_MENU"; self.refresh_menu()
            elif event.key == "f": self.mode = "FILENAME"; self.refresh_menu()
            elif event.key == "l": self.mode = "LOCATION"; self.refresh_menu()
                
        elif self.mode == "DATE_MENU":
            if event.key in ("q", "escape", "d"): self.mode = "MENU"; self.refresh_menu()
            elif event.key == "c": self.mode = "CALENDAR"; self.refresh_menu()
            elif event.key == "r": self._start_date_input("RANGE")
            elif event.key == "b": self._start_date_input("BEFORE")
            elif event.key == "a": self._start_date_input("AFTER")

        elif self.mode == "PLOT":
            if event.key in ("enter", "escape", "p"):
                # Sync & Exit
                self.selected_plots = set(self.query_one("#plot-list", SelectionList).selected)
                self.mode = "MENU"; self.refresh_menu()
            elif event.key == "a": self.query_one("#plot-list", SelectionList).select_all()
            elif event.key == "n": self.query_one("#plot-list", SelectionList).deselect_all()
            
        elif self.mode == "CALENDAR":
             if event.key == "d": # Toggle off
                 self.mode = "MENU"; self.refresh_menu()

    def _start_date_input(self, mode: str):
        self.date_input_mode = mode
        inp = self.query_one("#date-input", Input)
        inp.value = ""
        placeholder = "YYYY-MM-DD..YYYY-MM-DD" if mode == "RANGE" else "YYYY-MM-DD"
        inp.placeholder = placeholder
        self.mode = "DATE_INPUT"
        self.refresh_menu()

    @on(CalendarWidget.Submitted)
    def handle_calendar_done(self, message: CalendarWidget.Submitted):
        self.selected_dates = message.selected_dates
        self.mode = "MENU"
        self.refresh_menu()
        self.focus() # Catch keys

    @on(Input.Submitted)
    def handle_input_done(self, event: Input.Submitted):
        if not event.value.strip():
            self.mode = "MENU"; self.refresh_menu(); self.focus()
            return

        if event.input.id == "filename-input":
            self.filename = event.value.strip()
        elif event.input.id == "location-input":
            self.location = event.value.strip()
        elif event.input.id == "date-input":
            self._parse_date_input(event.value.strip())
            
        self.mode = "MENU"
        self.refresh_menu()
        self.focus()

    def _parse_date_input(self, text: str):
        # Implement parsing logic based on mode or raw text
        # Simple parsing for now
        dates_found = set()
        try:
            if ".." in text:
                start_s, end_s = text.split("..")
                start = date.fromisoformat(start_s.strip())
                end = date.fromisoformat(end_s.strip())
                curr = start
                while curr <= end:
                    dates_found.add(curr)
                    curr += timedelta(days=1)
            elif text.startswith("<"):
                limit = date.fromisoformat(text[1:].strip())
                for d in self.available_dates:
                    if d < limit: dates_found.add(d)
            elif text.startswith(">"):
                limit = date.fromisoformat(text[1:].strip())
                for d in self.available_dates:
                    if d > limit: dates_found.add(d)
            else:
                # Single date or special format
                d = date.fromisoformat(text.strip())
                dates_found.add(d)
                
            # Intersect with available? Or just set?
            # Ideally user wants to select from available.
            valid_dates = dates_found.intersection(self.available_dates)
            if valid_dates:
                self.selected_dates = valid_dates
                self.query_one("#calendar", CalendarWidget).selected_dates = valid_dates
                self.query_one("#calendar", CalendarWidget).refresh_calendar()
                self.app.notify(f"Selected {len(valid_dates)} dates")
            else:
                self.app.notify("No records match that date range", severity="warning")
                
        except Exception:
            self.app.notify("Invalid date format. Use YYYY-MM-DD", severity="error")

    def export_data(self) -> None:
        # Update path logic to use location
        filtered_data = [] # ... same filtering ...
        for row in self.recorded_data:
            if row.get('plot') not in self.selected_plots: continue
            if self.selected_dates:
                try:
                    ts = row.get('timestamp')
                    if isinstance(ts, str):
                        row_date = datetime.fromisoformat(ts).date()
                        if row_date not in self.selected_dates: continue
                except: continue
            filtered_data.append(row)
            
        if not filtered_data:
            self.app.notify("No records match configuration!", severity="warning")
            return
            
        try:
            full_path = os.path.join(self.location, self.filename)
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(full_path)), exist_ok=True)
            
            headers = [
                'timestamp', 'type', 'plot', 'record',
                'day', 'month', 'hour', 'minute',
                'co2_ppm', 'h2o_mb', 'temp_c', 'atmp_mb',
                'rh_pct', 'par', 'probe_type',
                'dc_ppm', 'dt_s', 'sr_rate'
            ]
            
            with open(full_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(filtered_data)
                
            self.app.notify(f"Exported {len(filtered_data)} records", severity="information")
            self.dismiss()
            
        except Exception as e:
            self.app.notify(f"Failed: {e}", severity="error")
