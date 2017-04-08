"""
GradeFast data models.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import collections
import posixpath
from os import PathLike
from typing import Dict, List, NamedTuple, Optional, Union


###################################################################################################
# Models for commands. See the GradeFast wiki:
# https://github.com/jhartz/gradefast/wiki/Command-Structure
###################################################################################################


class CommandItem:
    __slots__ = ("name", "command", "environment", "is_background", "stdin", "diff", "version")

    class Diff(NamedTuple):
        # ONE AND ONLY ONE of these 4 properties must be specified
        content: Optional[str]
        file: Optional[str]
        submission_file: Optional[str]
        command: Optional[str]

        # Diff options
        collapse_whitespace: bool

    def __init__(self, name: str, command: str, environment: Optional[Dict[str, str]] = None,
                 is_background: Optional[bool] = False, stdin: Optional[str] = None,
                 diff: Optional["Diff"] = None):
        self.name = name
        self.command = command
        self.environment = environment or {}
        self.is_background = is_background or False
        self.stdin = stdin
        self.diff = diff
        self.version = 1

    def get_name(self):
        if self.version > 1:
            return "%s (%s)" % (self.name, self.version)
        return self.name

    def get_modified(self, new_command: str) -> "CommandItem":
        command_item = CommandItem(self.name, new_command, self.environment, self.is_background,
                                   self.stdin, self.diff)
        command_item.version += self.version
        return command_item


class CommandSet:
    __slots__ = ("name", "commands", "folder", "environment")

    def __init__(self, name: str, commands: List["Command"],
                 folder: Optional[Union[str, List[str]]] = None,
                 environment: Optional[Dict[str, str]] = None):
        self.name = name
        self.commands = commands
        self.folder = folder
        self.environment = environment or {}


Command = Union[CommandSet, CommandItem]


###################################################################################################
# Other models that hold data needed by GradeFast components
###################################################################################################


class Path:
    """
    Represents a path to a file or folder. The path follows POSIX style (with forward slashes).
    The path may be relative or absolute depending on the Host instance that created it.

    It is guaranteed that the first component of the path (the part before the first "/") is never
    modified. This leaves Host implementations free to do things like start the path with "~"
    or "C:" or whatever they choose, knowing that that part will never be cut off.

    This is used for any representations of file paths within GradeFast to make it easier to use
    GradeFast configurations in a platform-agnostic way.
    """

    def __init__(self, gradefast_path: str):
        """
        :param gradefast_path: A path following POSIX style.
        """
        self._path = gradefast_path

    def get_gradefast_path(self) -> str:
        """
        :return: The path represented by this Path object, following POSIX style.
        """
        return self._path

    def append(self, subpart: str) -> "Path":
        """
        Create a new Path that is the result of appending "subpart" to this Path.

        This does NOT use "posixpath.normpath" to normalize the resulting path in order to preserve
        relative paths. For example, normpath would translate "~/../a" to just "a", but we keep it
        like that to preserve the fact that it's relative, not absolute. This keeps the path
        nonambiguous (and Host implementations thank us).
        """
        parts = self._path.split("/") + subpart.split("/")
        i = 1
        while i < len(parts):
            if parts[i] == "" or parts[i] == ".":
                parts.pop(i)
            else:
                i += 1

        # Start from the 3rd list element, because...
        #  - We want to keep the first bit of the path preserved (because that depends on the
        #    Host implementation, and it's not our job to touch it)
        #  - If the second element is "..", we can't do anything about it anyway
        i = 0
        while i < len(parts):
            if i > 1 and parts[i] == ".." and parts[i-1] != "..":
                parts.pop(i)
                parts.pop(i - 1)
                i -= 1
            else:
                i += 1

        path = "/".join(parts)
        if not path:
            path = "/"
        return Path(path)

    def relative_str(self, base_path: Optional["Path"]) -> str:
        """
        Get a string (only for displaying to the user) that is a representation of this path, but
        relative to another path (if provided). If the paths don't have the same prefix, then this
        original path is returned unchanged.
        """
        if base_path and self._path.startswith(base_path.get_gradefast_path()):
            rel_path = self._path[len(base_path.get_gradefast_path()):]
            if rel_path.startswith("/"):
                rel_path = rel_path[1:]
            if len(rel_path) > 0 and rel_path != ".." and not rel_path.startswith("../"):
                return rel_path
        return self._path

    def basename(self) -> str:
        """
        Get the base name (file or folder name) of this path.
        """
        return posixpath.basename(self._path)

    def __str__(self):
        return self._path

    def __repr__(self):
        return "Path(%s)" % repr(self._path)

    def __eq__(self, other):
        if not isinstance(other, Path):
            return NotImplemented
        return self._path == other.get_gradefast_path()

    def __ne__(self, other):
        if not isinstance(other, Path):
            return NotImplemented
        return not self.__eq__(other)


class LocalPath(PathLike):
    """
    Similar to Path, but the path is stored in the local operating system's format. You should NOT
    be using this class for anything that interacts with a Host instance (use Path instead).

    The path is just stored as a string; this class exists more for documentation purposes (to make
    it clear which kind of path a section of code is using). Since it is a path-like object, you
    can pass it directly to functions in the os.path module.
    """

    def __init__(self, path: str):
        self.path = path

    def __fspath__(self):
        return self.path

    def __str__(self):
        return self.path

    def __repr__(self):
        return "LocalPath(%s)" % repr(self.path)

    def __eq__(self, other):
        if not isinstance(other, LocalPath):
            return NotImplemented
        return self.path == other.path

    def __ne__(self, other):
        if not isinstance(other, LocalPath):
            return NotImplemented
        return not self.__eq__(other)


class Submission:
    """
    A submission by a particular student.
    """

    __slots__ = ("id", "name", "full_name", "path")

    def __init__(self, id: int, name: str, full_name: str, path: Path):
        """
        Initialize a new Submission.

        :param id: The unique ID of the submission.
        :param name: The name associated with the submission (i.e. the student's name).
        :param full_name: The full name of the submission (i.e. the full filename of the folder
            containing the submission).
        :param path: The path of the root of the submission.
        """
        self.id = id
        self.name = name
        self.full_name = full_name
        self.path = path

    def __str__(self):
        if self.name != self.full_name:
            return "%s (%s)" % (self.name, self.full_name)
        return self.name

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "full_name": self.full_name,
            "path": str(self.path)
        }


class Settings(NamedTuple):
    """
    Settings and metadata about a particular instance of GradeFast, including details about the
    assignment currently being graded.
    """

    project_name: str
    save_file: Optional[LocalPath]
    log_file: Optional[LocalPath]

    # GradeBook settings
    grade_structure: List[dict]
    host: int
    port: int

    # Grader settings
    commands: List[Command]
    submission_regex: Optional[str]
    check_zipfiles: bool
    check_file_extensions: Optional[List[str]]
    diff_file_path: Optional[LocalPath]

    # {Color,}CLIChannel (iochannels.py) settings
    use_color: bool

    # Host (hosts.py) settings
    base_env: Optional[Dict[str, str]]
    prefer_cli_file_chooser: bool
    # These "command" settings aren't necessarily local paths or GradeFast paths (hell, they could
    # just be the string "sh" or something).
    # We'll trust the user to tailor these to whatever Host subclass is in play.
    shell_command: Optional[str]
    terminal_command: Optional[str]


class SettingsDefaults:
    """
    Default values for noncritical items in Settings.
    """

    save_file = None
    log_file = None

    # Grader settings
    submission_regex = None
    check_zipfiles = False
    check_file_extensions = None
    diff_file_path = None

    # {Color,}CLIChannel (iochannels.py) settings
    use_color = True

    # Host (hosts.py) settings
    base_env = None
    prefer_cli_file_chooser = False
    shell_command = None
    terminal_command = None


class SettingsBuilder(collections.MutableMapping):
    """
    Mutable builder class to build a Settings object.
    """

    def __init__(self):
        self.__dict__["_settings"] = {}

    def __getattr__(self, key):
        return self._settings[key]

    def __setattr__(self, key, value):
        self[key] = value

    def __getitem__(self, key):
        return self._settings[key]

    def __setitem__(self, key, value):
        if key not in Settings._fields:
            raise NameError("Invalid setting name: %s" % key)
        self._settings[key] = value

    def __delitem__(self, key):
        del self._settings[key]

    def __iter__(self):
        return iter(self._settings)

    def __len__(self):
        return len(self._settings)

    def build(self) -> Settings:
        settings = dict(self._settings)
        for key in Settings._fields:
            if key not in settings and hasattr(SettingsDefaults, key):
                settings[key] = getattr(SettingsDefaults, key)
        return Settings(**settings)