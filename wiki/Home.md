# Welcome to Open-EGM4

Open-EGM4 is a terminal-based interface for the PP Systems EGM-4 CO₂ Gas Analyzer. It replaces legacy software with a keyboard-driven application for field work and data analysis.

## Key Features

- Live Monitoring: Real-time plotting of CO₂, Temperature, Humidity, and PAR
- Session Persistence: Automatic database saving with resume capability
- Keyboard-First Design: Optimized for field laptops, navigate entirely without a mouse
- Dynamic Charts: Auto-scaling, plot filtering, and multi-channel support
- Plot Management: Track multiple measurement plots and filter data by location
- Smart Export: Filter by plot and date with automatic intelligent filename generation
- Plug-and-Play: Automatic serial port detection and connection handling

## Navigation

- [Installation](Installation)
- [User Guide](User-Guide)
- [Exporting Data](Exporting-Data)
- [Release Process](Release-Process)

## Quick Start

```bash
# Install via pip
git clone https://github.com/mmorgans/open-egm4.git
cd open-egm4
pip install .

# Run
open-egm4
```

## What's New

### Session Resume
All data is automatically saved to a SQLite database. Resume any previous session from the connection screen to continue where you left off.

### Smart Export
New export screen with plot and date filtering. Filenames are automatically generated based on your filters for easy organization.

### Database Persistence
Every measurement is saved immediately. You won't lose data even if you quit unexpectedly.
