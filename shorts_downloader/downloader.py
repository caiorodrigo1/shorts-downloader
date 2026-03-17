import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yt_dlp
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
)

from shorts_downloader.console import console
from shorts_downloader.fetcher import VideoInfo

logger = logging.getLogger(__name__)

TIMEZONE = ZoneInfo("America/Sao_Paulo")


def download_videos(
    videos: list[VideoInfo],
    download_dir: Path,
    archive_file: Path | None = None,
) -> list[str]:
    """Download videos to a date-based subfolder."""
    today_str = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    day_dir = download_dir / today_str
    day_dir.mkdir(parents=True, exist_ok=True)

    downloaded_ids: list[str] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold]{task.description}[/bold]"),
        BarColumn(bar_width=30),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        overall = progress.add_task(
            f"Total (0/{len(videos)})",
            total=len(videos),
        )

        for i, video in enumerate(videos, 1):
            current_task = progress.add_task(
                f"{video.title[:45]}...",
                total=None,
            )

            def _progress_hook(d, _task_id=current_task):
                if d["status"] == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate")
                    downloaded = d.get("downloaded_bytes", 0)
                    if total:
                        progress.update(_task_id, total=total, completed=downloaded)
                elif d["status"] == "finished":
                    progress.update(_task_id, description=f"[success]{video.title[:45]}...[/success]")

            ydl_opts = {
                "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "outtmpl": str(day_dir / "%(title)s [%(id)s].%(ext)s"),
                "quiet": True,
                "no_warnings": True,
                "ignoreerrors": True,
                "progress_hooks": [_progress_hook],
            }

            if archive_file:
                ydl_opts["download_archive"] = str(archive_file)

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video.url])
                downloaded_ids.append(video.video_id)
                progress.update(current_task, description=f"[success]{video.title[:45]}[/success]")
            except Exception:
                progress.update(current_task, description=f"[error]ERRO: {video.title[:40]}[/error]")
                logger.error("Failed to download %s (%s)", video.title, video.video_id, exc_info=True)

            progress.update(overall, completed=i, description=f"Total ({i}/{len(videos)})")

    console.print(
        f"  [success]{len(downloaded_ids)}/{len(videos)} videos baixados com sucesso[/success]"
    )
    return downloaded_ids
