import psycopg2
from psycopg2.extras import DictCursor
from yoyo import read_migrations
from yoyo import get_backend

from logging import getLogger
_log = getLogger(__name__)

_instance = None


def get_db():
    global _instance
    return _instance


class Db:
    def __init__(self, options):
        global _instance
        if _instance is None:
            _instance = self

        self.conn = None

        self._do_migrations(options)

        try:
            self.conn = psycopg2.connect(
                dbname=options.db_name,
                user=options.db_user,
                cursor_factory=DictCursor)
        except psycopg2.Error as e:
            _log.error(f'Unable to connect to database: {e}')
            if self.conn is not None:
                self.conn.close()
            exit(1)

    def _do_migrations(self, options):
        try:
            backend = get_backend(
                f'postgresql://{options.db_user}@/{options.db_name}'
            )
        except psycopg2.Error as e:
            _log.error(f'Unable to open database: {e}')
            exit(1)

        migrations = read_migrations(options.db_migrations_dir)
        with backend.lock():
            backend.apply_migrations(backend.to_apply(migrations))

    def __del__(self):
        try:
            if self.conn is not None:
                self.conn.close()
        except psycopg2.Error as e:
            _log.error(f'database.py: Unable to close Databse: {e}')
