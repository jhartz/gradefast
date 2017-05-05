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
from typing import Callable, Dict, Iterable, List, Set, TypeVar, cast

from iochannels import MemoryLog
from pyprovide import inject

from gradefast import events, required_package_error
from gradefast.gradebook import eventhandlers, grades, utils
from gradefast.log import get_logger
from gradefast.models import Settings, Submission

try:
    import flask
except ImportError:
    flask = None
    required_package_error("flask")

_logger = get_logger("gradebook")

T = TypeVar("T")


class ClientUpdate:
    """
    Represents an event that the GradeBook server is sending to GradeBook clients.
    """

    _last_id = 0

    def __init__(self, event: str, data: object = None,
                 requires_authentication: bool = True) -> None:
        """
        Create a new ClientUpdate to send to GradeBook clients.

        :param event: The name of the update
        :param data: The data associated with this update (will be json-encoded if it's not a
            string)
        :param requires_authentication: Whether this update should only be sent to authenticated
            clients
        """
        self._event = event
        self._data = data if isinstance(data, str) else utils.to_json(data)
        self._requires_authentication = requires_authentication

        ClientUpdate._last_id += 1
        self._id = ClientUpdate._last_id

    @staticmethod
    def create_update_event(update_type: str, update_data: dict = None) -> "ClientUpdate":
        """
        Create a new ClientUpdate containing an "update" event to send to GradeBook clients.

        :param update_type: The type of "update" event (see connection.js).
        :param update_data: Data corresponding with this type.
        :return: An instance of ClientUpdate
        """
        return ClientUpdate("update", {
            "update_type": update_type,
            "update_data": update_data or {}
        })

    def requires_authentication(self) -> bool:
        return self._requires_authentication

    def encode(self) -> str:
        """
        Return the event in the HTML5 Server-Sent Events format.

        https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events
        """
        if not self._data:
            return ""

        result = ""
        result += "id: " + str(self._id) + "\n"
        if self._event:
            result += "event: " + str(self._event) + "\n"
        result += "data: " + "\ndata:".join(str(self._data).split("\n"))
        result += "\n\n"
        return result


