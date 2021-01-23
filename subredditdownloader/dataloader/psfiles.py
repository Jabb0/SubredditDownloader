"""
Download from: https://files.pushshift.io/reddit/submissions/
Files can be in .zst, .bz2, or .xz format.
If a file exists in bz2 and xz use the xz file as it is more compressed.
Files contain json files with one JSON entry per line called ndjson.

https://www.reddit.com/r/pushshift/comments/aibhec/reddit_comments_working_with_zst_files/
"""
import json
import zstandard as zstd
import bz2
import lzma
import logging
from pathlib import Path
from io import TextIOWrapper
from .common import get_objects_from_praw

logger = logging.getLogger("redditScraper")


class PushShiftFileLoader:
    def __init__(self, directory, batch_size=100, r=None):
        self._directory = Path(directory)
        self._batch_size = batch_size
        self._r = r

    def _get_dump_files_in_directory(self):
        types = ('*.zst', '*.bz2', '*.xz')
        files = []
        for t in types:
            files.extend(self._directory.glob(t))
        # Sort the files assuming they are prefixed by timestamps ascending
        files.sort()
        return files

    def _data_line_iterator_zst(self, fh):
            dctx = zstd.ZstdDecompressor()
            reader = dctx.stream_reader(fh)
            return TextIOWrapper(reader, encoding='utf-8')

    def _read_from_directory(self, subreddit, after=None, before=None):
        files = self._get_dump_files_in_directory()
        logger.info(f"Found files: {files}")
        batch = []
        count = 0
        for file in files:
            extension = file.suffix.lower()
            with open(file, 'rb') as fh:
                logger.info(f"Reading file {file}")
                if extension == '.zst':
                    reader = self._data_line_iterator_zst(fh)
                elif extension == '.bz2':
                    reader = bz2.open(file, mode="rt", encoding="utf-8")
                else:  # .xz
                    reader = lzma.open(file, mode="rt", encoding="utf-8")

                for line in reader:
                    line = line.strip('\x00')  # Some rows have zero bytes that cause issues in json decoding
                    entry = json.loads(line)
                    # Check if this is the correct subreddit and select the desired fields
                    if entry.get("subreddit") != subreddit:
                        continue
                    if after is not None and entry["created_utc"] < after:
                        continue
                    if before is not None and entry["created_utc"] > before:
                        continue
                    count += 1
                    batch.append(entry)

                    if count == self._batch_size:
                        yield batch
                        batch = []
                        count = 0

        return batch

    def fetch_submissions(self, subreddit, fields_to_fetch, after=None, before=None):
        # If we have a praw reddit instance set only request the id of the item with created_utc
        for batch in self._read_from_directory(subreddit, after, before):
            if self._r is not None:
                # Note: This will drop entries that reddit cannot resolve anymore
                # A small check will notify about this
                praw_batch = get_objects_from_praw(self._r, batch)
                if len(batch) != len(praw_batch):
                    logger.info(f"Asking reddit for the updated objects yielded "
                                f"{len(praw_batch)} of {len(batch)} requested objects")
                yield praw_batch
            else:
                yield batch

