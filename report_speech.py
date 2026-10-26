"""Short spoken report descriptions that avoid opaque file identifiers."""

from datetime import datetime
from json import loads
from pathlib import Path
from re import search, sub


MAX_DESCRIPTION_BYTES = 1024 * 1024


def spoken_model_name(value) -> str:
    """Expand common model notation without changing stored model names."""
    if not isinstance(value, str) or not value.strip() or len(value) > 100:
        return "model not recorded"
    if search(r"[a-fA-F0-9]{24,}", value):
        return "model name unavailable"
    name = value.strip().replace("_", " ").replace("/", " slash ")
    name = name.replace(":", " version ").replace("-", " ")
    name = sub(r"(?i)(\d+(?:\.\d+)?)b\b", r"\1 billion parameters", name)
    name = sub(r"([A-Za-z])(\d)", r"\1 \2", name)
    return " ".join(name.split())


def _spoken_date(value: datetime, *, time_known=True) -> str:
    date = f"{value.strftime('%B')} {value.day}, {value.year}"
    if not time_known:
        return date
    hour = value.hour % 12 or 12
    period = "AM" if value.hour < 12 else "PM"
    return f"{date} at {hour}:{value.minute:02d}:{value.second:02d} {period}"


def report_speech_details(filename: str | Path) -> str:
    """Read bounded optional metadata; filenames and paths are never spoken.

    A file's modified time is explicitly identified as such when run metadata
    is unavailable. This description is not report validation or scoring.
    """
    path = Path(filename)
    metadata = {}
    try:
        with path.open("rb") as source:
            raw = source.read(MAX_DESCRIPTION_BYTES + 1)
        if len(raw) <= MAX_DESCRIPTION_BYTES:
            report = loads(raw)
            if isinstance(report, dict) and isinstance(report.get("metadata"), dict):
                metadata = report["metadata"]
    except (OSError, ValueError):
        pass
    parts = []
    timestamp = metadata.get("timestamp")
    if isinstance(timestamp, str):
        try:
            when = datetime.fromisoformat(timestamp)
            if when.tzinfo is not None:
                when = when.astimezone()
                zone = ", local time"
            else:
                zone = ", time zone not recorded" if "T" in timestamp else ""
            parts.append("Run on " + _spoken_date(when, time_known="T" in timestamp) + zone)
        except (ValueError, OverflowError, OSError):
            pass
    if not parts:
        try:
            when = datetime.fromtimestamp(path.stat().st_mtime).astimezone()
            parts.append("File last modified " + _spoken_date(when) + ", local time")
        except (OSError, ValueError, OverflowError):
            parts.append("Date unavailable")
    model = metadata.get("model")
    if isinstance(model, str) and model.strip():
        parts.append(spoken_model_name(model))
    return ". ".join(parts)
