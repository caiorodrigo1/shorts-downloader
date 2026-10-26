import io
import sys

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

# Force UTF-8 output on Windows to avoid encoding errors with special characters
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "channel": "bold magenta",
    "video": "bold white",
    "views": "bold cyan",
})

console = Console(theme=theme)


def get_rich_handler() -> RichHandler:
    return RichHandler(
        console=console,
        show_path=False,
        show_time=True,
        rich_tracebacks=True,
        tracebacks_show_locals=False,
        markup=True,
    )
