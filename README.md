# Open EGM-4 Interface

A terminal-based interface for the PP Systems EGM-4 Environmental Gas Monitor.

## Quick Start

### Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Running the TUI

```bash
./venv/bin/python tui_main.py
```

## Features

- **Live Data Display**: Real-time terminal output showing incoming serial data
- **Statistics Panel**: Track data points and latest readings
- **CSV Export**: Save all recorded data to timestamped CSV files
- **Simple Controls**: 
  - Ctrl+C to stop monitoring
  - Automatic prompt to export data on exit

## Serial Configuration

The interface is configured for EGM-4 default settings:
- Baud rate: 9600
- Data bits: 8
- Parity: None
- Stop bits: 2

## Usage

1. Connect your EGM-4 to your computer via USB
2. Run `./venv/bin/python tui_main.py`
3. Select the appropriate serial port from the list
4. Monitor live data in the terminal
5. Press Ctrl+C when done
6. Choose whether to export data to CSV

## Project Structure

```
open-egm4/
├── tui_main.py           # Terminal interface (main entry point)
├── src/
│   └── egm_interface.py  # Serial communication backend
├── requirements.txt
└── README.md
```

## Troubleshooting

**No ports listed?**
- Ensure the EGM-4 is connected and powered on
- Check that USB drivers are installed
- Try unplugging and reconnecting the device

**Connection fails?**
- Verify the EGM-4 is not being accessed by another program
- Check cable connections
- Ensure you have permission to access serial ports (may need `sudo` on Linux)

**No data appearing?**
- Confirm the EGM-4 is transmitting (check device settings)  
- Verify baud rate matches device settings (9600 default)
