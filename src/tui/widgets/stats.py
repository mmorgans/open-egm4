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
    data_mode: reactive[str] = reactive("")  # "M" for Real-Time, "R" for Memory
    device_status: reactive[str] = reactive("")  # "WARMUP:55", "ZERO:10", or ""
    hw_record: reactive[int | None] = reactive(None)
    
    # Scientific Stats
    flux_slope: reactive[float] = reactive(0.0)
    flux_r2: reactive[float] = reactive(0.0)

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

    def add_reading(self, co2: float, record: int | None = None) -> None:
        """Add a new CO2 reading to history and update current value."""
        self._history.append(co2)
        self.current_co2 = co2
        if record is not None:
            self.hw_record = record

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
        """Render the stats content (no Panel - border from CSS)."""
        from rich.console import Group
        
        # Connection Status
        if self.is_connected:
            conn_style = "bold green"
            conn_text = "CONNECTED"
            icon = "●"
        else:
            conn_style = "bold red"
            conn_text = "DISCONNECTED"
            icon = "○"
            
        header = Text()
        header.append(f"{icon} {conn_text}\n", style=conn_style)
        header.append(self.port_name or "---", style="dim")
        
        # Data mode indicator
        if self.data_mode == "M":
            header.append("\n")
            header.append("REAL-TIME", style="bold cyan")
        elif self.data_mode == "R":
            header.append("\n")
            header.append("MEMORY DUMP", style="bold yellow")
        
        # Device status (warmup/zero check)
        if self.device_status:
            header.append("\n")
            if self.device_status.startswith("WARMUP"):
                header.append(self.device_status, style="bold red")
            elif self.device_status.startswith("ZERO"):
                header.append(self.device_status, style="bold magenta")
            else:
                header.append(self.device_status, style="bold white")
        
        header.append("\n\n")

        # Stats Table
        table = Table(show_header=False, box=None, padding=(0, 1), expand=True)
        table.add_column("Key", style="cyan")
        table.add_column("Value", justify="right")

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

        # Stats
        stats = self._calculate_stats()
        avg = f"{stats['avg']:.1f} ppm" if stats['avg'] else "---"
        rng = f"{stats['min']:.0f} / {stats['max']:.0f}" if stats['min'] else "---"
        
        table.add_row("Average", avg)
        table.add_row("Min/Max", rng)
        
        # Flux Data
        if self.flux_slope != 0:
            flux_str = f"{self.flux_slope:+.2f} ppm/s"
            r2_str = f"{self.flux_r2:.2f}"
            table.add_row("Flux", Text(flux_str, style="bold cyan"))
            table.add_row("R²", Text(r2_str, style="bold magenta"))
        else:
            table.add_row("Flux", "---")
        

        
        table.add_row("Session Rec", str(self.record_count))
        if self.hw_record is not None:
            table.add_row("Device REC", Text(str(self.hw_record), style="bold yellow"))

        # Stability
        stab = stats['stability']
        if stab == "STABLE":
            stab_style = "green"
        elif stab == "VARIABLE":
            stab_style = "yellow"
        elif stab == "NOISY":
            stab_style = "red"
        else:
            stab_style = "dim"
        table.add_row("Signal", Text(stab, style=stab_style))

        if self.is_paused:
            table.add_row("", Text("PAUSED", style="bold yellow reverse"))

        return Group(header, table)
