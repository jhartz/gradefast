"""
Classes for persisting and restoring GradeFast state to/from a save file.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import shelve
from typing import Any, Optional

from pyprovide import inject

from gradefast.loggingwrapper import get_logger
from gradefast.models import Settings

# Pickle protocol v4 was added in Python 3.4
_PICKLE_PROTOCOL_VERSION = 4

_PERSISTER_VERSION = 1

_logger = get_logger("persister")


class Persister:
    """
    Save data to the GradeFast save file. (This is just a thin wrapper around the shelve module.)
    """

    @staticmethod
    def _format_key(namespace: str, key: str) -> str:
        return "::".join((str(_PERSISTER_VERSION), namespace, key))

    @inject()
    def __init__(self, settings: Settings):
        self.settings = settings

        self._shelf = None  # type: Optional[shelve.Shelf]
        if settings.save_file:
            _logger.info("Opening save file: {}", settings.save_file)
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
