#!/usr/bin/env python3
"""
Run gradefast with the input of a YAML file.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jhartz@mail.rit.edu>
"""
import os, sys, threading, webbrowser, time, _thread, traceback

import yaml

from .grader import Grader
from .gradebook import GradeBook


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8051


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


def _run_grader(yaml_data, yaml_directory, *args, **kwargs):
    """
    Load the Grader and start it.
    
    This is a helper function for `run'; it's separate because it is run in a
    separate thread.
    
    :param yaml_data: The parsed data from the YAML file (assumed to be valid)
    :param yaml_directory: The directory where the YAML file lives (to get any
        paths that are relative to it)
    """
    # First, sleep for a bit to give some time for the web server to print shit
    time.sleep(1)
    try:
        print("")
        grader = Grader(*args, **kwargs)
        for submission in yaml_data["submissions"]:
            grader.add_submissions(
                os.path.join(yaml_directory, submission["path"]),
                submission["regex"],
                "checkZipfiles" in submission and submission["checkZipfiles"])
        print("")
        grader.run_commands(yaml_data["commands"], yaml_directory)
    except:
        print_bordered_message("ERROR RUNNING GRADER")
        traceback.print_exc()
    finally:
        print("")
        print_bordered_message("Grading complete!",
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
        yaml_data = yaml.load(open(yaml_file))
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
    gradebook = GradeBook(yaml_data["grades"])
    
    # Load up the Grader in its own thread
    grader_thread = threading.Thread(
        target=_run_grader,
        args=(yaml_data, os.path.dirname(yaml_file)),
        kwargs={
            "on_submission_start": lambda n: gradebook.start_submission(n),
            "on_end_of_submissions": lambda: gradebook.end_of_submissions()
        }
    )
    
    # Give the user the grade book URL
    url = "http://%s:%s/gradefast/gradebook" % (hostname, port)
    print_bordered_message("Grade Book URL: %s" % url)
    
    if input("Open in browser (y/N)? ").strip().lower() == "y":
        webbrowser.open_new(url)
    print("")
    
    # Start the Grader thread
    grader_thread.start()
    
    # Start the main gradebook server
    gradebook.run(hostname, port)


if __name__ == "__main__":
    # Make sure that we have a YAML file
    if len(sys.argv) <= 1:
        print("Usage: python -m gradefast YAML_FILE [HOSTNAME [PORT]]")
        print("    \"YAML_FILE\" contains the structure of the grading and " +
              "the commands to run.")
        print("    \"HOSTNAME\" is the hostname to run the grade book HTTP " +
              "server on. Default: localhost")
        print("    \"PORT\" is the port to run the grade book HTTP server " +
              "on. Default: 8051")
        sys.exit(2)
    
    # Figure out the hostname and port for the server
    HOST = DEFAULT_HOST if len(sys.argv) < 3 else sys.argv[2]
    PORT = DEFAULT_PORT if len(sys.argv) < 4 else int(sys.argv[3])
    
    # Zhu Li, do the thing!
    if run(sys.argv[1], HOST, PORT) == False:
        # Something bad happened
        sys.exit(1)

