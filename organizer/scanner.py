from pathlib import Path

from .config import CATEGORIES, DEFAULT_CATEGORY, RESERVED_NAMES, reserved_folders


def categorize(path):
    extension = Path(path).suffix.lower()
    for category, extensions in CATEGORIES.items():
        if extension in extensions:
            return category
    return DEFAULT_CATEGORY


def scan_folder(root, recursive=False):
    root = Path(root)
    skip_dirs = reserved_folders()
    found = []
    skipped = []

    if recursive:
        candidates = root.rglob("*")
    else:
        candidates = root.iterdir()

    for item in candidates:
        try:
            if not item.is_file() or item.is_symlink():
                continue
            relative_parts = item.relative_to(root).parts
            if any(part in skip_dirs for part in relative_parts[:-1]):
                continue
            if item.name in RESERVED_NAMES:
                continue
            if item.name.startswith("."):
                skipped.append((item, "hidden file"))
                continue
            found.append(item)
        except OSError as exc:
            skipped.append((item, str(exc)))

    found.sort(key=lambda p: str(p).lower())
    return found, skipped
