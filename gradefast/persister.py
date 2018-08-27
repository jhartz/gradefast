"""
Classes for persisting and restoring GradeFast state to/from a save file.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import pickle
import queue
import shelve
import sqlite3
import threading
from typing import Any, Optional

from pyprovide import inject

from gradefast.loggingwrapper import get_logger
from gradefast.models import Settings

# Pickle protocol v4 was added in Python 3.4
_PICKLE_PROTOCOL_VERSION = 4

_logger = get_logger("persister")


class Persister:
    """
    Interface for a persister to save data to a GradeFast save file. The persisted data should be
    eventually consistent, i.e., if something is set using "set()", this should be reflected in
    subsequent "get()" calls within some reasonable timeframe (e.g. half a second).
    """

    def get(self, namespace: str, key: str) -> Any:
        raise NotImplementedError()

    def set(self, namespace: str, key: str, value: Any) -> None:
        raise NotImplementedError()

    def clear(self, namespace: str, key: str) -> None:
        raise NotImplementedError()

    def clear_all(self, namespace: str) -> None:
        raise NotImplementedError()

    def close(self) -> None:
        raise NotImplementedError()


class ShelvePersister(Persister):
    """
    GradeFast persister based on the shelve module. (This is the "legacy" way of persisting save
    files.)
    """

    _PERSISTER_VERSION = 1

    @staticmethod
    def _format_key(namespace: str, key: str) -> str:
        return "::".join((str(ShelvePersister._PERSISTER_VERSION), namespace, key))

    @inject()
    def __init__(self, settings: Settings):
        self.settings = settings

        self._shelf = None  # type: Optional[shelve.Shelf]
        if settings.save_file:
            _logger.info("Opening Shelve save file: {}", settings.save_file)
            self._shelf = shelve.open(settings.save_file.get_local_path(),
                                      protocol=_PICKLE_PROTOCOL_VERSION)
        else:
            _logger.info("No save file specified")

    def get(self, namespace: str, key: str) -> Any:
        if self._shelf is None:
            return

        full_key = self._format_key(namespace, key)
        return self._shelf.get(full_key)

    def set(self, namespace: str, key: str, value: Any) -> None:
        if self._shelf is None:
            return

        full_key = self._format_key(namespace, key)
        try:
            self._shelf[full_key] = value
        except:
            _logger.exception("Error persisting {} to save file", key)

    def clear(self, namespace: str, key: str) -> None:
        if self._shelf is None:
            return

        full_key = self._format_key(namespace, key)
        if full_key in self._shelf:
            del self._shelf[full_key]

    def clear_all(self, namespace: str) -> None:
        if self._shelf is None:
            return

        key_prefix = self._format_key(namespace, "")
        _logger.debug("Clearing all persisted data with key prefix: {}", key_prefix)
        for full_key in self._shelf.keys():
            if full_key.startswith(key_prefix):
                del self._shelf[full_key]

    def close(self) -> None:
        if self._shelf is None:
            _logger.debug("No save file to close")
        else:
            _logger.info("Closing save file")
            self._shelf.close()
            self._shelf = None


class SqlitePersister(Persister):
    """
    GradeFast persister that uses sqlite and pickle. This is preferred over shelve because it works
    cross-platform.

    The mutator methods ("set", "clear", and "clear_all") do not commit the data right away, so
    they may return before the changes have been committed to the database.

    Unfortunately, this is a bit of a hackjob since we have to deal with the fact that Python
    sqlite connections can't be accessed from multiple threads :(
    """

    @inject()
    def __init__(self, settings: Settings):
        self._th = None
        if settings.save_file:
            self._th = SqlitePersisterThread(settings.save_file)
            self._th.start()
        else:
            _logger.info("No save file specified")

    def get(self, namespace: str, key: str) -> Any:
        if self._th is None:
            return
        return self._th.do_request(SqlitePersisterRequest("get", namespace, key))

    def set(self, namespace: str, key: str, value: str) -> Any:
        if self._th is None:
            return
        return self._th.do_request(SqlitePersisterRequest("set", namespace, key, value))

    def clear(self, namespace: str, key: str) -> Any:
        if self._th is None:
            return
        return self._th.do_request(SqlitePersisterRequest("clear", namespace, key))

    def clear_all(self, namespace: str) -> Any:
        if self._th is None:
            return
        return self._th.do_request(SqlitePersisterRequest("clear_all", namespace))

    def close(self) -> Any:
        if self._th is None:
            _logger.debug("No SQLite save file to close")
            return
        return self._th.do_request(SqlitePersisterRequest("close"))


class SqlitePersisterRequest:
    def __init__(self, action: str, namespace: Optional[str] = None, key: Optional[str] = None,
                 value: Optional[str] = None):
        self.action = action
        self.namespace = namespace
        self.key = key
        self.value = value

        self._result = None
        self._has_result = threading.Event()

    def get_result(self):
        self._has_result.wait()
        return self._result

    def put_result(self, result=True):
        self._result = result
        self._has_result.set()

    def __str__(self):
        s = "SqlitePersisterRequest{action=" + self.action
        if self.namespace:
            s += ", namespace=" + self.namespace
        if self.key:
            s += ", key=" + self.key
        if self.value:
            s += ", has new value"
        s += "}"
        return s


class SqlitePersisterThread(threading.Thread):
    def __init__(self, save_file):
        super().__init__(daemon=True)
        self.save_file = save_file
        self._conn = None  # type: sqlite3.Connection
        self._queue = queue.Queue()
        self._commit_timer = None

    def do_request(self, request: SqlitePersisterRequest):
        self._queue.put(request)
        return request.get_result()

    def run(self):
        _logger.info("Opening SQLite save file: {}", self.save_file)
        self._conn = sqlite3.connect(self.save_file.get_local_path())

        with self._conn:
            self._conn.execute("CREATE TABLE IF NOT EXISTS gradefast "
                               "(namespace TEXT NOT NULL, data_key TEXT NOT NULL, "
                               "data_value BLOB, PRIMARY KEY (namespace, data_key))")

        while True:
            request = self._queue.get(block=True)  # type: SqlitePersisterRequest

            if request.action == "get":
                request.put_result(self._get(request.namespace, request.key))

            elif request.action == "commit":
                self._commit()
                request.put_result()

            elif request.action == "close":
                self._close()
                request.put_result()

            else:
                if request.action == "set":
                    self._set(request.namespace, request.key, request.value)
                    request.put_result()

                elif request.action == "clear":
                    self._clear(request.namespace, request.key)
                    request.put_result()

                elif request.action == "clear_all":
                    self._clear_all(request.namespace)
                    request.put_result()

                # Wait to commit the changes so we can batch-commit if we have a lot of changes in
                # a short amount of time (0.5 seconds).
                if self._commit_timer:
                    self._commit_timer.cancel()
                self._commit_timer = threading.Timer(0.5, lambda:
                        self._queue.put(SqlitePersisterRequest("commit")))
                self._commit_timer.start()

    def _get(self, namespace: str, key: str) -> Any:
        c = self._conn.cursor()
        c.execute("SELECT data_value FROM gradefast WHERE namespace=? AND data_key=?",
                  (namespace, key))
        row = c.fetchone()
        if row is None:
            return None
        return pickle.loads(row[0])

    def _set(self, namespace: str, key: str, value: Any) -> None:
        try:
            pickled_value = pickle.dumps(value, protocol=_PICKLE_PROTOCOL_VERSION)
            self._conn.execute("INSERT OR REPLACE INTO gradefast "
                               "(namespace, data_key, data_value) VALUES (?, ?, ?)",
                               (namespace, key, pickled_value))
        except:
            _logger.exception("Error persisting {} to SQLite save file", key)

    def _clear(self, namespace: str, key: str) -> None:
        self._conn.execute("DELETE FROM gradefast WHERE namespace=? AND data_key=?",
                           (namespace, key))

    def _clear_all(self, namespace: str) -> None:
        _logger.debug("Clearing all persisted data with namespace: {}", namespace)
        self._conn.execute("DELETE FROM gradefast WHERE namespace=?", (namespace,))

    def _close(self) -> None:
        _logger.info("Closing SQLite save file")
        if self._commit_timer:
            self._commit_timer.cancel()
        self._conn.commit()
        self._conn.close()

    def _commit(self):
        self._conn.commit()
