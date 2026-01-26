# Open EGM-4

A terminal user interface for the PP Systems EGM-4 Environmental Gas Monitor.

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

## Features

- Real-time CO₂ charting with multi-channel support
- Session persistence with automatic database saving and resume capability
- SRC-1 soil respiration chamber support with delta CO₂ and respiration rate
- Plot-based data filtering for multi-location measurements
- Smart export with plot and date filtering
- Auto-saves raw data to timestamped log files and SQLite database
- Device status indicators for warmup temperature and zero check progress
- Cross-platform support for macOS, Windows, and Linux

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
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
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
| `Q` | Quit and save data automatically |
| `E` | Export to CSV with plot and date filters |
| `C` | Clear chart data |
| `P` | Pause or resume data stream |
| `N` | Add timestamped note to log |
| `?` | Help screen |

### Chart Controls

| Key | Action |
|-----|--------|
| `+` / `=` | Increase time span, zoom out |
| `-` / `_` | Decrease time span, zoom in |
| `.` / `>` | Next plot |
| `,` / `<` | Previous plot |

### Connect Screen

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate port or session list |
| `Enter` | Connect to port or resume session |
| `N` | Start new session |
| `Q` | Quit |

## EGM-4 Device Operation

### Dumping Stored Data

1. Press `4` on the EGM-4 for Data Output
2. Press `2` for RS232
3. Press any key to start dump

The app will display "MEMORY DUMP" and show download progress.

### Live Measurements

1. Press `1` on the EGM-4 for Measurement
2. Data streams in real-time

The app will display "REAL-TIME" mode indicator.

### Device Warmup

When the EGM-4 is warming up, you'll see `WARMUP: XXC` until it reaches operating temperature around 55°C.

### Zero Check

During zero check, you'll see `ZERO CHECK: Xs` counting up to 15 seconds before you can take a measurement.

## Output Files

| File | Description |
|------|-------------|
| `egm4_data.sqlite` | Session database, auto-saved, enables resume |
| `raw_dump_YYYY-MM-DD.log` | Raw serial data, auto-saved each session |
| `egm4_data_YYYYMMDD_HHMMSS.csv` | Parsed data export with all fields |

### CSV Columns

The exported CSV includes all fields from the EGM-4 record format:

- `timestamp` - When the record was received
- `type` - M for real-time or R for memory
- `plot`, `record` - Plot and record numbers
- `day`, `month`, `hour`, `minute` - Device timestamp
- `co2_ppm`, `h2o_mb`, `temp_c` - Core IRGA readings
- `par`, `rh_pct` - Probe measurements for SRC-1
- `dc_ppm`, `dt_s`, `sr_rate` - Delta CO₂ and respiration rate
- `atmp_mb`, `probe_type` - Atmospheric pressure and probe code

## License

MIT License - See LICENSE file for details.
