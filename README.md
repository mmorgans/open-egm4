# Open EGM-4

Terminal interface for the PP Systems EGM-4 Environmental Gas Monitor.

## Features

- **Real-time CO₂ charting** with plotext
- **Auto-saves raw data** to `raw_dump_YYYY-MM-DD.log`
- **CSV export** with parsed columns
- **Chamber stability** indicator
- **Auto-connects** to USB serial port

## Installation

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
./venv/bin/python main.py
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Q` | Quit |
| `E` | Export CSV |
| `C` | Clear log/chart |
| `H` | Toggle help |
| `R` | Reconnect |

### EGM-4 Device

- **Data Dump**: Press 4 → 2 → any key
- **Live Mode**: Press 1 (Measurement)

## Output Files

- `raw_dump_YYYY-MM-DD.log` - Raw serial data (auto-saved)
- `egm4_YYYYMMDD_HHMMSS.csv` - Parsed data export

## Requirements

- Python 3.8+
- pyserial
- textual
- textual-plotext
