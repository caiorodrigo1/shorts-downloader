import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yt_dlp

from shorts_downloader.fetcher import VideoInfo

logger = logging.getLogger(__name__)

TIMEZONE = ZoneInfo("America/Sao_Paulo")


def download_videos(
    videos: list[VideoInfo],
    download_dir: Path,
    archive_file: Path | None = None,
) -> list[str]:
    """Download videos to a date-based subfolder.

    Args:
        videos: List of videos to download.
        download_dir: Root download directory.
        archive_file: Optional yt-dlp archive file for extra deduplication.

    Returns:
        List of successfully downloaded video IDs.
    """
    today_str = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    day_dir = download_dir / today_str
    day_dir.mkdir(parents=True, exist_ok=True)

    downloaded_ids: list[str] = []

    for video in videos:
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": str(day_dir / "%(title)s [%(id)s].%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
        }

        if archive_file:
            ydl_opts["download_archive"] = str(archive_file)

        logger.info("Downloading: %s (%s)", video.title, video.video_id)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video.url])
            downloaded_ids.append(video.video_id)
            logger.info("Downloaded: %s", video.title)
        except Exception:
            logger.error(
                "Failed to download %s (%s)",
                video.title,
                video.video_id,
                exc_info=True,
            )

    logger.info("Downloaded %d/%d videos", len(downloaded_ids), len(videos))
    return downloaded_ids
