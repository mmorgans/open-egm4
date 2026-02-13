"""CO2 Chart Widget - Real-time single-channel plotting using textual-plotext."""

import sys
from collections import deque
from dataclasses import dataclass
from textual.reactive import var
from textual.message import Message
from textual_plotext import PlotextPlot

# Use ASCII-compatible marker on Windows (braille doesn't render in most Windows terminals)
DEFAULT_MARKER = "dot" if sys.platform == "win32" else "braille"


# SRC-1 (Soil Respiration Chamber) channel configuration
# The SRC-1 provides: CO2, Delta CO2, Delta Time, Soil Respiration, ATMP
# Note: H2O requires optional humidity probe (not shown if not installed)
# Format: (slot, short_name, full_name, unit, color RGB, typical_range)
CHANNELS_SRC = {
    'cr':   ('1', 'CO2',       'CO2 Concentration',    'ppm',        (255, 50, 50),   (0, 2000)),
    'dc':   ('2', 'Delta CO2', 'Delta CO2',            'ppm',        (50, 255, 50),   (0, 100)),
    'dt':   ('3', 'Delta Time', 'Delta Time',          's',          (100, 100, 100), (0, 300)),
    'sr':   ('4', 'Soil Resp', 'Soil Respiration',     'gCO2/m2/hr', (255, 200, 100), (0, 10)),
    'atmp': ('5', 'ATMP',      'Atmospheric Pressure', 'mb',         (180, 180, 255), (900, 1100)),
}

# Type 0: IRGA Only (No Sensor Connected)
# The EGM alone provides: CO2, H2O, ATMP
# mV1-5 raw inputs are available but typically unused
CHANNELS_IRGA = {
    'cr':   ('1', 'CO2',    'CO2 Concentration',    'ppm',  (255, 50, 50),   (0, 2000)),
    'hr':   ('2', 'H2O',    'Vapor Pressure',       'mb',   (0, 255, 200),   (0, 50)),
    'atmp': ('3', 'ATMP',   'Atmospheric Pressure', 'mb',   (180, 180, 255), (900, 1100)),
}

# Fallback for unknown probe types
CHANNELS_GENERIC = {
    'cr':   ('1', 'CO2',    'CO2 Concentration', 'ppm',  (50, 150, 255),  (0, 2000)),
    'hr':   ('2', 'H2O',    'Vapor Pressure',    'mb',   (0, 255, 200),   (0, 50)),
    'aux1': ('3', 'Aux1',   'Aux Input 1',       '',     (200, 200, 200), (0, 1000)),
    'aux2': ('4', 'Aux2',   'Aux Input 2',       '',     (200, 200, 200), (0, 1000)),
    'aux3': ('5', 'Aux3',   'Aux Input 3',       '',     (200, 200, 200), (0, 1000)),
    'aux4': ('6', 'Aux4',   'Aux Input 4',       '',     (200, 200, 200), (0, 1000)),
    'aux5': ('7', 'Aux5',   'Aux Input 5',       '',     (200, 200, 200), (0, 1000)),
    'atmp': ('8', 'Air Pres.', 'Atmospheric Pressure', 'mb',   (180, 180, 255), (900, 1100)),
}

# Type 1, 2, 3: HTR/STP
CHANNELS_HTR = {
    'cr':   ('1', 'CO2',    'CO2 Concentration', 'ppm',  (255, 50, 50),   (0, 2000)),
    'hr':   ('2', 'H2O',    'Vapor Pressure',    'mb',   (0, 255, 200),   (0, 50)),
    'par':  ('3', 'Light',  'PAR',               'umol/m2/s', (255, 255, 100), (0, 2000)),
    'rh':   ('4', 'RH',     'Relative Humidity', '%',    (100, 255, 100), (0, 100)),
    'temp': ('5', 'Temp',   'Temperature',       '°C',   (50, 100, 255),  (0, 50)),
    'atmp': ('8', 'Air Pres.', 'Atmospheric Pressure', 'mb', (180, 180, 255), (900, 1100)),
}

