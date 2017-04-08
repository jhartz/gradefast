"""
Run GradeFast.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import os
import threading
import time
import traceback
import webbrowser
from typing import List

import iochannels
from pyprovide import Injector

from gradefast.gradebook import GradeBook
from gradefast.grader import Grader
from gradefast.models import Path, Settings


class LazyUserError(Exception):
    pass


def run_gradefast(injector: Injector, submission_paths: List[Path]):
    # Create and start the GradeBook WSGI server in a new thread
    threading.Thread(
        target=lambda: injector.get_instance(GradeBook).run(debug=True),
        daemon=True
    ).start()
    # Sleep for a bit to give the web server some time to catch up
    time.sleep(0.4)

    # Wrap the rest in a `try` so that exceptions in the Grader don't kill everything
    # (i.e. the web server will still be running)
    channel: iochannels.Channel = injector.get_instance(iochannels.Channel)
    try:
        # Start the grader before showing the gradebook URL so "AuthRequestedEvent"s don't fall
        # away into the void
        grader: Grader = injector.get_instance(Grader)

        # Give the user the grade book URL
        settings: Settings = injector.get_instance(Settings)
        gradebook_url = "http://%s:%s/gradefast/gradebook" % (settings.host, settings.port)
        channel.print()
        channel.print_bordered("Grade Book URL: {}", gradebook_url)
        channel.print()
        if channel.prompt("Open in browser?", ["y", "N"], "n") == "y":
            webbrowser.open_new(gradebook_url)
        channel.print()

        # Finally... let's start grading!
        for path in submission_paths:
            grader.add_submissions(path)
        if not grader.prompt_for_submissions():
            raise LazyUserError("User is too lazy to find any submissions")
        grader.run_commands()

        # Well, the user thinks they're done
        channel.print()
        channel.print_bordered("Grading complete!", type=iochannels.Msg.PartType.STATUS)
        channel.print()
    except (InterruptedError, KeyboardInterrupt):
        channel.print()
        channel.print()
        channel.print_bordered("INTERRUPTED", type=iochannels.Msg.PartType.ERROR)
        channel.print()
    except:
        channel.print()
        channel.print_bordered("ERROR RUNNING GRADER", type=iochannels.Msg.PartType.ERROR)
        channel.print("{}", traceback.format_exc())
        channel.print()
    finally:
        channel.print()
        channel.print("Download the gradebook and any other data you need.")
        channel.print("Once you exit the server, the gradebook is lost.")
        channel.print()
        try:
            channel.input("Press Enter to exit server...")
        except (InterruptedError, KeyboardInterrupt):
            # Pretend that they pressed "Enter"
            channel.print()

        # Make sure that all of our doors are shut for the winter
        os._exit(0)
