# Changelog

All notable changes to this project are documented in this file.

## v1.5.0 - 2026-02-13

### Added
- Static sampling workflow with guided multi-step cycle (`inject -> settle/capture -> ambient flush`) and reset action (`x`).
- Static sample metadata in exports: `sample_id`, `sample_label`, `sample_ppm`, `sample_peak_ppm`.
- CSV event-row export for regular notes (`type=NOTE`) so notes are preserved outside static mode too.
- Marker plotting for note/sample events on the chart.
- Data-quality counters in stats panel: `Parsed/Err`, `Reconnects`, and `Serial Err`.
- CI workflow (`.github/workflows/ci.yml`) running compile + parser tests across Python 3.10-3.13.
- Release process documentation (`wiki/Release-Process.md`).
- Parser regression tests (`tests/test_parser.py`) for SRC, non-SRC ATMP parsing, CPY signed SR, warmup and zero-check records.

### Changed
- Static sampling guidance now appears in the status area (no static-mode popup); prompts are concise and operator-focused.
- Event log now wraps long lines to remove horizontal scrolling.
- Stats panel layout adjusted to avoid clipping when static mode status text is shown.
- Connect screen version reporting now prefers local git tag/describe values over stale installed metadata.
- Export docs/README/wiki updated for static sampling workflow, new CSV fields, and release flow.

### Fixed
- Export wizard now includes `rht_c` in CSV output (previously omitted).
- Parser handling improvements for atmospheric pressure and CPY signed respiration values.
- Release workflow permissions set explicitly for GitHub release creation.
