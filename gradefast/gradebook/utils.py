"""
Utility functions and classes related to the GradeBook HTTP server.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import json
import traceback
import uuid
from typing import Any


def print_error(*messages: Any, start="\n\n", sep: str = " ", end="\n",
                print_traceback: bool = False):
    """
    Print an error message, with details.

    :param messages: The messages to include
    :param start: A string to print before the error message. (If the grader is running, the user
        is probably in the middle of some interaction. To interrupt them a teensy bit less, this
        pads with some newlines by default.)
    :param sep: The separator used to join items in "messages".
    :param end: A string to print after the error messages (not including the line break at the end
        of the last message).
    :param print_traceback: Whether to include a traceback of the last exception.
    """
    message = sep.join(str(message) for message in messages)
    if print_traceback:
        message += "\n" + traceback.format_exc()

    print(start, end="")
    for line in message.split("\n"):
        print("==>", line.rstrip())
    print(end, end="")


class GradeBookJsonEncoder(json.JSONEncoder):
    """
    A custom JSONEncoder that encodes UUIDs as a string containing the hex version of the UUID.
    """

    _instance = None

    @staticmethod
    def get_instance() -> "GradeBookJsonEncoder":
        if GradeBookJsonEncoder._instance is None:
            GradeBookJsonEncoder._instance = GradeBookJsonEncoder()
        return GradeBookJsonEncoder._instance

    def default(self, o):
        if isinstance(o, uuid.UUID):
            return str(o)
        return super().default(o)


def to_json(o: Any) -> str:
    """
    Convert an object to a JSON string. For usage, see json.dumps(...).
    """
    return GradeBookJsonEncoder.get_instance().encode(o)


def from_json(*args, **kwargs):
    """
    Convert a JSON string to an object representation. For usage, see json.loads(...).
    """
    return json.loads(*args, **kwargs)


JSONDecodeError = json.JSONDecodeError
