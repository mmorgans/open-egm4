# Changelog

## Unreleased

### Recording and recovery
- Pause now freezes only the chart; database recording, CSV buffering, live values, and static sample capture continue.
- Quit and Ctrl+C share a shutdown path, including Ctrl+C from dialogs. Shutdown retains in-flight serial readings, drains ordered database writes, and creates a UTF-8 CSV safety export.
- Failed automatic exports leave the app open with buffered readings available for manual export or retry.
- Database initialization and write failures remain visible in the status panel.
- Session storage preserves device timestamps, RHT, raw records, notes, and static sample metadata using additive database migrations. Resume restores notes and sample markers.
- Raw serial logs are saved under `~/.open-egm4/logs/`, independent of the launch directory.

### Analysis and compatibility
- The concentration slope uses device elapsed time when available, falls back to a monotonic clock for live records, and resets across plot, probe, record-mode, and elapsed-time cycle changes.
- Memory records without elapsed time do not display an arrival-time-derived slope. The regression window is 30 points, and valid zero slopes display as zero.
- Regression results include slope standard error, bounded R², and a backwards-compatible flux alias.
- Serial parsing accepts CR, LF, and CRLF record separators while retaining incomplete records. Blocking serial operations use the active event loop.
- Manual and automatic CSV exports share one column definition.
- Installers enforce Python 3.10+; Windows big mode uses plain digits unless Unicode is explicitly enabled.

### Documentation and tests
- Updated README, in-app help, and user/export guides for recording, resume, export fields, log locations, and slope behavior.
- Added regression tests for parsing, analysis, database metadata, and hardware-free recording workflows, including pause, resume, dialog shutdown, save failures, export retry, and in-flight serial reads.

## v1.5.1 - 2026-02-13

### Added
- Installer version visibility on both macOS/Linux and Windows:
- Shows currently installed `open-egm4` version.
- Shows latest available tagged release version from GitHub.
- Shows update status (`update available`, `up to date`, `ahead of latest release`, or `unable to compare`).

### Changed
- Installer banner text no longer hardcodes an old installer version string.
- Installer completion output now reports the installed app version after install/update/repair.

### Docs
- README and Installation wiki updated to document installer version comparison behavior.

## v1.5.0 - 2026-02-13

### Added
- Much improved static sampling workflow mode (m) with some guidance in the status box
- Improved export logic so that static sample metadata is included: `sample_id`, `sample_label`, `sample_ppm`, `sample_peak_ppm`
- CSV event-row export for regular notes (`type=NOTE`) for notes made in and out of static mode
- Marker plotting for note/sample made on the chart
- Data-quality counters in stats panel: `Parsed/Err`, `Reconnects`, and `Serial Err`.

### Fixed
- A bunch of stability and data safety changes, notably:
- Generic atmospheric pressure no longer defaults to 0 on non-SRC records
- Clear All Data feature now clears export/session buffers and flux/timing state
- Stats box no longer displays valid zero values as ---
- CPY/CFX respiration now stores sr_sign and materalizes signed sr
- Export wizard now includes `rht_c` in CSV output. My bad!
- Parser handling improvements for atmospheric pressure and CPY signed respiration values
- Inconsistant version numbering on connection screen
- Event log text now wraps correctly


### Meta changes
- Updated keybindings and DB location in README
- Installation wiki now (correctly) requires Python 3.10+, python3, and pip install -e
- Updated user guide to include resume flow with s, chart controls, export destination, and DB path
- Export wiki now has actual save location and correct record ordering behavior
