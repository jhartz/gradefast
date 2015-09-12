#!/usr/bin/env python3
"""
Grader class to handle the grading subsystem

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jhartz@mail.rit.edu>
"""
import os, re, subprocess, zipfile, difflib

from colorama import init, Fore, Back, Style


def _cmd_exists(cmd):
    """Determine whether a command exists on this system"""
    return subprocess.call(["which", cmd], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL) == 0


def _default_shell_unix(path):
    """Default function to open a terminal in a Unix-like environment"""    
    if _cmd_exists("gnome-terminal"):
        # We have gnome-terminal
        subprocess.Popen([
            "gnome-terminal",
            "--working-directory=" + path
        ])
    elif _cmd_exists("xfce4-terminal"):
        # We have xfce4-terminal
        subprocess.Popen([
            "xfce4-terminal",
            "--default-working-directory=" + path
        ])
    elif _cmd_exists("xterm"):
        # We have xterm (WARNING: DANGEROUS if the path is malformed)
        subprocess.Popen([
            "xterm",
            "-e",
            "cd \"" + path + "\" && /bin/bash"
        ])
    else:
        print("No shell found")


def _default_shell_windows(path):
    """Default function to open a command prompt on Windows"""
    if path.find("\"") != -1:
        # Just get rid of parts with double-quotes
        path = path[0:path.find("\"")]
        path = path[0:path.rfind("\\")]
    os.system("start cmd /K \"cd " + path + "\"")


def extract_zipfile(path):
    """
    Extract a zipfile into a new folder in the same directory with a matching
    name (same name as zipile, but without ".zip").
    
    :param path: The path to the zipfile
    :return: True if we unzipped it, False if the folder already exists.
    """
    base = os.path.dirname(path)
    zipfile_name = os.path.basename(path)
    
    # Find the folder
    folder_name = zipfile_name
    if folder_name[-4:] == ".zip":
        folder_name = folder_name[:-4]
    folder = os.path.join(base, folder_name)
    if os.path.exists(folder):
        # Already exists!
        return False
    
    # Make the folder
    os.mkdir(folder)
    
    # Extract the zipfile
    zfile = zipfile.ZipFile(path, "r")
    zfile.extractall(folder)
    return True


def _find_folder_from_regex(working_dir, folder_regex):
    """
    Helper method for find_path
    
    :param working_dir: The current path
    :param folder_regex: The regex to match to a subfolder of working_dir
    :return: The full path to a valid subfolder, or None if none was found
    """
    regex = re.compile(folder_regex)
    for item in os.listdir(working_dir):
        # Make sure this is a directory
        if not os.path.isdir(os.path.join(working_dir, item)):
            continue
        
        # See if it matches our regex
        match = regex.fullmatch(item)
        if match is None:
            continue
        
        # It's good! Append it to our working dir and return it
        return os.path.join(working_dir, item)
    
    # If we got here, then we didn't find shit
    return None


class Submission:
    """
    Class representing a submission by a certain user.
    """
    def __init__(self, name, path, base=""):
        """
        Initialize a new Submission.
        
        :param name: The name of the submission (i.e. the user)
        :param path: The path of the root of the submission
        :param base: The base path of where all the submissions are
        """
        self.name = name
        self.path = path
        self.base = base
        self.grades = {}
        self.modify_all_commands = False


