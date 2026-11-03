import logging
import tempfile
import unittest
from pathlib import Path

from organizer.core import (
    CONFLICT_ASK,
    CONFLICT_SKIP,
    FileOrganizer,
    STATUS_DUPLICATE,
    STATUS_MOVED,
    STATUS_PLANNED,
    STATUS_SKIPPED,
)
from organizer.duplicates import find_duplicates
from organizer.naming import clean_name, unique_destination
from organizer.report import build_report, format_size
from organizer.scanner import categorize, scan_folder


def quiet_logger():
    logger = logging.getLogger("test_file_organizer")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    logger.propagate = False
    return logger


class TempFolderCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def make(self, name, content="data"):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path


class CategorizeTests(unittest.TestCase):
    def test_known_extensions(self):
        self.assertEqual(categorize("a.pdf"), "Documents")
        self.assertEqual(categorize("a.PNG"), "Images")
        self.assertEqual(categorize("a.mp4"), "Videos")
        self.assertEqual(categorize("a.zip"), "Archives")

    def test_unknown_and_no_extension(self):
        self.assertEqual(categorize("a.xyz"), "Others")
        self.assertEqual(categorize("README"), "Others")


class NamingTests(TempFolderCase):
    def test_clean_name(self):
        self.assertEqual(clean_name('a<b>c?.txt'), "a_b_c_.txt")
        self.assertEqual(clean_name("   "), "unnamed")

    def test_unique_destination(self):
        self.make("a.txt")
        self.assertEqual(unique_destination(self.root, "a.txt"), self.root / "a_1.txt")
        self.assertEqual(unique_destination(self.root, "b.txt"), self.root / "b.txt")

    def test_unique_destination_respects_reserved(self):
        reserved = {self.root / "b.txt"}
        self.assertEqual(unique_destination(self.root, "b.txt", reserved), self.root / "b_1.txt")


class ScannerTests(TempFolderCase):
    def test_non_recursive_ignores_subfolders(self):
        self.make("a.txt")
        self.make("sub/b.txt")
        files, _ = scan_folder(self.root)
        self.assertEqual([f.name for f in files], ["a.txt"])

    def test_recursive_includes_subfolders(self):
        self.make("a.txt")
        self.make("sub/b.txt")
        files, _ = scan_folder(self.root, recursive=True)
        self.assertEqual(sorted(f.name for f in files), ["a.txt", "b.txt"])

    def test_hidden_and_category_folders_skipped(self):
        self.make(".hidden")
        self.make("Documents/old.pdf")
        files, skipped = scan_folder(self.root, recursive=True)
        self.assertEqual(files, [])
        self.assertEqual(len(skipped), 1)


class DuplicateTests(TempFolderCase):
    def test_detects_identical_content(self):
        a = self.make("a.txt", "same")
        b = self.make("b.txt", "same")
        c = self.make("c.txt", "different")
        duplicates, errors = find_duplicates([a, b, c])
        self.assertEqual(errors, [])
        self.assertEqual(duplicates, {b: a})

    def test_same_size_different_content(self):
        a = self.make("a.txt", "aaaa")
        b = self.make("b.txt", "bbbb")
        duplicates, _ = find_duplicates([a, b])
        self.assertEqual(duplicates, {})

    def test_missing_file_reported(self):
        a = self.make("a.txt")
        ghost = self.root / "ghost.txt"
        _, errors = find_duplicates([a, ghost])
        self.assertEqual(len(errors), 1)


class OrganizerTests(TempFolderCase):
    def organizer(self, **kwargs):
        return FileOrganizer(self.root, quiet_logger(), **kwargs)

    def test_moves_files_into_categories(self):
        self.make("report.pdf", "r")
        self.make("photo.jpg", "p")
        self.make("data.bin", "d")
        result = self.organizer().run()
        self.assertEqual(len(result.by_status(STATUS_MOVED)), 3)
        self.assertTrue((self.root / "Documents" / "report.pdf").exists())
        self.assertTrue((self.root / "Images" / "photo.jpg").exists())
        self.assertTrue((self.root / "Others" / "data.bin").exists())

    def test_dry_run_changes_nothing(self):
        self.make("report.pdf")
        result = self.organizer(dry_run=True).run()
        self.assertEqual(len(result.by_status(STATUS_PLANNED)), 1)
        self.assertTrue((self.root / "report.pdf").exists())
        self.assertFalse((self.root / "Documents").exists())

    def test_duplicates_moved_to_duplicates_folder(self):
        self.make("a.txt", "same")
        self.make("b.txt", "same")
        result = self.organizer().run()
        self.assertEqual(len(result.by_status(STATUS_DUPLICATE)), 1)
        self.assertEqual(len(list((self.root / "Duplicates").iterdir())), 1)
        self.assertEqual(len(list((self.root / "Documents").iterdir())), 1)

    def test_keep_duplicates_leaves_them(self):
        self.make("a.txt", "same")
        self.make("b.txt", "same")
        result = self.organizer(move_duplicates=False).run()
        self.assertEqual(len(result.by_status(STATUS_SKIPPED)), 1)
        self.assertTrue((self.root / "b.txt").exists())

    def test_never_overwrites_by_default(self):
        self.make("Documents/a.txt", "old")
        self.make("a.txt", "new")
        self.organizer().run()
        self.assertEqual((self.root / "Documents" / "a.txt").read_text(), "old")
        self.assertEqual((self.root / "Documents" / "a_1.txt").read_text(), "new")

    def test_conflict_skip(self):
        self.make("Documents/a.txt", "old")
        self.make("a.txt", "new")
        result = self.organizer(on_conflict=CONFLICT_SKIP).run()
        self.assertEqual(len(result.by_status(STATUS_SKIPPED)), 1)
        self.assertTrue((self.root / "a.txt").exists())

    def test_conflict_ask_overwrite_confirmed(self):
        self.make("Documents/a.txt", "old")
        self.make("a.txt", "new")
        self.organizer(on_conflict=CONFLICT_ASK, prompt=lambda _: "y").run()
        self.assertEqual((self.root / "Documents" / "a.txt").read_text(), "new")

    def test_conflict_ask_declined(self):
        self.make("Documents/a.txt", "old")
        self.make("a.txt", "new")
        self.organizer(on_conflict=CONFLICT_ASK, prompt=lambda _: "n").run()
        self.assertEqual((self.root / "Documents" / "a.txt").read_text(), "old")
        self.assertTrue((self.root / "a.txt").exists())

    def test_invalid_folder_raises(self):
        with self.assertRaises(FileNotFoundError):
            FileOrganizer(self.root / "missing", quiet_logger()).run()

    def test_file_instead_of_folder_raises(self):
        path = self.make("a.txt")
        with self.assertRaises(NotADirectoryError):
            FileOrganizer(path, quiet_logger()).run()

    def test_empty_folder(self):
        result = self.organizer().run()
        self.assertEqual(result.actions, [])

    def test_second_run_is_stable(self):
        self.make("a.pdf", "x")
        self.organizer().run()
        result = self.organizer().run()
        self.assertEqual(result.actions, [])


class ReportTests(TempFolderCase):
    def test_report_contains_totals(self):
        self.make("a.pdf", "x")
        result = FileOrganizer(self.root, quiet_logger(), dry_run=True).run()
        text = build_report(result)
        self.assertIn("FILE ORGANIZER SUMMARY REPORT", text)
        self.assertIn("DRY RUN", text)
        self.assertIn("Documents", text)

    def test_format_size(self):
        self.assertEqual(format_size(512), "512 B")
        self.assertEqual(format_size(2048), "2.0 KB")


if __name__ == "__main__":
    unittest.main()
