import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
import os

logger = logging.getLogger(__name__)

TIMEZONE = ZoneInfo("America/Sao_Paulo")


@dataclass
class ChannelConfig:
    name: str
    url: str
    enabled: bool = True


@dataclass
class AppConfig:
    download_dir: Path
    total_videos: int
    schedule_time: str
    channels: list[ChannelConfig]
    history_file: Path
    log_level: str
    timezone: ZoneInfo = field(default_factory=lambda: TIMEZONE)


def load_config(env_path: str | None = None) -> AppConfig:
    load_dotenv(env_path)

    channels_file = Path(os.getenv("CHANNELS_FILE", "./channels.json"))
    if not channels_file.exists():
        raise FileNotFoundError(f"Channels file not found: {channels_file}")

    with open(channels_file) as f:
        raw_channels = json.load(f)

    channels = []
    for ch in raw_channels:
        channels.append(ChannelConfig(
            name=ch["name"],
            url=ch["url"],
            enabled=ch.get("enabled", True),
        ))

    if not channels:
        raise ValueError("No channels configured")

    config = AppConfig(
        download_dir=Path(os.getenv("DOWNLOAD_DIR", "./downloads")),
        total_videos=int(os.getenv("TOTAL_VIDEOS", "6")),
        schedule_time=os.getenv("SCHEDULE_TIME", "08:00"),
        channels=channels,
        history_file=Path(os.getenv("HISTORY_FILE", "./download_history.json")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )

    logger.info(
        "Config loaded: %d channels, %d total videos, schedule at %s",
        len(config.channels),
        config.total_videos,
        config.schedule_time,
    )
    return config
