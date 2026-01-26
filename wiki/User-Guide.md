# User Guide

## Getting Started

### Connection Screen

When you launch Open-EGM4, the Connection Screen shows two main sections:

1. Available Ports - USB serial devices detected on your system
2. Recent Sessions - Previously saved measurement sessions

#### Connecting to EGM-4

- Use up and down arrow keys to navigate the port list
- Press Enter to connect to the selected port
- The app will attempt auto-connection after a brief countdown

#### Resuming a Session

- Navigate to the "Recent Sessions" section
- Use up and down arrows to select a session
- Press Enter to resume and load all previous data
- Press N to start a new session instead

## Monitor Screen

The main screen where you view and collect data.

### Layout

- Left Panel: Real-time chart with channel legend
- Right Panel: Statistics table and event log
- Footer: Device status and keyboard shortcuts

### Live Data Collection

Real-Time Mode (Type M):
1. Start measurement on EGM-4 device
2. Data streams automatically
3. Chart updates in real-time

Memory Dump (Type R):
1. On EGM-4: Press 4, then 2, then any key
2. App shows "MEMORY DUMP" indicator
3. Progress shown in log panel
4. All records saved to database

### Chart Controls

| Key | Action |
|-----|--------|
| `+` or `=` | Zoom out, increase time span |
| `-` or `_` | Zoom in, decrease time span |
| `.` or `>` | Next plot if multiple plots |
| `,` or `<` | Previous plot |

### Data Management

| Key | Action |
|-----|--------|
| `P` | Pause or Resume data stream |
| `C` | Clear current chart, data still saved |
| `N` | Add timestamped note to log |
| `E` | Export data to CSV |
| `Q` | Quit, auto-saves session |

### Plot Filtering

When working with multiple measurement plots (Plot 0, Plot 1, etc.):

- Press period or greater-than to cycle to the next plot
- Press comma or less-than to cycle to the previous plot
- Chart automatically updates to show only selected plot
- Legend shows current plot number

### Device Status Indicators

The footer displays real-time device status:

- WARMUP: XXC - Device warming up, target around 55°C
- ZERO CHECK: Xs - Calibration in progress, 15s countdown
- REAL-TIME - Live measurement mode
- MEMORY DUMP - Downloading stored data

## Exporting Data

Press E from the Monitor screen to open the Export menu.

### Export Workflow

1. Filter by Plot (Press p)
   - Select which plots to include
   - Space to toggle selection
   - a to select all, n to select none

2. Filter by Date (Press d)
   - Select which dates to include
   - Leave empty to export ALL dates
   - c to clear selection

3. Export (Press e)
   - Filename auto-generated based on filters
   - Shows record count preview
   - Saves to current directory

### Export File Naming

Files are automatically named based on your filters:

- `egm4_YYYYMMDD_HHMMSS.csv` - All data
- `egm4_plot7_YYYYMMDD_HHMMSS.csv` - Single plot
- `egm4_3plots_YYYYMMDD_HHMMSS.csv` - Multiple plots
- `egm4_plot7_2026-01-26_YYYYMMDD_HHMMSS.csv` - With date filter

## Session Persistence

All data is automatically saved to `egm4_data.sqlite` as you collect it.

### Auto-Save Features

- Every record is saved immediately
- Timestamps are preserved exactly
- Raw log file also created
- Can safely quit anytime, data is safe

### Resume Capability

When resuming a session:
- All data loads exactly as it was
- Chart shows complete history
- Can continue collecting more data
- Export works on entire session

### Database Location

The SQLite database `egm4_data.sqlite` is created in the directory where you run the app.

Tips:
- Keep database with your project data
- Backup periodically for long-term storage
- Database includes ALL sessions, not just one

## Tips and Best Practices

### Field Work

- Start app before connecting EGM-4
- Let device complete warmup before measurements
- Use N key to annotate important events
- Export frequently during long sessions

### Data Quality

- Monitor device status indicators
- Watch for stable readings before recording
- Use plot numbers to organize measurements
- Add notes for context such as plot location and conditions

### Performance

- Large sessions with over 1000 records may take a moment to load on resume
- Chart uses smart rendering to stay responsive
- Clear chart with C if you only need recent data visible
