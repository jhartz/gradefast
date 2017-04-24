"""
Utility functions and classes related to the GradeBook server.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import json
import uuid
from collections import OrderedDict
from typing import Any, Optional


class GradeBookPublicError(Exception):
    """
    An error with a name and a message that are okay to send to the GradeBook client (or, if on a
    public endpoint, anyone who can access our HTTP server).
    """
    def __init__(self, message: Optional[str] = None, **more_details):
        self._message = message

        self._details = OrderedDict()
        self._details["name"] = self._get_error_name()
        if message is not None:
            self._details["message"] = message
        for key, value in more_details.items():
            self._details[key] = str(value) or str(value.__class__)

    def _get_error_name(self) -> str:
        return self.__class__.__name__

    def get_message(self) -> str:
        return "{}: {}".format(self._get_error_name(), self._message)

    def get_details(self) -> OrderedDict:
        return self._details


class GradeBookJSONEncoder(json.JSONEncoder):
    """
    A custom JSONEncoder that encodes UUIDs as a string containing the hex version of the UUID.
    """

    def default(self, o):
        if isinstance(o, uuid.UUID):
            return str(o)

        try:
            # If the object has a to_json method, use that
            return o.to_json()
        except AttributeError:
            # I guess it doesn't :(
            # Hopefully it's already json-encodable
            pass

        return super().default(o)


_json_encoder_instance: GradeBookJSONEncoder = None


def to_json(o: Any) -> str:
    """
    Convert an object to a JSON string. For usage, see json.dumps(...).
    """
    global _json_encoder_instance
    if _json_encoder_instance is None:
        _json_encoder_instance = GradeBookJSONEncoder()
    return _json_encoder_instance.encode(o)


def from_json(*args, **kwargs):
    """
    Convert a JSON string to an object representation. For usage, see json.loads(...).
    """
    return json.loads(*args, **kwargs)


JSONDecodeError = json.JSONDecodeError
