"""CO2 Chart Widget - Real-time single-channel plotting using textual-plotext."""

from collections import deque
from dataclasses import dataclass
from textual.reactive import var
from textual.message import Message
from textual_plotext import PlotextPlot


# SRC (Soil Respiration Chamber) channel configuration
# mV1-5 are mapped by EGM firmware in SRC mode:
#   mV1 = PAR, mV2 = %RH, mV3 = Temp, mV4 = DC, mV5 = DT (counter, not plotted)
# Format: (key, short_name, full_name, unit, color RGB, typical_range)
CHANNELS_SRC = {
    'cr':   ('1', 'Cr',   'CO2 Raw',          'ppm',           (255, 50, 50),    (0, 2000)),   # Red
    'hr':   ('2', 'Hr',   'H2O Raw',          'mb',            (0, 255, 200),    (0, 50)),
    'par':  ('3', 'PAR',  'Light (PAR)',      'umol/m2/s',     (255, 255, 100),  (0, 2000)),
    'rh':   ('4', '%RH',  'Chamber Humidity', '%',             (100, 255, 100),  (0, 100)),
    'temp': ('5', 'Temp', 'Soil Temperature', '°C',            (50, 100, 255),   (-10, 50)),   # Blue
    'dc':   ('6', 'DC',   'Delta CO2',        'ppm',           (50, 255, 50),    (-500, 500)), # Green
    'sr':   ('7', 'SR',   'Soil Respiration', 'gCO2/m2/hr',    (200, 200, 200),  (-100, 100)),
    'atmp': ('8', 'ATMP', 'Atm Pressure',     'mb',            (180, 180, 255),  (900, 1100)),
    'dt':   ('9', 'DT',   'Delta Time',       's',             (100, 100, 100),  (0, 200)),    # Dark Grey
}

# IRGA (base EGM, no external probe) - only core readings
CHANNELS_IRGA = {
    'cr':   ('1', 'Cr',   'CO2 Raw',      'ppm',  (50, 150, 255),  (0, 2000)),
    'hr':   ('2', 'Hr',   'H2O Raw',      'mb',   (0, 255, 200),   (0, 50)),
    'atmp': ('3', 'ATMP', 'Atm Pressure', 'mb',   (180, 180, 255), (900, 1100)),
}

# Default to SRC (most common use case with chamber)
CHANNELS = CHANNELS_SRC
DEFAULT_CHANNEL = 'cr'


