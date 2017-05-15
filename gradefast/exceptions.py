"""
Exceptions used throughout GradeFast.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

from collections import OrderedDict
from typing import Dict


class GradeBookPublicError(Exception):
    """
    An error with a name and a message that are okay to send to the GradeBook client (or, if on a
    public endpoint, anyone who can access our HTTP server).
    """
    def __init__(self, message: str = None, **more_details: object) -> None:
        self._message = message

        self._details = OrderedDict()  # type: Dict[str, str]
        self._details["name"] = self._get_error_name()
        if message is not None:
            self._details["message"] = message
        for key, value in more_details.items():
            self._details[key] = str(value) or str(value.__class__)

    def _get_error_name(self) -> str:
        return self.__class__.__name__

    def get_message(self) -> str:
        return "{}: {}".format(self._get_error_name(), self._message)

    def get_details(self) -> Dict[str, str]:
        return self._details


class BadPathError(GradeBookPublicError):
    """
    Error resulting from a bad path.
    """
    pass
