import sqlite3
import pandas as pd
from .constants import CREATE_SUBMISSIONS_TABLE, CREATE_SQLITE_INDEX


class SQLiteConnection:
    def __init__(self, database):
        self.conn = sqlite3.connect(database)

    def __del__(self):
        self.conn.close()

    def read_db_into_pandas(self, limit=None):
        # Warning this is expensive on the memory
        query = "SELECT * from submissions"
        if limit is not None:
            query += f" LIMIT {limit}"
        df = pd.read_sql_query(query, self.conn)
        return df

    def create_tables(self):
        c = self.conn.cursor()
        c.execute(CREATE_SUBMISSIONS_TABLE)
        c.execute(CREATE_SQLITE_INDEX)
        c.close()
        self.conn.commit()

    def get_latest_submission(self):
        c = self.conn.cursor()
        c.execute("SELECT created_utc FROM submissions ORDER BY created_utc DESC LIMIT 1;")
        item = c.fetchone()
        c.close()
        return item

    def insert_batch(self, batch, key_tpl):
        """
        Stores batch to database
        :param batch: Batch of submissions
        :param key_tpl: ordered tuple of keys that are in the batch and should be stored
        :return:
        """
        c = self.conn.cursor()

        c.executemany(f"INSERT INTO submissions {str(key_tpl)} "
                      f"VALUES ({','.join(['?'] * len(key_tpl))});", batch)
        c.close()
        self.conn.commit()
