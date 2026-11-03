import argparse
import sys
from pathlib import Path

from . import __version__
from .config import LOG_FILE_NAME, REPORT_FILE_NAME
from .core import (
    CONFLICT_ASK,
    CONFLICT_RENAME,
    CONFLICT_SKIP,
    FileOrganizer,
)
from .logger import setup_logger
from .report import build_report, write_report


def build_parser():
    parser = argparse.ArgumentParser(
        prog="file_organizer",
        description="Scan a folder and organize its files into category folders.",
    )
    parser.add_argument("folder", nargs="?", help="Folder to organize")
    parser.add_argument("-n", "--dry-run", action="store_true", help="Preview changes without moving files")
    parser.add_argument("-r", "--recursive", action="store_true", help="Include files in sub-folders")
    parser.add_argument("--keep-duplicates", action="store_true", help="Leave duplicate files in place")
    parser.add_argument(
        "--on-conflict",
        choices=[CONFLICT_RENAME, CONFLICT_SKIP, CONFLICT_ASK],
        default=CONFLICT_RENAME,
        help="What to do when a destination file already exists (default: rename)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed output")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def ask_folder():
    try:
        value = input("Enter the folder path to organize: ").strip().strip('"').strip("'")
    except EOFError:
        return None
    return value or None


def confirm_live_run(folder):
    try:
        answer = input(f"Files in '{folder}' will be moved. Continue? [y/N]: ").strip().lower()
    except EOFError:
        return False
    return answer in ("y", "yes")


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    folder = args.folder or ask_folder()
    if not folder:
        parser.print_usage()
        print("error: no folder given", file=sys.stderr)
        return 2

    root = Path(folder).expanduser()
    if not root.is_dir():
        print(f"error: '{folder}' is not a valid folder", file=sys.stderr)
        return 2

    root = root.resolve()
    log_path = root / LOG_FILE_NAME if not args.dry_run else None
    logger = setup_logger(log_path, args.verbose)

    if not args.dry_run and args.folder is None and not confirm_live_run(root):
        print("Cancelled.")
        return 0

    organizer = FileOrganizer(
        root,
        logger,
        dry_run=args.dry_run,
        recursive=args.recursive,
        move_duplicates=not args.keep_duplicates,
        on_conflict=args.on_conflict,
    )

    try:
        result = organizer.run()
    except (OSError, ValueError) as exc:
        logger.error("Run aborted: %s", exc)
        return 1
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        return 130

    if args.dry_run:
        print()
        print(build_report(result))
    else:
        report_path = root / REPORT_FILE_NAME
        try:
            text = write_report(result, report_path)
        except OSError as exc:
            logger.error("Could not write report: %s", exc)
            text = build_report(result)
        print()
        print(text)
        print(f"Report saved to: {report_path}")
        print(f"Log saved to: {log_path}")

    return 1 if result.by_status("failed") else 0
