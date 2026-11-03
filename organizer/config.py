CATEGORIES = {
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".csv", ".ppt", ".pptx", ".md"},
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".tiff", ".ico"},
    "Videos": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"},
    "Code": {".py", ".js", ".html", ".css", ".java", ".c", ".cpp", ".json", ".xml", ".sql"},
}

DEFAULT_CATEGORY = "Others"
DUPLICATES_FOLDER = "Duplicates"
LOG_FILE_NAME = "organizer.log"
REPORT_FILE_NAME = "summary_report.txt"
HASH_CHUNK_SIZE = 65536

RESERVED_NAMES = {
    LOG_FILE_NAME,
    REPORT_FILE_NAME,
}


def reserved_folders():
    folders = set(CATEGORIES)
    folders.add(DEFAULT_CATEGORY)
    folders.add(DUPLICATES_FOLDER)
    return folders
