"""
Parse GradeFast YAML configuration files.
See https://github.com/jhartz/gradefast/wiki/YAML-Configuration-Format

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import sys
from typing import Any, Dict, List, Optional, Union

from gradefast.models import Command, CommandItem, CommandSet, SettingsBuilder

try:
    import yaml
except ImportError:
    yaml = None
    print("")
    print("==> Couldn't find YAML package!")
    print("==> Please install 'PyYAML' and try again.")
    print("")
    sys.exit(1)


class YAMLStructureError(Exception):
    """
    Any error with the structure of the YAML configuration file.
    """


def _load_yaml_data(yaml_file) -> dict:
    """
    Read the YAML file and make sure it has the required top-level components.

    :param yaml_file: An open stream containing the YAML data.
    :return: The parsed YAML data.
    """
    yaml_data = yaml.load(yaml_file)
    if not yaml_data:
        raise YAMLStructureError("YAML file is empty")

    if "grades" not in yaml_data:
        raise YAMLStructureError("Missing \"grades\" section")

    if "commands" not in yaml_data:
        raise YAMLStructureError("Missing \"commands\" section")

    for key in yaml_data.keys():
        if key == "config":
            # compatibility :(
            raise YAMLStructureError("Found unexpected top-level key: \"config\" "
                                     "(did you mean \"settings\"?")
        if key not in ("grades", "commands", "settings"):
            raise YAMLStructureError("Found unexpected top-level key: \"%s\"" % key)

    return yaml_data


def _parse_commands(command_list: list) -> List[Command]:
    """
    Parse the "commands" section of the YAML file into a list of CommandItem and CommandSet objects.
    """
    commands = []
    for command_dict in command_list:
        if "name" not in command_dict:
            raise YAMLStructureError("Command missing \"name\"")
        if "command" not in command_dict and "commands" not in command_dict:
            raise YAMLStructureError("Command \"%s\" missing \"command\" or \"commands\"" %
                                     command_dict["name"])
        if "command" in command_dict and "commands" in command_dict:
            raise YAMLStructureError("Command \"%s\" has both \"command\" and \"commands\"" %
                                     command_dict["name"])

        if "commands" in command_dict:
            # It's a command set
            commands.append(CommandSet(
                command_dict["name"],
                _parse_commands(command_dict["commands"]),
                command_dict.get("folder"),
                command_dict.get("environment")
            ))
        else:
            # It's a command item
            commands.append(CommandItem(
                command_dict["name"],
                command_dict["command"],
                command_dict.get("environment"),
                command_dict.get("background"),
                command_dict.get("input") or command_dict.get("stdin"),
                _parse_command_diff(command_dict.get("diff"))
            ))
    return commands


def _parse_command_diff(diff_object: Optional[Union[dict, str]]) -> Optional[CommandItem.Diff]:
    """
    Parse the "diff" property for a command.
    """
    if diff_object is None:
        return None

    if isinstance(diff_object, str):
        return CommandItem.Diff(file=diff_object)

    content = diff_object.get("content") or None
    file = diff_object.get("file") or None
    submission_file = diff_object.get("submission file") or None
    command = diff_object.get("command") or None
    if [content, file, submission_file, command].count(None) != 3:
        raise YAMLStructureError("Diff object must have one and only one of the following: "
                                 "content, file, submission_file, command")

    return CommandItem.Diff(
        content=content, file=file, submission_file=submission_file, command=command,
        collapse_whitespace=diff_object.get("collapse whitespace", False))


def _parse_settings(settings_dict: dict) -> Dict[str, Any]:
    """
    Parse the "settings" section of the YAML file into the properties expected by the
    SettingsBuilder.

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

    settings: Dict[str, Any] = {}

    for key, value in settings_dict.items():
        if key in yaml_key_to_setting:
            setting = yaml_key_to_setting[key]
            if not setting_type_checks[setting](value):
                raise YAMLStructureError("Invalid type for setting: %s" % key)
            settings[setting] = value
        else:
            raise YAMLStructureError("Invalid setting: %s" % key)

    return settings


def parse_yaml(yaml_file) -> SettingsBuilder:
    """
    Parse a GradeFast YAML configuration file and convert it to the GradeFast data structures,
    returning them in a partially-populated SettingsBuilder.

    :param yaml_file: An open stream containing the YAML data.
    """
    data = _load_yaml_data(yaml_file)
    settings_builder = SettingsBuilder()

    settings_builder.commands = _parse_commands(data["commands"])
    settings_builder.grade_structure = data["grades"]

    settings_builder.update(_parse_settings(data["settings"] if "settings" in data else {}))
    return settings_builder
