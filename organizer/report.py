from collections import defaultdict
from pathlib import Path

from .core import (
    STATUS_DUPLICATE,
    STATUS_FAILED,
    STATUS_MOVED,
    STATUS_PLANNED,
    STATUS_SKIPPED,
)

LINE = "=" * 60


def format_size(num_bytes):
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{int(size)} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def build_report(result):
    handled = [a for a in result.actions if a.status in (STATUS_MOVED, STATUS_PLANNED)]
    duplicates = result.by_status(STATUS_DUPLICATE)
    duplicate_planned = [a for a in result.by_status(STATUS_PLANNED) if a.category == "Duplicates"]
    skipped = result.by_status(STATUS_SKIPPED)
    failed = result.by_status(STATUS_FAILED)

    per_category = defaultdict(lambda: [0, 0])
    for action in handled:
        per_category[action.category][0] += 1
        per_category[action.category][1] += action.size
    for action in duplicates:
        per_category[action.category][0] += 1
        per_category[action.category][1] += action.size

    mode = "DRY RUN (no files were changed)" if result.dry_run else "LIVE RUN"
    elapsed = (result.finished - result.started).total_seconds()

    lines = [
        LINE,
        "FILE ORGANIZER SUMMARY REPORT",
        LINE,
        f"Folder     : {result.root}",
        f"Mode       : {mode}",
        f"Started    : {result.started:%Y-%m-%d %H:%M:%S}",
        f"Duration   : {elapsed:.2f} seconds",
        "",
        "TOTALS",
        "-" * 60,
        f"Moved      : {len(result.by_status(STATUS_MOVED))}",
        f"Planned    : {len(result.by_status(STATUS_PLANNED))}",
        f"Duplicates : {len(duplicates) + len(duplicate_planned)}",
        f"Skipped    : {len(skipped)}",
        f"Failed     : {len(failed)}",
        "",
        "BY CATEGORY",
        "-" * 60,
    ]

    if per_category:
        for category in sorted(per_category):
            count, size = per_category[category]
            lines.append(f"{category:<14} {count:>5} file(s)   {format_size(size):>10}")
    else:
        lines.append("No files processed.")

    for title, items in (
        ("DUPLICATES", duplicates + duplicate_planned),
        ("SKIPPED", skipped),
        ("FAILED", failed),
    ):
        lines.extend(["", title, "-" * 60])
        if not items:
            lines.append("None")
            continue
        for action in items:
            lines.append(f"{action.source.name}  [{action.note}]")

    lines.append("")
    return "\n".join(lines)


def write_report(result, path):
    text = build_report(result)
    Path(path).write_text(text, encoding="utf-8")
    return text
