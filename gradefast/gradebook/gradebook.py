"""
The GradeBook HTTP server.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""
import sys
import queue
import logging
import csv
import io
import uuid
import mimetypes
import threading
from collections import OrderedDict
from typing import List, Optional, Union

from . import events, grades, utils

try:
    import flask
except ImportError:
    flask = None
    utils.print_error("Couldn't find Flask package! Please install 'flask' and try again.")
    sys.exit(1)


class GradeBook:
    """
    Represents a grade book with submissions and grade structures.
    """

    class BadStructureException(Exception):
        """Exception resulting from a bad grade structure"""
        pass

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
        if not grades.check_grade_structure(self._grade_structure):
            raise GradeBook.BadStructureException()

        self._grades_by_submission = {}
        self._current_submission_id = None
        self.is_done = False
        self._event_lock = threading.Lock()

        # Each instance of the GradeBook JavaScript client is given its own unique ID (a UUID).
        # They are stored in these sets.
        self._client_ids = set()
        self._authenticated_client_ids = set()

        # When a client accesses the events stream, it has an "update ququq" (a Queue that update
        # events are sent to).
        self._client_update_queues = {}

        # Secret key used by the client for accessing downloadables (CSV and JSON).
        # This is sent to the client through the client's events stream after authentication.
        self._client_data_keys = {}

        # Secret key used by the client for sending updates to the _update AJAX endpoint.
        # This is sent to the client through the client's events stream after authentication.
        self._client_update_keys = {}

        # Set up MIME type for JS source map
        mimetypes.add_type("application/json", ".map")

        # Start Flask app
        app = flask.Flask(__name__)
        self._app = app

        ###########################################################################################
        # Helper functions for Flask routes

        def check_uuid_key(arg: str, key_map: dict):
            try:
                key = uuid.UUID(flask.request.args[arg])
                if key not in key_map.values():
                    flask.abort(401)
            except ValueError:
                flask.abort(400)

        def json_response(**data):
            return flask.Response(utils.to_json(data), mimetype="application/json")

        def json_bad_request(message: str, **data):
            """
            This function will ALWAYS raise an exception, thus it never actually returns, but you
            can still prefix calls to it with "return" if it...
                a) makes PyCharm happier,
                b) makes your code look better, or
                c) makes you feel better about your life.
            """
            flask.abort(400, response=json_response(status=message, **data))

        def _get_value_from_form(field: str, constructor):
            if field not in flask.request.form:
                return json_bad_request("Missing " + field)
            try:
                value = constructor(flask.request.form[field])
            except (ValueError, utils.JSONDecodeError):
                return json_bad_request("Invalid " + field)
            return value

        def get_uuid_from_form(field: str):
            return _get_value_from_form(field, uuid.UUID)

        def get_int_from_form(field: str):
            return _get_value_from_form(field, int)

        def get_json_form_field(field: str):
            return _get_value_from_form(field, utils.from_json)

        ###########################################################################################
        # Flask routes

        @app.route("/gradefast/")
        def _gradefast_():
            return flask.redirect(flask.url_for("_gradefast_gradebook_HTM"))

        @app.route("/gradefast/gradebook/")
        def _gradefast_gradebook_():
            return flask.redirect(flask.url_for("_gradefast_gradebook_HTM"))

        # GradeBook page (yes, the HTM is solely for trolling, teehee)
        @app.route("/gradefast/gradebook.HTM")
        def _gradefast_gradebook_html():
            client_id = uuid.uuid4()
            self._client_ids.add(client_id)
            return flask.render_template(
                "gradebook.html",
                client_id=utils.to_json(client_id),
                initial_list=utils.to_json([]),
                initial_submission_id=utils.to_json(self._current_submission_id),
                is_done=utils.to_json(self.is_done),
                # TODO: implement (from YAML file)
                check_hint_range=utils.to_json(False))

        # Grades CSV file
        @app.route("/gradefast/grades.csv")
        def _gradefast_grades_csv():
            check_uuid_key("data_key", self._client_data_keys)
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
            check_uuid_key("data_key", self._client_data_keys)

            return flask.Response(self._get_json(), mimetype="application/json")

        # Log page
        @app.route("/gradefast/log/<submission_id>")
        def _gradefast_log__(submission_id):
            # TODO: This endpoint is INSECURE
            # TODO: Integrate this into the normal JS client, and fetch the logs via AJAX instead
            grade = self.get_grade(submission_id)
            if grade is None:
                flask.abort(404)
            else:
                return flask.render_template(
                    "log.html",
                    title="Log for %s" % grade.name,
                    content=grade.log
                )

        # AJAX endpoint to request update and data keys
        # (can only be called once per client ID)
        @app.route("/gradefast/_auth", methods=["POST"])
        def _gradefast_auth():
            client_id = get_uuid_from_form("client_id")
            if client_id not in self._client_ids:
                return json_bad_request("Unknown client ID")

            # Make sure this client_id hasn't already requested keys
            if client_id in self._authenticated_client_ids:
                return json_bad_request("Client already authenticated")

            device = flask.request.form.get("device", "unknown device")

            # TODO: Either check for a password in the request (if one was specified in the YAML
            # file), or prompt the user (with "device") to make sure it's okay.
            # For now, just do this:
            # (although note in the future that this will probably happen from another thread)
            self.client_is_authenticated(client_id)

            return json_response(status="Aight")

        # AJAX endpoint to update grades based on an action
        @app.route("/gradefast/_update", methods=["POST"])
        def _gradefast_update():
            try:
                client_id = get_uuid_from_form("client_id")
                if client_id not in self._client_ids:
                    return json_bad_request("Unknown client ID")
                if client_id not in self._authenticated_client_ids:
                    return json_bad_request("Client not authenticated")

                update_key = get_uuid_from_form("update_key")
                if self._client_update_keys[client_id] != update_key:
                    return json_bad_request("Invalid update key")

                client_seq = get_int_from_form("client_seq")
                submission_id = get_int_from_form("submission_id")
                action = get_json_form_field("action")

                # Parse the action into a ClientActionEvent (may raise BadSubmissionException)
                action_event = events.ClientActionEvent(
                    submission_id, client_id, client_seq, action)

                # Apply the action (this will send an update through the events stream).
                # This may raise BadActionException, BadPathException, or BadValueException
                self.apply_event(action_event)

                # If nothing threw, return that we processed everything successfully
                return json_response(status="Aight")

            except events.ActionEvent.BadSubmissionException:
                return json_bad_request("Invalid submission")

            except events.ClientActionEvent.BadActionException:
                return json_bad_request("Invalid action")

            except grades.BadPathException:
                return json_bad_request("Invalid path")

            except grades.BadValueException:
                return json_bad_request("Invalid value")

            except Exception as ex:
                utils.print_error("GRADEBOOK ERROR: Unknown exception (%s) in _update handler"
                                  % str(ex),
                                  print_traceback=True)
                return json_bad_request(
                    "Look what you did... (seriously, look in the server error console)")

        # Event stream
        @app.route("/gradefast/_events")
        def _gradefast_events():
            try:
                client_id = uuid.UUID(flask.request.args["client_id"])
            except ValueError:
                return flask.abort(400)

            if client_id not in self._client_ids:
                return flask.abort(401)

            def gen():
                update_queue = queue.Queue(999)
                self._client_update_queues[client_id] = update_queue
                # Some browsers need an initial kick to fire the "open" event on the EventSource
                update_queue.put(events.ClientUpdate("hello", requires_authentication=False))
                try:
                    while True:
                        client_update = update_queue.get()
                        if client_update.requires_authentication():
                            if client_id not in self._authenticated_client_ids:
                                continue

                        yield client_update.encode()

                except GeneratorExit:
                    pass
                finally:
                    if self._client_update_queues[client_id] is update_queue:
                        del self._client_update_queues[client_id]
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

        # Make sure that only one event is being applied at once, and that nobody is trying to
        # export the grades while we're applying changes.
        with self._event_lock:
            # Run the event on this GradeBook
            client_update = event.apply(self)

            # If the event resulted in a client update, send that to all authenticated GradeBook
            # JavaScript clients
            if client_update:
                assert isinstance(client_update, events.ClientUpdate)
                for client_id in self._authenticated_client_ids:
                    if client_id in self._client_update_queues:
                        try:
                            self._client_update_queues[client_id].put_nowait(client_update)
                        except queue.Full:
                            utils.print_error("GRADEBOOK WARNING: Client", client_id,
                                              "event queue is full")

    def client_is_authenticated(self, client_id: uuid.UUID):
        """
        Indicate that a client ID is now authenticated.
        """
        assert client_id not in self._authenticated_client_ids
        assert client_id not in self._client_data_keys
        assert client_id not in self._client_update_keys

        self._authenticated_client_ids.add(client_id)
        self._client_data_keys[client_id] = uuid.uuid4()
        self._client_update_keys[client_id] = uuid.uuid4()

        self._client_update_queues[client_id].put(events.ClientUpdate("auth", {
            "data_key": self._client_data_keys[client_id],
            "update_key": self._client_update_keys[client_id]
        }))

    def start_submission(self, submission_id: int, name: str):
        """
        Set a submission ID to be the current submission ID.

        This should only be called from a GradeBookEvent applied through the GradeBook apply_event
        method to ensure thread safety.

        :param submission_id: The ID of the submission.
        :param name: The name of the owner of the submission.
        """
        # Make a new Grade object for this submission
        if submission_id not in self._grades_by_submission:
            self._grades_by_submission[submission_id] = grades.SubmissionGrade(
                name, self._grade_structure)
        self._current_submission_id = submission_id

    def log_submission(self, log: str):
        """
        Add log info for the current submission.

        This should only be called from a GradeBookEvent applied through the GradeBook apply_event
        method to ensure thread safety.

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

        # Make sure that no events are applied while we are generating the grade list, ensuring
        # that everything is consistent. (For simplicity, we also build up the entire list and then
        # return it, instead of trying using a generator with the event lock.)
        with self._event_lock:
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
        return utils.to_json(self.get_grades())

    def run(self, hostname: str, port: int, log_level: Union[str, int] = logging.WARNING,
            debug: bool = False):
        """
        Start the Flask server (using Werkzeug internally).

        :param hostname: The hostname to run on
        :param port: The port to run on
        :param log_level: The level at which to set the Werkzeug logger
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
