"""
The GradeBook HTTP server.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import csv
import io
import mimetypes
import queue
import threading
import time
import uuid
from collections import OrderedDict
from typing import Dict, List, Optional, Set, Union

from iochannels import MemoryLog
from pyprovide import inject

from gradefast import events, required_package_error
from gradefast.gradebook import clients, eventhandlers, grades, utils
from gradefast.log import get_logger
from gradefast.models import Settings, Submission

try:
    import flask
except ImportError:
    flask = None
    required_package_error("flask")

_logger = get_logger("gradebook")


class GradeBook:
    """
    Represents a grade book with submissions and grade structures.
    """

    @inject()
    def __init__(self, event_manager: events.EventManager, settings: Settings):
        """
        Create a WSGI app representing a grade book.

        A grade structure is a list of grade items (grade scores and grade sections). For more, see
        the GradeFast wiki: https://github.com/jhartz/gradefast/wiki/Grade-Structure
        """
        self.settings: Settings = settings

        # Register our event handlers with the event manager
        self.event_lock = threading.Lock()
        self.event_manager: events.EventManager = event_manager
        event_manager.register_all_event_handlers_with_args(eventhandlers, gradebook_instance=self)

        self._grades_by_submission_id: Dict[int, grades.SubmissionGrade] = {}
        self._current_submission_id: Optional[int] = None
        self._submission_list: List[Submission] = []
        self.is_done: bool = False

        # Each instance of the GradeBook client is given its own unique ID (a UUID).
        # They are stored in these sets.
        self._client_ids: Set[uuid.UUID] = set()
        self._authenticated_client_ids: Set[uuid.UUID] = set()

        # When we send out an AuthRequestedEvent for a client, store the event ID here so we can
        # handle the corresponding AuthGrantedEvent when it comes.
        self._auth_event_id_to_client_id = {}

        # When a client accesses the events stream, it has an "update queue" (a Queue that update
        # events are sent to).
        self._client_update_queues: Dict[uuid.UUID, queue.Queue] = {}

        # Secret key used by the client and any other integrations for accessing downloadables
        # (CSV and JSON).
        # This is sent to the client through the client's events stream after authentication.
        self._data_keys: Set[uuid.UUID] = set()

        # Secret key used by the client to access the events stream
        # (mapping an events key to a client ID).
        # This is included in the client's HTML page when it is loaded.
        self._events_keys: Dict[uuid.UUID, uuid.UUID] = {}

        # Secret key used by the client for sending updates to the _update AJAX endpoint
        # (mapping a client ID to an update key).
        # This is sent to the client through the client's events stream after authentication.
        self._client_update_keys: Dict[uuid.UUID, uuid.UUID] = {}

        # Set up MIME type for JS source map
        mimetypes.add_type("application/json", ".map")

        # Set up Flask app
        _logger.info("Initializing Flask app")
        app = flask.Flask(__name__)
        self._app = app

        ###########################################################################################
        # Helper functions for Flask routes

        def check_data_key():
            try:
                key = uuid.UUID(flask.request.args["data_key"])
                if key not in self._data_keys:
                    flask.abort(401)
            except ValueError:
                flask.abort(400)

        def json_response(flask_response_args: Optional[dict] = None, **data) -> flask.Response:
            kwargs: dict = flask_response_args or {}
            return flask.Response(utils.to_json(data),
                                  mimetype="application/json",
                                  **kwargs)

        def json_aight() -> flask.Response:
            return json_response(status="Aight")

        def json_bad_request(status: str, **data) -> flask.Response:
            return json_response(flask_response_args={"status": 400}, status=status, **data)

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
            return flask.redirect(flask.url_for("_gradefast_gradebook_html"))

        @app.route("/gradefast/gradebook/")
        def _gradefast_gradebook_():
            return flask.redirect(flask.url_for("_gradefast_gradebook_html"))

        # GradeBook page (yes, the HTM is solely for trolling, teehee)
        @app.route("/gradefast/gradebook.HTM")
        def _gradefast_gradebook_html():
            client_id = uuid.uuid4()
            events_key = uuid.uuid4()
            self._client_ids.add(client_id)
            self._events_keys[events_key] = client_id
            return flask.render_template(
                "gradebook.html",
                client_id=utils.to_json(client_id),
                events_key=utils.to_json(events_key),
                markdown_msg=utils.to_json("(Markdown-parsed)" if grades.has_markdown else None))

        # Grades CSV file
        @app.route("/gradefast/grades.csv")
        def _gradefast_grades_csv():
            check_data_key()
            _logger.debug("Generating CSV export")
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
            filename_param = 'filename="{}.csv"'.format(
                self.settings.project_name.replace("\\", "").replace('"', '\\"'))
            resp.headers["Content-disposition"] = "attachment; " + filename_param
            return resp

        # Grades JSON file
        @app.route("/gradefast/grades.json")
        def _gradefast_grades_json():
            check_data_key()
            _logger.debug("Generating JSON export")
            return flask.Response(self._get_json(), mimetype="application/json")

        # Log page (HTML)
        @app.route("/gradefast/log/<submission_id>.html")
        def _gradefast_log_html(submission_id):
            check_data_key()
            grade = self.get_grade(submission_id)
            if grade is None:
                flask.abort(404)
            else:
                content_html = "\n\n\n<hr>\n\n\n\n".join(
                    "{}\n\n{}\n\n{}\n\n".format(
                        "Started: " + time.asctime(time.localtime(log.open_timestamp)),
                        log.get_content(),
                        "Finished: " + time.asctime(time.localtime(log.close_timestamp))
                        if log.close_timestamp else "..."
                    )
                    for log in grade.get_html_logs()
                )
                return flask.render_template(
                    "log.html",
                    title="Log for {}".format(grade.submission.name),
                    content_html=content_html
                )

        # Log page (plain text)
        @app.route("/gradefast/log/<submission_id>.txt")
        def _gradefast_log_txt(submission_id):
            check_data_key()
            grade = self.get_grade(submission_id)
            if grade is None:
                flask.abort(404)
            else:
                def gen():
                    yield "Log for {}\n".format(grade.submission.name)
                    for log in grade.get_text_logs():
                        yield "\n" + "=" * 79 + "\n"
                        yield time.asctime(time.localtime(log.open_timestamp))
                        if log.close_timestamp:
                            yield " - "
                            yield time.asctime(time.localtime(log.close_timestamp))
                        yield "\n\n"
                        yield log.get_content()
                        yield "\n"
                return flask.Response(gen(), mimetype="text/plain")

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
            event = events.AuthRequestedEvent("device: " + device)
            _logger.debug("Client {} requesting auth (event {}); device: {}",
                          client_id, event.event_id, device)
            self._auth_event_id_to_client_id[event.event_id] = client_id
            self.event_manager.dispatch_event(event)

            return json_aight()

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

                # Parse the action and apply it (may raise a subclass of GradeBookPublicError)
                self._parse_action(submission_id, client_id, client_seq, action)

                # If nothing threw, return that we processed everything successfully
                return json_aight()

            except utils.GradeBookPublicError as err:
                return json_bad_request("GradeBook Error", **err.get_details())

            except:
                _logger.exception("Non-public exception in _update handler")
                return json_bad_request(
                    "Look what you did... (seriously, look in the server error console)")

        # Event stream
        @app.route("/gradefast/_events")
        def _gradefast_events():
            try:
                events_key = uuid.UUID(flask.request.args["events_key"])
            except ValueError:
                return flask.abort(400)
            if events_key not in self._events_keys:
                return flask.abort(401)
            client_id = self._events_keys[events_key]
            _logger.debug("Client {} connected to _events", client_id)

            def gen():
                update_queue = queue.Queue(999)
                self._client_update_queues[client_id] = update_queue
                # Some browsers need an initial kick to fire the "open" event on the EventSource
                update_queue.put(clients.ClientUpdate("hello", requires_authentication=False))
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

        if submission_id not in self._grades_by_submission_id:
            return None
        return self._grades_by_submission_id[submission_id]

    def get_submission_list(self):
        """
        Get the current list of submissions, with each submission represented by its "simple data"
        format.
        """
        return list(map(lambda s: self.get_grade(s.id).to_simple_data(), self._submission_list))

    def _send_client_update(self, client_update: clients.ClientUpdate, client_id: uuid.UUID = None):
        """
        Send a ClientUpdate to either a specific GradeBook client or to all open, authenticated
        GradeBook clients.

        :param client_update: The update to send.
        :param client_id: The ID of the client to send to. If this is None, then send to all
            clients.
        """
        assert isinstance(client_update, clients.ClientUpdate)

        if client_id is None:
            client_ids = self._authenticated_client_ids
        else:
            client_ids = [client_id]

        for client_id in client_ids:
            if client_id in self._client_update_queues:
                try:
                    self._client_update_queues[client_id].put_nowait(client_update)
                except queue.Full:
                    _logger.warning("Client {} event queue is full", client_id)

    def auth_granted(self, auth_event_id: int):
        """
        Indicate that a client ID is now authenticated, identified by the event ID of the original
        AuthRequestEvent that was sent out.
        """
        client_id = self._auth_event_id_to_client_id[auth_event_id]
        assert client_id not in self._authenticated_client_ids
        assert client_id not in self._client_update_keys
        _logger.debug("Authentication granted to client {} (event {})", client_id, auth_event_id)

        self._authenticated_client_ids.add(client_id)
        data_key = uuid.uuid4()
        self._data_keys.add(data_key)
        self._client_update_keys[client_id] = uuid.uuid4()

        # Send the client its auth keys
        self._send_client_update(clients.ClientUpdate("auth", {
            "data_key": data_key,
            "update_key": self._client_update_keys[client_id],
            "initial_submission_list": self.get_submission_list(),
            "initial_submission_id": self._current_submission_id,
            "is_done": self.is_done
        }), client_id)

    def set_submission_list(self, submission_list: List[Submission]):
        """
        Set a new submission list.
        """
        self._submission_list = submission_list

        # Make new SubmissionGrade objects for any submissions that we haven't seen before
        for submission in submission_list:
            if submission.id not in self._grades_by_submission_id:
                self._grades_by_submission_id[submission.id] = grades.SubmissionGrade(
                    submission, self.settings.grade_structure)

        # Tell GradeBook clients about this new list
        self._send_client_update(clients.ClientUpdate.create_update_event("NEW_SUBMISSION_LIST", {
            "submissions": self.get_submission_list()
        }))

    def set_current_submission(self, submission_id: int, html_log: MemoryLog, text_log: MemoryLog):
        """
        Set a submission ID to be the current submission ID, and add new html/text logs for it.

        :param submission_id: The ID of the submission.
        :param html_log: A new HTMLMemoryLog that will be written to as the submission is graded.
        :param text_log: A new MemoryLog that will be written to as the submission is graded.
        """
        assert submission_id in self._grades_by_submission_id
        self._current_submission_id = submission_id
        self.get_grade(submission_id).append_logs(html_log, text_log)

        # Tell GradeBook clients about this change in the current submission
        # (include the list of submissions so the clients have an updated idea of who has a log)
        self._send_client_update(clients.ClientUpdate.create_update_event("SUBMISSION_STARTED", {
            "submissions": self.get_submission_list(),
            "submission_id": submission_id
        }))

    def set_done(self, is_done: bool):
        """
        Set whether we are done grading.
        """
        self.is_done = is_done

        # Tell GradeBook clients that we're done
        self._send_client_update(clients.ClientUpdate.create_update_event("END_OF_SUBMISSIONS"))

    def _parse_action(self, submission_id: int, client_id: int, client_seq: int, action: dict):
        """
        Parse and apply an action received from a GradeBook client.

        :param submission_id: The ID of the submission that this action applies to.
        :param client_id: The ID of the GradeBook client that submitted this action event.
        :param client_seq: The sequence number from the GradeBook client that submitted this event.
        :param action: The action, directly from the GradeBook client that submitted it.
        """
        client_action = clients.ClientAction(submission_id, client_id, client_seq, action)
        data = client_action.apply_to_gradebook(self)
        self._send_client_update(
            clients.ClientUpdate.create_update_event("SUBMISSION_UPDATED", data))

        # Also update the submission list (to get the new scores, etc.)
        self._send_client_update(clients.ClientUpdate.create_update_event("NEW_SUBMISSION_LIST", {
            "submissions": self.get_submission_list()
        }))

    def _get_grades_export(self) -> List[OrderedDict]:
        """
        Return a list of ordered dicts representing the scores and feedback for each submission.
        """
        grade_list = []

        # Make sure that no events are applied while we are generating the grade list, ensuring
        # that everything is consistent. (For simplicity, we also build up the entire list and then
        # return it, instead of trying using a generator with the event lock.)
        with self.event_lock:
            for grade in self._grades_by_submission_id.values():
                points_earned, points_possible, individual_points = grade.get_score()
                grade_details = OrderedDict()
                grade_details["name"] = grade.submission.name
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
        point_titles = grades.get_point_titles(self.settings.grade_structure)
        row_titles = ["Name", "Total Score", "Percentage", "Feedback", ""] + \
                     ["({}) {}".format(points, title) for title, points in point_titles]
        csv_writer.writerow(row_titles)

        # Make the value rows
        for grade in self._get_grades_export():
            csv_writer.writerow([
                grade["name"],
                grade["score"],
                grade["percentage"],
                grade["feedback"],
                ""
            ] + ["" if title not in grade else grade[title] for title, _ in point_titles])

        # Return the resulting stream
        csv_stream.seek(0)
        return csv_stream

    def _get_json(self) -> str:
        """
        Return a string representing the grades as JSON.
        """
        return utils.to_json(self._get_grades_export())

    def run(self, debug: bool = False):
        """
        Start the Flask server (using Werkzeug internally).

        :param debug: Whether to start the server in debug mode (includes tracebacks with HTTP 500
            error pages)
        """
        # Start the server
        kwargs = {
            "threaded": True,
            "use_reloader": False
        }
        if debug:
            kwargs["debug"] = True
            kwargs["use_reloader"] = False

        _logger.info("Running Flask app")
        self._app.run(self.settings.host, self.settings.port, **kwargs)
