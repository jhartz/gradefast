"""
The GradeBook HTTP server.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""
import sys
import json
import queue
import logging
import csv
import io
import random
import mimetypes
from collections import OrderedDict
import traceback
from typing import List, Optional, Union

try:
    import mistune
except ImportError:
    mistune = None

try:
    import flask
except ImportError:
    print("")
    print("*** Couldn't find Flask package!")
    print("    Please install 'flask' and try again.")
    print("")
    sys.exit(1)

from . import events, grades


class GradeBook:
    """
    Represents a grade book with submissions and grade structures.
    """
    def __init__(self, grade_structure: List[dict], grade_name: str=None):
        """
        Create a WSGI app representing a grade book.

        A grade structure is a list of grade items (grade scores and grade sections). For more, see
        the GradeFast wiki: https://github.com/jhartz/gradefast/wiki/Grade-Structure

        :param grade_structure: A list of grade items
        :param grade_name: A name for whatever we're grading
        """
        self._grade_name = grade_name or "grades"

        # Check validity of _grade_structure
        self._grade_structure = grade_structure
        grades.check_grade_structure(self._grade_structure)

        self._grades_by_submission = {}
        self._current_submission_id = None
        self._subscriptions = []
        self.is_done = False

        # Set up Mistune (Markdown)
        if mistune is None:
            print("")
            print("*** Couldn't find mistune package!")
            print("    Items will not be Markdown-parsed.")
            print("")

            def parse_md(*args, **kwargs):
                return args[0]
        else:
            markdown = mistune.Markdown(renderer=mistune.Renderer(hard_wrap=True))

            def parse_md(*args, **kwargs):
                text = markdown(*args, **kwargs).strip()
                # Stylize p tags
                text = text.replace('<p>', '<p style="margin: 3px 0">')

                # Stylize code tags (even though MyCourses cuts out the background anyway...)
                text = text.replace(
                    '<code>', '<code style="background-color: rgba(0, 0, 0, '
                              '0.04); padding: 1px 3px; border-radius: 5px;">')
                return text

        self._md = parse_md

        # Set up MIME type for JS source map
        mimetypes.add_type("application/json", ".map")

        # Start Flask app
        app = flask.Flask(__name__)
        self._app = app
        self._client_id = 0
        self._client_keys = {}
        random.seed()

        # Now, initialize the routes for the app

        @app.route("/gradefast/")
        def _gradefast_():
            return flask.redirect(flask.url_for("_gradefast_gradebook_HTM"))

        @app.route("/gradefast/gradebook/")
        def _gradefast_gradebook_():
            return flask.redirect(flask.url_for("_gradefast_gradebook_HTM"))

        # GradeBook page (yes, the HTM is solely for trolling, teehee)
        @app.route("/gradefast/gradebook.HTM")
        def _gradefast_gradebook_HTM():
            self._client_id += 1
            self._client_keys[self._client_id] = str(self._client_id + random.random()) + ".secret"
            return flask.render_template(
                "gradebook.html",
                client_id=self._client_id,
                client_key=json.dumps(self._client_keys[self._client_id]),
                initial_list=json.dumps([]),
                initial_submission_id=json.dumps(self._current_submission_id),
                is_done=json.dumps(self.is_done),
                # TODO: implement (from YAML file)
                check_hint_range=json.dumps(False))

        # Log page
        @app.route("/gradefast/log/<submission_id>")
        def _gradefast_log__(submission_id):
            grade = self.get_grade(submission_id)
            if grade is None:
                flask.abort(404)
            else:
                return flask.render_template(
                    "log.html",
                    title="Log for %s" % grade.name,
                    content=grade.log
                )

        # AJAX endpoint to update grades based on an action
        @app.route("/gradefast/_update", methods=["POST"])
        def _gradefast_update():
            def status(s):
                return json.dumps({"status": s})

            try:
                if "client_id" not in flask.request.form:
                    return status("Missing client ID")
                try:
                    client_id = int(flask.request.form["client_id"])
                except ValueError:
                    return status("Invalid client ID")

                if "client_key" not in flask.request.form:
                    return status("Missing client key")
                if flask.request.form["client_key"] != self._client_keys.get(client_id, None):
                    return status("Invalid client key")

                if "client_seq" not in flask.request.form:
                    return status("Missing client seq")
                try:
                    client_seq = int(flask.request.form["client_seq"])
                except ValueError:
                    return status("Invalid client seq")

                if "submission_id" not in flask.request.form:
                    return status("Missing submission ID")
                try:
                    submission_id = int(flask.request.form["submission_id"])
                except ValueError:
                    return status("Invalid submission ID")

                action = {}
                if "action" in flask.request.form:
                    try:
                        action = json.loads(flask.request.form["action"])
                    except json.JSONDecodeError:
                        return status("Invalid action")

                # Parse the action into a ClientActionEvent (may raise BadSubmissionException)
                action_event = events.ClientActionEvent(
                    submission_id, client_id, client_seq, action)

                # Apply the action (this will send an update through the events stream)
                # This may raise BadActionException, BadPathException, or BadValueException
                self.apply_event(action_event)

                # If nothing threw, return that we processed everything successfully
                return status("Aight")

            except events.ActionEvent.BadSubmissionException:
                return status("Invalid submission")

            except events.ClientActionEvent.BadActionException:
                return status("Invalid action")

            except grades.BadPathException:
                return status("Invalid path")

            except grades.BadValueException:
                return status("Invalid value")

            except Exception as ex:
                print("\n\nGRADEBOOK AJAX HANDLER EXCEPTION:", ex)
                print(traceback.format_exc())
                print("")
                return status("Look what you did... (seriously, look in the server error console)")

        # Grades CSV file
        @app.route("/gradefast/grades.csv")
        def _gradefast_grades_csv():
            csv_stream = self._get_csv()

            def gen():
                try:
                    while True:
                        line = csv_stream.readline()
                        if line == "":
                            break
                        yield line
                except GeneratorExit:
                    pass

            resp = flask.Response(gen(), mimetype="text/csv")
            filename_param = 'filename="%s.csv"' % \
                self._grade_name.replace("\\", "").replace('"', '\\"')
            resp.headers["Content-disposition"] = "attachment; " + filename_param
            return resp

        # Grades JSON file
        @app.route("/gradefast/grades.json")
        def _gradefast_grades_json():
            return flask.Response(self._get_json(), mimetype="application/json")

        # Event stream
        @app.route("/gradefast/_events")
        def _gradefast_events():
            def gen():
                q = queue.Queue()
                self._subscriptions.append(q)
                try:
                    yield events.ClientUpdate("init").encode()
                    while True:
                        ev = q.get()
                        assert isinstance(ev, events.ClientUpdate)
                        yield ev.encode()
                except GeneratorExit:
                    pass
                finally:
                    self._subscriptions.remove(q)
            return flask.Response(gen(), mimetype="text/event-stream")

    def get_current_submission_id(self):
        return self._current_submission_id

    def get_grade(self, submission_id: Union[str, int]) -> Optional[grades.SubmissionGrade]:
        """
        Test whether a submission ID is valid and, if so, get the Grade corresponding to it.
        
        :param submission_id: The ID to test
        :return: a Grade if valid, or None otherwise
        """
        try:
            submission_id = int(submission_id)
        except ValueError:
            submission_id = None
            pass
        if submission_id is None:
            return None
        if submission_id not in self._grades_by_submission:
            return None
        return self._grades_by_submission[submission_id]

    def apply_event(self, event: events.GradeBookEvent):
        """
        Apply a GradeBook event to this gradebook.

        :param event: An instance of a subclass of events.GradeBookEvent
        """
        assert isinstance(event, events.GradeBookEvent)

        # Run the event on this GradeBook
        client_event = event.apply(self)
        # If the event resulted in a client event, send that to all GradeBook JavaScript clients
        if client_event:
            self._send_client_update(client_event)

    def _send_client_update(self, client_update: events.ClientUpdate):
        """
        Send a client update to any open GradeBook JavaScript clients.

        :param client_update: The ClientUpdate to send
        """
        assert isinstance(client_update, events.ClientUpdate)
        for q in self._subscriptions:
            q.put(client_update)

    def start_submission(self, submission_id: int, name: str):
        """
        Set a submission ID to be the current submission ID.

        :param submission_id: The ID of the submission.
        :param name: The name of the owner of the submission.
        """
        # Make a new Grade object for this submission
        if submission_id not in self._grades_by_submission:
            self._grades_by_submission[submission_id] = grades.SubmissionGrade(
                name, self._grade_structure, self._md)
        self._current_submission_id = submission_id

    def log_submission(self, log: str):
        """
        Add log info for the current submission.

        :param log: The HTML log info
        """
        if len(self._grades_by_submission):
            self._grades_by_submission[self._current_submission_id].log += log

    def get_grades(self) -> List[OrderedDict]:
        """
        Return a list of ordered dicts representing the scores and feedback for
        each submission.
        """
        grade_list = []
        for grade in self._grades_by_submission.values():
            points_earned, points_possible, individual_points = grade.get_score()
            grade_details = OrderedDict()
            grade_details["name"] = grade.name
            grade_details["score"] = points_earned
            grade_details["possible_score"] = points_possible
            grade_details["percentage"] = 0 if points_possible == 0 else \
                100 * points_earned / points_possible
            grade_details["feedback"] = grade.get_feedback()
            for item_name, item_points in individual_points:
                grade_details[item_name] = item_points
            grade_list.append(grade_details)
        return grade_list

    def _get_csv(self) -> io.StringIO:
        """
        Return a stream representing the grades as a CSV file.
        """
        csv_stream = io.StringIO()
        csv_writer = csv.writer(csv_stream)

        # Make the header row
        point_titles = grades.get_point_titles(self._grade_structure)
        row_titles = ["Name", "Total Score", "Percentage", "Feedback", ""] + \
                     ["(%s) %s" % (pts, title) for title, pts in point_titles]
        csv_writer.writerow(row_titles)

        # Make the value rows
        for grade in self.get_grades():
            csv_writer.writerow([
                grade["name"],
                grade["score"],
                grade["percentage"],
                grade["feedback"],
                ""
            ] + ["" if title not in grade else grade[title] for title, pts in point_titles])

        # Return the resulting stream
        csv_stream.seek(0)
        return csv_stream

    def _get_json(self) -> str:
        """
        Return a string representing the grades as JSON.
        """
        return json.dumps(self.get_grades())

    def run(self, hostname: str, port: int, log_level: Union[str, int] = logging.WARNING,
            debug: bool = False):
        """
        Start the Flask server (using Werkzeug internally).

        :param hostname: The hostname to run on
        :param port: The port to run on
        :param log_level: The level to set the Werkzeug logger at
        :param debug: Whether to start the server in debug mode (prints tracebacks with "HTTP 500"
            errors)
        """
        # Set logging level
        server_log = logging.getLogger("werkzeug")
        server_log.setLevel(log_level)
        # Start the server
        kwargs = {
            "threaded": True,
            "use_reloader": False
        }
        if debug:
            kwargs["debug"] = True
            kwargs["use_reloader"] = False
        self._app.run(hostname, port, **kwargs)

    def get_wsgi_app(self):
        """
        Get a function representing the server as a WSGI app.
        """
        return self._app.wsgi_app
