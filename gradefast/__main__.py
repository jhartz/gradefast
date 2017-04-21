"""
Run GradeFast with the input of a YAML file and some command line arguments.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

# NOTE: In order for this version check to be executed, the interpreter must be able to parse this
# file. Therefore, avoid using new syntax (like variable type annotations). Stick to anything that
# would've been valid Python 3.0 (showing the error message for Python 2 is sort of a lost cause).

import sys
if sys.version_info < (3, 6):
    print("==> GradeFast requires Python 3.6 or later.")
    print("==> You have version:")
    print("    " + str(sys.version).replace("\n", "\n    "))
    sys.exit(1)

import argparse
import logging
import os
from typing import Optional

from pyprovide import Injector

from gradefast import yamlsettings
from gradefast.config.local import GradeFastLocalModule
from gradefast.hosts import LocalHost
from gradefast.models import LocalPath
from gradefast.run import run_gradefast

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


def get_parser():
    parser = argparse.ArgumentParser(
        "GradeFast",
        usage="python3 -m gradefast [-h|--help] [options] yaml-file",
        description="For GradeFast usage documentation, see: https://github.com/jhartz/gradefast",
        formatter_class=Formatter,
        epilog="The search path for the \"shell\" or \"terminal\" commands will include the "
               "folder containing the YAML Configuration File."
    )
    parser.add_argument(
        "--host",
        help="The hostname to run the gradebook HTTP server on.\nDefault: %s" % DEFAULT_HOST,
        default=DEFAULT_HOST
    )
    parser.add_argument(
        "--port",
        help="The port to run the gradebook HTTP server on.\nDefault: %s" % DEFAULT_PORT,
        default=DEFAULT_PORT
    )
    parser.add_argument(
        "--shell", metavar="CMD",
        help="A program used to parse and run the commands in the \"commands\" section of the "
             "YAML file.\n"
             "The command to run will be passed as an argument.\n"
             "Default: the operating system's default shell"
    )
    parser.add_argument(
        "--terminal", metavar="CMD",
        help="A program used to open a terminal or command prompt window.\n"
             "The path to the directory to start in will be passed as an argument (and will also "
             "be the working directory of the process).\n"
             "Default: the operating system's default terminal"
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
             "Default: \"native\" (if available)",
        default="native"
    )
    parser.add_argument(
        "--save-file", metavar="PATH",
        help="A file in which to save the current GradeFast state, allowing GradeFast to recover "
             "if it crashes. This file is checked on startup; if it already exists, then "
             "GradeFast reads it to resume from where it left off.\n"
             "Default: [yaml filename].save.data (in the same directory as the YAML file)"
    )
    parser.add_argument(
        "--log-file", metavar="PATH",
        help="A file to save all output to. This is usually better than using \"tee\" since it "
             "includes user input (stdin) as well. If a log file already exists at this path, it "
             "is appended to.\n"
             "If the filename ends in \".html\" or \".htm\", then the output is logged as HTML.\n"
             "Default: [yaml filename].log (in the same directory as the YAML file)"
    )
    parser.add_argument(
        "--debug-file", metavar="PATH",
        help="A file to log debug output to.\nDefault: (none)"
    )
    parser.add_argument(
        "-f", "-s", "--submissions", metavar="PATH", action="append",
        help="A folder in which to look for submissions (optional; can be specified multiple "
             "times).\n"
             "When GradeFast starts, you will be able to choose more folders if you want."
    )
    parser.add_argument(
        "yaml_file", metavar="yaml-file",
        help="The GradeFast YAML Configuration File that contains the structure of the grading "
             "and the commands to run (see the GradeFast wiki at the link above)"
    )

    return parser


def init_logging(log_file: str):
    logging.basicConfig(
        filename=log_file,
        level=logging.DEBUG,
        format="%(asctime)s  %(threadName)-11s %(levelname)-5s [%(name)s]  %(message)s"
    )


def disable_logging():
    logging.basicConfig(level=logging.CRITICAL)


def shutdown_logging():
    logging.shutdown()


def _absolute_path_if_exists(item: str, base: LocalPath) -> Optional[str]:
    # Search order: working directory, YAML file directory
    if not item:
        return None
    if os.path.exists(item):
        return os.path.abspath(item)
    alt_path = os.path.join(base, item)
    if os.path.exists(alt_path):
        return alt_path
    return item


def build_settings(args):
    yaml_file_path = os.path.abspath(args.yaml_file)
    logging.info("YAML file: %s", yaml_file_path)
    if not os.path.isfile(yaml_file_path):
        logging.info("(not found)")
        print("YAML file not found: %s" % yaml_file_path)
        sys.exit(1)

    yaml_file_name = os.path.splitext(os.path.basename(yaml_file_path))[0]
    yaml_directory = LocalPath(os.path.dirname(yaml_file_path))

    if args.save_file:
        save_file = LocalPath(os.path.abspath(args.save_file))
    else:
        save_file = LocalPath(os.path.join(yaml_directory, yaml_file_name + ".save.data"))
    logging.info("Save file: %s", save_file)

    if args.log_file:
        log_file = LocalPath(os.path.abspath(args.log_file))
    else:
        log_file = LocalPath(os.path.join(yaml_directory, yaml_file_name + ".log"))
    logging.info("Log file: %s", log_file)

    log_as_html = log_file.path.endswith(".html") or log_file.path.endswith(".htm")
    if log_as_html:
        logging.info("Logging as HTML")

    base_env = dict(os.environ)
    base_env.update({
        "SUPPORT_DIRECTORY": yaml_directory.path,
        "HELPER_DIRECTORY": yaml_directory.path,
        "CONFIG_DIRECTORY": yaml_directory.path
    })

    with open(yaml_file_path, encoding="utf-8") as yaml_file:
        try:
            settings_builder = yamlsettings.parse_yaml(yaml_file)
        except yamlsettings.YAMLStructureError as e:
            print("Error parsing YAML file:", e)
            sys.exit(1)

    settings_builder.project_name = yaml_file_name
    settings_builder.save_file = save_file
    settings_builder.log_file = log_file
    settings_builder.log_as_html = log_as_html
    # "grade_structure" filled from YAML file
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
    settings_builder.terminal_command = _absolute_path_if_exists(args.terminal, yaml_directory)

    return settings_builder.build()


def main():
    args = get_parser().parse_args()
    if args.debug_file:
        init_logging(args.debug_file)
    else:
        disable_logging()
    logging.info("STARTING GRADEFAST")

    settings = build_settings(args)

    # A PyProvide injector for all our needs
    injector = Injector(GradeFastLocalModule(settings))

    # Get and validate the initial list of submission folders
    local_host = injector.get_instance(LocalHost)
    submission_paths = []
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
    logging.info("SHUTTING DOWN GRADEFAST")
    shutdown_logging()
    os._exit(0)


if __name__ == "__main__":
    main()
