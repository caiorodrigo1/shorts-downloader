import logging
from dataclasses import dataclass

import yt_dlp
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn

from shorts_downloader.console import console

logger = logging.getLogger(__name__)


@dataclass
class VideoInfo:
    video_id: str
    title: str
    url: str
    view_count: int
    upload_date: str


def fetch_today_videos(
    channel_url: str,
    already_downloaded: set[str],
    valid_dates: set[str],
) -> list[VideoInfo]:
    """Fetch recent videos (up to 48h) from a channel's /shorts tab."""
    ydl_opts = {
        "extract_flat": "in_playlist",
        "playlistend": 50,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
    }

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("Buscando lista de shorts...", total=None)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(channel_url, download=False)

    if not result or "entries" not in result:
        return []

    entries = [e for e in result["entries"] if e is not None]
    entries = [e for e in entries if e.get("id") not in already_downloaded]

    videos: list[VideoInfo] = []
    needs_full_extract: list[dict] = []

    for entry in entries:
        vid_id = entry.get("id")
        upload_date = entry.get("upload_date")
        view_count = entry.get("view_count")

        if upload_date and view_count is not None:
            if upload_date in valid_dates:
                videos.append(VideoInfo(
                    video_id=vid_id,
                    title=entry.get("title", "Unknown"),
                    url=entry.get("url") or f"https://www.youtube.com/shorts/{vid_id}",
                    view_count=view_count,
                    upload_date=upload_date,
                ))
        else:
            needs_full_extract.append(entry)

    if needs_full_extract:
        full_opts = {
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
        }
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task(
                "Verificando metadados...",
                total=len(needs_full_extract),
            )
            with yt_dlp.YoutubeDL(full_opts) as ydl:
                for entry in needs_full_extract:
                    vid_id = entry.get("id")
                    vid_url = entry.get("url") or f"https://www.youtube.com/shorts/{vid_id}"
                    try:
                        info = ydl.extract_info(vid_url, download=False)
                        if not info:
                            progress.advance(task)
                            continue
                        upload_date = info.get("upload_date", "")
                        if upload_date not in valid_dates:
                            progress.advance(task)
                            continue
                        videos.append(VideoInfo(
                            video_id=vid_id,
                            title=info.get("title", "Unknown"),
                            url=vid_url,
                            view_count=info.get("view_count", 0),
                            upload_date=upload_date,
                        ))
                    except Exception:
                        logger.warning("Failed to extract info for %s", vid_id, exc_info=True)
                    progress.advance(task)

    videos.sort(key=lambda v: v.view_count, reverse=True)
    return videos
