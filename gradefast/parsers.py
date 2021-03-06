"""
Parsers for GradeFast data models.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

from typing import Callable, Dict, List, Optional, Tuple, TypeVar, Union

from gradefast.loggingwrapper import get_logger
from gradefast.models import Command, CommandItem, CommandSet, \
    GradeItem, GradeScore, GradeSection, Hint, ScoreNumber, WeakScoreNumber

T = TypeVar("T")


class ModelParseError(Exception):
    """
    Exception used for errors when parsing a dict into one of the models. If it makes sense for the
    model, multiple errors can be batched up and included in a single exception.
    """

    def __init__(self) -> None:
        self._errors = []  # type: List[Union[str, Tuple[str, str, str]]]

    def add(self, title: str, subject: str, error: str) -> "ModelParseError":
        self._errors.append((title, subject, error))
        return self

    def add_line(self, line: str) -> "ModelParseError":
        self._errors.append(line)
        return self

    def add_all(self, exc: "ModelParseError") -> "ModelParseError":
        self._errors += exc._errors
        return self

    def has_errors(self) -> bool:
        return len(self._errors) > 0

    def raise_if_errors(self) -> None:
        if self.has_errors():
            raise self

    def __str__(self) -> str:
        s = ""
        for line in self._errors:
            if isinstance(line, tuple):
                s += "==> {} {}: {}".format(*line)
            else:
                s += "==> {}".format(line)
            s += "\n"
        return s


def make_score_number(val: WeakScoreNumber) -> ScoreNumber:
    """
    Convert a string or something else to either a float or a int.
    """
    try:
        num_val = float(val)
    except Exception:
        raise ValueError("Not a number: " + str(val))

    # Make it an int if we can
    if int(num_val) == num_val:
        num_val = int(num_val)
    return num_val


def _str_or_none(s: Optional[object]) -> Optional[str]:
    return None if s is None else str(s)


def _parse_list(lst: List[dict], parse_func: Callable[[dict, List[int], str], T],
                _path: List[int] = None) -> List[T]:
    if _path is None:
        _path = []

    if not isinstance(lst, list):
        raise ModelParseError().add("Item", "#" + ".".join(map(str, _path)), "must be a list")

    items = []  # type: List[T]
    errors = ModelParseError()
    for index, item in enumerate(lst, start=1):
        path = _path + [index]
        subject = "#" + ".".join(map(str, path))
        try:
            items.append(parse_func(item, path, subject))
        except ModelParseError as exc:
            errors.add_all(exc)
    errors.raise_if_errors()
    return items


def parse_commands(lst: List[dict]) -> List[Command]:
    """
    Parse a list of commands (list of dictionaries) into a list of CommandSets and CommandItems,
    raising a ModelParseError if something ain't right.
    """
    return _parse_list(lst, _parse_command)


def _parse_command(command_dict: dict, path: List[int], subject: str) -> Command:
    errors = ModelParseError()

    name = _str_or_none(command_dict.get("name"))
    if name:
        name = name.strip()
    if name:
        subject += " ({})".format(name)

    if "command" not in command_dict and "commands" not in command_dict:
        raise errors.add("Command", subject, "has neither \"command\" nor \"commands\"")
    if "command" in command_dict and "commands" in command_dict:
        raise errors.add("Command", subject, "has both \"command\" and \"commands\"")

    if "commands" in command_dict:
        # It's a command set
        errors = ModelParseError()

        for key in command_dict.keys():
            if key not in ["name", "folder", "confirm folder", "environment", "commands"]:
                errors.add("Command set", subject, "has an invalid property: \"{}\"".format(key))

        try:
            commands = _parse_list(command_dict["commands"], _parse_command, path)
        except ModelParseError as exc:
            errors.add_all(exc)

        errors.raise_if_errors()
        return CommandSet(
            commands,
            _str_or_none(command_dict.get("name")),
            command_dict.get("folder"),
            command_dict.get("confirm folder", "folder" in command_dict),
            command_dict.get("environment")
        )
    else:
        # It's a command item
        if "name" not in command_dict:
            raise errors.add("Command item", subject, "missing \"name\"")

        for key in command_dict.keys():
            if key not in ["name", "command", "environment", "background", "passthrough",
                           "passthru", "input", "stdin", "diff"]:
                errors.add("Command item", subject, "has an invalid property: \"{}\"".format(key))

        is_background = command_dict.get("background")
        is_passthrough = command_dict.get("passthrough") or command_dict.get("passthru")
        stdin = _str_or_none(command_dict.get("input") or command_dict.get("stdin"))
        diff_value = command_dict.get("diff")

        if is_passthrough:
            if is_background:
                errors.add("Command item", subject,
                           "has both \"background\" and \"passthrough\" set")
            if stdin:
                errors.add("Command item", subject,
                           "has both \"passthrough\" and \"input\" set")
            if diff_value:
                errors.add("Command item", subject,
                           "has both \"passthrough\" and \"diff\" set")

        try:
            diff = _parse_command_diff(diff_value, subject)
        except ModelParseError as exc:
            errors.add_all(exc)

        errors.raise_if_errors()
        return CommandItem(
            str(command_dict["name"]).strip(),
            str(command_dict["command"]).rstrip(),
            command_dict.get("environment"),
            is_background,
            is_passthrough,
            stdin,
            diff
        )


def _parse_command_diff(diff_object: Optional[Union[dict, str]],
                        subject: str) -> Optional[CommandItem.Diff]:
    """
    Parse the "diff" property for a command.
    """
    if diff_object is None:
        return None

    if isinstance(diff_object, str):
        return CommandItem.Diff(file=diff_object)

    errors = ModelParseError()

    try:
        content = _str_or_none(diff_object.get("content") or None)
        file = _str_or_none(diff_object.get("file") or None)
        submission_file = _str_or_none(diff_object.get("submission file") or None)
        command = _str_or_none(diff_object.get("command") or None)
    except AttributeError:
        raise errors.add("Command item", subject, "diff object must be a string or dictionary")

    if [content, file, submission_file, command].count(None) != 3:
        errors.add("Command item", subject,
                   "diff object must have one and only one of the following: "
                   "content, file, submission file, command")

    for key in diff_object.keys():
        if key not in ["content", "file", "submission file", "command", "collapse whitespace"]:
            errors.add("Command item", subject,
                       "diff object has an invalid property: \"{}\"".format(key))

    errors.raise_if_errors()
    return CommandItem.Diff(
        content=content, file=file, submission_file=submission_file, command=command,
        collapse_whitespace=diff_object.get("collapse whitespace", False))


def parse_grade_structure(lst: List[dict]) -> List[GradeItem]:
    """
    Parse a grade structure (list of dictionaries) into a list of GradeScores and GradeSections,
    raising a ModelParseError if something ain't right.
    """
    return _parse_list(lst, _parse_grade_item)


def _parse_grade_item(item: dict, path: List[int], subject: str) -> GradeItem:
    _logger = get_logger("parsers: grade structure")
    errors = ModelParseError()

    name = item.get("name")
    if name:
        name = str(name).strip()
    if name:
        subject += " ({})".format(name)
    else:
        errors.add("Grade item", subject, "missing \"name\"")

    if "grades" in item and "points" in item:
        raise errors.add("Grade item", subject, "has both \"points\" and \"grades\"")
    if "grades" not in item and "points" not in item:
        raise errors.add("Grade item", subject, "has neither \"points\" nor \"grades\"")

    title = "Grade score" if "points" in item else "Grade section"

    def error(error_str: str) -> ModelParseError:
        return errors.add(title, subject, error_str)

    hint_dicts = []  # type: List[Dict[str, object]]
    if "hints" in item:
        if not isinstance(item["hints"], list):
            error("\"hints\" section is not a list")
        else:
            hint_dicts += item["hints"]

    # Check for old, deprecated versions of "hints"
    for old_hints_prop in ["section deductions", "deductions", "point hints"]:
        if old_hints_prop in item:
            _logger.warning("{} {} has deprecated \"{}\" (converted to \"hints\")",
                            title, subject, old_hints_prop)
            hint_dicts += map(lambda old_hint: {
                "name": _str_or_none(old_hint.get("name")),
                "value": make_score_number(old_hint.get("value") or -old_hint.get("minus", 0)),
                "default enabled": old_hint.get("default enabled", False)
            }, item[old_hints_prop])

    hints = []  # type: List[Hint]
    for hint_dict in hint_dicts:
        if "name" not in hint_dict:
            error("has a hint without a name")
        else:
            hint_name = str(hint_dict["name"]).strip()
            hint_value = 0  # type: ScoreNumber
            if "value" not in hint_dict:
                _logger.warning("Hint \"{}\" in {} {} is missing a value; assuming 0",
                                hint_dict["name"], title, subject)
            else:
                try:
                    hint_value = make_score_number(hint_dict["value"])
                except ValueError:
                    error("value for hint \"{}\" (\"{}\") is not a number".format(
                        hint_name, hint_dict["value"]))

            for key in hint_dict.keys():
                if key not in ["name", "value", "default enabled"]:
                    error("hint \"{}\" has an invalid property: \"{}\"".format(hint_name, key))

            hints.append(Hint(hint_name, hint_value, hint_dict.get("default enabled", False)))

    notes = ""
    if "notes" in item:
        notes = item["notes"]
    elif "note" in item:
        notes = item["note"]
    if isinstance(notes, list):
        notes = "- " + "\n- ".join(str(n) for n in notes)
    else:
        notes = str(notes)

    default_enabled = True
    if "default enabled" in item:
        default_enabled = bool(item["default enabled"])
    elif item.get("disabled"):
        default_enabled = False

    # Check stuff specific to grade sections
    if "grades" in item:
        deduct_percent_if_late_prop = None
        deduct_percent_if_late = 0  # type: ScoreNumber
        try:
            if "deduct percent if late" in item:
                deduct_percent_if_late_prop = "deduct percent if late"
                deduct_percent_if_late = make_score_number(item["deduct percent if late"])
            elif "deductPercentIfLate" in item:
                deduct_percent_if_late_prop = "deductPercentIfLate"
                deduct_percent_if_late = make_score_number(item["deductPercentIfLate"])
                raise ValueError()
        except ValueError:
            error("{} (\"{}\") must be a number".format(deduct_percent_if_late_prop,
                                                        item[deduct_percent_if_late_prop]))
        else:
            if deduct_percent_if_late < 0:
                error("{} (\"{}\") cannot be negative".format(deduct_percent_if_late_prop,
                                                              deduct_percent_if_late))
            if deduct_percent_if_late > 100:
                error("{} (\"{}\") cannot be greater than 100".format(deduct_percent_if_late_prop,
                                                                      deduct_percent_if_late))

        for key in item.keys():
            if key not in ["name", "grades", "hints", "point hints", "section deductions",
                           "deductions", "default enabled", "disabled",
                           "deduct percent if late", "deductPercentIfLate", "notes", "note"]:
                error("has an invalid property: \"{}\"".format(key))

        try:
            grades = _parse_list(item["grades"], _parse_grade_item, path)
        except ModelParseError as exc:
            errors.add_all(exc)

        errors.raise_if_errors()
        return GradeSection(
            default_name=name,
            default_notes=notes,
            default_enabled=default_enabled,
            hints=hints,
            grades=grades,
            default_late_deduction=deduct_percent_if_late
        )

    # Check stuff specific to grade scores
    else:
        try:
            points = make_score_number(item["points"])
        except ValueError:
            raise error("points (\"{}\") must be a number".format(item["points"]))

        if points < 0:
            error("points (\"{}\") must be at least zero".format(points))

        default_score = points  # type: ScoreNumber
        try:
            if "default score" in item:
                default_score = make_score_number(item["default score"])
            elif "default points" in item:
                _logger.warning("Grade score {} has deprecated \"default points\" (converted to "
                                "\"default score\")", subject)
                default_score = make_score_number(item["default points"])
        except ValueError:
            error("default score (\"{}\") must be a number".format(item["default score"] or
                                                                   item["default points"]))
        if default_score < 0:
            error("default score (\"{}\") cannot be negative".format(default_score))
        if default_score > points:
            error("default score (\"{}\") cannot be greater than the total points ({})".format(
                default_score, points))

        for key in item.keys():
            if key not in ["name", "points", "hints", "point hints", "section deductions",
                           "deductions", "default enabled", "disabled", "default score",
                           "default points", "default comments", "notes", "note"]:
                error("has an invalid property: \"{}\"".format(key))

        errors.raise_if_errors()
        return GradeScore(
            default_name=name,
            default_notes=notes,
            default_enabled=default_enabled,
            hints=hints,
            points=points,
            default_score=default_score,
            default_comments=item.get("default comments", ""),
        )


def parse_settings(settings_dict: dict) -> Dict[str, object]:
    """
    Parse the "settings" section of a YAML file into the properties expected by SettingsBuilder.

    See https://github.com/jhartz/gradefast/wiki/YAML-Configuration-Format#settings
    """
    yaml_key_to_setting = {
        "submission regex": "submission_regex",
        "check zipfiles": "check_zipfiles",
        "check file extensions": "check_file_extensions"
    }
    setting_type_checks = {
        "submission_regex": lambda value: isinstance(value, str),
        "check_zipfiles": lambda value: isinstance(value, bool),
        "check_file_extensions": lambda value: isinstance(value, list) and
                                               all(isinstance(item, str) for item in value)
    }

    settings = {}  # type: Dict[str, object]
    errors = ModelParseError()

    for key, value in settings_dict.items():
        if key in yaml_key_to_setting:
            setting = yaml_key_to_setting[key]
            if setting_type_checks[setting](value):
                settings[setting] = value
            else:
                errors.add_line("Invalid type for setting \"{}\"".format(key))
        elif key == "regex":
            errors.add_line("Invalid setting: \"regex\" (did you mean \"submission regex\"?)")
        else:
            errors.add_line("Invalid setting: \"{}\"".format(key))

    errors.raise_if_errors()
    return settings
