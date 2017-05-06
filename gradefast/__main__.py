"""
Run GradeFast with the input of a YAML file and some command line arguments.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import sys
if sys.version_info < (3, 5):
    print("==> GradeFast requires Python 3.5 or later.")
    print("==> You have version:")
    print("    " + str(sys.version).replace("\n", "\n    "))
    sys.exit(1)

import argparse
import os
from typing import List, Optional, TextIO

from pyprovide import Injector

from gradefast import required_package_error
from gradefast.config.local import GradeFastLocalModule
from gradefast.hosts import LocalHost
from gradefast.loggingwrapper import get_logger, init_logging, shutdown_logging
from gradefast.models import LocalPath, Path, Settings, SettingsBuilder
from gradefast.parsers import ModelParseError, parse_commands, parse_grade_structure, parse_settings
from gradefast.run import run_gradefast

try:
    import yaml
except ImportError:
    yaml = None
    required_package_error("yaml", "PyYAML")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8051


class Formatter(argparse.HelpFormatter):
    """
    We're all consenting adults... https://mail.python.org/pipermail/tutor/2003-October/025932.html
    """

    def _split_lines(self, text, width):
        # Preserve newlines (as opposed to the default, which collapses them)
        lines = []
        for line in text.splitlines():
            lines += super()._split_lines(line, width)
        lines.append("")
        return lines


def get_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        "GradeFast",
        usage="python3 -m gradefast [-h|--help] [options] yaml-file",
        description="For GradeFast usage documentation, see: https://github.com/jhartz/gradefast",
        formatter_class=Formatter,
        epilog="The search path for the \"--shell\" or \"--terminal\" commands will include the "
               "folder containing the YAML Configuration File. Also, if the argument provided to "
               "\"--shell-arg\" or \"--terminal-arg\" begins with a hyphen, make sure to specify "
               "it using an equals sign, e.g. --whatever-arg=-c"
    )
    parser.add_argument(
        "--host",
        help="The hostname to run the gradebook HTTP server on.\n"
             "DEFAULT: {}".format(DEFAULT_HOST),
        default=DEFAULT_HOST
    )
    parser.add_argument(
        "--port",
        help="The port to run the gradebook HTTP server on.\n"
             "DEFAULT: {}".format(DEFAULT_PORT),
        default=DEFAULT_PORT
    )
    parser.add_argument(
        "--no-gradebook", action="store_true",
        help="Don't run the gradebook HTTP server."
    )
    parser.add_argument(
        "--shell", metavar="CMD",
        help="A program used to parse and run the commands in the \"commands\" section of the "
             "YAML file. The command to run will be passed as the last argument.\n"
             "DEFAULT: the operating system's default shell"
    )
    parser.add_argument(
        "--shell-arg", metavar="ARG", action="append",
        help="An argument for the command specified with --shell. This can be specified "
             "multiple times."
    )
    parser.add_argument(
        "--terminal", metavar="CMD",
        help="A program used to open a terminal or command prompt window. The path to the "
             "directory to start in will be passed as the last argument (and will also be the "
             "working directory of the process).\n"
             "DEFAULT: the operating system's default terminal"
    )
    parser.add_argument(
        "--terminal-arg", metavar="ARG", action="append",
        help="An argument for the command specified with --terminal. This can be specified "
             "multiple times."
    )
    parser.add_argument(
        "--no-readline", action="store_true",
        help="Don't try to use \"readline\" for command line autocompletion. This can help on "
             "some platforms (*cough* OS X) that have buggy readline support."
    )
    parser.add_argument(
        "--no-color", action="store_true",
        help="Don't use any color on the command line."
    )
    parser.add_argument(
        "--file-chooser", choices=("native", "cli"),
        help="Which file chooser to use when selecting folders. \"native\" attempts to use your "
             "OS's file chooser, while \"cli\" is a command-line-based file chooser.\n"
             "DEFAULT: \"native\" (if available)",
        default="native"
    )
    parser.add_argument(
        "--save-file", metavar="PATH",
        help="A file in which to save the current GradeFast state, allowing GradeFast to recover "
             "if you quit and come back later. This file is checked on startup; if it already "
             "exists, then GradeFast reads it to resume from where it left off.\n"
             "DEFAULT: [yaml filename].save.data (in the same directory as the YAML file)"
    )
    parser.add_argument(
        "--log-file", metavar="PATH",
        help="A file to save all command line output to. If a log file already exists at this "
             "path, it is appended to. If the filename ends in \".html\" or \".htm\", then the "
             "output is logged as HTML.\n"
             "DEFAULT: [yaml filename].log (in the same directory as the YAML file)"
    )
    parser.add_argument(
        "--debug-file", metavar="PATH",
        help="A file to log debug output to.\n"
             "DEFAULT: (none)"
    )
    parser.add_argument(
        "-f", "-s", "--submissions", metavar="PATH", action="append",
        help="A folder in which to look for submissions (optional; can be specified multiple "
             "times). When GradeFast starts, you will be able to choose more folders if you want."
    )
    parser.add_argument(
        "yaml_file", metavar="yaml-file",
        help="The GradeFast YAML Configuration File that contains the structure of the grading "
             "and the commands to run (see the GradeFast wiki at the link above)"
    )

    return parser


def parse_yaml_file(yaml_file: TextIO, gradebook_enabled: bool) -> SettingsBuilder:
    """
    Parse a GradeFast YAML configuration file and convert it to the GradeFast data structures,
    returning them in a partially-populated SettingsBuilder.

    See https://github.com/jhartz/gradefast/wiki/YAML-Configuration-Format

    :param yaml_file: An open stream containing the YAML data.
    :param gradebook_enabled: Whether the GradeBook is enabled. If this is False, then we won't
        bother parsing the grade structure.
    """
    errors = ModelParseError()

    yaml_data = yaml.load(yaml_file)
    if not yaml_data:
        raise errors.add_line("YAML file is empty")

    settings_builder = SettingsBuilder()

    for key in yaml_data.keys():
        if key == "config":
            # compatibility :(
            raise errors.add_line("Found unexpected top-level key: \"config\" "
                                  "(did you mean \"settings\"?")
        if key not in ("grades", "commands", "settings"):
            raise errors.add_line("Found unexpected top-level key: \"{}\"".format(key))

    # Parse the "commands" section using parse_command
    if "commands" in yaml_data:
        try:
            settings_builder.commands = parse_commands(yaml_data["commands"])
        except ModelParseError as exc:
            errors.add_all(exc)
    else:
        errors.add_line("YAML file missing \"commands\" section")

    # Parse the "grades" section using parse_grade_structure
    if gradebook_enabled:
        if "grades" in yaml_data:
            try:
                settings_builder.grade_structure = parse_grade_structure(yaml_data["grades"])
            except ModelParseError as exc:
                errors.add_all(exc)
        else:
            errors.add_line("YAML file missing \"grades\" section")
    else:
        settings_builder.grade_structure = None

    try:
        settings_builder.update(parse_settings(
            yaml_data["settings"] if "settings" in yaml_data else {}))
    except ModelParseError as exc:
        errors.add_all(exc)

    errors.raise_if_errors()
    return settings_builder


def _absolute_path_if_exists(item: str, base: LocalPath) -> Optional[str]:
    # Search order: working directory, YAML file directory
    if not item:
        return None
    if os.path.exists(item):
        return os.path.abspath(item)
    alt_path = os.path.join(base.get_local_path(), item)
    if os.path.exists(alt_path):
        return alt_path
    return item


def build_settings(args) -> Settings:
    logger = get_logger("build_settings")

    yaml_file_path = os.path.abspath(args.yaml_file)
    logger.info("YAML file: {}", yaml_file_path)
    if not os.path.isfile(yaml_file_path):
        logger.info("(not found)")
        print("YAML file not found:", yaml_file_path)
        sys.exit(1)

    yaml_file_name = os.path.splitext(os.path.basename(yaml_file_path))[0]
    yaml_directory = LocalPath(os.path.dirname(yaml_file_path))

    if args.save_file:
        save_file = LocalPath(os.path.abspath(args.save_file))
    else:
        save_file = LocalPath(os.path.join(yaml_directory.get_local_path(),
                                           yaml_file_name + ".save.data"))
    logger.info("Save file: {}", save_file)

    if args.log_file:
        log_file = LocalPath(os.path.abspath(args.log_file))
    else:
        log_file = LocalPath(os.path.join(yaml_directory.get_local_path(),
                                          yaml_file_name + ".log"))
    logger.info("Log file: {}", log_file)

    log_as_html = any(log_file.get_local_path().endswith(ext) for ext in (".html", ".htm"))
    if log_as_html:
        logger.info("Logging as HTML")

    base_env = dict(os.environ)
    base_env.update({
        "SUPPORT_DIRECTORY": yaml_directory.get_local_path(),
        "HELPER_DIRECTORY": yaml_directory.get_local_path(),
        "CONFIG_DIRECTORY": yaml_directory.get_local_path()
    })

    with open(yaml_file_path, encoding="utf-8") as yaml_file:
        try:
            settings_builder = parse_yaml_file(yaml_file, not args.no_gradebook)
        except ModelParseError as exc:
            print()
            print("Error parsing YAML file:")
            print(exc)
            sys.exit(1)

    settings_builder.project_name = yaml_file_name
    settings_builder.save_file = save_file
    settings_builder.log_file = log_file
    settings_builder.log_as_html = log_as_html

    settings_builder.gradebook_enabled = not args.no_gradebook
    # "grade_structure" filled from YAML file (if gradebook is enabled)
    settings_builder.host = args.host
    settings_builder.port = args.port

    # "commands" filled from YAML file
    # "submission_regex" filled from YAML file
    # "check_zipfiles" filled from YAML file
    # "check_file_extensions" filled from YAML file
    settings_builder.diff_file_path = yaml_directory

    settings_builder.use_readline = not args.no_readline
    settings_builder.use_color = not args.no_color

    settings_builder.base_env = base_env
    settings_builder.prefer_cli_file_chooser = args.file_chooser == "cli"

    settings_builder.shell_command = _absolute_path_if_exists(args.shell, yaml_directory)
    settings_builder.shell_args = args.shell_arg
    settings_builder.terminal_command = _absolute_path_if_exists(args.terminal, yaml_directory)
    settings_builder.terminal_args = args.terminal_arg

    return settings_builder.build()


def main() -> None:
    args = get_argument_parser().parse_args()
    init_logging(args.debug_file)

    settings = build_settings(args)

    # A PyProvide injector for all our needs
    injector = Injector(GradeFastLocalModule(settings))

    # Get and validate the initial list of submission folders
    local_host = injector.get_instance(LocalHost)
    submission_paths = []  # type: List[Path]
    if args.submissions:
        found_bad = False
        for folder in args.submissions:
            if not os.path.isdir(folder):
                print("Submissions path must be a folder:", folder)
                found_bad = True
        if found_bad:
            sys.exit(1)
        submission_paths = [
            local_host.local_path_to_gradefast_path(LocalPath(os.path.abspath(folder)))
            for folder in args.submissions
        ]

    # Zhu Li, do the thing!
    run_gradefast(injector, submission_paths)

    # Make sure that all of our doors are shut for the winter
    shutdown_logging()

    # Back in the day, for some reason, we had some unruly threads hanging around that would
    # prevent GradeFast from exiting, hence brutally killing them using os._exit; however, it
    # doesn't seem like we need this anymore.
    # TODO: Do we still need this for certain platforms (*cough* Windows)?
    #os._exit(0)


if __name__ == "__main__":
    main()
