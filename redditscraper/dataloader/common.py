from itertools import islice
from praw.const import API_PATH

thing_prefix = {
            'Comment': 't1_',
            'Account': 't2_',
            'Submission': 't3_',
            'Message': 't4_',
            'Subreddit': 't5_',
            'Award': 't6_'
}


# Returns a generator that allows retrieval of all current submissions of the given full names
def get_praw_batch_gen(r, fullnames):
    def generator(r, fullnames):
        iterable = iter(fullnames)
        while True:
            chunk = list(islice(iterable, 100))
            if not chunk:
                break

            params = {"id": ",".join(chunk)}
            result = r.request(method="GET", path=API_PATH["info"], params=params)
            for r in result["data"]["children"]:
                yield r["data"]

    return generator(r, fullnames)


def get_objects_from_praw(r, batch_ids):
    prefix = thing_prefix['Submission']
    if not batch_ids:
        return
    fullnames = [prefix + c["id"] for c in batch_ids]
    return list(get_praw_batch_gen(r, fullnames))
