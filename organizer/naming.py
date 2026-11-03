import re
from pathlib import Path

INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def clean_name(name):
    cleaned = INVALID_CHARS.sub("_", name).strip()
    return cleaned or "unnamed"


def unique_destination(folder, filename, reserved=None):
    reserved = reserved if reserved is not None else set()
    folder = Path(folder)
    candidate = folder / filename
    if not candidate.exists() and candidate not in reserved:
        return candidate

    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1
    while True:
        candidate = folder / f"{stem}_{counter}{suffix}"
        if not candidate.exists() and candidate not in reserved:
            return candidate
        counter += 1
