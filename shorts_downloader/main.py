import argparse
import logging
import signal
import sys
import time
from datetime import datetime, timedelta

import schedule
from rich.panel import Panel
from rich.table import Table

from shorts_downloader.config import AppConfig, load_config
from shorts_downloader.console import console, get_rich_handler
from shorts_downloader.downloader import download_videos
from shorts_downloader.fetcher import fetch_today_videos
from shorts_downloader.history import load_downloaded_ids, record_downloads

logger = logging.getLogger("shorts_downloader")

shutdown_requested = False


def run_job(config: AppConfig) -> None:
    console.print()
    console.rule("[bold cyan]Shorts Downloader[/bold cyan]")
    console.print()

    now = datetime.now(config.timezone)
    valid_dates = {(now - timedelta(days=d)).strftime("%Y%m%d") for d in range(3)}
    downloaded_ids = load_downloaded_ids(config.history_file)

    info_table = Table(show_header=False, box=None, padding=(0, 2))
    info_table.add_column(style="bold")
    info_table.add_column()
    info_table.add_row("Data", now.strftime("%d/%m/%Y"))
    info_table.add_row("Margem", "Ate 48h atras")
    info_table.add_row("Canais", str(len([c for c in config.channels if c.enabled])))
    info_table.add_row("Ja baixados", f"{len(downloaded_ids)} videos")
    info_table.add_row("Top videos", str(config.total_videos))
    info_table.add_row("Salvar em", str(config.download_dir))
    console.print(Panel(info_table, title="[bold]Configuracao[/bold]", border_style="cyan"))
    console.print()

    all_videos = []

    active_channels = [c for c in config.channels if c.enabled]
    skipped = [c for c in config.channels if not c.enabled]

    for ch in skipped:
        console.print(f"  [dim]Pulando canal desativado: {ch.name}[/dim]")

    for channel in active_channels:
        console.print(f"  [channel]>> {channel.name}[/channel]")
        try:
            videos = fetch_today_videos(
                channel_url=channel.url,
                already_downloaded=downloaded_ids,
                valid_dates=valid_dates,
            )
            if videos:
                console.print(f"     [success]{len(videos)} shorts encontrados[/success]")
            else:
                console.print(f"     [dim]Nenhum short novo hoje[/dim]")
            all_videos.extend(videos)
        except Exception:
            console.print(f"     [error]Erro ao buscar videos![/error]")
            logger.error("Failed to fetch videos for %s", channel.name, exc_info=True)

    console.print()

    if not all_videos:
        console.print(Panel(
            "[dim]Nenhum short novo encontrado hoje em nenhum canal[/dim]",
            border_style="yellow",
        ))
    else:
        all_videos.sort(key=lambda v: v.view_count, reverse=True)
        top_videos = all_videos[:config.total_videos]

        ranking = Table(title="Top Shorts do Dia", border_style="cyan", title_style="bold cyan")
        ranking.add_column("#", style="bold", justify="right", width=3)
        ranking.add_column("Titulo", style="video", max_width=50)
        ranking.add_column("Views", style="views", justify="right")

        for i, v in enumerate(top_videos, 1):
            ranking.add_row(str(i), v.title, f"{v.view_count:,}")

        console.print(ranking)
        console.print()

        archive_file = config.download_dir / "yt-dlp-archive.txt"
        new_ids = download_videos(top_videos, config.download_dir, archive_file)

        if new_ids:
            record_downloads(config.history_file, new_ids, "all")
            downloaded_ids.update(new_ids)

    console.print()
    console.rule("[bold green]Concluido[/bold green]")
    console.print()


def _handle_signal(signum: int, _frame) -> None:
    global shutdown_requested
    sig_name = signal.Signals(signum).name
    console.print(f"\n[warning]Recebido {sig_name}, encerrando...[/warning]")
    shutdown_requested = True


def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube Shorts Downloader")
    parser.add_argument("--now", action="store_true", help="Run immediately")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()

    config = load_config()

    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format="%(message)s",
        datefmt="%H:%M:%S",
        handlers=[get_rich_handler()],
    )

    if args.now:
        run_job(config)
        if args.once:
            return

    if not args.once or not args.now:
        schedule.every().day.at(config.schedule_time, str(config.timezone)).do(
            run_job, config
        )
        console.print(Panel(
            f"Agendado para [bold]{config.schedule_time}[/bold] ({config.timezone})\n"
            f"Pressione [bold]Ctrl+C[/bold] para sair",
            title="[bold]Modo Agendado[/bold]",
            border_style="green",
        ))

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    while not shutdown_requested:
        schedule.run_pending()
        time.sleep(30)

    console.print("[success]Encerrado.[/success]")


if __name__ == "__main__":
    main()
