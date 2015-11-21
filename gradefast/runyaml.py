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


def load_yaml_data(yaml_file):
    """
    Load and check the YAML file.
    """
    yaml_data = None
    try:
        with open(yaml_file, encoding="utf-8") as f:
            yaml_data = yaml.load(f)
    except FileNotFoundError:
        raise FileNotFoundError("YAML file not found: %s" % yaml_file)

    # Make sure we have all the data
    if not (yaml_data and "grades" in yaml_data
                      and "submissions" in yaml_data
                      and "commands" in yaml_data):
        raise RuntimeError("YAML data missing required items")

    return yaml_data


def _start_gradebook(grade_structure, grade_name, hostname, port):
    """
    Create and start the GradeBook web server.
    """
    gradebook = GradeBook(grade_structure, grade_name)

    # Start the main GradeBook server
    gradebook_thread = threading.Thread(
        target=lambda: gradebook.run(hostname, port, debug=True),
        daemon=True
    )
    gradebook_thread.start()

    return gradebook


def _run_grader(yaml_data, yaml_directory, on_event):
    """
    Create and run the Grader CLI.
    """
    grader = Grader(on_event)

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


def run(yaml_file, hostname, port):
    """
    Start gradefast based on a YAML file and server parameters.

    :param yaml_file: The path to a YAML file detailing what we should do
    :param hostname: The hostname to run the server on
    :param port: The port to run the server on
    """
    # Try to load the YAML file
    yaml_data = load_yaml_data(yaml_file)

    # Create and start the grade book WSGI app
    gradebook = _start_gradebook(
        yaml_data["grades"],
        os.path.splitext(os.path.basename(yaml_file))[0],
        hostname, port)

    # First, sleep for a bit to give some time for the web server to start up
    time.sleep(0.5)

    # Wrap the rest in a `try` so that exceptions in the Grader don't kill
    # everything (i.e. the server will still be running)
    try:
        # Give the user the grade book URL
        gradebook_url = "http://%s:%s/gradefast/gradebook" % (hostname, port)
        print_bordered_message("Grade Book URL: %s" % gradebook_url)

        if input("Open in browser (y/N)? ").strip().lower() == "y":
            webbrowser.open_new(gradebook_url)
        print("")

        # Finally... let's start grading!
        _run_grader(yaml_data, os.path.dirname(yaml_file),
                    lambda evt: gradebook.event(evt))
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
        try:
            input("Press Enter to exit server... ")
        except (InterruptedError, KeyboardInterrupt):
            # Just ignore Ctrl+C here
            pass
