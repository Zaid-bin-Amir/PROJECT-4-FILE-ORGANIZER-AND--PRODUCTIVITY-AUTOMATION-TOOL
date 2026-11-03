import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .config import DUPLICATES_FOLDER
from .duplicates import find_duplicates
from .naming import clean_name, unique_destination
from .scanner import categorize, scan_folder

STATUS_MOVED = "moved"
STATUS_SKIPPED = "skipped"
STATUS_FAILED = "failed"
STATUS_DUPLICATE = "duplicate"
STATUS_PLANNED = "planned"

CONFLICT_RENAME = "rename"
CONFLICT_SKIP = "skip"
CONFLICT_ASK = "ask"


@dataclass
class Action:
    status: str
    source: Path
    destination: Path = None
    category: str = ""
    size: int = 0
    note: str = ""


@dataclass
class RunResult:
    root: Path
    dry_run: bool
    started: datetime
    finished: datetime
    actions: list

    def by_status(self, status):
        return [a for a in self.actions if a.status == status]


def default_prompt(message):
    try:
        return input(message).strip().lower()
    except EOFError:
        return "n"


class FileOrganizer:
    def __init__(
        self,
        root,
        logger,
        dry_run=False,
        recursive=False,
        move_duplicates=True,
        on_conflict=CONFLICT_RENAME,
        prompt=default_prompt,
    ):
        self.root = Path(root).expanduser().resolve()
        self.logger = logger
        self.dry_run = dry_run
        self.recursive = recursive
        self.move_duplicates = move_duplicates
        self.on_conflict = on_conflict
        self.prompt = prompt

    def validate(self):
        if not self.root.exists():
            raise FileNotFoundError(f"Folder does not exist: {self.root}")
        if not self.root.is_dir():
            raise NotADirectoryError(f"Not a folder: {self.root}")

    def run(self):
        self.validate()
        started = datetime.now()
        mode = "DRY RUN" if self.dry_run else "LIVE"
        self.logger.info("Starting %s on %s", mode, self.root)

        try:
            files, skipped = scan_folder(self.root, self.recursive)
        except PermissionError as exc:
            self.logger.error("Cannot read folder %s: %s", self.root, exc)
            raise

        actions = []
        for path, reason in skipped:
            self.logger.info("SKIPPED %s (%s)", path.name, reason)
            actions.append(Action(STATUS_SKIPPED, path, note=reason))

        self.logger.info("Found %d file(s) to process", len(files))

        duplicates, hash_errors = find_duplicates(files)
        for path, reason in hash_errors:
            self.logger.error("FAILED %s (%s)", path.name, reason)
            actions.append(Action(STATUS_FAILED, path, note=reason))

        failed_paths = {path for path, _ in hash_errors}
        reserved = set()

        for path in files:
            if path in failed_paths:
                continue
            if path in duplicates:
                actions.append(self._handle_duplicate(path, duplicates[path], reserved))
            else:
                actions.append(self._handle_file(path, reserved))

        finished = datetime.now()
        self.logger.info("Finished %s", mode)
        return RunResult(self.root, self.dry_run, started, finished, actions)

    def _size(self, path):
        try:
            return path.stat().st_size
        except OSError:
            return 0

    def _handle_duplicate(self, path, original, reserved):
        size = self._size(path)
        note = f"duplicate of {original.name}"

        if not self.move_duplicates:
            self.logger.info("SKIPPED %s (%s)", path.name, note)
            return Action(STATUS_SKIPPED, path, category=DUPLICATES_FOLDER, size=size, note=note)

        target_dir = self.root / DUPLICATES_FOLDER
        return self._transfer(path, target_dir, DUPLICATES_FOLDER, size, reserved, STATUS_DUPLICATE, note)

    def _handle_file(self, path, reserved):
        category = categorize(path)
        size = self._size(path)
        target_dir = self.root / category
        return self._transfer(path, target_dir, category, size, reserved, STATUS_MOVED, "")

    def _resolve_destination(self, path, target_dir, reserved):
        filename = clean_name(path.name)
        direct = target_dir / filename
        conflict = direct.exists() or direct in reserved

        if not conflict:
            return direct, None

        if self.on_conflict == CONFLICT_SKIP:
            return None, "destination already exists"

        if self.on_conflict == CONFLICT_ASK and not self.dry_run:
            answer = self.prompt(
                f"'{direct}' already exists. Overwrite? [y = overwrite / r = rename / N = skip]: "
            )
            if answer == "y" and direct.exists():
                return direct, "overwritten after confirmation"
            if answer != "r":
                return None, "destination already exists, not overwritten"

        return unique_destination(target_dir, filename, reserved), "renamed to avoid overwrite"

    def _transfer(self, path, target_dir, category, size, reserved, success_status, note):
        destination, conflict_note = self._resolve_destination(path, target_dir, reserved)

        if destination is None:
            self.logger.info("SKIPPED %s (%s)", path.name, conflict_note)
            return Action(STATUS_SKIPPED, path, category=category, size=size, note=conflict_note)

        full_note = "; ".join(part for part in (note, conflict_note) if part)
        reserved.add(destination)

        if self.dry_run:
            self.logger.info("WOULD MOVE %s -> %s", path.name, destination.relative_to(self.root))
            return Action(STATUS_PLANNED, path, destination, category, size, full_note)

        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(destination))
        except (OSError, shutil.Error) as exc:
            self.logger.error("FAILED %s (%s)", path.name, exc)
            return Action(STATUS_FAILED, path, destination, category, size, str(exc))

        label = "DUPLICATE" if success_status == STATUS_DUPLICATE else "MOVED"
        self.logger.info("%s %s -> %s", label, path.name, destination.relative_to(self.root))
        return Action(success_status, path, destination, category, size, full_note)
