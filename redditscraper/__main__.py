#!/bin/env python3
import logging
import signal
import click
import praw
import time
from datetime import datetime

from .database.sqlite import SQLiteConnection
from .dataloader.psaw import PushShiftDataLoader
from .dataloader.psfiles import PushShiftFileLoader

from .utils.constants import USER_AGENT_TEMPLATE, KEY_LST

handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)

logger = logging.getLogger("redditScraper")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

psaw_logger = logging.getLogger('psaw')
psaw_logger.setLevel(logging.WARN)
psaw_logger.addHandler(handler)

for logger_name in ("praw", "prawcore"):
    praw_logger = logging.getLogger(logger_name)
    praw_logger.setLevel(logging.INFO)
    praw_logger.addHandler(handler)

old_sig_int = signal.getsignal(signal.SIGINT)
terminate = False


def load_data(database_file, subreddit_name, data_source, data_files_directory, after_latest_known,
              update_object_reddit,
              reddit_client_id, reddit_client_secret, reddit_username, limit, exclude_removed, start_utc, end_utc):
    global terminate

    start_timestamp_utc = start_utc
    # We should not update up to now. There is always spam and other nasty stuff and we certainly do not want this
    # Therefore we wait one day before processing data.
    # This makes use of the collective power of the internet to filter content.
    # However, it requires to update with the reddit API for correct scores
    if end_utc is None:
        end_timestamp_utc = int(datetime.utcnow().timestamp()) - (60 * 60 * 24 * 1)  # Subtract 1 days in seconds
    else:
        end_timestamp_utc = end_utc

    db_connector = SQLiteConnection(database_file)
    db_connector.create_tables()

    r = None  # PRAW reddit instance
    if update_object_reddit:
        r = praw.Reddit(client_id=reddit_client_id, client_secret=reddit_client_secret,
                        user_agent=USER_AGENT_TEMPLATE.format(reddit_username))
    # Select the desired datasource
    if data_source == "datafiles":
        dataloader = PushShiftFileLoader(directory=data_files_directory, r=r)
    else:
        dataloader = PushShiftDataLoader(r=r)

    if after_latest_known and not start_utc:
        # Get the latest timestamp of an entry for the "after" query
        latest_submission_in_db = db_connector.get_latest_submission()
        if latest_submission_in_db is not None:
            start_timestamp_utc = latest_submission_in_db[0]
            logger.info(f"Starting from UNIX epoch {latest_submission_in_db[0]} "
                        f"/ UTC {datetime.utcfromtimestamp(start_timestamp_utc).strftime('%c')}")
        else:
            logger.info("No submission found. Starting new read in of all data...")
    else:
        logger.info("Ignoring timestamps of existing records. Trying to load everything. Can cause conflicts.")

    fetched_entries = 0

    time_start = time.time()
    # Both dataloaders share a common interface such that it does not matter if you use datafiles or pushshift as source
    for batch in dataloader.fetch_submissions(subreddit=subreddit_name,
                                              fields_to_fetch=KEY_LST,  # Already limit the fields to those requested
                                              after=start_timestamp_utc,
                                              before=end_timestamp_utc
                                              ):
        time_loaded = time.time()
        # Filter out data from the batch
        if exclude_removed:
            batch = [thing for thing in batch if not thing.get("removed_by_category", None)]

        # Each entry in the batch is a tuple with a lot of information in it.
        # We filter only the fields that we desire and bring them in order for the database insert.
        # Right now the fetch_submissions API can return more elements than in fields_to_fetch
        #  depending if the underlying datasource supports filtering already
        batch_final = [tuple(thing.get(k, None) for k in KEY_LST) for thing in batch]

        num_final_entries = len(batch_final)
        time_processed = time.time()
        if num_final_entries > 0:
            db_connector.insert_batch(batch_final, KEY_LST)
            time_inserted = time.time()
            fetched_entries += num_final_entries
            if limit is not None:
                logger.info(f"Loaded {fetched_entries} out of {limit} "
                            f"({(fetched_entries / limit) * 100:.2f}%)")

                if fetched_entries >= limit:
                    break
            else:
                logger.info(f"Loaded {fetched_entries} entries. "
                            f"Times: Batchload {time_loaded - time_start:.2f}, "
                            f"Process {time_processed - time_loaded:.2f}, "
                            f"DB Insert {time_inserted - time_processed:.2f}")

        if terminate:
            break
        time_start = time.time()


def interrupt_signal_handling(signum, frame):
    """
    Handler for CTRL+C interrupt
    :param signum:
    :param frame:
    :return:
    """
    signal.signal(signal.SIGINT, old_sig_int)
    logger.info("Shutdown by CTRL+C")
    global terminate
    terminate = True


@click.command()
@click.option('-db', '--database-file', required=True, type=click.Path())
@click.option('-r', '--subreddit-name', required=True, type=str)
@click.option('-ds', '--data-source', required=True, type=click.Choice(['pushshift', 'datafiles']))
@click.option('-s', '--data-files-directory', type=click.Path(exists=True, readable=True))
@click.option('--after-latest-known/--no-after-latest-known', type=bool, default=True)
@click.option('--update-object-reddit/--no-update-object-reddit', type=bool, default=True)
@click.option('--reddit-client-id', envvar='REDDIT_CLIENT_ID')  # Can be provided via env variable REDDIT_CLIENT_ID
@click.option('--reddit-client-secret', envvar='REDDIT_CLIENT_SECRET')  # Can be provided via env variable
@click.option('--reddit-username', envvar='REDDIT_USER_NAME')  # Can be provided via env variable
@click.option('-l', '--limit', default=None, type=int)
@click.option('--exclude-removed/--no-exclude-removed', default=False, type=bool)
@click.option('--start-utc', default=None, type=int)
@click.option('--end-utc', default=None, type=int)
def main(database_file, subreddit_name, data_source, data_files_directory, after_latest_known, update_object_reddit,
         reddit_client_id, reddit_client_secret, reddit_username, limit, exclude_removed, start_utc, end_utc):
    if data_source == "datafiles" and not data_files_directory:
        logger.error("datafiles import option needs to have path to directory")
        exit(1)

    if update_object_reddit and not (reddit_client_id and reddit_client_secret and reddit_username):
        logger.error("The usage of the reddit API requires a valid OAuth2 client for the "
                     "API as well as a reddit username of the creator.\n"
                     "This is in accordance with the reddit API rules "
                     "(https://github.com/reddit-archive/reddit/wiki/API).\n"
                     "Create a OAuth2 client as explained "
                     "https://github.com/reddit-archive/reddit/wiki/OAuth2-Quick-Start-Example#first-steps\n"
                     f"Username will be resolved to {USER_AGENT_TEMPLATE.format('<username>')}\n"
                     f"This is used to respect the rate-limiting of the reddit API.")
        exit(1)

    # Setup interrupt handling
    signal.signal(signal.SIGINT, interrupt_signal_handling)
    load_data(database_file, subreddit_name, data_source, data_files_directory, after_latest_known,
              update_object_reddit,
              reddit_client_id, reddit_client_secret, reddit_username, limit, exclude_removed, start_utc, end_utc)


if __name__ == '__main__':
    main()
