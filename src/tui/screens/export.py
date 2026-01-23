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
        border: thick $accent;
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

    .key {
        color: $secondary;
        text-style: bold;
    }
    
    .value {
        color: $primary;
        text-style: bold;
    }
    
    .description {
        color: $text;
    }

    #calendar-container {
        display: none;
        margin-top: 1;
        border-top: solid $primary;
        padding-top: 1;
    }
    
    .mode-active #calendar-container {
        display: block;
    }
    
    #plot-container {
        display: none;
        height: 10;
        border: solid $primary;
        margin-top: 1;
        background: $surface-darken-1;
    }
    
    SelectionList {
        height: auto;
        border: none;
    }
    
    /* When in sub-mode, dim the main menu */
    .dimmed {
        opacity: 0.5;
    }
    
    #filename-input {
        display: none;
        margin-top: 1;
    }
    
    .filename-active #filename-input {
        display: block;
    }
    """
    
    # Selection State
    selected_plots: Set[int] = set()
    selected_dates: Set[date] = set()
    filename: str = ""
    
    # UI State
    mode = reactive("MENU")  # MENU, CALENDAR, PLOT, FILENAME

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
                
        # Defaults: All plots, All dates
        self.selected_plots = set(self.available_plots)
        self.filename = f"egm4_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self.default_path = os.getcwd()

    def compose(self) -> ComposeResult:
        with Container(id="menu-container"):
            yield Static("Export Menu", classes="menu-header")
            
            # Main Menu Area
            with Vertical(id="main-menu"):
                yield Static("Actions", classes="menu-section")
                # Use fixed width for keys to align descriptions
                yield Static("  [b $accent]e[/]   Export Now", classes="menu-item")
                yield Static("  [b $accent]q[/]   Cancel", classes="menu-item")
                
                yield Static("Filters", classes="menu-section")
                yield Static("", id="plot-status", classes="menu-item")
                yield Static("", id="date-status", classes="menu-item")
                
                yield Static("Configuration", classes="menu-section")
                yield Static("", id="file-status", classes="menu-item")
            
            # Sub-mode areas
            with Vertical(id="calendar-container"):
                yield CalendarWidget(id="calendar")
            
            with Vertical(id="plot-container"):
                yield SelectionList(id="plot-list")
                
            yield Input(id="filename-input")
            
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
        # Plot Status
        if len(self.selected_plots) == len(self.available_plots):
            plot_str = "ALL"
        elif not self.selected_plots:
            plot_str = "NONE"
        else:
            plot_str = ",".join(str(p) for p in sorted(self.selected_plots))
        self.query_one("#plot-status", Static).update(f"  [b $accent]p[/]   Plots: [b]{plot_str}[/b]")
        
        # Date Status
        if not self.selected_dates:
            date_str = "ALL"
        else:
            date_str = f"{len(self.selected_dates)} selected"
        self.query_one("#date-status", Static).update(f"  [b $accent]d[/]   Dates: [b]{date_str}[/b]")
        
        # File Status
        self.query_one("#file-status", Static).update(f"  [b $accent]f[/]   File:  [b]{self.filename}[/b]")
        
        # Visibility and Classes
        menu = self.query_one("#main-menu")
        cal_container = self.query_one("#calendar-container")
        plot_container = self.query_one("#plot-container")
        
        cal = self.query_one("#calendar", CalendarWidget)
        plot_list = self.query_one("#plot-list", SelectionList)
        inp = self.query_one("#filename-input", Input)
        helper = self.query_one("#helper-text", Static)
        
        # Reset visibility
        menu.remove_class("dimmed")
        cal_container.display = False
        plot_container.display = False
        inp.display = False
        helper.update("")
        
        if self.mode == "CALENDAR":
            menu.add_class("dimmed")
            cal_container.display = True
            cal.focus()
            helper.update("\n[dim]ARROWS: Move  SPACE: Toggle  ENTER: Done[/dim]")
            
        elif self.mode == "FILENAME":
            menu.add_class("dimmed")
            inp.display = True
            inp.value = self.filename
            inp.focus()
            helper.update("\n[dim]ENTER: Save filename  ESC: Cancel[/dim]")
            
        elif self.mode == "PLOT":
            menu.add_class("dimmed")
            plot_container.display = True
            plot_list.focus()
            helper.update("\n[dim][b]SPACE[/]: Toggle  [b $accent]a[/]: All  [b $accent]n[/]: None  [b]ENTER[/]: Done[/dim]")

    def on_key(self, event) -> None:
        """Handle global keys."""
        if self.mode == "MENU":
            if event.key == "q" or event.key == "escape":
                self.dismiss()
            elif event.key == "e":
                self.export_data()
            elif event.key == "p":
                self.mode = "PLOT"
                self.refresh_menu()
            elif event.key == "d":
                self.mode = "CALENDAR"
                self.refresh_menu()
            elif event.key == "f":
                self.mode = "FILENAME"
                self.refresh_menu()
                
        elif self.mode == "PLOT":
            if event.key == "enter" or event.key == "escape":
                # Sync selection before exiting
                plot_list = self.query_one("#plot-list", SelectionList)
                self.selected_plots = set(plot_list.selected)
                self.mode = "MENU"
                self.refresh_menu()
            elif event.key == "a":
                plot_list = self.query_one("#plot-list", SelectionList)
                plot_list.select_all()
            elif event.key == "n":
                plot_list = self.query_one("#plot-list", SelectionList)
                plot_list.deselect_all()
            # SelectionList handles space/arrows internally for toggling


    @on(CalendarWidget.Submitted)
    def handle_calendar_done(self, message: CalendarWidget.Submitted):
        self.selected_dates = message.selected_dates
        self.mode = "MENU"
        self.refresh_menu()
        # Focus back to container to catch keys
        self.focus()

    @on(Input.Submitted)
    def handle_filename_done(self, event: Input.Submitted):
        if event.value.strip():
            self.filename = event.value.strip()
        self.mode = "MENU"
        self.refresh_menu()
        self.focus()

    def export_data(self) -> None:
        # Same export logic as before
        filtered_data = []
        for row in self.recorded_data:
            if row.get('plot') not in self.selected_plots:
                continue
            
            if self.selected_dates:
                try:
                    ts = row.get('timestamp')
                    if isinstance(ts, str):
                        row_date = datetime.fromisoformat(ts).date()
                        if row_date not in self.selected_dates:
                            continue
                except:
                    continue
            filtered_data.append(row)
            
        if not filtered_data:
            self.app.notify("No records match configuration!", severity="warning")
            return
            
        try:
            full_path = self.filename
            if not os.path.isabs(full_path):
                full_path = os.path.join(self.default_path, full_path)
                
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
