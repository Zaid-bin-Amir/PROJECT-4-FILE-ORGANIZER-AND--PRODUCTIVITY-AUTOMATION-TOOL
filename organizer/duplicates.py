import hashlib
from collections import defaultdict
from pathlib import Path

from .config import HASH_CHUNK_SIZE


def file_hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(HASH_CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def find_duplicates(files):
    by_size = defaultdict(list)
    errors = []

    for path in files:
        try:
            by_size[Path(path).stat().st_size].append(Path(path))
        except OSError as exc:
            errors.append((Path(path), str(exc)))

    originals = {}
    duplicates = {}

    for same_size in by_size.values():
        if len(same_size) < 2:
            continue
        seen = {}
        for path in same_size:
            try:
                digest = file_hash(path)
            except OSError as exc:
                errors.append((path, str(exc)))
                continue
            if digest in seen:
                duplicates[path] = seen[digest]
            else:
                seen[digest] = path
                originals[digest] = path

    return duplicates, errors
