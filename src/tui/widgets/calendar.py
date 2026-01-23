from datetime import date, timedelta
from typing import Set

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Grid, Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Static


class CalendarDay(Static):
    """A single day cell in the calendar grid."""

    DEFAULT_CSS = """
    CalendarDay {
        width: 1fr;
        height: 1;
        content-align: center middle;
        color: $text-muted;
    }
    
    CalendarDay:hover {
        background: $primary-darken-3;
    }
    
    CalendarDay.has-data {
        color: $accent;
        text-style: bold;
    }
    
    CalendarDay.selected {
        background: $success;
        color: $surface;
        text-style: bold;
    }
    
    CalendarDay.today {
        text-style: underline;
    }
    
    CalendarDay.empty {
        background: transparent;
        color: transparent;
    }
    
    /* Cursor style for keyboard nav */
    CalendarDay.cursor {
        background: $accent;
        color: $surface;
        text-style: bold reverse;
    }
    """

    def __init__(self, day: date | None, has_data: bool = False, selected: bool = False):
        self.day = day
        # Use proper centered text content
        label = f"{day.day}" if day else ""
        super().__init__(label, classes="calendar-day")
        
        if not day:
            self.add_class("empty")
        else:
            if has_data:
                self.add_class("has-data")
            if selected:
                self.add_class("selected")
            if day == date.today():
                self.add_class("today")
                
    def on_click(self) -> None:
        """Handle click event."""
        if self.day:
            self.post_message(self.Selected(self.day))
            
    class Selected(Message):
        """Day clicked message."""
        def __init__(self, day: date) -> None:
            self.day = day
            super().__init__()


