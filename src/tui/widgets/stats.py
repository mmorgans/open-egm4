"""Stats Widget - Displays key metrics and connection status."""

import statistics
from collections import deque

from rich.console import RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.widget import Widget
from textual.reactive import reactive


class StatsWidget(Widget):
    """Widget displaying CO2 statistics and connection status."""

    DEFAULT_CSS = """
    StatsWidget {
        height: 100%;
        padding: 1;
    }
    """

    # Reactive properties that trigger re-render when changed
    current_co2: reactive[float | None] = reactive(None)
    is_connected: reactive[bool] = reactive(False)
    record_count: reactive[int] = reactive(0)
    port_name: reactive[str] = reactive("")
    is_paused: reactive[bool] = reactive(False)

    def __init__(
        self,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self._history: deque[float] = deque(maxlen=100)

    def add_reading(self, co2: float) -> None:
        """Add a new CO2 reading to history and update current value."""
        self._history.append(co2)
        self.current_co2 = co2

    def clear_history(self) -> None:
        """Clear the history data."""
        self._history.clear()
        self.current_co2 = None

    def _calculate_stats(self) -> dict:
        """Calculate statistics from history."""
        if len(self._history) < 2:
            return {"avg": None, "min": None, "max": None, "stability": "WAITING"}
        
        data = list(self._history)
        avg = statistics.mean(data)
        min_val = min(data)
        max_val = max(data)
        
        # Calculate stability from recent readings
        recent = data[-10:] if len(data) >= 10 else data
        try:
            stdev = statistics.stdev(recent)
            if stdev < 5:
                stability = "STABLE"
            elif stdev < 20:
                stability = "VARIABLE"
            else:
                stability = "NOISY"
        except statistics.StatisticsError:
            stability = "---"
        
        return {"avg": avg, "min": min_val, "max": max_val, "stability": stability}

    def render(self) -> RenderableType:
        """Render the stats panel."""
        from rich.console import Group
        from rich import box
        
        # Connection Status
        if self.is_connected:
            conn_style = "bold cyan"
            conn_text = "CONNECTED"
            icon = "●"
        else:
            conn_style = "bold red"
            conn_text = "DISCONNECTED"
            icon = "○"
            
        header = Text()
        header.append(f"{icon} {conn_text}\n", style=conn_style)
        header.append(self.port_name or "Scanning...", style="dim cyan")
        header.append("\n")

        # Main Stats Table
        table = Table(show_header=False, box=None, padding=(0, 1), expand=True)
        table.add_column("Key", style="cyan dim")
        table.add_column("Value", justify="right", style="bold white")

        # Current CO2
        if self.current_co2 is not None:
            val = self.current_co2
            if val < 400:
                color = "green"
            elif val < 1000:
                color = "yellow"
            else:
                color = "red"
            table.add_row("CO2", Text(f"{val:.0f} ppm", style=f"bold {color}"))
        else:
            table.add_row("CO2", Text("---", style="dim"))

        # Meta Stats
        stats = self._calculate_stats()
        avg = f"{stats['avg']:.1f}" if stats['avg'] else "-"
        rng = f"{stats['min']:.0f}-{stats['max']:.0f}" if stats['min'] else "-"
        
        table.add_row("Average", avg)
        table.add_row("Range", rng)
        table.add_row("Records",str(self.record_count))

        # Stability
        stab = stats['stability']
        stab_color = "green" if stab == "STABLE" else "yellow" if stab == "VARIABLE" else "red"
        if stab == "WAITING": stab_color = "dim white"
        table.add_row("Signal", Text(stab, style=stab_color))

        if self.is_paused:
             table.add_row("", Text("PAUSED", style="bold red reverse"))

        return Panel(
            Group(header, table),
            title="System Status",
            border_style="cyan dim",
            box=box.ROUNDED
        )
