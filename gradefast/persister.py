"""
Classes for persisting and restoring GradeFast state to/from a save file.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import shelve
from typing import Any, Optional

from pyprovide import inject

from gradefast.models import Settings

# Pickle protocol v4 was added in Python 3.4
_PICKLE_PROTOCOL_VERSION = 4


class Persister:
    """
    Save data to the GradeFast save file. (This is just a thin wrapper around the shelve module.)
    """

    @inject()
    def __init__(self, settings: Settings):
        self.settings = settings

        self._shelf = None  # type: Optional[shelve.Shelf]
        if settings.save_file:
            self._shelf = shelve.open(settings.save_file.get_local_path(),
                                      protocol=_PICKLE_PROTOCOL_VERSION)

    def get(self, key: str) -> Any:
        if not self._shelf:
            return None
        return self._shelf.get(key)

    def set(self, key: str, value: Any) -> None:
        self._shelf[key] = value

    def close(self) -> None:
        if self._shelf:
            self._shelf.close()
            self._shelf = None
