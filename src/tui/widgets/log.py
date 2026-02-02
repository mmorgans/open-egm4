"""Log Widget - Scrollable event log for raw data stream."""

import sys
from datetime import datetime
from textual.widgets import RichLog

# Symbol definitions
def get_symbol(name: str, force_unicode: bool = False) -> str:
    """Get symbol based on platform and force_unicode flag."""
    is_windows = sys.platform == "win32"
    use_unicode = not is_windows or force_unicode
    
    symbols = {
        "check": ("\u2713", "[OK]"),
        "warn":  ("\u26a0", "[!]"),
        "info":  ("\u2139", "[i]"),
    }
    
    uni, ascii_ = symbols.get(name, ("?", "?"))
    return uni if use_unicode else ascii_


class LogWidget(RichLog):
    """A scrollable log widget for displaying serial data events."""

    def __init__(
        self,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
        max_lines: int = 100,
    ) -> None:
        super().__init__(
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
            max_lines=max_lines,
            highlight=True,
            markup=True,
        )
        self.can_focus = False
        # Download counter state
        self._download_count: int = 0
        self._download_line_id: str | None = None
        self._is_downloading: bool = False

    def log_event(self, message: str, style: str = "") -> None:
        """Log an event with timestamp.

        Args:
            message: The message to log.
            style: Optional Rich style for the message.
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        if style:
            formatted = f"[dim]{timestamp}[/dim] [{style}]{message}[/{style}]"
        else:
            formatted = f"[dim]{timestamp}[/dim] {message}"
        self.write(formatted)

    def log_data(self, plot: int, record: int, co2: float) -> None:
        """Log a data record in standardized format.

        Args:
            plot: Plot number.
            record: Record number.
            co2: CO2 value in ppm.
        """
        self.log_event(f"[P{plot:02d}-R{record:04d}] CO₂: {co2:.0f} ppm", "green")

    def log_error(self, message: str) -> None:
        """Log an error message."""
        sym = get_symbol("warn", getattr(self.app, "force_unicode", False))
        self.log_event(f"{sym} {message}", "bold red")

    def log_info(self, message: str) -> None:
        """Log an informational message."""
        sym = get_symbol("info", getattr(self.app, "force_unicode", False))
        self.log_event(f"{sym} {message}", "cyan")

    def log_success(self, message: str) -> None:
        """Log a success message."""
        sym = get_symbol("check", getattr(self.app, "force_unicode", False))
        self.log_event(f"{sym} {message}", "bold green")

    def log_complete(self) -> None:
        """Log the download complete message."""
        self._is_downloading = False
        self._download_count = 0
        self.write("[bold green]━━━━━━━ DOWNLOAD COMPLETE ━━━━━━━[/bold green]")

    def start_download(self) -> None:
        """Start download mode with compact counter."""
        self._is_downloading = True
        self._download_count = 0
        self.log_event(">> Memory dump starting...", "cyan")

    def log_download_record(self, plot: int, record: int, co2: float) -> None:
        """Log a download record with compact counter.
        
        Instead of logging each record, shows a single updating counter.
        """
        self._download_count += 1
        # Only log every 10 records to reduce spam, or first record
        if self._download_count == 1 or self._download_count % 10 == 0:
            self.log_event(
                f">> Downloading: {self._download_count} records (P{plot:02d}-R{record:04d} CO₂:{co2:.0f})",
                "cyan"
            )

    @property
    def is_downloading(self) -> bool:
        """Check if currently in download mode."""
        return self._is_downloading

    @property
    def download_count(self) -> int:
        """Get current download count."""
        return self._download_count
