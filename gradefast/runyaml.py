#!/usr/bin/env python3
"""
Run gradefast with the input of a YAML file.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jhartz@mail.rit.edu>
"""
import os
import sys
import threading
import webbrowser
import time
import _thread
import traceback
import subprocess

try:
    import yaml
except ImportError:
    print("")
    print("*** Couldn't find YAML package!")
    print("    Please install 'PyYAML' and try again.")
    print("")
    sys.exit(1)

from .grader import Grader
from .gradebook import GradeBook


def print_bordered_message(*msgs):
    """
    Print a message surrounded by a border.

    :param msgs: The messages to print.
    """
    longest = 0
    for msg in msgs:
        if len(msg) > longest:
            longest = len(msg)
    msgs = ["**  %s%s  **" % (msg, " " * (longest - len(msg))) for msg in msgs]
    longest += 8
    print("")
    print("*" * longest)
    for msg in msgs:
        print(msg)
    print("*" * longest)
    print("")


class SaveFile:
    def __init__(self, path, overwrite=False):
        """
        Initialize a new Save File.

        :param path: The path to the save file.
        :param overwrite: Whether to overwrite anything that already exists at
            `path`. If this is false, then we will attempt to use the contents
            of the existing file (if it exists) to "pick up" where we last left
            off.
        """
        self.path = path
        self.overwrite = overwrite

    def save_submission_grade(self, grade_id, grade):
        """
        Save a SubmissionGrade.

        :param grade_id: The ID (or index) of the SubmissionGrade.
        :param grade: The SubmissionGrade object.
        """
        pass

    def save_submission_list(self, submissions):
        """
        Save a list of Submissions.

        :param submissions: The list of submissions to save.
        """
        pass


def _start_thread(grader_thread, url):
    """
    Prompt the user for whether they want to open the gradebook in their web
    browser, then start the grader thread.

    This is a helper function for `run'; it's separate because it is run in a
    separate thread.

    :param grader_thread: The grader thread to start
    :param url: The URL to the grade book
    """
    # First, sleep for a bit to give some time for the web server to print shit
    time.sleep(0.5)

    # Give the user the grade book URL
    print_bordered_message("Grade Book URL: %s" % url)

    if input("Open in browser (y/N)? ").strip().lower() == "y":
        webbrowser.open_new(url)
    print("")

    # Start the Grader thread
    grader_thread.start()


def _run_grader(yaml_data, yaml_directory, *args, **kwargs):
    """
    Load the Grader and start it. "args" and "kwargs" are passed directly on to
    Grader.

    This is a helper function for `run'; it's separate because it is run in a
    separate thread.

    :param yaml_data: The parsed data from the YAML file (assumed to be valid)
    :param yaml_directory: The directory where the YAML file lives (to get any
        paths that are relative to it)
    """
    try:
        print("")
        grader = Grader(*args, **kwargs)
        for submission in yaml_data["submissions"]:
            grader.add_submissions(
                os.path.join(yaml_directory, submission["path"]),
                submission["regex"],
                "check zipfiles" in submission and submission["check zipfiles"],
                "check files" in submission and submission["check files"])
        print("")

        # A function to open a shell window
        terminal_shell = None
        # A list representing executing a command
        command_shell = None

        if "config" in yaml_data:
            # Check if they've provided a command to open a shell window
            if "terminal shell" in yaml_data["config"]:
                terminal_shell = lambda path, env: subprocess.Popen([
                    path if arg is None else arg
                    for arg in yaml_data["config"]["terminal shell"]
                ], cwd=path, env=env)
            # Check if they've provided a command to execute a command
            if "command shell" in yaml_data["config"]:
                command_shell = yaml_data["config"]["command shell"]

        grader.run_commands(yaml_data["commands"], yaml_directory,
                            command_shell, terminal_shell)
    except:
        print_bordered_message("ERROR RUNNING GRADER")
        traceback.print_exc()
    finally:
        print("")
        print_bordered_message(
            "Grading complete!",
            "Download the gradebook and any other data you need.",
            "Once you exit the server, the gradebook is lost.")
        print("")
        input("Press Enter to exit server... ")
        #sys.exit()
        _thread.interrupt_main()
        os._exit(0)


def run(yaml_file, hostname, port):
    """
    Start gradefast based on a YAML file and server parameters.

    :param yaml_file: The path to a YAML file detailing what we should do
    :param hostname: The hostname to run the server on
    :param port: The port to run the server on
    :return: False if a fatal error occurred
    """
    # Try to load the YAML file
    yaml_data = None
    try:
        with open(yaml_file) as f:
            yaml_data = yaml.load(f)
    except FileNotFoundError:
        print("YAML file not found: %s" % yaml_file)
        return False

    # Make sure we have all the data
    if not (yaml_data and "grades" in yaml_data
                      and "submissions" in yaml_data
                      and "commands" in yaml_data):
        print("YAML data missing required items")
        return False

    # Create grade book WSGI app
    gradebook = GradeBook(yaml_data["grades"],
                          os.path.splitext(os.path.basename(yaml_file))[0])

    # These keyword arguments will be used for the Grader constructor
    grader_kwargs = {
        "on_submission_start": lambda nam: gradebook.start_submission(nam),
        "on_submission_end": lambda log: gradebook.log_submission(log),
        "on_end_of_submissions": lambda: gradebook.end_of_submissions()
    }

    # Load up the Grader in its own thread
    grader_thread = threading.Thread(
        target=_run_grader,
        # The args are (yaml data, yaml file location)
        args=(yaml_data, os.path.dirname(yaml_file)),
        # The kwargs are passed right on to Grader
        kwargs=grader_kwargs
    )

    # Start a different thread that will start the Grader thread
    threading.Thread(
        target=_start_thread,
        kwargs={
            "grader_thread": grader_thread,
            "url": "http://%s:%s/gradefast/gradebook" % (hostname, port)
        }
    ).start()

    # Start the main gradebook server
    gradebook.run(hostname, port, debug=True)

    # All good!
    return True

