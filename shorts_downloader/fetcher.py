import logging
from dataclasses import dataclass

import yt_dlp

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
    today_date: str,
) -> list[VideoInfo]:
    """Fetch all videos uploaded today from a channel's /shorts tab.

    Args:
        channel_url: URL to the channel's /shorts tab.
        already_downloaded: Set of video IDs to skip.
        today_date: Date string in YYYYMMDD format (Brasilia timezone).

    Returns:
        List of VideoInfo for today's uploads, sorted by view_count descending.
    """
    ydl_opts = {
        "extract_flat": "in_playlist",
        "playlistend": 50,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
    }

    logger.info("Fetching shorts from %s", channel_url)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(channel_url, download=False)

    if not result or "entries" not in result:
        logger.warning("No entries found for %s", channel_url)
        return []

    entries = [e for e in result["entries"] if e is not None]
    logger.info("Found %d entries from %s", len(entries), channel_url)

    # Filter already downloaded
    entries = [e for e in entries if e.get("id") not in already_downloaded]

    # Entries from flat extraction may lack view_count or upload_date.
    # We need to do individual extraction for those.
    videos: list[VideoInfo] = []
    needs_full_extract: list[dict] = []

    for entry in entries:
        vid_id = entry.get("id")
        upload_date = entry.get("upload_date")
        view_count = entry.get("view_count")

        if upload_date and view_count is not None:
            if upload_date == today_date:
                videos.append(VideoInfo(
                    video_id=vid_id,
                    title=entry.get("title", "Unknown"),
                    url=entry.get("url") or f"https://www.youtube.com/shorts/{vid_id}",
                    view_count=view_count,
                    upload_date=upload_date,
                ))
        else:
            needs_full_extract.append(entry)

    # Full extraction for entries missing metadata
    if needs_full_extract:
        logger.info(
            "Extracting full metadata for %d videos from %s",
            len(needs_full_extract),
            channel_url,
        )
        full_opts = {
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
        }
        with yt_dlp.YoutubeDL(full_opts) as ydl:
            for entry in needs_full_extract:
                vid_id = entry.get("id")
                vid_url = entry.get("url") or f"https://www.youtube.com/shorts/{vid_id}"
                try:
                    info = ydl.extract_info(vid_url, download=False)
                    if not info:
                        continue
                    upload_date = info.get("upload_date", "")
                    if upload_date != today_date:
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

    videos.sort(key=lambda v: v.view_count, reverse=True)

    if videos:
        logger.info(
            "Found %d shorts today from %s: %s",
            len(videos),
            channel_url,
            ", ".join(f"{v.title} ({v.view_count:,} views)" for v in videos),
        )
    else:
        logger.info("No shorts uploaded today found for %s", channel_url)

    return videos
