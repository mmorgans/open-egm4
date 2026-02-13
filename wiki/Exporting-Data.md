# Exporting Data

The Export screen provides a keyboard-driven interface for filtering and exporting your data to CSV format.

## Opening the Export Menu

Press E from the Monitor screen at any time.

## Export Screen Layout

```
Export Data
120 records (all data)
→ egm4_20260126_124530.csv

Filters
  [p]  Plots: ALL
  [d]  Dates: ALL

Actions
  [e]  Export Now
  [q]  Cancel
```

## Workflow

### Step 1: Filter by Plot (Optional)

Press p to open plot selection:

```
Select Plots
[ ] Plot 0
[x] Plot 7
[ ] Plot 8
```

Controls:
- Up and down arrows - Navigate list
- Space - Toggle selection
- a - Select all plots
- n - Deselect all plots  
- p or ESC - Done, return to main menu

Effect on filename:
- Single plot: `egm4_plot7_...csv`
- Multiple plots: `egm4_3plots_...csv`
- All plots: `egm4_...csv`

### Step 2: Filter by Date (Optional)

Press d to open date selection:

```
Select Dates
[x] 2026-01-25
[x] 2026-01-26
[ ] 2026-01-27
```

Controls:
- Up and down arrows - Navigate list
- Space - Toggle selection
- a - Select all dates
- n - Deselect all dates
- c - Clear all, show ALL dates
- d or ESC - Done, return to main menu

Effect on filename:
- Single date: `egm4_2026-01-26_...csv`
- Date range: `egm4_2026-01-25to2026-01-27_...csv`
- All dates: No date suffix

### Step 3: Export

Press e from the main export screen.

What happens:
1. Data is filtered based on your selections
2. Filename is auto-generated
3. CSV is written to `~/Downloads` if available (otherwise current directory)
4. Success notification shows file size
5. Export menu closes

## Filtering Behavior

### Plot Filtering

Only records matching selected plots are exported:
- If Plot 7 selected: Only Plot 7 records exported
- If no plots selected: Warning shown, no records match filters
- If all plots selected: All records exported

### Date Filtering

Filters by the timestamp field:
- Empty selection (default): ALL dates included
- Selected dates: Only records from those dates
- Date comparison uses the date portion only, ignores time

### Combined Filters

Filters are applied with AND logic:
- Must match selected plots AND selected dates
- More restrictive means fewer records
- Preview shows filtered count before export

## Examples

### Example 1: Export Single Plot

1. Press E
2. Press p
3. Navigate to Plot 7, press Space to select
4. Navigate to other plots, press Space to deselect
5. Press p to return
6. Press e to export

Result: `egm4_plot7_20260126_124530.csv`

### Example 2: Export Date Range

1. Press E
2. Press d
3. Press n to deselect all
4. Navigate and select 2026-01-25 and 2026-01-26
5. Press d to return
6. Press e to export

Result: `egm4_2026-01-25to2026-01-26_20260126_124530.csv`

### Example 3: Export Everything

1. Press E
2. Press e immediately

Result: `egm4_20260126_124530.csv` with all data

## CSV Format

### Columns

All exports include these columns:

| Column | Description |
|--------|-------------|
| `timestamp` | ISO 8601 timestamp, when record received |
| `type` | Record type, M for real-time or R for memory |
| `plot` | Plot number, 0 through 99 |
| `record` | Record number, 1 through 9999 |
| `day`, `month`, `hour`, `minute` | Device timestamp components |
| `co2_ppm` | CO₂ concentration in ppm |
| `h2o_mb` | H₂O vapor pressure in mbar |
| `rht_c` | IRGA RH sensor temperature in degrees Celsius |
| `temp_c` | Temperature in degrees Celsius |
| `atmp_mb` | Atmospheric pressure in mbar |
| `par` | PAR light in µmol/m²/s, SRC-1 only |
| `rh_pct` | Relative humidity in percent, SRC-1 only |
| `probe_type` | Probe type code, 0 for IRGA, 8 for SRC |
| `dc_ppm` | Delta CO₂ in ppm, SRC-1 only |
| `dt_s` | Elapsed time in seconds |
| `sr_rate` | Soil respiration rate, SRC-1 only |
| `note` | Free-form note text |
| `sample_id` | Static sample sequence number |
| `sample_label` | User-entered sample label |
| `sample_ppm` | Captured ppm at sample time |
| `sample_peak_ppm` | Peak ppm observed between injection and settled capture |

### Notes

- Empty cells appear for probe-specific fields when not applicable
- Headers are always included
- Data order matches session capture order
- UTF-8 encoding
- Regular `N` key notes are exported as `type=NOTE` rows

## Troubleshooting

No records match filters:
- You have filtered too aggressively
- Try selecting more plots or dates
- Press q and verify data exists in Monitor screen

File already exists:
- Each export gets unique timestamp in filename
- Safe to export multiple times
- Old files are never overwritten

Wrong data exported:
- Verify plot numbers in chart, use period and comma to cycle
- Check date filters match your measurement times
- Preview count should match expectations
