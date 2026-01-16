"""Channel Legend Widget - Shows which channel is active."""

from rich.console import RenderableType
from rich.text import Text
from textual.widget import Widget


# SRC mode channels (8 channels)
CHANNEL_COLORS_SRC = {
    'cr':   ('1', 'Cr',   '#3296FF'),   # CO2 Raw
    'hr':   ('2', 'Hr',   '#00FFC8'),   # H2O Raw
    'par':  ('3', 'PAR',  '#FFFF64'),   # Light
    'rh':   ('4', '%RH',  '#64FF64'),   # Chamber humidity
    'temp': ('5', 'Temp', '#FFB400'),   # Soil temperature
    'dc':   ('6', 'DC',   '#FF5050'),   # Delta CO2
    'sr':   ('7', 'SR',   '#C8C8C8'),   # Soil respiration
    'atmp': ('8', 'ATMP', '#B4B4FF'),   # Atm pressure
}

# IRGA mode channels (3 channels - base EGM only)
CHANNEL_COLORS_IRGA = {
    'cr':   ('1', 'Cr',   '#3296FF'),
    'hr':   ('2', 'Hr',   '#00FFC8'),
    'atmp': ('3', 'ATMP', '#B4B4FF'),
}


class ChannelLegend(Widget):
    """A compact legend bar showing which channel is active."""

    DEFAULT_CSS = """
    ChannelLegend {
        height: 1;
        width: 100%;
        padding: 0 1;
    }
    """

    def __init__(
        self,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
        probe_type: str = "SRC",
    ) -> None:
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self._active: str = 'cr'
        self._probe_type = probe_type
        self._channel_colors = CHANNEL_COLORS_SRC if probe_type == "SRC" else CHANNEL_COLORS_IRGA

    def set_probe_type(self, probe_type: str) -> None:
        """switch between 'SRC' and 'IRGA' configs."""
        if probe_type == self._probe_type:
            return
        
        self._probe_type = probe_type
        self._channel_colors = CHANNEL_COLORS_SRC if probe_type == "SRC" else CHANNEL_COLORS_IRGA
        
        # Reset active if invalid
        if self._active not in self._channel_colors:
            self._active = 'cr'
        
        self.refresh()

    def set_active(self, channel: str) -> None:
        """Set the active channel."""
        if channel in self._channel_colors:
            self._active = channel
            self.refresh()

    def render(self) -> RenderableType:
        """Render the legend bar."""
        text = Text()
        
        for i, (ch, (key, name, color)) in enumerate(self._channel_colors.items()):
            if i > 0:
                text.append(" ")
            
            if ch == self._active:
                # Active: show with channel color, bold, bracketed
                text.append(f"[{key}]", style=f"bold {color}")
                text.append(name, style=f"bold {color} reverse")
            else:
                # Inactive: dim
                text.append(f"[{key}]", style="dim")
                text.append(name, style="dim")
        
        # Add span hint
        text.append("  |  =/- Span", style="dim")
        
        return text
