import difflib
import io
import os
import platform
import re
import subprocess
import zipfile


from .gradebook import events


class Grader:
    """
    Class to grade (run commands on) submissions.
    """

    def __init__(self, on_event=None, **FancyIO_args):
        """
        Initialize a Grader.
        Any extra arguments will be passed to the FancyIO constructor.

        :param on_event: A function to call with a GradeBookEvent when an event
            occurs that
        """
        self._submissions = []

        # Set up our I/O
        self._io = FancyIO(**FancyIO_args)
        
        # Set up on_event
        if callable(on_event):
            self._event = on_event
        else:
            self._event = lambda event: None

    def add_submissions(self, submissions_directory, folder_regex,
                        check_zipfiles=False, check_files=None):
        """
        Add a directory of submissions to our list of submissions.
        
        The regular expression is used to limit which folders are picked up.
        Also, the first matched group in the regex is used as the name of the
        submission.

        For more info on some of the parameters, see the YAML format
        documentation on the GradeFast wiki:
        https://github.com/jhartz/gradefast/wiki/YAML-Format
        
        :param submissions_directory: Path to the directory containing
            submissions
        :param folder_regex: Regular expression to use to match subfolders
        :param check_zipfiles: Whether to check zipfiles in the directory to
            see if any match folder_regex
        :param check_files: Whether to check files in the directory to see if
            any with specific extensions match folder_regex. This is a LIST of
            file extensions to check. Both [] and None skip this check.
        """
        
        # Step 1: Make sure "submissions_directory" exists and is a directory
        if not os.path.isdir(submissions_directory):
            raise FileNotFoundError("Cannot find given directory: '" +
                                    submissions_directory + "'")
        
        regex = re.compile(folder_regex)
        
        # Step 2: Check zipfiles or other files (if necessary)
        if check_zipfiles or (check_files and len(check_files)):
            for item in os.listdir(submissions_directory):
                # Split the file name and extension
                name, ext = os.path.splitext(item)
                # Make sure it's not a directory and it matches our regex
                if os.path.isfile(os.path.join(submissions_directory, item)) \
                        and regex.fullmatch(name) is not None:
                    # "from path" is the file, "to path" is the new directory
                    from_path = os.path.join(submissions_directory, item)
                    to_path = os.path.join(submissions_directory, name)
                    # Make sure the directory doesn't already exist
                    if not os.path.exists(to_path):
                        # Is it a zipfile?
                        if check_zipfiles and ext == ".zip":
                            # Make the directory
                            os.mkdir(to_path)
                            # Extract the zipfile
                            zfile = zipfile.ZipFile(from_path, "r")
                            zfile.extractall(to_path)
                            self._io.print("Unzipped: %s" % item)
                        elif check_files and ext[1:] in check_files:
                            # Make a folder and move it there
                            os.mkdir(to_path)
                            os.rename(from_path, os.path.join(to_path, item))
                            self._io.print("Moved to folder: %s" % item)
        
        # Step 3: Get a list of folders that match folder_regex
        for item in os.listdir(submissions_directory):
            # Make sure this is a directory
            if not os.path.isdir(os.path.join(submissions_directory, item)):
                continue
            
            # Make sure the directory matches our regex
            match = regex.fullmatch(item)
            if match is None:
                continue
            
            # Make some details for this submission in this directory
            submission_name = item
            for group in match.groups():
                if group:
                    submission_name = group
                    break
            submission = Submission(submission_name, item,
                                    os.path.join(submissions_directory, item),
                                    submissions_directory)
            
            # Add this submission to our list
            self._io.print("Found submission: " + str(submission))
            self._submissions.append(submission)

        # Sort the submissions by name
        self._submissions.sort(key=lambda s: s.name)

    def run_commands(self, commands, support_directory=None,
                     shell_command=None, open_shell=None):
        """
        Run some commands for each of our submissions. For details on what
        should be in the list of commands, see the GradeFast wiki:
        https://github.com/jhartz/gradefast/wiki/Command-Structure
        
        Each command has certain environmental variables available to it.
        By default (i.e. for top-level commands), the working directory is the
        folder at the root of the submission it's running in.
        
        Before and after each command is run, the user will be prompted as to
        what they want to do.
        
        :param commands: The command list to run (see GradeFast wiki page).
        :param support_directory: If specified, available to the client as an
            environmental variable and used as the default location for diff
            files.
        :param shell_command: A list representing a shell used to execute the
            commands. If not provided, the OS default is used. If provided,
            should contain at least one list item whose value is None; this
            will be replaced with the command.
        :param open_shell: A function to open a shell in a certain directory.
            This function is passed 2 arguments: the working directory, and a
            dictionary of environmental variables. If "None", then a platform
            default is used.
        """
        # Make sure support_directory is absolute, if provided
        if support_directory is not None:
            support_directory = os.path.abspath(support_directory)

        # Set up open_shell, if needed
        if open_shell is None:
            if platform.system() == "Windows":
                open_shell = _default_shell_windows
            else:
                open_shell = _default_shell_unix

        # Create the CommandRunner to run this command set
        runner = CommandRunner(self._io, commands, support_directory,
                               shell_command, open_shell)

        # Run the commands on each submission
        total = len(self._submissions)
        index = 1  ### NOTE: 1-based indexing!!
        while index <= total:
            # Reset the I/O log so it's good and fresh
            self._io.reset_log()

            next_submission = self._submissions[index - 1]
            msg = "Next Submission: %s (%s/%s)" % (next_submission.name,
                                                   index, total)
            self._io.status("-" * len(msg))
            self._io.status(msg)
            self._io.status("-" * len(msg))
            
            what_to_do = self._io.prompt(
                "Press Enter to begin, 'g'oto, 'b'ack, 's'kip, 'l'ist, 'quit', "
                "'?' for help",
                ["", "g", "b", "s", "l", "quit", "?"], show_choices=False)
            if what_to_do == "?":
                # Print more help
                self._io.print("(Enter):  Start the next submission")
                self._io.print("g:  Go to a specific submission")
                self._io.print("b:  Go to the previous submission (goto -1)")
                self._io.print("s:  Skip the next submission (goto +1)")
                self._io.print("l:  List all the submissions and corresponding "
                               "indices")
                self._io.print("quit:  Give up on grading")
            elif what_to_do == "quit":
                # Give up on the rest
                break
            elif what_to_do == "b":
                # Go back to the last-completed submission
                index = max(index - 1, 1)
            elif what_to_do == "s":
                # Skip to the next submission
                index = min(index + 1, total)
            elif what_to_do == "g":
                # Go to a user-entered submission
                self._io.print("Enter index of submission to jump to.")
                self._io.print("n   Jump to submission n")
                self._io.print("+n  Jump forward n submissions")
                self._io.print("-n  Jump back n submissions")
                new_index = self._io.input("Go:").strip()

                try:
                    if new_index[0] == "+":
                        index += int(new_index[1:])
                    elif new_index[0] == "-":
                        index -= int(new_index[1:])
                    else:
                        index = int(new_index)
                except (ValueError, IndexError):
                    self._io.error("Invalid index!")

                index = min(max(index, 1), total)
            elif what_to_do == "l":
                # List all the submissions (and indices)
                for i, submission in enumerate(self._submissions, start=1):
                    self._io.print("%d: %s" % (i, submission))
            else:
                # Run next_submission
                self._event(events.SubmissionStarted(index, next_submission.name))
                runner.run_on_submission(
                    next_submission,
                    next_submission.path,
                    {
                        "SUPPORT_DIRECTORY": support_directory,
                        "HELPER_DIRECTORY": support_directory
                    }
                )
                # All done! Send the HTML log back up the chain
                self._event(events.SubmissionFinished(self._io.get_log_as_html()))
                # And reset the log, just for good measure (i.e. memory)
                self._io.reset_log()
                # Move on to the next submission
                index += 1

        # No more submissions!
        self._io.print("")
        self._io.status("End of submissions")
        self._io.print("")

        # Wait for any background processes, if necessary
        runner.wait_for_background_processes()

        # All done with everything!
        self._event(events.EndOfSubmissions())


