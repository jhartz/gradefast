"""
GradeFast Grader - Runs commands on submissions and controls the grading process.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import difflib
import os
import random
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple, Union

from iochannels import Channel, HTMLMemoryLog, MemoryLog, Msg
from pyprovide import Injector, inject

from gradefast import events
from gradefast.grader import eventhandlers
from gradefast.grader.banners import BANNERS
from gradefast.hosts import BackgroundCommand, CommandRunError, CommandStartError, Host
from gradefast.log import get_logger
from gradefast.models import Command, CommandItem, Path, Settings, Submission

_logger = get_logger("grader")


class Grader:
    """
    Control the grading process and run commands on submissions.
    """

    @inject(injector=Injector.CURRENT_INJECTOR)
    def __init__(self, injector: Injector, channel: Channel, host: Host,
                 event_manager: events.EventManager, settings: Settings) -> None:
        self.injector = injector
        self.channel = channel
        self.host = host
        self.event_manager = event_manager
        self.settings = settings

        self._submissions = []  # type: List[Submission]

        event_manager.register_all_event_handlers(eventhandlers)

    def prompt_for_submissions(self) -> bool:
        """
        Nag the user into choosing at least one folder of submissions. The user is prompted
        (repeatedly) to choose the folder.

        :return: True if there's some submissions to go on; False if they got nuthin'.
        """
        if len(self._submissions):
            # Go each on them
            while self.channel.prompt("Want to add another folder of submissions?",
                                      ["y", "N"], "n") == "y":
                self.add_submissions(None)
        else:
            # They don't have anything yet; they're in for quite a treat
            self.channel.input("Press Enter to choose a folder containing the submissions...")
            while True:
                if not self.add_submissions(None):
                    # They've actually hit "cancel"; I guess we can give up
                    break

                if not len(self._submissions):
                    self.channel.error("No submissions found")
                    continue

                self.channel.print()
                if self.channel.prompt("Add another folder?", ["y", "N"], "n") == "n":
                    break

        return len(self._submissions) > 0

    def add_submissions(self, base_folder: Path = None) -> bool:
        """
        Add a folder of submissions to our list of submissions. The user is prompted to choose the
        folder.

        The regular expression is used to limit which folders are picked up. Also, the first
        matched group in the regex is used as the name of the submission.

        For more info on some of the parameters, see the documentation on the GradeFast wiki:
        https://github.com/jhartz/gradefast/wiki

        :param base_folder: The path to a base folder to use when prompting the user to choose a
            folder. If it does not exist, then it falls back to the Host::choose_dir default.

        :return: True if the user actually tried to pick something (even if we couldn't find any
            submissions in the folder they picked); False if they cancelled.
        """
        check_file_extensions = self.settings.check_file_extensions
        if check_file_extensions is None:
            check_file_extensions = []

        # Step 1: Prompt the user for a folder
        path = self.host.choose_folder(base_folder)
        if not path:
            self.channel.error("No folder provided")
            return False

        # Step 2: Find matching submissions
        regex = None
        if self.settings.submission_regex:
            regex = re.compile(self.settings.submission_regex)

        for name, type, is_link in sorted(self.host.list_folder(path)):
            submission_match = False  # type: Any
            folder_path = None  # type: Path

            valid_submission = False
            if type == "folder":
                if regex:
                    submission_match = regex.fullmatch(name)
                else:
                    submission_match = True
                if submission_match:
                    self.channel.print("Found submission folder: {}", name)
                    folder_path = path.append(name)
                    valid_submission = True
            elif type == "file" and name.find(".") > 0:
                name, ext = name.rsplit(".", maxsplit=1)
                if regex:
                    submission_match = regex.fullmatch(name)
                else:
                    submission_match = True
                if submission_match and not self.host.exists(path.append(name)):
                    folder_path = path.append(name)
                    file_path = path.append(name + "." + ext)
                    if self.settings.check_zipfiles and ext == "zip":
                        self.channel.print("Found submission zipfile: {}.zip", name, end="; ")
                        self.host.unzip(file_path, folder_path)
                        self.channel.print("    extracted to {}/", name)
                        valid_submission = True
                    elif ext in check_file_extensions:
                        self.channel.print("Found submission file: {}.{}", name, ext, end="; ")
                        self.host.move_to_folder(file_path, folder_path)
                        self.channel.print("    moved into {}/", name)
                        valid_submission = True

            if valid_submission:
                submission_id = len(self._submissions) + 1
                submission_name = name
                if regex:
                    for group in submission_match.groups():
                        if group:
                            submission_name = group
                            break
                self._submissions.append(Submission(
                    submission_id, submission_name, name, folder_path))

        # Step 3: Tell the world
        if len(self._submissions):
            self.event_manager.dispatch_event(events.NewSubmissionListEvent(self._submissions))

        return True

    def run_commands(self) -> None:
        """
        Run some commands on each of the previously added submissions.

        For details on what should be in the list of commands, see the GradeFast wiki:
        https://github.com/jhartz/gradefast/wiki/Command-Structure
        """

        self.channel.print()
        self.channel.print()
        self.channel.error_bordered(random.choice(BANNERS))
        self.channel.print()

        submission_id = 1
        background_commands = []  # type: List[BackgroundCommand]
        while True:
            # A quick check in case the list of submissions is modified during grading
            if submission_id > len(self._submissions):
                submission_id = len(self._submissions)

            submission = self._submissions[submission_id - 1]

            self.channel.print()
            self.channel.status_bordered("Next Submission: {} ({}/{})",
                                         submission.name, submission.id, len(self._submissions))

            what_to_do = self.channel.prompt(
                "Press Enter to begin; (g)oto, (b)ack, (s)kip, (l)ist, (a)dd, (q)uit, (h)elp",
                ["", "g", "goto", "b", "back", "s", "skip", "l", "list", "a", "add", "q", "quit",
                 "h", "help", "?"],
                show_choices=False)

            if what_to_do == "?" or what_to_do == "h" or what_to_do == "help":
                # Print more help
                self.channel.print("(Enter): Start the next submission")
                self.channel.print("g/goto:  Go to a specific submission")
                self.channel.print("b/back:  Go to the previous submission (goto -1)")
                self.channel.print("s/skip:  Skip the next submission (goto +1)")
                self.channel.print("l/list:  List all the submissions and corresponding indices")
                self.channel.print("a/add:   Add another folder of submissions")
                self.channel.print("q/quit:  Give up on grading")

            elif what_to_do == "g" or what_to_do == "goto":
                # Go to a user-entered submission
                self.channel.print("Enter index of submission to jump to.")
                self.channel.print("n   Jump to submission n")
                self.channel.print("+n  Jump forward n submissions")
                self.channel.print("-n  Jump back n submissions")
                new_id = self.channel.input("Go:")

                if new_id:
                    try:
                        if new_id[0] == "+":
                            submission_id += int(new_id[1:])
                        elif new_id[0] == "-":
                            submission_id -= int(new_id[1:])
                        else:
                            submission_id = int(new_id)
                    except (ValueError, IndexError):
                        self.channel.error("Invalid index!")
                    if submission_id < 1 or submission_id > len(self._submissions):
                        self.channel.error("Invalid index: {}", submission_id)
                    submission_id = min(max(submission_id, 1), len(self._submissions))

            elif what_to_do == "b" or what_to_do == "back":
                # Go back to the last-completed submission
                submission_id = max(submission_id - 1, 1)

            elif what_to_do == "s" or what_to_do == "skip":
                # Skip to the next submission
                submission_id = min(submission_id + 1, len(self._submissions))

            elif what_to_do == "l" or what_to_do == "list":
                # List all the submissions
                id_len = len(str(len(self._submissions)))
                for submission in self._submissions:
                    self.channel.print("{:{}}: {}", submission.id, id_len, submission.name)

            elif what_to_do == "a" or what_to_do == "add":
                # Add another folder of submissions
                self.add_submissions(None)

            elif what_to_do == "q" or what_to_do == "quit":
                # Give up on the rest
                if self.channel.prompt("Are you sure you want to quit grading?", ["y", "n"]) == "y":
                    break

            else:
                # Run the next submission

                # Set up logs for the submission
                html_log = HTMLMemoryLog()
                text_log = MemoryLog()
                self.channel.add_delegate(html_log, text_log)
                self.event_manager.dispatch_event(events.SubmissionStartedEvent(
                    submission_id, html_log, text_log))

                runner = CommandRunner(self.injector, self.channel, self.host, self.settings,
                                       submission)
                runner.run()

                # Stop the logs
                html_log.close()
                text_log.close()

                background_commands += runner.get_background_commands()

                if submission_id != len(self._submissions):
                    # By default, we want to move on to the next submission in the list
                    submission_id += 1
                else:
                    # Special case: we're at the end
                    self.channel.print()
                    self.channel.status_bordered("End of submissions!")
                    loop = self.channel.prompt(
                        "Loop back around to the front?", ["y", "n"],
                        empty_choice_msg="C'mon, you're almost done; you can make a simple choice "
                                         "between `yes' and `no'")
                    if loop == "y":
                        submission_id = 1
                    else:
                        # Well, they said they're done
                        break

        # All done with everything
        self.event_manager.dispatch_event(events.EndOfSubmissionsEvent())

        for background_command in background_commands:
            background_command = background_command
            self.channel.print()
            self.channel.status("Waiting for background command {} ...",
                                background_command.get_description())
            background_command.wait()
            if background_command.get_error():
                self.channel.error("Background command ERROR: {}", background_command.get_error())
            else:
                self.channel.print("Background command output:")
                self.channel.print(background_command.get_output())
                self.channel.print("__________________________")


class CommandRunner:
    """
    Class that actually handles running commands on a submission.
    """

    def __init__(self, injector: Injector, channel: Channel, host: Host, settings: Settings,
                 submission: Submission) -> None:
        """
        Initialize a new CommandRunner to use for running commands on a submission.
        """
        self.injector = injector
        self.channel = channel
        self.host = host
        self.settings = settings
        self._submission = submission

        self._background_commands = []  # type: List[BackgroundCommand]

    def _check_folder(self, path: Path) -> Optional[Path]:
        """
        Check whether the user is satisfied with a folder, and, if not, allow them to choose a
        different one.

        :param path: The path to the folder to check.
        :return: Either the original folder (if they're satisfied), a different folder of their
            choice, or None if they're feeling particularly unagreeable today.
        """
        self.channel.print()
        self.host.print_folder(path, self._submission.path)
        choice = self.channel.prompt("Does this folder satisfy your innate human needs?",
                                     ["Y", "n"], "y")
        if choice == "y":
            return path
        else:
            return self.host.choose_folder(path)

    def _find_folder_from_regex(self, base_path: Path, folder_regex: str) -> Optional[Path]:
        """
        Find a folder, relative to an existing folder, based on a regular expression.

        :param base_path: The path to the current folder.
        :param folder_regex: The regex to match to a subfolder of base_folder.
        :return: The path to a valid subfolder, or None if none was found.
        """
        regex = re.compile(folder_regex)
        matches = []
        for name, type, is_link in self.host.list_folder(base_path):
            if type == "folder":
                match = regex.fullmatch(name)
                if match is not None:
                    matches.append(name)

        folder = None
        if len(matches) == 1:
            folder = matches[0]
        elif len(matches) > 1:
            self.channel.status("Multiple folders found when looking for {} in {}:", folder_regex,
                                base_path.relative_str(self._submission.path))
            for name in matches:
                self.channel.print("   ", name)
            choice = self.channel.input("Make a choice:", matches)
            if choice and choice in matches:
                folder = choice
        if folder is None:
            return None
        return base_path.append(folder)

    def _find_folder(self, base_path: Path, subfolder: Union[str, List[str]]) -> Optional[Path]:
        """
        Find a new path to a folder based on a current folder and either a subfolder or a list of
        regular expressions representing subfolders. Prompts the user for validation.

        :param base_path: The path to the base folder to start the search from.
        :param subfolder: The name of a subfolder (or relative path to a subfolder), or a list of
            regular expressions.
        :return: The path to a valid (sub)*folder, or None if none was found.
        """
        path = base_path
        if isinstance(subfolder, list):
            for folder_regex in subfolder:
                new_path = self._find_folder_from_regex(path, folder_regex)
                if new_path is None:
                    break
                path = new_path
        else:
            path = path.append(subfolder)

        if not self.host.folder_exists(path):
            self.channel.error("Folder not found: {}", path.relative_str(base_path))
            path = base_path
        return self._check_folder(path)

    def _get_modified_command(self, command: CommandItem) -> CommandItem:
        """
        Prompt the user for a modified version of a command.

        :param command: The command to modify.
        :return: A copy of "command" with "name" and "command" changed.
        """
        self.channel.print("Existing command: {}", command.command)
        new_command = self.channel.input("Enter new command (TAB to input old): ",
                                         [command.command])
        if not new_command:
            self.channel.print("No change :(")
            return command
        return command.get_modified(new_command)

    def run(self) -> None:
        """
        Run the commands on the submission.
        """
        _logger.info("Running commands for: {}", self._submission)
        try:
            base_path = self._check_folder(self._submission.path)
            if base_path is None:
                _logger.info("Skipping submission because user didn't pick a folder")
                self.channel.error("Skipping submission")
                return

            self._do_command_set(self.settings.commands, base_path, self.settings.base_env or {})
        except (InterruptedError, KeyboardInterrupt):
            self.channel.print("")
            self.channel.error("Submission interrupted")
            self.channel.print("")

    def get_background_commands(self) -> List[BackgroundCommand]:
        """
        Get any background commands that were started. (They're not necessarily still running.)
        """
        return self._background_commands

    def _do_command_set(self, commands: List[Command], path: Path,
                        environment: Dict[str, str]) -> bool:
        """
        Run a group of commands on the submission.

        :param commands: The commands to run.
        :param path: The initial working directory for the commands.
        :param environment: A base dictionary of environment variables for the commands.
        :return: True if we made it through successfully, or False if we should skip the rest of
            this submission.
        """
        if not self.host.folder_exists(path):
            _logger.warning("_do_command_set: Folder not found: {}", path)
            self.channel.print()
            self.channel.error("Folder not found: {}", path)
            self.channel.error("Skipping {} commands: {}",
                               len(commands),
                               [command.name for command in commands])
            return False
        _logger.debug("_do_command_set: in {}", path)

        for command in commands:
            if hasattr(command, "commands"):
                # It's a command set

                msg = Msg(sep="").print("\n").status("Command Set")
                if command.name:
                    msg.status(": {}", command.name)
                if command.folder:
                    msg.status(": ")
                    msg.print("{}", command.folder)
                self.channel.output(msg)

                if command.folder:
                    new_path = self._find_folder(path, command.folder)
                else:
                    new_path = self._check_folder(path)

                if new_path is None:
                    # The user didn't let us get a path; cancel this bit
                    self.channel.print()
                    self.channel.error("Skipping {} commands: {}",
                                       len(command.commands),
                                       [command.name for command in command.commands])
                    self.channel.input("Press Enter to continue...")
                    continue

                new_environment = environment.copy()
                new_environment.update(command.environment)

                # Run the command set
                # If it returns False, then we want to skip the rest of this submission
                if not self._do_command_set(command.commands, new_path, new_environment):
                    return False

                self.channel.print()
                self.channel.status("End Command Set", end="")
                if command.name:
                    self.channel.status(": {}", command.name, end="")
                self.channel.print()
            else:
                # It's a command item

                # Run the command
                # If it returns False, then we want to skip the rest of this submission
                if not self._do_command(command, path, environment):
                    return False

        # Everything went well!
        return True

    def _do_command(self, command: CommandItem, path: Path, environment: Dict[str, str]) -> bool:
        """
        Run an individual command on the submission.

        :param command: The command to run.
        :param path: The working directory for the command.
        :param environment: A base dictionary of environment variables for the command.
        :return: True to move on to the next command, False to skip the rest of this submission.
        """
        _logger.debug("_do_command: {}", command)

        msg = Msg(sep="\n").print()
        status_title = ("-" * 3) + " " + self._submission.name
        if len(status_title) < 56:
            status_title += " "
            status_title += "-" * (56 - len(status_title))
        msg.status(status_title)

        msg.status("::: {}", command.name)
        if command.is_background:
            msg.status("    (background command)")
        for line in command.command.split("\n"):
            if line:
                msg.bright("    {}", line)
        self.channel.output(msg.print())

        # Set up the command environment dictionary
        # (This is used for running the command, and if we open a shell)
        env = environment.copy()
        env.update(command.environment)
        env.update({
            "SUBMISSION_NAME": self._submission.name
        })

        # Before starting, ask the user what they want to do
        while True:
            choice = self.channel.prompt("What now?", ["o", "f", "m", "s", "ss", "?", ""])
            if choice == "o":
                # Open a shell in the current folder
                self.host.open_shell(path, env)
            elif choice == "f":
                # Open the current folder
                self.host.open_folder(path)
            elif choice == "m":
                # Modify the command
                command = self._get_modified_command(command)
            elif choice == "s":
                # Skip this command
                return True
            elif choice == "ss":
                # Skip the rest of this submission
                return False
            elif choice == "?":
                # Show help
                msg = Msg(sep="\n")
                msg.print("  o:  Open a shell in the current folder")
                msg.print("  f:  Open the current folder")
                msg.print("  m:  Modify the command (just for this submission)")
                msg.print("  s:  Skip this command")
                msg.print("  ss: Skip the rest of this submission")
                msg.print("  ?:  Show this help message")
                msg.print("  Enter: Run the command")
                self.channel.output(msg)
            else:
                # Run the command
                self.channel.print("")
                break

        # Alrighty, it's command-running time!
        if command.is_background:
            self._run_background_command(command, path, env)
        else:
            self._run_foreground_command(command, path, env)

        # All done with the command!
        # Ask user what they want to do
        while True:
            self.channel.print("")
            choice = self.channel.prompt("Repeat command?", ["y", "N"], "n")
            self.channel.print("")
            if choice == "y":
                # Repeat the command
                return self._do_command(command, path, environment)
            else:
                # Move on to the next command
                return True

    def _run_background_command(self, command: CommandItem, path: Path,
                                environment: Dict[str, str]) -> None:
        """
        Actually run an individual background command.

        :param command: The command to run.
        :param path: The working directory for the command.
        :param environment: A dictionary of environment variables for the command.
        """
        try:
            self._background_commands.append(self.host.start_background_command(
                command.command, path, environment, command.stdin))
        except CommandStartError as e:
            self.channel.print()
            self.channel.error("Error starting background command: {}", e.message)
        else:
            self.channel.print()
            self.channel.status("Background command started.")

    def _run_foreground_command(self, command: CommandItem, path: Path,
                                environment: Dict[str, str]) -> None:
        """
        Actually run an individual foreground command.

        :param command: The command to run.
        :param path: The working directory for the command.
        :param environment: A dictionary of environment variables for the command.
        """
        # Filled with the text content to compare the command's output to (if any)
        diff_reference = None
        diff_reference_source = None

        if command.diff:
            if command.diff.content:
                diff_reference = command.diff.content
                diff_reference_source = "content from command config"
            elif command.diff.file and self.settings.diff_file_path:
                local_diff_path = os.path.join(self.settings.diff_file_path.get_local_path(),
                                               command.diff.file)
                try:
                    with open(local_diff_path) as f:
                        diff_reference = f.read()
                    diff_reference_source = "local file ({})".format(command.diff.file)
                except FileNotFoundError:
                    self.channel.error("Diff file not found: {} ({})", command.diff.file,
                                       self.settings.diff_file_path)
            elif command.diff.submission_file:
                diff_path = path.append(command.diff.submission_file)
                try:
                    diff_reference = self.host.read_text_file(diff_path)
                    diff_reference_source = "submission file ({})".format(
                        command.diff.submission_file)
                except FileNotFoundError:
                    self.channel.error("Diff file not found: {} ({})",
                                       command.diff.submission_file, path)
            elif command.diff.command:
                try:
                    diff_reference = self.host.run_command(command.diff.command, path, environment,
                                                           print_output=False)
                    diff_reference_source = "command ({})".format(command.diff.command)
                except CommandStartError as e:
                    self.channel.error("Error starting diff command: {}", e.message)
                except CommandRunError as e:
                    self.channel.error("Error running diff command: {}", e.message)
            else:
                self.channel.error("Diff object doesn't include "
                                   "\"content\", \"file\", \"submission_file\", or \"command\"")

        output = None
        try:
            if command.is_passthrough:
                self.host.run_command_passthrough(command.command, path, environment)
            else:
                output = self.host.run_command(command.command, path, environment, command.stdin)
        except CommandStartError as e:
            self.channel.print()
            self.channel.error("Error starting command: {}", e.message)
            return
        except CommandRunError as e:
            self.channel.print()
            self.channel.error("Error running command: {}", e.message)
            return

        if diff_reference is not None:
            self.channel.print()
            self.channel.status("DIFF with reference from {}", diff_reference_source)
            self.channel.print()
            self._print_diff(output, diff_reference, command.diff)

    @staticmethod
    def _clean_lines(lines: List[str], collapse_whitespace: bool = False) \
            -> Tuple[List[str], Dict[str, List[str]]]:
        """
        Clean up some lines of output to make diffing work better. In particular, make an
        entirely-lowercase version and optionally collapse whitespace.

        :return: A tuple with (list of str, dict) representing the list of cleaned-up lines
            (each ending with a newline) and a dictionary mapping each cleaned-up line to a list
            of the original line(s) that it came from (none ending with a newline).
        """
        clean_to_orig = defaultdict(lambda: [])  # type: Dict[str, List[str]]
        clean_lines = []  # type: List[str]
        for line in lines:
            if collapse_whitespace:
                line = re.sub(r'\s+', " ", line.strip())
            else:
                line = line.rstrip()

            clean_line = line.lower() + "\n"
            clean_lines.append(clean_line)
            clean_to_orig[clean_line].append(line)
        return clean_lines, clean_to_orig

    def _print_diff(self, output: str, reference: str, options: CommandItem.Diff) -> None:
        """
        Print the results of performing a diff between "output" and "reference".
        """
        # Nothing ain't anything without a reference
        self.channel.bg_happy("- Reference")
        self.channel.bg_sad  ("+ Output")
        self.channel.bg_meh  ("  Both")
        self.channel.print   ("-----------")
        self.channel.print   ("")

        # Split everything by lines
        output_lines = output.splitlines()
        reference_lines = reference.splitlines()

        # Try some metric-level hackery to ignore case and clean up a bit
        reference_clean, reference_orig = CommandRunner._clean_lines(
            reference_lines, options.collapse_whitespace)
        output_clean, output_orig = CommandRunner._clean_lines(
            output_lines, options.collapse_whitespace)

        # Print that diff!
        for line in difflib.ndiff(reference_clean, output_clean):
            signal = line[0]
            content = line[2:]
            self.channel.bright("{}", line[0:2], end="")
            if signal == "-":
                # Line from reference only
                self.channel.bg_happy("{}", reference_orig[content].pop(0))
            elif signal == "+":
                # Line from output only
                self.channel.bg_sad("{}", output_orig[content].pop(0))
            elif signal == "?":
                # Extra line (to mark locations, etc.)
                self.channel.bright("{}", content.rstrip("\n"))
            else:
                # Line from both reference and output
                # Pop the reference side
                reference_orig[content].pop(0)
                # Pop and print the output side
                self.channel.bg_meh("{}", output_orig[content].pop(0))
