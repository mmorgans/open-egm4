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
        # USB connection status (not EGM communication - that requires data flow)
        if self.is_connected:
            conn_indicator = Text("USB ATTACHED", style="bold #006400")
        else:
            conn_indicator = Text("USB DETACHED", style="bold #CC0000")
        
        # Build stats table
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Label", style="cyan")
        table.add_column("Value", justify="right")
        
        # Current CO2 - use dark colors for contrast
        if self.current_co2 is not None:
            co2 = self.current_co2
            if co2 < 400:
                co2_style = "bold #006400"  # Dark green
            elif co2 < 800:
                co2_style = "bold #CC6600"  # Dark orange
            else:
                co2_style = "bold #CC0000"  # Dark red
            table.add_row("Current", Text(f"{co2:.0f} ppm", style=co2_style))
        else:
            table.add_row("Current", Text("--- ppm", style="dim"))
        
        # Stats
        stats = self._calculate_stats()
        if stats["avg"] is not None:
            table.add_row("Average", f"{stats['avg']:.1f} ppm")
            table.add_row("Min/Max", f"{stats['min']:.0f} / {stats['max']:.0f}")
        else:
            table.add_row("Average", "---")
            table.add_row("Min/Max", "---")
        
        # Stability - use dark colors
        stability = stats["stability"]
        if stability == "STABLE":
            stab_text = Text(f"[+] {stability}", style="#006400")  # Dark green
        elif stability == "VARIABLE":
            stab_text = Text(f"[~] {stability}", style="#CC6600")  # Dark orange  
        elif stability == "NOISY":
            stab_text = Text(f"[!] {stability}", style="#CC0000")  # Dark red
        else:
            stab_text = Text(f"[ ] {stability}", style="dim")
        table.add_row("Signal", stab_text)
        
        # Record count
        table.add_row("Records", str(self.record_count))
        
        # Paused indicator
        if self.is_paused:
            table.add_row("", Text("|| PAUSED", style="bold #CC6600"))
        
        # Port info
        port_text = Text(self.port_name if self.port_name else "---", style="dim")
        
        # Compose header content
        header = Text()
        header.append_text(conn_indicator)
        header.append("\n")
        header.append_text(port_text)
        header.append("\n\n")
        
        # Use Group to combine text and table
        from rich.console import Group
        content = Group(header, table)
        
        return Panel(
            content,
            title="[bold]System Status[/bold]",
            border_style="cyan",
        )
