# Open EGM-4

A terminal user interface for the PP Systems EGM-4 Environmental Gas Monitor.

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

## Features

- Real-time CO₂ charting with multi-channel support
- Session persistence with automatic database saving and resume capability
- Multiple different probe types, including SRC-1
- Plot-based data filtering for multi-location measurements
- Smart export with plot and date filtering
- Auto-saves raw data to timestamped log files and SQLite database
- Device status indicators for warmup temperature and zero check progress

## Installation

Install directly from GitHub using pip:

```bash
pip install git+https://github.com/mmorgans/open-egm4
```

Or using [pipx](https://github.com/pypa/pipx) (recommended for isolated environments):

```bash
pipx install git+https://github.com/mmorgans/open-egm4
```

> **For Beginners**: If you are new to the terminal or don't have Python installed, please see our **[Detailed Installation Guide](egm4-guide.org)** for step-by-step instructions.

### For Developers

If you want to modify the code:

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

### Installation Troubleshooting

#### macOS: "python: command not found"

On macOS, use `python3` and `pip3` instead of `python` and `pip`:

```bash
python3 --version
pip3 install .
```

#### macOS: "pip: command not found"

If pip isn't installed, run this to install it:

```bash
python3 -m ensurepip --upgrade
```

Alternatively, install Python via Homebrew which includes pip:

```bash
brew install python@3.13
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
| `q` | Quit and save data automatically |
| `e` | Export to CSV with plot and date filters |
| `c` | Clear chart data |
| `p` | Pause or resume data stream |
| `n` | Add timestamped note to log |
| `?` | Help screen |

### Chart Controls

| Key | Action |
|-----|--------|
| `.` / `>` | Next plot |
| `,` / `<` | Previous plot |

### Connect Screen

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate port or session list |
| `Enter` | Connect to port or resume session |
| `n` | Start new session |
| `q` | Quit |

## EGM-4 Device Operation

### Dumping Stored Data

1. Press `4` on the EGM-4 for DMP
2. Press `2` for DATA DUMP
3. Press any key to start dump

### Live Measurements

1. Press `1` on the EGM-4 for REC.

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
- `co2_ppm`, `h2o_mb`, `temp_c` - IRGA readings
- `par`, `rh_pct` - Probe measurements
- `dc_ppm`, `dt_s`, `sr_rate` - Change in CO₂ and respiration rate
- `atmp_mb`, `probe_type` - Atmospheric pressure and probe code

## License

MIT License - See LICENSE file for details.
