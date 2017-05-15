"""
Utility functions and classes related to the GradeBook server.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import json
import uuid
from typing import Any


class GradeBookJSONEncoder(json.JSONEncoder):
    """
    A custom JSONEncoder that encodes UUIDs as a string containing the hex version of the UUID.
    """

    def default(self, o):
        if isinstance(o, uuid.UUID):
            return str(o)

        # If the object has a to_json method, use that
        if hasattr(o, "to_json") and callable(o.to_json):
            return o.to_json()

        return super().default(o)


_json_encoder_instance = None


def to_json(o: object, **kwargs: Any) -> str:
    """
    Convert an object to a JSON string. For usage, see json.dumps(...).
    """
    if kwargs:
        encoder = GradeBookJSONEncoder(**kwargs)
    else:
        global _json_encoder_instance
        if _json_encoder_instance is None:
            _json_encoder_instance = GradeBookJSONEncoder()
        encoder = _json_encoder_instance
    return encoder.encode(o)


def from_json(s: str, **kwargs: Any) -> object:
    """
    Convert a JSON string to an object representation. For usage, see json.loads(...).
    """
    return json.loads(s, **kwargs)


JSONDecodeError = json.JSONDecodeError
