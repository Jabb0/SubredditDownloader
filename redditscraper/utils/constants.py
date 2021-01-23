VERSION = "v1.0.0"
PACKAGE_NAME = "redditSubmissionDownloader"
USER_AGENT_TEMPLATE = "python:" + PACKAGE_NAME + ":" + VERSION + " (by /u/{})"

# This is the key list that we want to have from each submission for storing it into the DB
# See here for all available data
# https://api.pushshift.io/reddit/submission/search?subreddit=worldnews&limit=1&metadata=true&sort=desc
# Maybe the reddit API has more data available check here:
# https://www.reddit.com/r/WorldNews/top/.json?limit=1
# and here
# https://praw.readthedocs.io/en/latest/getting_started/quick_start.html#determine-available-attributes-of-an-object
KEY_LST = ('id', 'created_utc', 'author', 'author_fullname', 'domain', 'title', 'url', 'upvote_ratio', 'score',
           'removed_by_category')