class CO2PlotWidget(PlotextPlot):
    """A real-time single-channel chart widget using Plotext."""
    
    @dataclass
    class ProbeTypeChanged(Message):
        """Posted when the probe type is detected/changed."""
        probe_type: str

    marker: var[str] = var("braille")

    def __init__(
        self,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
        max_points: int = 120,
        probe_type: str = "SRC",
    ) -> None:
        """Initialize the chart widget."""
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        
        # Display span (how many points to show)
        self._max_points = max_points
        
        self._probe_type = probe_type
        self._channels_config = CHANNELS_SRC if probe_type == "SRC" else CHANNELS_IRGA
        
        # Data storage for all possible channels
        # FIXED CAPACITY: Store up to 3600 points (buffer) regardless of view span
        # This allows non-destructive zooming.
        self._buffer_size = 3600
        self._channels: dict[str, deque] = {
            ch: deque(maxlen=self._buffer_size) for ch in CHANNELS_SRC  # Use full set
        }
        
        # Active channel (what's currently displayed)
        self._active_channel: str = DEFAULT_CHANNEL
        
        # Current plot number and DT for reference
        self._current_plot: int = 0
        self._current_dt: int = 0
        
        # Watch for theme changes
        self.watch(self.app, "theme", lambda: self.call_after_refresh(self.replot))

    @property
    def channels_config(self) -> dict:
        """Get channel config for current probe type."""
        return self._channels_config

    @property
    def max_points(self) -> int:
        return self._max_points

    @max_points.setter
    def max_points(self, value: int) -> None:
        """Update display span (zoom level). Does not minimize data."""
        self._max_points = value
        # Don't resize deques! Just replot to change the view window.
        self.replot()

    @property
    def active_channel(self) -> str:
        return self._active_channel

    def set_active_channel(self, channel: str) -> None:
        """Set which channel to display."""
        if channel in self._channels_config:
            self._active_channel = channel
            self.replot()

    def on_mount(self) -> None:
        """Configure the plot when mounted."""
        self.replot()

    def replot(self) -> None:
        """Redraw the plot with active channel data."""
        self.plt.clear_data()
        
        ch = self._active_channel
        if ch not in self._channels_config:
            ch = 'cr'  # Fall back to CO2
            self._active_channel = ch
        
        key, short_name, full_name, unit, color, (typical_min, typical_max) = self._channels_config[ch]
        
        # Get data from storage
        full_data = list(self._channels[ch])
        
        # Slice for display based on max_points (span)
        # Show only the last N points
        if len(full_data) > self._max_points:
            data = full_data[-self._max_points:]
        else:
            data = full_data
        
        if len(data) >= 2:
            y_values = data
            x_values = list(range(len(y_values)))
            
            self.plt.plot(x_values, y_values, marker=self.marker, color=color)
            
            # Auto-scaling logic
            data_min = min(y_values)
            data_max = max(y_values)
            data_span = data_max - data_min
            
            # Determine minimum allowed span (e.g., 5% of typical range)
            # This prevents zooming in too effectively on noise
            typical_span = abs(typical_max - typical_min)
            min_span = typical_span * 0.05
            if min_span == 0: min_span = 1.0
            
            # Calculate padded limits
            padding = max(data_span * 0.1, min_span * 0.1)
            plot_min = data_min - padding
            plot_max = data_max + padding
            
            # Ensure minimum span is respected
            current_span = plot_max - plot_min
            if current_span < min_span:
                center = (plot_min + plot_max) / 2
                plot_min = center - (min_span / 2)
                plot_max = center + (min_span / 2)
            
            self.plt.ylim(plot_min, plot_max)
            
            current = y_values[-1]
            title = f"{short_name}: {current:.1f} {unit}  |  Plot:{self._current_plot}  Span:{self._max_points}"
        else:
            title = f"{short_name} ({full_name})  |  Waiting for data..."
            self.plt.ylim(typical_min, typical_max)
        
        self.plt.title(title)
        self.plt.xlabel("Samples (newest ->)")
        self.plt.ylabel(f"{short_name} ({unit})")
        
        self.refresh()

    def add_data(self, parsed_data: dict) -> None:
        """Add data from a parsed R-record.

        Args:
            parsed_data: Dictionary from EGM4Serial parser.
        """
        # Track plot number
        if 'plot' in parsed_data:
            self._current_plot = parsed_data['plot']
        
        # Track DT
        if 'dt' in parsed_data:
            self._current_dt = parsed_data['dt']
            
        # Detect Probe Type and switch config if needed
        if 'probe_type' in parsed_data:
            pt = parsed_data['probe_type']
            new_type = "SRC" if pt == 8 else "IRGA"
            
            if new_type != self._probe_type:
                self._probe_type = new_type
                self._channels_config = CHANNELS_SRC if new_type == "SRC" else CHANNELS_IRGA
                
                # Notify app of probe change
                self.post_message(self.ProbeTypeChanged(new_type))

        # Add data to channels
        # Map output keys from parser to internal channel keys
        field_map = {
            'co2_ppm': 'cr',
            'h2o_ref': 'hr',
            'par': 'par',
            'rh': 'rh',
            'temp': 'temp',
            'dc': 'dc',
            'sr': 'sr',
            'atmp': 'atmp',
            'dt': 'dt', # Map dt if we decide to plot it
        }
        
        for p_key, ch_key in field_map.items():
            if p_key in parsed_data:
                val = parsed_data[p_key]
                # Add to main channel deque if it exists
                if ch_key in self._channels:
                    try:
                        self._channels[ch_key].append(float(val))
                    except (ValueError, TypeError):
                        pass
        
        self.replot()

    def get_current_value(self, channel: str = None) -> float | None:
        """Get the latest value for a channel."""
        ch = channel or self._active_channel
        if ch in self._channels and self._channels[ch]:
            return self._channels[ch][-1]
        return None

    def clear_data(self) -> None:
        """Clear all chart data."""
        for ch in self._channels:
            self._channels[ch].clear()
        self.replot()

    @property
    def data(self) -> dict[str, list[float]]:
        """Get all channel data as a dictionary."""
        return {ch: list(data) for ch, data in self._channels.items()}

    def _watch_marker(self) -> None:
        """React to marker type being changed."""
        self.replot()
