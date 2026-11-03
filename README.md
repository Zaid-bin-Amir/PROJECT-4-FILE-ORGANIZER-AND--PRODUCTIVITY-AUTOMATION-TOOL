# File Organizer & Productivity Automation Tool

A Python command-line tool that scans a folder, identifies files by extension, and organizes them into category folders. It detects duplicates, writes a summary report, and logs every action.

Uses only the Python standard library (`os`, `pathlib`, `shutil`, `datetime`, `logging`, `hashlib`, `re`, `argparse`). Requires Python 3.8+.

## Features

- Automated file organizer
- File type categorization (Documents, Images, Videos, Audio, Archives, Code, Others)
- Duplicate detection using SHA-256 content hashes
- File summary report
- Activity log of moved, skipped, and failed operations
- Error handling for missing folders, permissions, and unreadable files
- Dry-run mode to preview changes before moving anything
- Never overwrites existing files without confirmation

## Project Structure

```
file_organizer/
├── main.py
├── organizer/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── core.py
│   ├── duplicates.py
│   ├── logger.py
│   ├── naming.py
│   ├── report.py
│   └── scanner.py
├── tests/
│   └── test_organizer.py
├── .gitignore
└── README.md
```

## Usage

Preview first (nothing is moved):

```
python main.py "C:\Users\You\Downloads" --dry-run
```

Organize for real:

```
python main.py "C:\Users\You\Downloads"
```

Run without arguments to be asked for the folder path:

```
python main.py
```

## Options

| Option | Description |
|---|---|
| `-n`, `--dry-run` | Preview changes without moving files |
| `-r`, `--recursive` | Include files inside sub-folders |
| `--keep-duplicates` | Leave duplicate files where they are |
| `--on-conflict {rename,skip,ask}` | Behaviour when a destination file exists (default: `rename`) |
| `-v`, `--verbose` | Show detailed output |
| `--version` | Show version |

## Output

After a live run the tool creates, inside the organized folder:

- `organizer.log` with every moved, skipped, duplicate, and failed operation
- `summary_report.txt` with totals, per-category counts and sizes, duplicates, skipped, and failed files

Duplicates are moved to a `Duplicates` folder. The first file found is kept as the original.

## Overwrite Safety

If a file with the same name already exists in the destination:

- `rename` (default): the new file is saved as `name_1.ext`, `name_2.ext`, and so on
- `skip`: the file is left where it is
- `ask`: you are asked whether to overwrite, rename, or skip

## Exit Codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | One or more operations failed |
| 2 | Invalid input |
| 130 | Interrupted |

## Customizing Categories

Edit the `CATEGORIES` dictionary in `organizer/config.py` to add or change extensions and folders.

## Running Tests

```
python -m unittest discover -s tests -v
```

## Git and GitHub

```
git init
git add .
git commit -m "Add file organizer tool"
git branch -M main
git remote add origin https://github.com/<your-username>/file-organizer.git
git push -u origin main
```
