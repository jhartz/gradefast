"""
Run GradeFast.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import threading
import time
import webbrowser
from typing import List

from iochannels import Channel, Msg
from pyprovide import Injector

from gradefast.gradebook.gradebook import GradeBook
from gradefast.grader.grader import Grader
from gradefast.loggingwrapper import get_logger
from gradefast.models import Path, Settings
from gradefast.persister import Persister

_logger = get_logger("run")


class LazyUserError(Exception):
    pass


def _try_run_gradebook(gradebook: GradeBook) -> None:
    logger = get_logger("run: gradebook")
    try:
        gradebook.run(debug=True)
    except:
        logger.exception("Exception when running gradebook server")


def run_gradefast(injector: Injector, submission_paths: List[Path]) -> None:
    # Initialize the Channel used to communicate via the CLI (if we haven't already)
    channel = injector.get_instance(Channel)

    # Initialize the Persister (i.e. save file wrapper)
    persister = injector.get_instance(Persister)

    # Wrap the rest in a try-finally to ensure the channel and persister get cleaned up properly
    try:
        _logger.debug("Running GradeFast")
        _run_gradefast_internal(injector, submission_paths)
    except:
        _logger.exception("Error running GradeFast")
    finally:
        _logger.debug("Closing resources")
        persister.close()
        channel.close()


def _run_gradefast_internal(injector: Injector, submission_paths: List[Path]) -> None:
    settings = injector.get_instance(Settings)
    channel = injector.get_instance(Channel)

    if settings.gradebook_enabled:
        # Create and start the GradeBook WSGI server in a new thread
        gradebook = injector.get_instance(GradeBook)
        threading.Thread(
            name="GradeBookTh",
            target=_try_run_gradebook,
            args=(gradebook,),
            daemon=True
        ).start()
        # Sleep for a bit to give the web server some time to catch up
        time.sleep(0.4)

    # Wrap the rest in a `try` so that exceptions in the Grader don't kill everything
    # (i.e. the web server will still be running)
    try:
        # Start the grader before showing the gradebook URL so "AuthRequestedEvent"s don't fall
        # away into the void
        grader = injector.get_instance(Grader)

        if settings.gradebook_enabled:
            # Give the user the grade book URL
            gradebook_url = "http://{host}:{port}/gradefast/gradebook".format(host=settings.host,
                                                                              port=settings.port)
            channel.print()
            channel.print_bordered("Grade Book URL: {}", gradebook_url)
            channel.print()
            if channel.prompt("Open in browser?", ["y", "N"], "n") == "y":
                webbrowser.open_new(gradebook_url)
                # Sleep for a tad to allow for the auth prompt to come up
                time.sleep(0.8)
            channel.print()

        # Finally... let's start grading!
        for path in submission_paths:
            grader.add_submissions(path)
        if not grader.prompt_for_submissions():
            raise LazyUserError("User is too lazy to find any submissions")
        grader.run_commands()

        # Well, the user thinks they're done
        channel.print()
        channel.print_bordered("Grading complete!", type=Msg.PartType.STATUS)
        channel.print()
    except (InterruptedError, KeyboardInterrupt):
        channel.print()
        channel.print()
        channel.print_bordered("INTERRUPTED", type=Msg.PartType.ERROR)
        channel.print()
    except:
        _logger.exception("ERROR RUNNING GRADER")
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
