# Check these keys match the ones given in utils.constants

# Create the table to store the submission data
CREATE_SUBMISSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS submissions (
    id TEXT PRIMARY KEY,
    created_utc INTEGER NOT NULL,
    author TEXT NOT NULL,
    author_fullname TEXT,
    domain TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    upvote_ratio REAL,
    score INTEGER NOT NULL,
    removed_by_category TEXT,
    downloaded BOOL NOT NULL DEFAULT FALSE,
    download_file TEXT,
    downloaded_at INTEGER
);
"""

# Index for sorting on the time column
CREATE_SQLITE_INDEX = """
CREATE INDEX IF NOT EXISTS time_sort ON submissions(created_utc);
"""