class GradeBook:
    """
    Represents a grade book with submissions and grade structures.
    """

    @inject()
    def __init__(self, event_manager: events.EventManager, settings: Settings) -> None:
        """
        Create a WSGI app representing a grade book.

        A grade structure is a list of grade items (grade scores and grade sections). For more, see
        the GradeFast wiki: https://github.com/jhartz/gradefast/wiki/Grade-Structure
        """
        self.settings = settings

        # Register our event handlers with the event manager
        self.event_lock = threading.Lock()
        self.event_manager = event_manager
        event_manager.register_all_event_handlers_with_args(eventhandlers, gradebook_instance=self)

        self._grades_by_submission_id = {}  # type: Dict[int, grades.SubmissionGrade]
        self._current_submission_id = None  # type: int
        self._submission_list = []  # type: List[Submission]
        self.is_done = False

        # Each instance of the GradeBook client is given its own unique ID (a UUID).
        # They are stored in these sets.
        self._client_ids = set()  # type: Set[uuid.UUID]
        self._authenticated_client_ids = set()  # type: Set[uuid.UUID]

        # When we send out an AuthRequestedEvent for a client, store the event ID here so we can
        # handle the corresponding AuthGrantedEvent when it comes.
        self._auth_event_id_to_client_id = {}  # type: Dict[int, uuid.UUID]

        # When a client accesses the events stream, it has an "update queue" (a Queue that update
        # events are sent to).
        self._client_update_queues = {}  # type: Dict[uuid.UUID, queue.Queue]

        # Secret key used by the client and any other integrations for accessing downloadables
        # (CSV and JSON).
        # This is sent to the client through the client's events stream after authentication.
        self._data_keys = set()  # type: Set[uuid.UUID]

        # Secret key used by the client to access the events stream
        # (mapping an events key to a client ID).
        # This is included in the client's HTML page when it is loaded.
        self._events_keys = {}  # type: Dict[uuid.UUID, uuid.UUID]

        # Secret key used by the client for sending updates to the _update AJAX endpoint
        # (mapping a client ID to an update key).
        # This is sent to the client through the client's events stream after authentication.
        self._client_update_keys = {}  # type: Dict[uuid.UUID, uuid.UUID]

        # Set up MIME type for JS source map
        mimetypes.add_type("application/json", ".map")

    def run(self, debug: bool = False) -> None:
        """
        Start the Flask server (using Werkzeug internally).

        :param debug: Whether to start the server in debug mode (includes tracebacks with HTTP 500
            error pages)
        """
        _logger.info("Starting Flask app")
        app = flask.Flask(__name__)

        # Initialize the routes for the app
        self._init_routes(app)

        # Start the server
        kwargs = {
            "threaded": True,
            "use_reloader": False
        }
        if debug:
            kwargs["debug"] = True
            kwargs["use_reloader"] = False

        _logger.info("Running Flask app")
        app.run(self.settings.host, self.settings.port, **kwargs)

    def _init_routes(self, app: flask.Flask) -> None:
        """
        Initialize the routes for the GradeBook Flask app.
        """
        ###########################################################################################
        # Helper functions for Flask routes

        def check_data_key() -> None:
            try:
                key = uuid.UUID(flask.request.args["data_key"])
                if key not in self._data_keys:
                    flask.abort(401)
            except ValueError:
                flask.abort(400)

        def json_response(flask_response_args: Dict[str, object] = None,
                          **data: object) -> flask.Response:
            kwargs = flask_response_args or {}  # type: Dict[str, object]
            return flask.Response(utils.to_json(data),
                                  mimetype="application/json",
                                  **kwargs)

        def json_aight() -> flask.Response:
            return json_response(status="Aight")

        def json_bad_request(status: str, **data: object) -> flask.Response:
            return json_response(flask_response_args={"status": 400}, status=status, **data)

        def _get_value_from_form(field: str, constructor: Callable[[str], T]) -> T:
            # flask.abort will raise an exception (so the "raise" here does nothing but satisfy
            # type checkers)
            if field not in flask.request.form:
                raise flask.abort(json_bad_request("Missing " + field))
            try:
                value = constructor(flask.request.form[field])
            except (ValueError, utils.JSONDecodeError):
                raise flask.abort(json_bad_request("Invalid " + field))
            return value

        def get_uuid_from_form(field: str) -> uuid.UUID:
            return _get_value_from_form(field, uuid.UUID)

        def get_int_from_form(field: str) -> int:
            return _get_value_from_form(field, int)

        def get_json_form_field(field: str) -> object:
            return _get_value_from_form(field, utils.from_json)

        ###########################################################################################
        # Flask routes

        @app.route("/gradefast/")
        def _gradefast_() -> flask.Response:
            return flask.redirect(flask.url_for("_gradefast_gradebook_html"))

        @app.route("/gradefast/gradebook/")
        def _gradefast_gradebook_() -> flask.Response:
            return flask.redirect(flask.url_for("_gradefast_gradebook_html"))

        # GradeBook page (yes, the ".HTM" is solely for trolling, teehee)
        @app.route("/gradefast/gradebook.HTM")
        def _gradefast_gradebook_html() -> flask.Response:
            client_id = uuid.uuid4()
            events_key = uuid.uuid4()
            self._client_ids.add(client_id)
            self._events_keys[events_key] = client_id
            return flask.render_template(
                "gradebook.html",
                client_id=utils.to_json(client_id),
                events_key=utils.to_json(events_key),
                markdown_msg=utils.to_json("(Markdown-parsed)" if grades.has_markdown else None))

        # Grades CSV export
        @app.route("/gradefast/grades.csv")
        def _gradefast_grades_csv() -> flask.Response:
            check_data_key()
            _logger.debug("Generating CSV export")

            csv_stream = io.StringIO()
            csv_writer = csv.writer(csv_stream)

            # Make the header row
            point_titles = grades.get_point_titles(self.settings.grade_structure)
            csv_writer.writerow(
                ["Name", "Total Score", "Percentage", "Feedback", ""] +
                ["({}) {}".format(points, title) for title, points in point_titles])

            # Make the value rows
            for grade in self._get_grades_export():
                csv_writer.writerow(
                    [grade["name"], grade["score"], grade["percentage"], grade["feedback"], ""] +
                    ["" if title not in grade else grade[title] for title, _ in point_titles])

            return flask.Response(csv_stream.getvalue(), mimetype="text/csv", headers={
                "Content-disposition": "attachment; filename=\"{}.csv\"".format(
                    # Quick-and-hacky filename escaping; replaces backslashes with forward flashes,
                    # and escapes double quotes
                    self.settings.project_name.replace("\\", "/").replace('"', '\\"'))
            })

        # Grades JSON export
        @app.route("/gradefast/grades.json")
        def _gradefast_grades_json() -> flask.Response:
            check_data_key()
            _logger.debug("Generating JSON export")
            return flask.Response(utils.to_json(self._get_grades_export()),
                                  mimetype="application/json")

        # Log page (HTML)
        @app.route("/gradefast/log/<submission_id>.html")
        def _gradefast_log_html(submission_id: str) -> flask.Response:
            check_data_key()
            try:
                grade = self._grades_by_submission_id[int(submission_id)]
            except (ValueError, IndexError):
                raise flask.abort(404)

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
        def _gradefast_log_txt(submission_id: str) -> flask.Response:
            check_data_key()
            try:
                grade = self._grades_by_submission_id[int(submission_id)]
            except (ValueError, IndexError):
                raise flask.abort(404)

            def gen() -> Iterable[str]:
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
        def _gradefast_auth() -> flask.Response:
            client_id = get_uuid_from_form("client_id")
            if client_id not in self._client_ids:
                return json_bad_request("Unknown client ID")

            # Make sure this client_id hasn't already requested keys
            if client_id in self._authenticated_client_ids:
                return json_bad_request("Client already authenticated")

            device = flask.request.form.get("device", "unknown device")
            event = events.AuthRequestedEvent("device: " + device)
            auth_event_id = event.event_id  # type: int

            _logger.debug("Client {} requesting auth (event {}); device: {}",
                          client_id, auth_event_id, device)
            self._auth_event_id_to_client_id[auth_event_id] = client_id
            self.event_manager.dispatch_event(event)

            return json_aight()

        # AJAX endpoint to update grades based on an action
        @app.route("/gradefast/_update", methods=["POST"])
        def _gradefast_update() -> flask.Response:
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
                action = get_json_form_field("action")  # type: Dict[str, object]

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
        def _gradefast_events() -> flask.Response:
            try:
                events_key = uuid.UUID(flask.request.args["events_key"])
            except ValueError:
                return flask.abort(400)
            if events_key not in self._events_keys:
                return flask.abort(401)
            client_id = self._events_keys[events_key]
            _logger.debug("Client {} connected to _events", client_id)

            def gen() -> Iterable[str]:
                update_queue = queue.Queue(999)  # type: queue.Queue
                self._client_update_queues[client_id] = update_queue
                # Some browsers need an initial kick to fire the "open" event on the EventSource
                update_queue.put(ClientUpdate("hello", requires_authentication=False))
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

    def _get_submission_list(self) -> List[Dict[str, object]]:
        """
        Get the current list of submissions, with each submission represented by its "simple data"
        format.
        """
        return [self._grades_by_submission_id[s.id].to_simple_data() for s in self._submission_list]

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
                grade_details = OrderedDict()  # type: Dict[str, object]
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

    def _send_client_update(self, client_update: ClientUpdate, client_id: uuid.UUID = None) -> None:
        """
        Send a ClientUpdate to either a specific GradeBook client or to all open, authenticated
        GradeBook clients.

        :param client_update: The update to send.
        :param client_id: The ID of the client to send to. If this is None, then send to all
            clients.
        """
        assert isinstance(client_update, ClientUpdate)

        if client_id is None:
            client_ids = self._authenticated_client_ids
        else:
            client_ids = {client_id}

        for client_id in client_ids:
            if client_id in self._client_update_queues:
                try:
                    self._client_update_queues[client_id].put_nowait(client_update)
                except queue.Full:
                    _logger.warning("Client {} event queue is full", client_id)

    def auth_granted(self, auth_event_id: int) -> None:
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
        self._send_client_update(ClientUpdate("auth", {
            "data_key": data_key,
            "update_key": self._client_update_keys[client_id],
            "initial_submission_list": self._get_submission_list(),
            "initial_submission_id": self._current_submission_id,
            "is_done": self.is_done
        }), client_id)

    def set_submission_list(self, submission_list: List[Submission]) -> None:
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
        self._send_client_update(ClientUpdate.create_update_event("NEW_SUBMISSION_LIST", {
            "submissions": self._get_submission_list()
        }))

    def set_current_submission(self, submission_id: int, html_log: MemoryLog,
                               text_log: MemoryLog) -> None:
        """
        Set a submission ID to be the current submission ID, and add new html/text logs for it.

        :param submission_id: The ID of the submission.
        :param html_log: A new HTMLMemoryLog that will be written to as the submission is graded.
        :param text_log: A new MemoryLog that will be written to as the submission is graded.
        """
        assert submission_id in self._grades_by_submission_id
        self._current_submission_id = submission_id
        self._grades_by_submission_id[submission_id].append_logs(html_log, text_log)

        # Tell GradeBook clients about this change in the current submission
        # (include the list of submissions so the clients have an updated idea of who has a log)
        self._send_client_update(ClientUpdate.create_update_event("SUBMISSION_STARTED", {
            "submissions": self._get_submission_list(),
            "submission_id": submission_id
        }))

    def set_done(self, is_done: bool) -> None:
        """
        Set whether we are done grading.
        """
        self.is_done = is_done

        # Tell GradeBook clients that we're done
        self._send_client_update(ClientUpdate.create_update_event("END_OF_SUBMISSIONS"))

    def _parse_action(self, submission_id: int, client_id: uuid.UUID, client_seq: int,
                      action: Dict[str, object]) -> None:
        """
        Parse and apply an action received from a GradeBook client.

        :param submission_id: The ID of the submission that this action applies to.
        :param client_id: The ID of the GradeBook client that submitted this action event.
        :param client_seq: The sequence number from the GradeBook client that submitted this event.
        :param action: The action, directly from the GradeBook client that submitted it.
        """
        try:
            grade = self._grades_by_submission_id[submission_id]
        except IndexError:
            raise utils.GradeBookPublicError("Invalid submission ID: {}".format(submission_id))
        self._apply_action_to_grade(grade, action)

        # Recalculate the score, etc., and tell clients
        data = grade.to_plain_data()
        data.update({
            "submission_id": submission_id,
            "originating_client_id": client_id,
            "originating_client_seq": client_seq
        })
        self._send_client_update(ClientUpdate.create_update_event("SUBMISSION_UPDATED", data))

        # Also update the submission list (so clients get the new overall scores)
        self._send_client_update(ClientUpdate.create_update_event("NEW_SUBMISSION_LIST", {
            "submissions": self._get_submission_list()
        }))

    @staticmethod
    def _apply_action_to_grade(grade: grades.SubmissionGrade, action: Dict[str, object]) -> None:
        action_type = action["type"] if "type" in action else None

        # It's possible we have no actual action to take, and that's okay
        if not action_type:
            return

        if action_type == "SET_LATE":
            # Set whether the submission is marked as late
            if "is_late" in action:
                grade.set_late(bool(action["is_late"]))
                return

        if action_type == "SET_OVERALL_COMMENTS":
            # Set the overall comments of the submission
            if "overall_comments" in action:
                grade.set_overall_comments(str(action["overall_comments"]))
                return

        # All of the other action types have a path
        if "path" not in action:
            raise utils.GradeBookPublicError("Action missing a path", action=action)
        try:
            path = [int(p) for p in cast(List[int], action["path"])]
        except (TypeError, ValueError) as ex:
            raise utils.BadPathError("Error parsing path {}".format(action["path"]), exception=ex)

        if action_type == "ADD_HINT":
            # Add a hint by changing the grade structure (MUA HA HA HA)
            if "content" in action and \
                    "name" in action["content"] and "value" in action["content"]:
                grade.add_hint_to_all_grades(path,
                                             action["content"]["name"],
                                             action["content"]["value"])
                return

        if action_type == "EDIT_HINT":
            # Edit a hint by changing the grade structure (MUA HA HA HA)
            if "index" in action and "content" in action and \
                    "name" in action["content"] and "value" in action["content"]:
                try:
                    index = int(cast(int, action["index"]))
                except ValueError as ex:
                    raise utils.BadPathError("Invalid hint index \"{}\" at path {}"
                                             .format(action["index"], path), exception=ex)
                grade.replace_hint_for_all_grades(path,
                                                  index,
                                                  action["content"]["name"],
                                                  action["content"]["value"])
                return

        # All of the rest of the action types operate directly on a grade item
        grade_item = grade.get_by_path(path)

        # They also all have a value
        if "value" not in action:
            raise utils.GradeBookPublicError("Action missing a value", action=action)
        value = action["value"]

        if action_type == "SET_ENABLED":
            grade_item.set_enabled(bool(value))
            return

        if action_type == "SET_SCORE":
            if isinstance(grade_item, grades.SubmissionGradeScore):
                grade_item.set_effective_score(str(value))
                return

        if action_type == "SET_COMMENTS":
            if isinstance(grade_item, grades.SubmissionGradeScore):
                grade_item.set_comments(str(value))
                return

        if action_type == "SET_HINT_ENABLED" and "index" in action:
            try:
                index = int(cast(int, action["index"]))
                grade_item.set_hint_enabled(index, bool(value))
                return
            except (ValueError, IndexError) as ex:
                raise utils.BadPathError("Invalid hint index \"{}\" at path {}"
                                         .format(action["index"], path), exception=ex)

        # If we're still here, something went wrong...
        raise utils.GradeBookPublicError("Action does not have a valid type", action=action)