class CalendarWidget(Widget):
    """A 3-month calendar widget with keyboard navigation."""
    
    can_focus = True

    DEFAULT_CSS = """
    CalendarWidget {
        width: 100%;
        height: auto;
        border: solid $primary;
        padding: 0 1;
        background: $surface;
    }
    
    CalendarWidget:focus {
        border: double $accent;
    }

    .calendar-container {
        height: auto;
        width: 100%;
        layout: horizontal;
    }
    
    .month-section {
        width: 1fr;
        height: auto;
        margin: 0 1;
    }

    .calendar-header {
        width: 100%;
        height: 1;
        align: center middle;
        padding: 0;
        margin-bottom: 0;
    }
    
    .nav-btn {
        width: 4;
        min-width: 4;
        padding: 0;
        height: 1;
        border: none;
        background: $primary;
        color: $text;
    }
    
    .month-label {
        width: 1fr;
        content-align: center middle;
        text-style: bold;
        color: $text-muted;
    }
    
    .month-label.current {
        color: $accent;
        text-style: bold underline;
    }
    
    .calendar-grid {
        grid-size: 7;
        grid-gutter: 0;
        margin-bottom: 0;
        width: 100%;
    }
    
    .day-header {
        width: 1fr;
        content-align: center middle;
        color: $secondary;
        text-style: bold;
        padding-bottom: 0;
    }
    """

    BINDINGS = [
        ("left", "move_left", "Previous Day"),
        ("right", "move_right", "Next Day"),
        ("up", "move_up", "Previous Week"),
        ("down", "move_down", "Next Week"),
        ("space", "toggle_select", "Toggle Selection"),
        ("enter", "confirm_selection", "Confirm"),
    ]

    # Current month (Center month)
    current_month = reactive(date.today().replace(day=1))
    cursor_date = reactive(date.today())
    
    def __init__(self, id: str | None = None):
        super().__init__(id=id)
        self.data_dates: Set[date] = set()
        self.selected_dates: Set[date] = set()

    def set_data_dates(self, dates: Set[date]) -> None:
        self.data_dates = dates
        if dates:
            latest = max(dates)
            self.current_month = latest.replace(day=1)
            self.cursor_date = latest
        self.refresh_calendar()

    def get_selected_dates(self) -> Set[date]:
        return self.selected_dates

    def compose(self) -> ComposeResult:
        # Top Nav
        with Horizontal(classes="calendar-header"):
            yield Button("<<", id="prev-month", classes="nav-btn")
            yield Static("Select Dates", classes="month-label")
            yield Button(">>", id="next-month", classes="nav-btn")
            
        # 3-Month View
        with Horizontal(classes="calendar-container"):
            # Month 1 (Left)
            with Vertical(id="month-container-0", classes="month-section"):
                yield Static("", id="label-0", classes="month-label")
                with Grid(classes="calendar-grid"):
                     for day in ["S", "M", "T", "W", "T", "F", "S"]:
                        yield Static(day, classes="day-header")
                yield Grid(id="grid-0", classes="calendar-grid")
                
            # Month 2 (Center)
            with Vertical(id="month-container-1", classes="month-section"):
                yield Static("", id="label-1", classes="month-label current")
                with Grid(classes="calendar-grid"):
                     for day in ["S", "M", "T", "W", "T", "F", "S"]:
                        yield Static(day, classes="day-header")
                yield Grid(id="grid-1", classes="calendar-grid")
                
            # Month 3 (Right)
            with Vertical(id="month-container-2", classes="month-section"):
                yield Static("", id="label-2", classes="month-label")
                with Grid(classes="calendar-grid"):
                     for day in ["S", "M", "T", "W", "T", "F", "S"]:
                        yield Static(day, classes="day-header")
                yield Grid(id="grid-2", classes="calendar-grid")

    def on_mount(self) -> None:
        self.refresh_calendar()

    def refresh_calendar(self) -> None:
        # Offsets: -1, 0, +1
        start_months = [
            (self.current_month - timedelta(days=1)).replace(day=1),
            self.current_month,
            (self.current_month.replace(day=28) + timedelta(days=4)).replace(day=1)
        ]
        
        for i, month_start in enumerate(start_months):
            label = self.query_one(f"#label-{i}", Static)
            label.update(month_start.strftime("%B %Y"))
            
            grid = self.query_one(f"#grid-{i}", Grid)
            grid.remove_children()
            
            # Days
            start_weekday = (month_start.weekday() + 1) % 7
            for _ in range(start_weekday):
                grid.mount(CalendarDay(None))
                
            current = month_start
            while current.month == month_start.month:
                has_data = current in self.data_dates
                is_selected = current in self.selected_dates
                
                day_widget = CalendarDay(current, has_data=has_data, selected=is_selected)
                if current == self.cursor_date:
                    day_widget.add_class("cursor")
                
                grid.mount(day_widget)
                current += timedelta(days=1)

    def watch_cursor_date(self, new_date: date) -> None:
        # Current view range:
        start_curr = self.current_month
        next_month = (start_curr.replace(day=28) + timedelta(days=4)).replace(day=1) 
        prev_month = (start_curr - timedelta(days=1)).replace(day=1)
        month_after_next = (next_month.replace(day=28) + timedelta(days=4)).replace(day=1)
        
        if new_date < prev_month:
             self.current_month = (self.current_month - timedelta(days=1)).replace(day=1)
        elif new_date >= month_after_next:
             self.current_month = next_month

        self.refresh_calendar()

    def watch_current_month(self, new_month: date) -> None:
        self.refresh_calendar()

    def action_move_left(self) -> None:
        self.cursor_date -= timedelta(days=1)
        
    def action_move_right(self) -> None:
        self.cursor_date += timedelta(days=1)
        
    def action_move_up(self) -> None:
        self.cursor_date -= timedelta(days=7)
        
    def action_move_down(self) -> None:
        self.cursor_date += timedelta(days=7)

    def action_toggle_select(self) -> None:
        if self.cursor_date in self.selected_dates:
            self.selected_dates.remove(self.cursor_date)
        else:
            self.selected_dates.add(self.cursor_date)
        self.refresh_calendar()
        self.post_message(self.SelectionChanged(self.selected_dates))
        
    def action_confirm_selection(self) -> None:
        self.post_message(self.Submitted(self.selected_dates))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "prev-month":
             # Shift view back by 1 month
            first = self.current_month.replace(day=1)
            prev = first - timedelta(days=1)
            self.current_month = prev.replace(day=1)
        elif event.button.id == "next-month":
            next_month = (self.current_month.replace(day=28) + timedelta(days=4)).replace(day=1)
            self.current_month = next_month
            
    def on_calendar_day_selected(self, message: CalendarDay.Selected) -> None:
        """Handle click selection."""
        # Update cursor to clicked date too
        self.cursor_date = message.day
        self.action_toggle_select()

    class SelectionChanged(Message):
        def __init__(self, selected_dates: Set[date]) -> None:
            self.selected_dates = selected_dates
            super().__init__()

    class Submitted(Message):
        def __init__(self, selected_dates: Set[date]) -> None:
            self.selected_dates = selected_dates
            super().__init__()