class CommandRunner:
    """
    Class that actually handles running commands on a bunch of submissions.
    """
    _command_modified_re = re.compile(r'^(.*)( \(modified ([0-9]+)\))$')

    def __init__(self, io, commands, diff_directory, shell_command, open_shell):
        """
        Initialize a CommandRunner with a bunch of commands.

        :param io: A FancyIO instance used for input/output
        :param commands: The command list to run
        :param diff_directory: The location for relative diff files
        :param shell_command: The command to run commands (see
            Grader::run_commands)
        :param open_shell: A function to open a shell in a certain directory.
            This function is passed 2 arguments: the working directory, and a
            dictionary of environmental variables.
        """
        self._io = io
        self.commands = commands
        self.diff_directory = diff_directory
        self.shell_command = shell_command
        self.open_shell = open_shell
        self.background_processes = []

    def get_modified_command(self, cmd):
        """
        Prompt the user for a modified version of a command.

        :param cmd: The command to modify
        :return: A copy of cmd with "name" and "command" changed
        """
        self._io.print("Existing command: " + cmd["command"])
        completer = InputCompleter([cmd["command"]])
        cmd = cmd.copy()

        result = CommandRunner._command_modified_re.match(cmd["name"])
        if result is None:
            name = cmd["name"]
            modified_num = 1
        else:
            name = result.group(1)
            modified_num = int(result.group(3)) + 1

        cmd.update({
            "name": "%s (modified %s)" % (name, modified_num),
            "command": self._io.input("Enter new command (TAB to input old): ",
                                      completer.complete)
        })
        return cmd

    def find_path(self, working_dir, folder, base=""):
        """
        Find a new path based on a current path and either a subfolder or a list
        of regular expressions representing subfolders. Prompts the user for
        input if a folder is invalid.

        :param working_dir: The current path
        :param folder: A single subfolder, or list of regular expressions
        :param base: The base directory (that we shouldn't include when printing
            directory paths)
        :return: None if there is no new path, or a tuple: (new full path,
                                                            new relative path)
        """
        # Make sure the current path exists
        if not os.path.isdir(working_dir):
            return None

        def without_base(path, our_base=base):
            """Get a pretty version of a path"""
            if path[0:len(our_base)] == our_base:
                path = path[len(our_base):]
                if path.startswith(os.sep):
                    path = path[len(os.sep):]
            if path[-1] == ".":
                path = path[:-1]
            if path.endswith(os.sep):
                path = path[:-len(os.sep)]
            return path

        new_path = working_dir
        if isinstance(folder, list):
            # Form up the sub-paths
            for folder_regex in folder:
                new_dir = _find_folder_from_regex(new_path, folder_regex)
                if new_dir is None:
                    # We ain't got shit
                    new_path = None
                    break
                new_path = new_dir
        elif isinstance(folder, str):
            # Just a simple path concat
            new_path = os.path.join(working_dir, folder)

        # Get list of folders in working_dir (for autocomplete)
        folders = []
        for root, dirs, files in os.walk(working_dir):
            for directory in sorted(dirs):
                folders.append(
                    without_base(os.path.join(root, directory), working_dir))

        # Check the folder, and make sure it's what the user wants
        user_happy = False
        while not user_happy:
            if new_path is None or not os.path.isdir(new_path):
                # It doesn't exist!
                user_happy = False
                if new_path is None:
                    self._io.error("Folder not found:", end=" ")
                    self._io.print(without_base(working_dir), end=" ")
                    self._io.status("::", end=" ")
                    self._io.print(folder)
                else:
                    self._io.error("Folder not found:", end=" ")
                    self._io.print(without_base(new_path))
            else:
                # List the files inside
                self._io.status("Files inside %s:" % without_base(new_path),
                                end=" ")
                for (index, item) in enumerate(os.listdir(new_path)):
                    if index != 0:
                        self._io.status(",", end=" ")
                    self._io.print(item, end="")
                self._io.print("\n")

                user_happy = self._io.prompt(
                    "Does this directory satisfy your innate human needs?",
                    ["Y", "n"], "y") == "y"

            if not user_happy:
                completer = InputCompleter(folders, sort=False)
                new_path_input = self._io.input(
                    "Enter folder path (relative to %s), or Enter to cancel:" %
                    without_base(working_dir),
                    completer.complete)
                if new_path_input:
                    new_path = os.path.join(working_dir, new_path_input)
                else:
                    # They've given up
                    new_path = None
                    # And they'd better be damn happy with that choice
                    user_happy = True

        if new_path is None:
            return None
        else:
            return new_path, without_base(new_path)

    def wait_for_background_processes(self):
        """
        If there are any background processes still running, wait for them to
        exit, then return.
        """
        for p, info in self.background_processes:
            if p.poll() is None:
                # He's alive! Print his info
                self._io.status("Waiting for background process: ", end="")
                if info is not None:
                    for index, nfo in enumerate(info):
                        if index: self._io.status(" / ", end="")
                        self._io.print(nfo, end="")
                    self._io.print("")
                else:
                    self._io.print(p.args)

                # Now, wait for him...
                try:
                    p.wait()
                except (InterruptedError, KeyboardInterrupt):
                    self._io.error("Process interrupted")

    def run_on_submission(self, submission, path, environment):
        """
        Run some commands from a command set for a specific submission.

        :param submission: The current submission that we're operating on
        :param path: The working directory for the commands to run
        :param environment: A dictionary of environmental variables for these
            commands
        :return: False if part of this submission was skipped
        """
        try:
            return self._do_command_set(self.commands, submission, path,
                                        environment)
        except (InterruptedError, KeyboardInterrupt):
            self._io.print("")
            self._io.error("Submission interrupted")
            self._io.print("")

    def _do_command_set(self, commands, submission, path, environment):
        """
        Run some commands from a command set for a specific submission.

        :param commands: The command set to run
        :param submission: The current submission that we're operating on
        :param path: The working directory for the commands to run
        :param environment: A dictionary of environmental variables for these
            commands
        :return: False to skip the rest of the commands for this submission
        """
        for cmd in commands:
            if "commands" not in cmd:
                # It's an actual command
                if "name" in cmd and "command" in cmd:
                    # If False, then we want to skip the rest of this submission
                    if not self._do_command(cmd, submission, path,
                                            environment):
                        return False
                    # Otherwise, just continue on to the next command
                    continue
                else:
                    self._io.error("Invalid command found")
                    continue
            
            # If we're still here, we have a group of commands
            # Figure out our new directory for these commands
            new_path = path
            new_path_pretty = None
            if "folder" in cmd:
                retval = self.find_path(path, cmd["folder"], submission.base)
                # Handle a bad folder
                if retval is None:
                    self._io.error("Skipping commands: " + ", ".join(
                        [subcmd["name"] for subcmd in cmd["commands"]
                         if "name" in subcmd]))
                    # Skip running these commands
                    self._io.input("Press Enter to continue...")
                    continue
                # Expand the retval tuple
                new_path, new_path_pretty = retval

            self._io.print("")
            if new_path_pretty is not None:
                self._io.status("Running commands for folder: " +
                                new_path_pretty)
            self._io.print("")

            # Make new environment dictionary
            new_environment = environment.copy()
            if "environment" in cmd:
                new_environment.update(cmd["environment"])

            # Run the command set
            # If False, then we want to skip the rest of this submission
            if not self._do_command_set(cmd["commands"], submission, new_path,
                                        new_environment):
                return False

            if new_path_pretty is not None:
                self._io.status("End commands for folder: " + new_path_pretty)
            self._io.print("")

        # All done!
        return True
    
    def _do_command(self, cmd, submission, path, environment):
        """
        Run an individual command.
        
        :param cmd: The command to run
        :param submission: The submission that we're running these commands on
        :param path: The working directory for the command
        :param environment: A dictionary of environmental variables for these
            commands
        :return: True to move on to the next command,
                 False to move on to the next submission
        """
        status_title = ("-" * 4) + submission.name
        if len(status_title) < 50:
            status_title += "-" * (50 - len(status_title))
        self._io.status(status_title)

        self._io.status("::: " + cmd["name"])
        self._io.print_bright("    " + cmd["command"])
        self._io.print("")

        # Set up the command environment dictionary
        # (This is used for running the command, and if we open a shell)
        # Start off with this process's environment
        env = dict(os.environ)
        # Add some specific environmental variables
        env.update({
            "SUBMISSION_DIRECTORY": submission.path,
            "CURRENT_DIRECTORY": path,
            "SUBMISSION_NAME": submission.name
        })
        # Add any environmental variables from parents of this command
        env.update(environment)
        # Add this command's specific environmental variables
        if "environment" in cmd:
            env.update(cmd["environment"])

        # Before starting, ask the user what they want to do
        while True:
            choice = self._io.prompt("What now?",
                                     ["o", "f", "m", "s", "ss", "?", ""])
            if choice == "o":
                # Open a shell in the current folder
                self.open_shell(path, env)
            elif choice == "f":
                # Open the current folder
                open_file(path)
            elif choice == "m":
                # Modify the command
                cmd = self.get_modified_command(cmd)
            elif choice == "s":
                # Skip this command
                return True
            elif choice == "ss":
                # Skip the rest of this submission
                return False
            elif choice == "?":
                # Show help
                self._io.print("  o:  Open a shell in the current folder")
                self._io.print("  f:  Open the current folder")
                self._io.print("  m:  Modify the command (just for this "
                               "submission)")
                self._io.print("  s:  Skip this command")
                self._io.print("  ss: Skip the rest of this submission")
                self._io.print("  ?:  Show this help message")
                self._io.print("  Enter: Run the command")
            else:
                # Run the command
                self._io.print("")
                break

        # Alrighty, it's command-running time!
        self._run_command(cmd, path, env, (str(submission), cmd["name"]))

        # All done with the command!
        # Ask user what they want to do
        while True:
            self._io.print("")
            choice = self._io.prompt("Repeat command?", ["y", "N"], "n")
            self._io.print("")
            if choice == "y":
                # Repeat the command
                return self._do_command(cmd, submission, path, environment)
            else:
                # Move on to the next command
                return True

    @staticmethod
    def _clean_lines(lines, collapse_whitespace=False):
        """
        Clean up some lines of output to make diffing work better.
        In particular, make an entirely-lowercase version and optionally
        collapsing whitespace.

        :param lines: The lines to clean up (list of str)
        :return: A tuple with (list of str, dict) representing the list of
            cleaned-up lines (each ending with a newline) and a dictionary
            mapping each cleaned-up line to a list of the original line(s) that
            it came from (none ending with a newline).
        """
        clean_to_orig = {}
        clean_lines = []
        for line in lines:
            if collapse_whitespace:
                line = re.sub(r'\s+', " ", line.strip())
            else:
                line = line.rstrip()

            clean_line = line.lower() + "\n"
            clean_lines.append(clean_line)

            if clean_line not in clean_to_orig:
                clean_to_orig[clean_line] = []
            clean_to_orig[clean_line].append(line)
        return clean_lines, clean_to_orig

    def _run_command(self, cmd, path, environment, info=None):
        """
        Run an individual command, handling the output if necessary.

        :param cmd: The command to run
        :param path: The working directory for the command
        :param environment: A dictionary of environmental variables for the
            command
        :param info: Any extra metadata info about the command (stored with
            the process if it runs in the background)
        """
        # Filled with the text content to compare to, if any
        diff_reference = None

        # Default diff options
        diff_options = {
            "collapse whitespace": False
        }

        if "diff" in cmd:
            # The location of a reference diff file, if we have one
            diff_file = None
            # The location of a reference diff command, if we have one
            diff_command = None

            # Check if we have the diff represented as a string or a dict
            if isinstance(cmd["diff"], str):
                # It's a string (so, just a file path)
                diff_file = cmd["diff"]
            else:
                # It's a dict
                if "command" in cmd["diff"] and cmd["diff"]["command"]:
                    diff_command = cmd["diff"]["command"]
                elif "file" in cmd["diff"] and cmd["diff"]["file"]:
                    diff_file = cmd["diff"]["file"]
                else:
                    self._io.error("Diff options do not include either \""
                                   "command\" or \"file\".")
                # Initialize any other options
                for key in diff_options.keys():
                    if key in cmd["diff"]:
                        diff_options[key] = cmd["diff"][key]

            # If we have a reference file, load that
            if diff_file is not None:
                diff_file = os.path.join(self.diff_directory, diff_file)
                if os.path.exists(diff_file):
                    with open(diff_file, "r") as ref:
                        diff_reference = [line for line in ref]
                else:
                    self._io.error("Diff file not found: %s" % diff_file)

            # If we have a reference command, load that
            if diff_command is not None:
                self._io.print("Running command to get diff reference: %s" %
                               diff_command)
                diff_reference = self._exec_command(diff_command, path,
                                                    environment,
                                                    capture_output=True)

        # RUN THE COMMAND ALREADY
        output = self._exec_command(
            cmd["command"], path, environment,
            input=None if "input" not in cmd else cmd["input"],
            capture_output=diff_reference is not None,
            wait=not ("background" in cmd and cmd["background"]),
            info=info)

        # Only continue if we need to diff the output
        if diff_reference is not None and output is not None:
            # Nothing ain't anything without a reference
            self._io.print_bright("- ", end="")
            self._io.print_happy("Reference")
            self._io.print_bright("+ ", end="")
            self._io.print_sad("Output")
            self._io.print_bright("  ", end="")
            self._io.print_highlighted("Both")
            self._io.print("-----------")
            self._io.print("")

            # Split the output by lines
            output = output.splitlines()

            # Try some hackery to ignore case and clean up a bit
            reference_clean, reference_orig = CommandRunner._clean_lines(
                diff_reference, diff_options["collapse whitespace"])
            output_clean, output_orig = CommandRunner._clean_lines(
                output, diff_options["collapse whitespace"])

            # Print that diff!
            for line in difflib.ndiff(reference_clean, output_clean):
                signal = line[0]
                content = line[2:]
                self._io.print_bright(line[0:2], end="")
                if signal == "-":
                    # Line from reference only
                    self._io.print_happy(reference_orig[content].pop(0))
                elif signal == "+":
                    # Line from output only
                    self._io.print_sad(output_orig[content].pop(0))
                elif signal == "?":
                    # Extra line (to mark locations, etc.)
                    self._io.print_bright(content.rstrip("\n"))
                else:
                    # Line from both reference and output
                    # Pop the reference side
                    reference_orig[content].pop(0)
                    # Pop and print the output side
                    self._io.print_highlighted(output_orig[content].pop(0))

    def _exec_command(self, command, path, environment, input=None,
                      capture_output=False, wait=True, info=None):
        """
        Actually execute an individual command.

        :param command: The command to run
        :param path: The working directory for the command
        :param environment: A dictionary of environmental variables for the
            command
        :param input: Any input to use as stdin
        :param capture_output: Whether to capture and return the output
        :param wait: Whether to wait for the process to complete
            (will always wait if input is not None or capture_output is True)
        :param info: Any info about the command (stored with the process if
            wait is False, i.e. if we're going to run it in the background)
        :return: The output of the process if capture_output, otherwise None
        """
        # kwargs for subprocess.Popen
        kwargs = {
            "cwd": path,
            "env": environment,
            "universal_newlines": True
        }

        # args is the first argument for subprocess.Popen
        args = command
        if self.shell_command is None:
            # Use platform shell
            kwargs["shell"] = True
        else:
            # Reformat args to use the provided shell command
            args = [command if arg is None else arg
                    for arg in self.shell_command]

        # Check if we have input to throw at stdin
        if input is not None:
            kwargs["stdin"] = subprocess.PIPE
            # We must wait, regardless of what the user wants
            wait = True

        # Check if we should capture stdout and stderr
        if capture_output:
            kwargs["stdout"] = subprocess.PIPE
            kwargs["stderr"] = subprocess.STDOUT
            # We must wait, regardless of what the user wants
            wait = True

        process = None
        output = None
        try:
            process = subprocess.Popen(args, **kwargs)
            # If we're not waiting, return now
            if not wait:
                self.background_processes.append((process, info))
                self._io.status("Running in background...")
                return
            # The output will only be collected here if we have stdout set above
            # (i.e. if we're planning on capturing the output)
            output, _ = process.communicate(input=input)
        except (NotADirectoryError, FileNotFoundError) as ex:
            self._io.error("Directory or file not found: " + str(ex))
        except (InterruptedError, KeyboardInterrupt):
            self._io.error("Process interrupted")
            # TODO: Try to get what output there was from the process

        # Check the return code
        if not process:
            self._io.print("")
            self._io.error("Command did not complete successfully")
            self._io.print("")
        elif process.returncode:
            self._io.print("")
            self._io.error("Command had nonzero return code: %s" %
                           process.returncode)
            self._io.print("")

        return output if capture_output else None
