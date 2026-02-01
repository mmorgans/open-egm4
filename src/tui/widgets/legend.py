"""Channel Legend Widget - Shows which channel is active."""

from rich.console import RenderableType
from rich.text import Text
from textual.widget import Widget


# SRC-1 mode channels (5 channels - H2O removed as no humidity probe installed)
CHANNEL_COLORS_SRC = {
    'cr':   ('1', 'CO2',       '#FF3232'),   # CO2 (Red)
    'dc':   ('2', 'Delta CO2', '#32FF32'),   # Delta CO2 (Green)
    'dt':   ('3', 'Delta Time', '#646464'),  # Delta Time (Grey)
    'sr':   ('4', 'Soil Resp', '#FFB464'),   # Soil respiration (Orange)
    'atmp': ('5', 'ATMP',      '#B4B4FF'),   # Atm pressure
}

# Type 0: IRGA Only (3 channels - just the EGM analyzer)
CHANNEL_COLORS_IRGA = {
    'cr':   ('1', 'CO2',    '#FF3232'),   # CO2 (Red)
    'hr':   ('2', 'H2O',    '#00FFC8'),   # H2O
    'atmp': ('3', 'ATMP',   '#B4B4FF'),   # Atm pressure
}

# Fallback for unknown types
CAMERA_COLORS_GENERIC = {
    'cr':   ('1', 'CO2',    '#3296FF'),
    'hr':   ('2', 'H2O',    '#00FFC8'),
    'aux1': ('3', 'Aux1',   '#C8C8C8'),
    'aux2': ('4', 'Aux2',   '#C8C8C8'),
    'aux3': ('5', 'Aux3',   '#C8C8C8'),
    'aux4': ('6', 'Aux4',   '#C8C8C8'),
    'aux5': ('7', 'Aux5',   '#C8C8C8'),
    'atmp': ('8', 'Air Pres.', '#B4B4FF'),
}

CHANNEL_COLORS_HTR = {
    'cr':   ('1', 'CO2',    '#FF3232'),
    'hr':   ('2', 'H2O',    '#00FFC8'),
    'par':  ('3', 'Light',  '#FFFF64'),
    'rh':   ('4', 'RH',     '#64FF64'),
    'temp': ('5', 'Temp',   '#3264FF'),
    'atmp': ('8', 'Air Pres.', '#B4B4FF'),
}

CHANNEL_COLORS_CPY = {
    'cr':   ('1', 'CO2',    '#FF3232'),
    'hr':   ('2', 'H2O',    '#00FFC8'),
    'par':  ('3', 'Light',  '#FFFF64'),
    'evap': ('4', 'Evap',   '#1E90FF'),
    'temp': ('5', 'Temp',   '#3264FF'),
    'dc':   ('6', 'ΔCO2',   '#32FF32'),
    'flow': ('7', 'Flow',   '#C8C8C8'),
    'sr':   ('8', 'Soil Resp', '#FFA500'),
    'atmp': ('9', 'Air Pres.', '#B4B4FF'),
}

CHANNEL_COLORS_PMR = {
    'cr':   ('1', 'CO2',    '#FF3232'),
    'hr':   ('2', 'H2O',    '#00FFC8'),
    'par':  ('3', 'Light',  '#FFFF64'),
    'rh':   ('4', 'RH In',  '#64FF64'),
    'temp': ('5', 'Temp',   '#3264FF'),
    'rh_out':('6', 'RH Out', '#32FF32'),
    'flow': ('7', 'Flow',   '#C8C8C8'),
    'gs':   ('8', 'GS',     '#FFA500'),
    'atmp': ('9', 'Air Pres.', '#B4B4FF'),
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
        probe_type: str = "GENERIC",
    ) -> None:
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self._active: str = 'cr'
        self._probe_type = probe_type
        # Default init
        self.set_probe_type(probe_type)

    def set_probe_type(self, probe_type: str) -> None:
        """switch between configs."""
        # probe_type might be "8", "GENERIC", etc.
        # convert to int if digit
        pt_code = 0
        try:
            pt_code = int(probe_type)
        except (ValueError, TypeError):
             # handle string keys if passed
             pass
        
        if pt_code == 0:
            self._channel_colors = CHANNEL_COLORS_IRGA
        elif pt_code == 8 or probe_type == "SRC":
            self._channel_colors = CHANNEL_COLORS_SRC
        elif pt_code == 11:
            self._channel_colors = CHANNEL_COLORS_CPY
        elif pt_code == 7:
             self._channel_colors = CHANNEL_COLORS_PMR
        elif pt_code in (1, 2, 3):
             self._channel_colors = CHANNEL_COLORS_HTR
        else:
             self._channel_colors = CAMERA_COLORS_GENERIC
        
        self._probe_type = str(pt_code)
        
        # Reset active if invalid
        if self._active not in self._channel_colors:
            self._active = 'cr'
        
        # Trigger re-render to show new labels
        self.refresh()

    def set_active(self, channel: str) -> None:
        """Set the active channel."""
        if channel in self._channel_colors:
            self._active = channel
            self.refresh()

    def set_plot_info(self, current_plot: int | None, known_plots: list[int]) -> None:
        """Update plot filter display info."""
        self._current_plot = current_plot
        self._known_plots = known_plots
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
        
        # Plot selector hint
        text.append("  |  </>", style="dim")
        if hasattr(self, '_current_plot') and hasattr(self, '_known_plots'):
            if self._current_plot is None:
                text.append(" ALL", style="bold cyan")
            else:
                text.append(f" P{self._current_plot}", style="bold yellow")
            
            # Show available plots
            if self._known_plots:
                plots_str = ",".join(str(p) for p in self._known_plots[:5])  # Max 5
                if len(self._known_plots) > 5:
                    plots_str += "..."
                text.append(f" ({plots_str})", style="dim")
        
        return text
