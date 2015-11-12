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
    longest = max((len(msg) for msg in msgs), default=0)
    msgs = ["**  %-*s  **" % (longest, msg) for msg in msgs]
    width = longest + 8
    print("\n" + "*" * width)
    for msg in msgs:
        print(msg)
    print("*" * width + "\n")


def _run_grader(yaml_data, yaml_directory, gradebook, gradebook_url,
                *args, **kwargs):
    """
    Load the Grader and start it. "args" and "kwargs" are passed directly on to
    Grader.

    This is a helper function for `run'.

    :param yaml_data: The parsed data from the YAML file (assumed to be valid)
    :param yaml_directory: The directory where the YAML file lives (to get any
        paths that are relative to it)
    :param gradebook: The Gradebook instance (that holds the web server)
    :param gradebook_url: The URL to the Gradebook server
    """
    # First, sleep for a bit to give some time for the web server to start up
    time.sleep(0.5)

    # Give the user the grade book URL
    print_bordered_message("Grade Book URL: %s" % gradebook_url)

    if input("Open in browser (y/N)? ").strip().lower() == "y":
        webbrowser.open_new(gradebook_url)
    print("")

    # Wrap the rest in a `try` so that exceptions in the Grader don't kill
    # everything (i.e. the server will still be running)
    try:
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
                # Re-define the terminal shell function to use their command
                def terminal_shell(path, env):
                    subprocess.Popen([
                        path if arg is None else arg
                        for arg in yaml_data["config"]["terminal shell"]
                    ], cwd=path, env=env)

            # Check if they've provided a command to execute a command
            if "command shell" in yaml_data["config"]:
                command_shell = yaml_data["config"]["command shell"]

        grader.run_commands(yaml_data["commands"], yaml_directory,
                            command_shell, terminal_shell)
    except:
        print("")
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

        # Things we tried before we realized Thread(daemon=True)
        #sys.exit()
        #_thread.interrupt_main()
        #os._exit(0)


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
        with open(yaml_file, encoding="utf-8") as f:
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
    gradebook_url = "http://%s:%s/gradefast/gradebook" % (hostname, port)

    # These keyword arguments will be used for the Grader constructor
    grader_kwargs = {
        "on_submission_start": lambda nam: gradebook.start_submission(nam),
        "on_submission_end": lambda log: gradebook.log_submission(log),
        "on_end_of_submissions": lambda: gradebook.end_of_submissions()
    }

    # Start the main Gradebook server
    gradebook_thread = threading.Thread(
        target=lambda: gradebook.run(hostname, port, debug=True),
        daemon=True
    )
    gradebook_thread.start()

    # Run the Grader CLI interface
    _run_grader(yaml_data, os.path.dirname(yaml_file), gradebook, gradebook_url,
                **grader_kwargs)

    # All good!
    return True
