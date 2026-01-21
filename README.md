# Open EGM-4

A modern Terminal User Interface (TUI) for the PP Systems EGM-4 Environmental Gas Monitor.

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

## Features

- **Real-time CO₂ charting** with multi-channel support (CO₂, H₂O, PAR, Temperature, etc.)
- **SRC-1 soil respiration chamber** support with delta CO₂ and respiration rate
- **Plot-based data filtering** - view data from specific measurement plots
- **Auto-saves raw data** to timestamped log files
- **CSV export** with all parsed fields
- **Device status indicators** - warmup temperature, zero check progress
- **Cross-platform** - works on macOS, Windows, and Linux

## Installation

### Quick Install

```bash
git clone https://github.com/mmorgans/open-egm4
cd open-egm4
pip install .
```

Then run from anywhere:
```bash
open-egm4
```

### Development Install

```bash
git clone https://github.com/mmorgans/open-egm4
cd open-egm4
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

Run with:
```bash
open-egm4
# or
./venv/bin/python main.py
```

## Platform Notes

### Linux

You may need to add your user to the `dialout` group to access serial ports:

```bash
sudo usermod -a -G dialout $USER
```

Log out and back in for the change to take effect.

### Windows

USB-to-serial adapters may require driver installation. Ports appear as `COM1`, `COM3`, etc.

### macOS

USB-to-serial adapters should work automatically. Ports appear as `/dev/cu.usbserial-*`.

## Keyboard Shortcuts

### Monitor Screen

| Key | Action |
|-----|--------|
| `Q` | Quit (saves data) |
| `E` | Export to CSV |
| `C` | Clear all data |
| `P` | Pause/resume data stream |
| `B` | Big mode (large CO₂ display) |
| `D` | Toggle dark/light theme |
| `?` | Help screen |

### Channel Selection (1-9)

| Key | Channel |
|-----|---------|
| `1` | CO₂ Raw (ppm) |
| `2` | H₂O Raw (mb) |
| `3` | PAR (µmol/m²/s) |
| `4` | Chamber %RH |
| `5` | Soil Temperature (°C) |
| `6` | Delta CO₂ (ppm) |
| `7` | Soil Respiration Rate |
| `8` | Atmospheric Pressure |
| `9` | Delta Time (s) |

### Chart Controls

| Key | Action |
|-----|--------|
| `+` / `=` | Increase time span |
| `-` / `_` | Decrease time span |
| `.` / `>` | Next plot |
| `,` / `<` | Previous plot |

## EGM-4 Device Operation

### Dumping Stored Data
1. Press `4` (Data Output)
2. Press `2` (RS232)
3. Press any key to start dump

The app will display "MEMORY DUMP" and show download progress.

### Live Measurements
1. Press `1` (Measurement)
2. Data streams in real-time

The app will display "REAL-TIME" mode indicator.

### Device Warmup
When the EGM-4 is warming up, you'll see `WARMUP: XXC` until it reaches operating temperature (~55°C).

### Zero Check
During zero check, you'll see `ZERO CHECK: Xs` counting up to 15 seconds before you take take a measurement.

## Output Files

| File | Description |
|------|-------------|
| `raw_dump_YYYY-MM-DD.log` | Raw serial data (auto-saved each session) |
| `egm4_data_YYYYMMDD_HHMMSS.csv` | Parsed data export with all fields |

### CSV Columns

The exported CSV includes all fields from the EGM-4 record format:

- `timestamp` - When the record was received
- `type` - M (real-time) or R (memory)
- `plot`, `record` - Plot and record numbers
- `day`, `month`, `hour`, `minute` - Device timestamp
- `co2_ppm`, `h2o_mb`, `rht_c` - Core IRGA readings
- `par`, `rh_pct`, `temp_c` - Probe measurements (SRC-1)
- `dc_ppm`, `dt_s`, `sr_rate` - Delta CO₂ and respiration rate
- `atmp_mb`, `probe_type` - Atmospheric pressure and probe code

## Requirements

- Python 3.10+
- textual >= 0.40.0
- textual-plotext >= 0.2.0
- pyserial >= 3.5

## License

MIT License - See LICENSE file for details.