# Type 11: CPY/CFX
CHANNELS_CPY = {
    'cr':   ('1', 'CO2',    'CO2 Concentration', 'ppm',  (255, 50, 50),   (0, 2000)),
    'hr':   ('2', 'H2O',    'Vapor Pressure',    'mb',   (0, 255, 200),   (0, 50)),
    'par':  ('3', 'Light',  'PAR',               'umol/m2/s', (255, 255, 100), (0, 2000)),
    'evap': ('4', 'Evap',   'Evaporation Rate',  '',     (100, 200, 255), (0, 100)),
    'temp': ('5', 'Temp',   'Temperature',       '°C',   (50, 100, 255),  (0, 50)),
    'dc':   ('6', 'ΔCO2',   'ΔCO2',              'ppm',  (50, 255, 50),   (-500, 500)),
    'flow': ('7', 'Flow',   'Flow Rate',         'ml/min', (200, 200, 200), (0, 500)),
    'sr':   ('8', 'Soil Resp', 'Assimilation Rate', 'units', (255, 150, 0), (-50, 50)),
    'atmp': ('9', 'Air Pres.', 'Atmospheric Pressure', 'mb', (180, 180, 255), (900, 1100)),
}

# Type 7: PMR Porometer
CHANNELS_PMR = {
    'cr':   ('1', 'CO2',    'CO2 Concentration', 'ppm',  (255, 50, 50),   (0, 2000)),
    'hr':   ('2', 'H2O',    'Vapor Pressure',    'mb',   (0, 255, 200),   (0, 50)),
    'par':  ('3', 'Light',  'PAR',               'umol/m2/s', (255, 255, 100), (0, 2000)),
    'rh':   ('4', 'RH In',  'Relative Humidity', '%',    (100, 255, 100), (0, 100)),
    'temp': ('5', 'Temp',   'Temperature',       '°C',   (50, 100, 255),  (0, 50)),
    'rh_out':('6', 'RH Out', 'RH Out',           '%',    (50, 200, 50),   (0, 100)),
    'flow': ('7', 'Flow',   'Flow Rate',         'ml/min', (200, 200, 200), (0, 500)),
    'gs':   ('8', 'GS',     'Stomatal Conductance', 'mmol/m2/s', (255, 150, 0), (0, 1000)),
    'atmp': ('9', 'Air Pres.', 'Atmospheric Pressure', 'mb', (180, 180, 255), (900, 1100)),
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

    marker: var[str] = var(DEFAULT_MARKER)

    def __init__(
        self,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
        max_points: int = 5000,
        probe_type: str = "GENERIC",
    ) -> None:
        """Initialize the chart widget."""
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        
        # Display span (how many points to show) - effectively infinite for session
        self._max_points = max_points
        
        
        self._probe_type = probe_type
        self._channels_config = self._get_config_for_type(probe_type)
        
        # Data storage: per-plot, per-channel
        # Structure: _plot_data[plot_num][channel_key] = deque of values
        # Also store DT (time) values: _plot_dt[plot_num] = deque of DT values
        self._buffer_size = 5000
        self._plot_data: dict[int, dict[str, deque]] = {}
        self._plot_dt: dict[int, deque] = {}  # DT (time) for X-axis
        self._plot_markers: dict[int, deque] = {}  # (dt, value, label)
        
        # Track all plots seen
        self._known_plots: set[int] = set()
        # Track probe type per plot
        self._plot_probe_types: dict[int, str] = {}
        # Track if we've ever received data (for first-time probe detection)
        self._first_data_received: bool = False
        
        # Filter: which plot to display (None = show all plots combined)
        self._filter_plot: int | None = None
        
        # Active channel (what's currently displayed)
        self._active_channel: str = DEFAULT_CHANNEL
        
        # Current plot number from latest data
        self._current_plot: int = 0
        self._current_dt: int = 0
        
        # Data cursor for inspecting individual points
        self._cursor_index: int | None = None  # None = cursor off, int = index in displayed data
        self._cursor_mode: bool = False  # True when cursor is active
        
        # Watch for theme changes
        self.watch(self.app, "theme", lambda: self.call_after_refresh(self.replot))

    def _get_plot_channels(self, plot_num: int) -> dict[str, deque]:
        """Get or create channel storage for a specific plot."""
        if plot_num not in self._plot_data:
            self._plot_data[plot_num] = {
                ch: deque(maxlen=self._buffer_size) for ch in self._channels_config
            }
            self._plot_dt[plot_num] = deque(maxlen=self._buffer_size)
            self._plot_markers[plot_num] = deque(maxlen=200)
            self._known_plots.add(plot_num)
        return self._plot_data[plot_num]

    @property
    def filter_plot(self) -> int | None:
        """Get current plot filter (None = show all)."""
        return self._filter_plot

    @filter_plot.setter
    def filter_plot(self, value: int | None) -> None:
        """Set plot filter and refresh."""
        self._filter_plot = value
        self._switch_to_plot_config(value)
        self.replot()

    def get_known_plots(self) -> list[int]:
        """Get sorted list of all plot numbers seen."""
        return sorted(self._known_plots)

    def next_plot(self) -> int | None:
        """Switch to next plot in sequence. Returns new plot number."""
        plots = self.get_known_plots()
        if not plots:
            return None

        if self._filter_plot is None:
            # Currently showing all - switch to first plot
            self._filter_plot = plots[0]
        else:
            # Find next plot
            try:
                idx = plots.index(self._filter_plot)
                if idx + 1 < len(plots):
                    self._filter_plot = plots[idx + 1]
                else:
                    # Wrap to "all"
                    self._filter_plot = None
            except ValueError:
                self._filter_plot = plots[0]

        self._switch_to_plot_config(self._filter_plot)
        self.replot()
        return self._filter_plot

    def prev_plot(self) -> int | None:
        """Switch to previous plot in sequence. Returns new plot number."""
        plots = self.get_known_plots()
        if not plots:
            return None

        if self._filter_plot is None:
            # Currently showing all - switch to last plot
            self._filter_plot = plots[-1]
        else:
            # Find previous plot
            try:
                idx = plots.index(self._filter_plot)
                if idx > 0:
                    self._filter_plot = plots[idx - 1]
                else:
                    # Wrap to "all"
                    self._filter_plot = None
            except ValueError:
                self._filter_plot = plots[-1]

        self._switch_to_plot_config(self._filter_plot)
        self.replot()
        return self._filter_plot

    @property
    def channels_config(self) -> dict:
        """Get channel config for current probe type."""
        return self._channels_config

    @property
    def max_points(self) -> int:
        return self._max_points

    @max_points.setter
    def max_points(self, value: int) -> None:
        """Update max points (internal use mainly)."""
        self._max_points = value
        self.replot()

    @property
    def view_span(self) -> int:
        """Alias for max_points."""
        return self._max_points

    @property
    def active_channel(self) -> str:
        return self._active_channel

    def set_active_channel(self, channel: str) -> None:
        """Set which channel to display."""
        if channel in self._channels_config:
            self._active_channel = channel
            self.replot()

    def set_active_by_slot_index(self, slot_idx: str) -> str | None:
        """Set active channel by its slot index (e.g. '1', '2'...).
        
        Returns the key of the selected channel, or None if not found.
        """
        for ch_key, config in self._channels_config.items():
            # config is (key, short_name, full_name, ...)
            # key is index 0
            if config[0] == slot_idx:
                self._active_channel = ch_key
                self.replot()
                return ch_key
        return None

    def toggle_cursor(self) -> None:
        """Toggle cursor mode on/off."""
        self._cursor_mode = not self._cursor_mode
        if self._cursor_mode:
            # Start cursor at the end of data
            self._cursor_index = -1  # Will be clamped during replot
        else:
            self._cursor_index = None
        self.replot()

    def cursor_left(self) -> None:
        """Move cursor left (earlier in time)."""
        if self._cursor_mode and self._cursor_index is not None:
            self._cursor_index = max(0, self._cursor_index - 1)
            self.replot()

    def cursor_right(self) -> None:
        """Move cursor right (later in time)."""
        if self._cursor_mode and self._cursor_index is not None:
            self._cursor_index += 1  # Will be clamped during replot
            self.replot()

    def cursor_home(self) -> None:
        """Move cursor to start of data."""
        if self._cursor_mode:
            self._cursor_index = 0
            self.replot()

    def cursor_end(self) -> None:
        """Move cursor to end of data."""
        if self._cursor_mode:
            self._cursor_index = -1  # Will be set to last index during replot
            self.replot()

    @property
    def cursor_active(self) -> bool:
        """Check if cursor mode is active."""
        return self._cursor_mode

    def on_mount(self) -> None:
        """Configure the plot when mounted."""
        # Check if we should force Unicode (braille) even on Windows
        force_unicode = getattr(self.app, "force_unicode", False)
        if force_unicode and self.marker == "dot":
             self.marker = "braille"
             
        self.replot()

    def replot(self) -> None:
        """Redraw the plot with active channel data."""
        self.plt.clear_data()
        
        ch = self._active_channel
        if ch not in self._channels_config:
            ch = 'cr'  # Fall back to CO2
            self._active_channel = ch
        
        key, short_name, full_name, unit, color, (typical_min, typical_max) = self._channels_config[ch]
        
        # Gather data and DT values based on filter setting
        full_data = []
        full_dt = []
        use_dt_axis = False  # Only use DT for X-axis when viewing single plot
        
        if self._filter_plot is not None:
            # Show only specific plot - can use DT for X-axis
            if self._filter_plot in self._plot_data:
                full_data = list(self._plot_data[self._filter_plot].get(ch, []))
                full_dt = list(self._plot_dt.get(self._filter_plot, []))
                use_dt_axis = True
        else:
            # Show all plots combined - use sample index (DT resets per plot)
            for plot_num in sorted(self._plot_data.keys()):
                full_data.extend(self._plot_data[plot_num].get(ch, []))
        
        # Slice for display based on max_points (span)
        if len(full_data) > self._max_points:
            data = full_data[-self._max_points:]
            dt_data = full_dt[-self._max_points:] if full_dt else []
        else:
            data = full_data
            dt_data = full_dt
        
        # Build plot filter label for title
        if self._filter_plot is not None:
            plot_label = f"Plot:{self._filter_plot}"
        else:
            plot_label = "Plot:ALL"
        
        if len(data) >= 2:
            y_values = data
            
            # Handle DT resets (multiple measurement sessions in one plot)
            # Accumulate DT across sessions so they display sequentially
            if use_dt_axis and len(dt_data) >= 2:
                accumulated_dt = []
                offset = 0
                prev_dt = 0
                for dt in dt_data:
                    if dt < prev_dt - 5:  # DT decreased by >5 seconds = new session
                        offset += prev_dt + 5  # Add gap between sessions
                    accumulated_dt.append(dt + offset)
                    prev_dt = dt
                dt_data = accumulated_dt
            
            # Use DT for X-axis if available
            if use_dt_axis and len(dt_data) == len(y_values) and any(dt_data):
                x_values = dt_data
                x_label = "Time (seconds)"
            else:
                x_values = list(range(len(y_values)))
                x_label = "Samples (newest ->)"
            
            self.plt.plot(x_values, y_values, marker=self.marker, color=color)
            marker_points_x = []
            marker_points_y = []
            if self._filter_plot is not None:
                for marker_dt, marker_val, _label in self._plot_markers.get(self._filter_plot, []):
                    marker_points_x.append(marker_dt if use_dt_axis else len(x_values) - 1)
                    marker_points_y.append(marker_val)
            else:
                for plot_num in sorted(self._plot_markers.keys()):
                    for _marker_dt, marker_val, _label in self._plot_markers.get(plot_num, []):
                        marker_points_x.append(len(marker_points_x))
                        marker_points_y.append(marker_val)
            if marker_points_x and marker_points_y:
                self.plt.scatter(marker_points_x, marker_points_y, marker="x", color=(255, 255, 0))
            
            # Improved auto-scaling: fit tightly to actual data
            data_min = min(y_values)
            data_max = max(y_values)
            data_span = data_max - data_min
            
            # Add 10% padding to data range for visual comfort
            if data_span > 0:
                padding = data_span * 0.10
            else:
                # If flat line, add small padding based on value magnitude
                padding = max(abs(data_min) * 0.05, 1.0)
            
            plot_min = data_min - padding
            plot_max = data_max + padding
            
            # Include 0 in the Y-axis if data is reasonably close to 0
            # (within 50% of data range from 0)
            if data_min >= 0 and data_min < data_span * 0.5:
                plot_min = min(0, plot_min)
            if data_max <= 0 and data_max > -data_span * 0.5:
                plot_max = max(0, plot_max)
            
            self.plt.ylim(plot_min, plot_max)
            
            # Handle cursor display
            cursor_info = ""
            if self._cursor_mode and self._cursor_index is not None:
                # Clamp cursor index to valid range
                if self._cursor_index < 0:
                    self._cursor_index = len(y_values) - 1
                self._cursor_index = min(self._cursor_index, len(y_values) - 1)
                
                # Get cursor values
                cursor_x = x_values[self._cursor_index]
                cursor_y = y_values[self._cursor_index]
                
                # Draw cursor marker (a vertical line or highlighted point)
                self.plt.scatter([cursor_x], [cursor_y], marker="x", color=(255, 255, 0))
                
                # Build cursor info for title
                cursor_info = f"  [Cursor: t={cursor_x:.0f}s, {short_name}={cursor_y:.2f}]"
            
            current = y_values[-1]
            title = f"{full_name}, {unit}: {current:.1f}  |  {plot_label}{cursor_info}"
        else:
            title = f"{full_name}, {unit}  |  {plot_label}  Waiting for data..."
            self.plt.ylim(typical_min, typical_max)
            x_label = "Time (seconds)"
        
        self.plt.title(title)
        self.plt.xlabel(x_label)
        self.plt.ylabel(f"{short_name}, {unit}")
        
        self.refresh()

    def add_data(self, parsed_data: dict, batch_mode: bool = False) -> None:
        """Add data from a parsed R-record.

        Args:
            parsed_data: Dictionary from EGM4Serial parser.
            batch_mode: If True, skip replotting (caller will replot manually).
        """
        # Get plot number (default to 0 if not present)
        plot_num = parsed_data.get('plot', 0)
        self._current_plot = plot_num

        # Track DT
        if 'dt' in parsed_data:
            self._current_dt = parsed_data['dt']

        # Detect Probe Type and switch config if needed
        if 'probe_type' in parsed_data:
            pt = parsed_data['probe_type']

            # Use raw INT probe type for logic
            # 0=IRGA Only, 8=SRC, 11=CPY, 7=PMR, 1/2/3=HTR
            new_config = self._get_config_for_type(pt)

            # ALWAYS emit on first data so legend knows the initial probe type
            if not self._first_data_received:
                self._first_data_received = True
                self._probe_type = pt
                self._channels_config = new_config
                self.post_message(self.ProbeTypeChanged(str(pt)))
            elif new_config != self._channels_config:
                # Subsequent changes
                self._probe_type = pt
                self._channels_config = new_config
                self.post_message(self.ProbeTypeChanged(str(pt)))

                # Update all existing plots with new channel keys if missing
                for p_num in self._plot_data:
                    p_chans = self._plot_data[p_num]
                    for key in new_config:
                        if key not in p_chans:
                            p_chans[key] = deque(maxlen=self._buffer_size)

        # Update per-plot probe type tracking
        self._plot_probe_types[plot_num] = str(parsed_data.get('probe_type', "GENERIC"))

        # Get channel storage for this plot
        plot_channels = self._get_plot_channels(plot_num)

        # Store DT (time) value for X-axis
        dt_value = parsed_data.get('dt', self._current_dt)
        if plot_num in self._plot_dt:
            self._plot_dt[plot_num].append(dt_value)

        # Standardize keys from parser to widget internal keys
        # We create a copy or alias to make the generic loop detecting 'cr' and 'hr' work
        if 'co2_ppm' in parsed_data:
            parsed_data['cr'] = parsed_data['co2_ppm']
        if 'h2o' in parsed_data:
            parsed_data['hr'] = parsed_data['h2o']

        # Map output keys from parser to internal channel keys
        # We can just iterate the current config and look for matching keys in parsed_data
        for ch_key in self._channels_config.keys():
            if ch_key in parsed_data:
                val = parsed_data[ch_key]
                try:
                    plot_channels[ch_key].append(float(val))
                except (ValueError, TypeError):
                    pass

        # Only replot if not in batch mode
        if not batch_mode:
            self.replot()

    def _get_config_for_type(self, pt: int | str) -> dict:
        """Return the correct channel config map for a probe type."""
        try:
            pt = int(pt)
        except (ValueError, TypeError):
            return CHANNELS_GENERIC
            
        if pt == 0: return CHANNELS_IRGA
        if pt == 8: return CHANNELS_SRC
        if pt == 11: return CHANNELS_CPY
        if pt == 7: return CHANNELS_PMR
        if pt in (1, 2, 3): return CHANNELS_HTR
        return CHANNELS_GENERIC

    def get_current_value(self, channel: str = None) -> float | None:
        """Get the latest value for a channel from current plot."""
        ch = channel or self._active_channel
        if self._current_plot in self._plot_data:
            plot_channels = self._plot_data[self._current_plot]
            if ch in plot_channels and plot_channels[ch]:
                return plot_channels[ch][-1]
        return None

    def clear_data(self) -> None:
        """Clear all chart data."""
        self._plot_data.clear()
        self._plot_dt.clear()
        self._plot_markers.clear()
        self._known_plots.clear()
        self._filter_plot = None
        self.replot()

    @property
    def current_plot(self) -> int:
        return self._current_plot

    @property
    def current_dt(self) -> int:
        return self._current_dt

    def add_marker(self, plot_num: int, dt_value: float, value: float, label: str) -> None:
        """Add a visual marker for note/sample events."""
        if plot_num not in self._plot_markers:
            self._plot_markers[plot_num] = deque(maxlen=200)
        self._plot_markers[plot_num].append((float(dt_value), float(value), label))
        self.replot()

    @property
    def data(self) -> dict[str, list[float]]:
        """Get all channel data as a dictionary (aggregated from all plots)."""
        result = {ch: [] for ch in CHANNELS_SRC}
        for plot_num in sorted(self._plot_data.keys()):
            for ch, values in self._plot_data[plot_num].items():
                result[ch].extend(list(values))
        return result

    def _switch_to_plot_config(self, plot_num: int | None) -> None:
        """Switch config to match the specified plot's stored probe type."""
        pt = "GENERIC"
        if plot_num is not None and plot_num in self._plot_probe_types:
            pt = self._plot_probe_types[plot_num]
        elif plot_num is None:
            # If viewing ALL, stick to current, or maybe use latest known?
            # Sticking to current active config is safest to minimize flashing
            return 
            
        # If the plot's type differs from active config, switch
        try:
             # Normalize pt for comparison
             pt_int = int(pt)
             current_int = int(self._probe_type) if self._probe_type != "GENERIC" else 0
             if pt_int == current_int:
                 return
        except (ValueError, TypeError):
             # String comparison fall back
             if str(pt) == str(self._probe_type):
                 return

        # Perform switch
        new_config = self._get_config_for_type(pt)
        self._probe_type = str(pt)
        self._channels_config = new_config
        self.post_message(self.ProbeTypeChanged(str(pt)))
        
        # Reset active channel if invalid in new config
        if self._active_channel not in new_config:
            self._active_channel = 'cr' if 'cr' in new_config else next(iter(new_config))


    def _watch_marker(self) -> None:
        """React to marker type being changed."""
        self.replot()
