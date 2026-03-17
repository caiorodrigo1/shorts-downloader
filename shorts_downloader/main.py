import argparse
import logging
import signal
import sys
import time
from datetime import datetime

import schedule

from shorts_downloader.config import AppConfig, load_config
from shorts_downloader.downloader import download_videos
from shorts_downloader.fetcher import fetch_today_videos
from shorts_downloader.history import load_downloaded_ids, record_downloads

logger = logging.getLogger("shorts_downloader")

shutdown_requested = False


def run_job(config: AppConfig) -> None:
    logger.info("Starting download job")

    today_date = datetime.now(config.timezone).strftime("%Y%m%d")
    downloaded_ids = load_downloaded_ids(config.history_file)

    logger.info(
        "Today: %s | Already downloaded: %d videos | Channels: %d | Picking top %d",
        today_date,
        len(downloaded_ids),
        len(config.channels),
        config.total_videos,
    )

    all_videos = []

    for channel in config.channels:
        if not channel.enabled:
            logger.info("Skipping disabled channel: %s", channel.name)
            continue

        logger.info("Processing channel: %s", channel.name)

        try:
            videos = fetch_today_videos(
                channel_url=channel.url,
                already_downloaded=downloaded_ids,
                today_date=today_date,
            )
            all_videos.extend(videos)
        except Exception:
            logger.error(
                "Failed to fetch videos for %s",
                channel.name,
                exc_info=True,
            )

    if not all_videos:
        logger.info("No new shorts today from any channel")
    else:
        all_videos.sort(key=lambda v: v.view_count, reverse=True)
        top_videos = all_videos[:config.total_videos]

        logger.info(
            "Top %d videos across all channels: %s",
            len(top_videos),
            ", ".join(f"{v.title} ({v.view_count:,} views)" for v in top_videos),
        )

        archive_file = config.download_dir / "yt-dlp-archive.txt"
        new_ids = download_videos(top_videos, config.download_dir, archive_file)

        if new_ids:
            record_downloads(config.history_file, new_ids, "all")
            downloaded_ids.update(new_ids)

    logger.info("Download job finished")


def _handle_signal(signum: int, _frame) -> None:
    global shutdown_requested
    sig_name = signal.Signals(signum).name
    logger.info("Received %s, shutting down...", sig_name)
    shutdown_requested = True


def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube Shorts Downloader")
    parser.add_argument("--now", action="store_true", help="Run immediately")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()

    config = load_config()

    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if args.now:
        run_job(config)
        if args.once:
            return

    if not args.once or not args.now:
        schedule.every().day.at(config.schedule_time, str(config.timezone)).do(
            run_job, config
        )
        logger.info(
            "Scheduled daily at %s (%s)",
            config.schedule_time,
            config.timezone,
        )

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    while not shutdown_requested:
        schedule.run_pending()
        time.sleep(30)

    logger.info("Shutdown complete")


if __name__ == "__main__":
    main()
