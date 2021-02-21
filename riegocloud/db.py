import sqlite3
import asyncio
from pathlib import Path
from yoyo import read_migrations
from yoyo import get_backend

from logging import getLogger
_log = getLogger(__name__)

_instance = None


def get_db():
    global _instance
    return _instance


def setup_db(options=None):
    global _instance
    if _instance is not None:
        del _instance
    _instance = Db(options=options)
    return _instance


class Db:
    def __init__(self, options=None):
        global _instance
        if _instance is None:
            _instance = self

        self.conn = None
        Path(options.db_filename).parent.mkdir(
            parents=True, exist_ok=True)

        self._do_migrations(options)

        try:
            self.conn = sqlite3.connect(options.db_filename,
                                        detect_types=sqlite3.PARSE_DECLTYPES)
        except Exception as e:
            _log.error(f'Unable to connect to database: {e}')
            if self.conn is not None:
                self.conn.close()
            exit(1)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.row_factory = sqlite3.Row

    def _do_migrations(self, options):
        try:
            backend = get_backend('sqlite:///' + options.db_filename)
        except Exception as e:
            _log.error(f'Unable to open database: {e}')
            exit(1)

        migrations = read_migrations(options.db_migrations_dir)
        with backend.lock():
            backend.apply_migrations(backend.to_apply(migrations))

    def __del__(self):
        try:
            if self.conn is not None:
                self.conn.close()
        except Exception as e:
            _log.error(f'database.py: Unable to close Databse: {e}')
