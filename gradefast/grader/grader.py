"""
GradeFast Grader - Runs commands on submissions and controls the grading process.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import difflib
import io
import os
import platform
import re
import zipfile

from typing import Callable, List, Optional

from .. import events

from .graderio import GraderIO
from .graderos import GraderOS


class Grader:
    """
    Run commands on submissions.
    """

    def __init__(self, grader_io: GraderIO, grader_os: GraderOS):
        self._io = grader_io
        self._os = grader_os
        self._submissions = []

    def _find_directory_from_regex(self, base_directory: str, regex: str) -> Optional[str]:
        """
        Find a directory, relative to an existing directory, based on a regular expression.

        :param base_directory: The current path.
        :param regex: The regex to match to a subdirectory of base_directory.
        :return: The full path to a valid subdirectory, or None if none was found.
        """
        regex = re.compile(regex)
        for item_name, item_type, is_link in self._os.list_dir(base_directory):
            if item_type != "directory":
                continue
            match = regex.fullmatch(item_name)
            if match is None:
                continue
            return base_directory + "/" + item_name

        # If we got here, then we didn't find shit
        return None
