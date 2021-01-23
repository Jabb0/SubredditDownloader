import logging
from psaw import PushshiftAPI
from .common import get_objects_from_praw

logger = logging.getLogger("redditScraper")


class PushShiftDataLoader:
    def __init__(self, r=None):
        self._api = PushshiftAPI()  # There is support for the integration of PRAW into PSAW but it is not well suited
        self._r = r

    def fetch_submissions(self, subreddit, fields_to_fetch, after, before):
        """
        Wrapped call through to the PushShift API Wrapper library. Returns batches of submissions.
        :param subreddit:
        :param fields_to_fetch:
        :param after:
        :param before:
        :return: batches of submissions. batch consists of named tuples
        """
        for batch in self._api.search_submissions(return_batch=True, subreddit=subreddit,
                                                  filter=fields_to_fetch if self._r is None else ["id"],
                                                  after=after,
                                                  before=before,
                                                  sort='asc'):
            batch = [thing.d_ for thing in batch]
            # Sort ascending so that it can be stopped and continued into the future the next time
            if self._r is not None:
                # Note: If you want to drop removed submissions. This can be speed by filtering for submissions
                #   that are already removed according to pushshift.
                # Note: This will drop entries that reddit cannot resolve anymore
                # A small check will notify about this
                praw_batch = get_objects_from_praw(self._r, batch)
                if len(batch) != len(praw_batch):
                    logger.info(f"Asking reddit for the updated objects yielded "
                                f"{len(praw_batch)} of {len(batch)} requested objects")
                yield praw_batch
            else:
                yield batch
