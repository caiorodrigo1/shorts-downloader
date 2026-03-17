from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

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