class Grader:
    """
    Class to grade (run commands on) submissions.
    """

    def error(self, msg, *args, **kwargs):
        """Print a red error"""
        if self._use_color:
            msg = Style.BRIGHT + Fore.RED + msg + Fore.RESET + Style.NORMAL
        print(msg, *args, **kwargs)

    def status(self, msg, *args, **kwargs):
        """Print a green status message"""
        if self._use_color:
            msg = Style.BRIGHT + Fore.GREEN + msg + Fore.RESET + Style.NORMAL
        print(msg, *args, **kwargs)

    def print_happy(self, msg, *args, **kwargs):
        """Print a happy message with a green background"""
        if self._use_color:
            msg = Style.BRIGHT + Fore.WHITE + Back.GREEN + msg + \
                  Back.RESET + Fore.RESET + Style.NORMAL
        print(msg, *args, **kwargs)

    def print_sad(self, msg, *args, **kwargs):
        """Print a sad message with a red background"""
        if self._use_color:
            msg = Style.BRIGHT + Fore.WHITE + Back.RED + msg + \
                  Back.RESET + Fore.RESET + Style.NORMAL
        print(msg, *args, **kwargs)

    def print_bright(self, msg, *args, **kwargs):
        """Print a bright white message"""
        if self._use_color:
            msg = Style.BRIGHT + msg + Style.NORMAL
        print(msg, *args, **kwargs)

    def input_color(self, msg):
        """Ask the user for input in cyan"""
        msg = msg.rstrip()
        if self._use_color:
            msg = Style.BRIGHT + Fore.CYAN + msg + Fore.RESET + Style.NORMAL
        print(msg, end=" ")
        return input()

    def prompt_user(self, prompt, choices, show_choices=True):
        """
        Ask the user a question, returning their choice.

        :param prompt: The string to prompt the user with
        :param choices: The list of valid choices (possibly including "")
        :show_choices: Whether to add the list of choices
        :return: An element of choices chosen by the user (lowercase)
        """
        our_choices = []
        user_choices = "("
        has_enter_key = False

        for choice in choices:
            if choice == "":
                has_enter_key = True
            else:
                user_choices += choice + "/"
                our_choices.append(choice.lower())

        if has_enter_key:
            user_choices += "Enter"
        else:
            user_choices = user_choices[:-1]
        user_choices += ")"

        msg = prompt
        if show_choices:
            msg += " " + user_choices
        msg += ": "

        while True:
            choice = self.input_color(msg).strip().lower()
            if choice == "" and has_enter_key:
                return ""
            elif choice in our_choices:
                return choice
            else:
                self.error("Learn how to read, dumbass. `%s' ain't a choice!" %
                           choice)

    def get_modified_command(self, cmd):
        """
        Prompt the user for a modified version of a command.
        """
        print("Existing command: " + cmd["command"])
        return {
            "name": cmd["name"] + " (modified)",
            "command": self.input_color("Enter new command: ")
        }

    def __init__(self, use_color=True, open_shell=None,
                 on_submission_start=None, on_end_of_submissions=None):
        """
        Initialize a Grader.
        
        :param open_shell: A function to open a shell in a certain directory
            (passed as a string). If "None", then a platform default is used.
        :param on_submission_start: A function to call with the name of a
            submission when we start it.
        :param on_end_of_submissions: A function to call when we are done with
            all the submissions.
        """
        self._submissions = []
        self._use_color = use_color
        
        if open_shell is not None:
            self._open_shell = open_shell
        elif os.name == "nt":
            self._open_shell = _default_shell_windows
        else:
            self._open_shell = _default_shell_unix
        
        # Set up on_submission_start
        if callable(on_submission_start):
            self._on_submission_start = on_submission_start
        else:
            self._on_submission_start = lambda n: None
        
        # Set up on_end_of_submissions
        if callable(on_end_of_submissions):
            self._on_end_of_submissions = on_end_of_submissions
        else:
            self._on_end_of_submissions = lambda: None

        # Initialize colorama
        init()

    def find_path(self, working_dir, folder, base=""):
        """
        Find a new path based on a current path and either a subfolder or a list
        of regular expressions representing subfolders. Prompts the user for
        input if a folder is invalid.

        :param working_dir: The current path
        :param folder: A single subfolder, or list of regular expressions
        :param base: The base directory (that we shouldn't include when printing
            directory paths)
        :return: The new path, or None if none exists
        """
        # Make sure the current path exists
        if not os.path.isdir(working_dir):
            return None

        def without_base(path):
            """Get a pretty version of a path"""
            if path[0:len(base)] == base:
                path = path[len(base):]
                if path[0] == "/":
                    path = path[1:]
            if path[-1] == ".":
                path = path[:-1]
            if path[-1] == "/":
                path = path[:-1]
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

        # Check the folder, and make sure it's what the user wants
        user_happy = False
        while not user_happy:
            if new_path is None or not os.path.isdir(new_path):
                # It doesn't exist!
                user_happy = False
                if new_path is None:
                    self.error("Folder not found:", end=" ")
                    print(without_base(working_dir), end=" ")
                    self.status("::", end=" ")
                    print(folder)
                else:
                    self.error("Folder not found:", end=" ")
                    print(without_base(new_path))
            else:
                # List the files inside
                self.status("Files inside %s:" % without_base(new_path),
                            end=" ")
                for (index, item) in enumerate(os.listdir(new_path)):
                    if index != 0:
                        self.status(",", end=" ")
                    print(item, end="")
                print("\n")

                user_happy = self.prompt_user(
                    "Does this directory satisfy your innate human needs?",
                    ["y", "n"]) == "y"

            if not user_happy:
                new_path_input = self.input_color(
                    "Enter folder path (relative to %s), or Enter to cancel:" %
                    without_base(working_dir))
                if new_path_input:
                    new_path = os.path.join(working_dir, new_path_input)
                else:
                    # They've given up
                    new_path = None
                    # And they'd better be damn happy with that choice
                    user_happy = True

        return new_path

    def add_submissions(self, submissions_directory, folder_regex,
                        check_zipfiles=False, print_found_submissions=True):
        """
        Add a directory of submissions to our list of submissions.
        
        The regular expression is used to limit which folders are picked up.
        Also, the first matched group in the regex is used as the name of the
        submission.
        
        :param submissions_directory: Path to the directory containing
            submissions
        :param folder_regex: Regular expression to use to match subfolders
            (see the YAML format documentation for more info).
        :param check_zipfiles: Whether to check zipfiles in the directory to
            see if any match (see the YAML format documentation for more).
        :param print_found_submissions: Whether to print a list of all the
            submissions we've found. Also prints when we've extracted a zipfile.
        """
        
        # Step 1: Make sure "submissions_directory" exists and is a directory
        if not os.path.isdir(submissions_directory):
            raise FileNotFoundError("Cannot find given directory: '" +
                                    submissions_directory + "'")
        
        regex = re.compile(folder_regex)
        
        # Step 2: Check zipfiles (if necessary)
        if check_zipfiles:
            for item in os.listdir(submissions_directory):
                # Is it a zipfile?
                if os.path.isfile(os.path.join(submissions_directory, item)) \
                   and item[-4:] == ".zip":
                    # Unzip it! (will return False if folder already exists)
                    if extract_zipfile(os.path.join(submissions_directory,
                                                    item)):
                        # We unzipped it
                        print("Unzipped: " + item)
        
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
            submission = Submission(item,
                                    os.path.join(submissions_directory, item),
                                    submissions_directory)
            for group in match.groups():
                if group:
                    submission.name = group
                    break
            
            # Add this submission to our list
            if print_found_submissions:
                print("Found submission: " + submission.name)
            self._submissions.append(submission)

    def run_commands(self, commands, helper_directory=None):
        """
        Run some commands for each of our submissions. The command list is
        detailed in the documentation for the YAML format.
        
        Each command has certain environmental variables available to it. For
        details, see the documentation for the YAML format.
        
        By default (i.e. for top-level commands), the working directory is the
        folder at the root of the submission it's running in.
        
        After each command is run, the user will be prompted as to what they
        want to do.
        
        :param commands: The command list to run.
        :param helper_directory: If specified, available to the client as an
            environmental variable and used as the default location for diff
            files.
        """
        for submission in self._submissions:
            msg = "Starting " + submission.name
            
            self.status("-" * len(msg))
            self.status(msg)
            self.status("-" * len(msg))
            
            if self.prompt_user(
                    "Press Enter to begin, or 's' to skip",
                    ["s", ""],
                    False) == "s":
                continue
            
            self._on_submission_start(submission.name)
            self._run_command_set(commands, submission, submission.path,
                                  helper_directory)
        self._on_end_of_submissions()

    def _run_command_set(self, commands, submission, path,
                         helper_directory=None):
        """
        Run some commands from a command set for a specific submission.
        
        :param commands: The list of commands to run
        :param submission: The current submission that we're operating on
        :param path: The working directory for the commands to run
        :param helper_directory: If specified, available to the client as an
            environmental variable and used as the default location for diff
            files.
        :return: False to skip the rest of the commands for this submission
        """
        for cmd in commands:
            if "commands" not in cmd:
                # It's an actual command
                if "name" in cmd and "command" in cmd:
                    # If False, then we want to skip the rest of this submission
                    if not self._run_command(cmd, submission, path,
                                             helper_directory):
                        return False
                    # Otherwise, just continue on to the next command
                    continue
                else:
                    self.error("Invalid command found")
                    continue
            
            # If we're still here, we have a group of commands
            # Figure out our new directory for these commands
            new_path = path
            if "folder" in cmd:
                new_path = self.find_path(path, cmd["folder"], submission.base)
                # Handle a bad folder
                if new_path is None:
                    self.error("Skipping commands: " + ", ".join(
                        [subcmd["name"] for subcmd in cmd["commands"]
                         if "name" in subcmd]))
                    # Skip running these commands
                    self.input_color("Press Enter to continue...")
                    continue
            
            # Run the subcommands in this folder
            new_path_pretty = new_path
            # Make the path relative if possible
            if new_path[0:len(submission.path)] == submission.path:
                new_path_pretty = "." + new_path[len(submission.path):]
            # Remove trailing "." if necessary
            if new_path_pretty[-2:] == "/.":
                new_path_pretty = new_path_pretty[:-1]
            print("")
            self.status("Running commands for folder: ." + new_path_pretty)
            print("")
            self._run_command_set(cmd["commands"], submission, new_path,
                                  helper_directory)
            self.status("End commands for folder: " + new_path_pretty)
            print("")
    
    def _run_command(self, cmd, submission, path, helper_directory=None):
        """
        Actually run a command.
        
        :param cmd: The command to run
        :param submission: The submission that we're running these commands on
        :param path: The working directory for the command
        :param helper_directory: If specified, available to the client as an
            environmental variable and used as the default location for diff
            files.
        :return: True to move on to the next command,
                 False to move on to the next submission
        """
        self.status("-" * 50)
        self.status("::: " + cmd["name"])
        if submission.modify_all_commands:
            cmd = self.get_modified_command(cmd)
        else:
            self.print_bright("    " + cmd["command"])
        
        print("")
        
        env = dict(os.environ)
        # Set command environment
        env.update({
            "SUBMISSION_DIRECTORY": submission.path,
            "CURRENT_DIRECTORY": path,
            "SUBMISSION_NAME": submission.name
        })
        if helper_directory is not None:
            env["HELPER_DIRECTORY"] = helper_directory
        
        # Run the command!
        output = None
        try:
            kwargs = {
                "cwd": path,
                "shell": True,
                "env": env,
                "stderr": subprocess.STDOUT,
                "universal_newlines": True
            }
            if "diff" in cmd and os.path.exists(os.path.join(helper_directory,
                                                             cmd["diff"])):
                # Run with check_output so we can compare the output
                output = subprocess.check_output(cmd["command"], **kwargs)
            else:
                # Just run with check_call
                subprocess.check_call(cmd["command"], **kwargs)
        except subprocess.CalledProcessError as ex:
            self.error("Command had nonzero return code: %s" % ex.returncode)
            print("")
        
        if output is not None:
            # Run diff
            with open(os.path.join(helper_directory, cmd["diff"]), "r") as ref:
                #diff = difflib.unified_diff(ref, output, "reference", "output")
                diff = difflib.ndiff(
                    [line for line in ref],
                    output.splitlines(keepends=True))
                self.print_happy("--- Reference")
                self.print_sad("+++ Output")
                print("")
                for line in diff:
                    line = line.rstrip("\n")
                    if line[0] == "-":
                        self.print_happy(line)
                    elif line[0] == "+":
                        self.print_sad(line)
                    elif line[0] == "?":
                        self.print_bright(line)
                    else:
                        print(line)
        
        # All done with the command!
        # Ask user what they want to do
        available_choices = ["o", "r", "m", "p", "s", "?", ""]
        if submission.modify_all_commands:
            available_choices.remove("m")
            available_choices.remove("p")
        while True:
            print("")
            choice = self.prompt_user("What now?", available_choices)
            print("")
            if choice == "o":
                # Open a shell in the current folder
                self._open_shell(path)
            elif choice == "r":
                # Repeat the command
                return self._run_command(cmd, submission, path,
                                         helper_directory)
            elif choice == "m":
                # Modify the command, then repeat it
                return self._run_command(self.get_modified_command(cmd),
                                         submission,
                                         path, helper_directory)
            elif choice == "p":
                # Move on to the next command, but modify it before running
                submission.modify_all_commands = True
                return True
            elif choice == "s":
                # Skip the rest of this submission
                return False
            elif choice == "?":
                # Show help
                print("  o: Open a shell in the current folder")
                print("  r: Repeat the command")
                if not submission.modify_all_commands:
                    print("  m: Modify the command (just for this " +
                          "submission) and repeat it")
                    print("  p: Continue to the next command, but modify " +
                          "each command for the rest of this submission " +
                          "before running it")
                print("  s: Skip the rest of this submission")
                print("  ?: Show this help message")
                print("  Enter: Continue to the next command")
            else:
                # Continue on to the next submission
                return True







