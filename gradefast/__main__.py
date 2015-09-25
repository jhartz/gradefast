#!/usr/bin/env python3
"""
Run gradefast with the input of a YAML file.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jhartz@mail.rit.edu>
"""
import sys

from .runyaml import run


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8051


if __name__ == "__main__":
    # Make sure that we have a YAML file
    if len(sys.argv) <= 1:
        print("Usage: python -m gradefast YAML_FILE [HOSTNAME [PORT]]")
        print("")
        print("    \"YAML_FILE\" contains the structure of the grading and " +
              "the commands to run.")
        print("    \"HOSTNAME\"  is the hostname to run the grade book HTTP " +
              "server on.")
        print("                Default: localhost")
        print("    \"PORT\"      is the port to run the grade book HTTP " +
              "server on.")
        print("                Default: 8051")
        sys.exit(2)

    # Figure out the hostname and port for the server
    HOST = DEFAULT_HOST if len(sys.argv) < 3 else sys.argv[2]
    PORT = DEFAULT_PORT if len(sys.argv) < 4 else int(sys.argv[3])

    # Zhu Li, do the thing!
    if not run(sys.argv[1], HOST, PORT):
        # Something bad happened
        sys.exit(1)
