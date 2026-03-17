import json
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

TIMEZONE = ZoneInfo("America/Sao_Paulo")


def load_downloaded_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()

    with open(path) as f:
        records = json.load(f)

    return {r["video_id"] for r in records}


def record_downloads(
    path: Path,
    video_ids: list[str],
    channel_name: str,
) -> None:
    if not video_ids:
        return

    existing: list[dict] = []
    if path.exists():
        with open(path) as f:
            existing = json.load(f)

    now = datetime.now(TIMEZONE).isoformat()
    for vid in video_ids:
        existing.append({
            "video_id": vid,
            "channel": channel_name,
            "downloaded_at": now,
        })

    # Atomic write: write to temp file then rename
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=parent, suffix=".tmp")
    try:
        with open(fd, "w") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
        Path(tmp_path).replace(path)
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise

    logger.info("Recorded %d downloads for %s", len(video_ids), channel_name)
