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
import uuid
from collections import OrderedDict
from typing import Callable, Dict, Iterable, List, Mapping, Set, TypeVar, cast

from pyprovide import inject

from gradefast import events, exceptions, grades, utils
from gradefast.gradebook import eventhandlers
from gradefast.loggingwrapper import get_logger
from gradefast.models import Settings
from gradefast.submissions import SubmissionManager

try:
    import flask
except ImportError:
    flask = None
    utils.required_package_error("flask")

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
    def create_update_event(update_type: str, update_data: object = None) -> "ClientUpdate":
        """
        Create a new ClientUpdate containing an "update" event to send to GradeBook clients.

        :param update_type: The type of "update" event (see connection.js).
        :param update_data: Data corresponding with this type (must be JSON-encodable).
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

        result = "id: " + str(self._id) + "\n"
        if self._event:
            result += "event: " + str(self._event) + "\n"
        for line in str(self._data).splitlines():
            result += "data: " + line + "\n"
        result += "\n"
        return result


class GradeBook:
    """
    Represents a grade book, with a WSGI web app.
    """

    @inject()
    def __init__(self, event_manager: events.EventManager, settings: Settings,
                 submission_manager: SubmissionManager) -> None:
        self.settings = settings
        self.submission_manager = submission_manager

        # Register our event handlers with the event manager
        self.event_lock = threading.Lock()
        self.event_manager = event_manager
        event_manager.register_all_event_handlers(eventhandlers)

        self._current_submission_id = None  # type: int
        self._is_done = False

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

        def json_response(flask_response_args: Mapping[str, object] = None,
                          **data: object) -> flask.Response:
            kwargs = flask_response_args or {}  # type: Mapping[str, object]
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
                markdown_msg=utils.to_json("(Markdown-parsed)" if utils.has_markdown else None))

        # Grades CSV export
        @app.route("/gradefast/grades.csv")
        def _gradefast_grades_csv() -> flask.Response:
            check_data_key()
            _logger.debug("Generating CSV export")

            csv_stream = io.StringIO()
            csv_writer = csv.writer(csv_stream)

            # Make the header row
            csv_writer.writerow(
                ["Name", "Total Score", "Possible Score", "Percentage", "Feedback"])

            # Make the value rows
            for grade in self._get_grades_export(include_all=False):
                csv_writer.writerow([
                    grade["name"],
                    grade["score"],
                    grade["possible_score"],
                    grade["percentage"],
                    grade["feedback"]
                ])

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
            return flask.Response(utils.to_json(self._get_grades_export(include_all=True)),
                                  mimetype="application/json")

        # Log page (HTML)
        @app.route("/gradefast/log/<submission_id>.html")
        def _gradefast_log_html(submission_id: str) -> flask.Response:
            check_data_key()
            try:
                submission = self.submission_manager.get_submission(int(submission_id))
            except (ValueError, IndexError):
                raise flask.abort(404)

            content_html = "\n\n\n<hr>\n\n\n\n".join(
                "{}\n\n{}\n\n{}\n\n".format(
                    "Started: " + utils.timestamp_to_str(log.open_timestamp),
                    log.get_content(),
                    "Finished: " + utils.timestamp_to_str(log.close_timestamp)
                    if log.close_timestamp else "..."
                )
                for log in submission.get_html_logs()
            )
            return flask.render_template(
                "log.html",
                title="Log for {}".format(submission.get_name()),
                content_html=content_html
            )

        # Log page (plain text)
        @app.route("/gradefast/log/<submission_id>.txt")
        def _gradefast_log_txt(submission_id: str) -> flask.Response:
            check_data_key()
            try:
                submission = self.submission_manager.get_submission(int(submission_id))
            except (ValueError, IndexError):
                raise flask.abort(404)

            def gen() -> Iterable[str]:
                yield "Log for {}\n".format(submission.get_name())
                for log in submission.get_text_logs():
                    yield "\n" + "=" * 79 + "\n"
                    yield utils.timestamp_to_str(log.open_timestamp)
                    if log.close_timestamp:
                        yield " - "
                        yield utils.timestamp_to_str(log.close_timestamp)
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

            if self.settings.prompt_for_auth:
                event = events.AuthRequestedEvent("device: " + device)
                auth_event_id = event.event_id  # type: int

                _logger.debug("Client {} requesting auth (event {}); device: {}",
                              client_id, auth_event_id, device)
                self._auth_event_id_to_client_id[auth_event_id] = client_id
                self.event_manager.dispatch_event(event)
            else:
                _logger.info("Client {} automatically granted auth; device {}", client_id, device)
                self._init_client(client_id)

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

            except exceptions.GradeBookPublicError as err:
                return json_bad_request("GradeBook Error", **err.get_details())

            except:
                _logger.exception("Non-public exception in _update handler")
                return json_bad_request(
                    "Look what you did... (seriously, look in the server error console)")

        # AJAX endpoint to trigger a ClientUpdate with refreshed stats
        @app.route("/gradefast/_refresh_stats", methods=["POST"])
        def _gradefast_refresh_stats() -> flask.Response:
            client_id = get_uuid_from_form("client_id")
            if client_id not in self._client_ids:
                return json_bad_request("Unknown client ID")
            if client_id not in self._authenticated_client_ids:
                return json_bad_request("Client not authenticated")

            _logger.debug("Client {} requested stats", client_id)
            self.send_updated_stats(client_id)
            return json_aight()

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

    def _get_grades_export(self, include_all: bool) -> List[OrderedDict]:
        """
        Return a list of ordered dicts representing the scores, feedback, and timing for each
        submission.

        :param include_all: Whether to include extra information (in addition to "name", "score",
            "possible_score", "percentage", and "feedback")
        """
        grade_list = []

        # Make sure that no events are applied while we are generating the grade list, ensuring
        # that everything is consistent. (For simplicity, we also build up the entire list and then
        # return it, instead of trying using a generator with the event lock.)
        with self.event_lock:
            for submission in self.submission_manager.get_all_submissions():
                points_earned, points_possible = submission.get_grade().get_score()
                grade_details = OrderedDict()  # type: Dict[str, object]
                grade_details["name"] = submission.get_name()
                grade_details["score"] = points_earned
                grade_details["possible_score"] = points_possible
                grade_details["percentage"] = 0 if points_possible == 0 else \
                    100 * points_earned / points_possible
                grade_details["feedback"] = submission.get_grade().get_feedback()

                if include_all:
                    grade_details.update(submission.get_grade().get_export_data())

                    times = submission.get_times()
                    if len(times) == 1:
                        grade_details["Started Grading"] = utils.timestamp_to_str(times[0][0])
                        grade_details["Finished Grading"] = utils.timestamp_to_str(times[0][1])
                    elif len(times) > 1:
                        for index, (start, end) in enumerate(times, start=1):
                            grade_details["Started Grading #" + str(index)] = \
                                utils.timestamp_to_str(start)
                            grade_details["Finished Grading #" + str(index)] = \
                                utils.timestamp_to_str(end)

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

    def send_submission_list(self) -> None:
        """
        Send the latest submission list to GradeBook clients.
        """
        self._send_client_update(ClientUpdate.create_update_event("NEW_SUBMISSIONS", {
            "submissions": list(self.submission_manager.get_all_submissions())
        }))

    def send_submission_updated(self, submission_id: int, originating_client_id: uuid.UUID = None,
                                originating_client_seq: int = None) -> None:
        """
        Send a submission's latest grades, comments, etc. after it has been updated to any
        interested GradeBook clients.
        """
        submission = self.submission_manager.get_submission(submission_id)
        data = submission.get_grade().get_data()
        data.update({
            "submission_id": submission_id,
            "originating_client_id": originating_client_id,
            "originating_client_seq": originating_client_seq
        })
        self._send_client_update(ClientUpdate.create_update_event("SUBMISSION_UPDATED", data))

    def send_updated_stats(self, client_id: uuid.UUID = None) -> None:
        """
        Generate and send the latest grading and timing stats to an interested client.
        """
        self._send_client_update(ClientUpdate.create_update_event("UPDATED_STATS", {
            "grading_stats": self.submission_manager.get_grading_stats(),
            "timing_stats": self.submission_manager.get_timing_stats()
        }), client_id)

    def auth_granted(self, auth_event_id: int) -> None:
        """
        Indicate that a client ID is now authenticated, identified by the event ID of the original
        AuthRequestEvent that was sent out.
        """
        client_id = self._auth_event_id_to_client_id[auth_event_id]
        _logger.debug("Authentication granted to client {} (event {})", client_id, auth_event_id)
        self._init_client(client_id)

    def _init_client(self, client_id: uuid.UUID) -> None:
        """
        Initialize a new client, giving it the keys it needs to succeed. (This should only be
        called AFTER a client has been authenticated, and it must only be called ONCE per client.)
        """
        assert client_id not in self._authenticated_client_ids
        assert client_id not in self._client_update_keys
        self._authenticated_client_ids.add(client_id)
        data_key = uuid.uuid4()
        self._data_keys.add(data_key)
        self._client_update_keys[client_id] = uuid.uuid4()

        # Send the client its auth keys
        self._send_client_update(ClientUpdate("auth", {
            "data_key": data_key,
            "update_key": self._client_update_keys[client_id],
            "initial_submission_list": list(self.submission_manager.get_all_submissions()),
            "initial_submission_id": self._current_submission_id,
            "is_done": self._is_done
        }), client_id)

    def set_current_submission(self, submission_id: int) -> None:
        """
        Set a submission ID to be the current submission ID.
        """
        self._current_submission_id = submission_id

        # Tell GradeBook clients about this change in the current submission
        self._send_client_update(ClientUpdate.create_update_event("SUBMISSION_STARTED", {
            "submission_id": submission_id
        }))

    def set_done(self) -> None:
        """
        Set that we are done grading.
        """
        self._is_done = True

        # Tell GradeBook clients that we're done
        self._send_client_update(ClientUpdate.create_update_event("END_OF_SUBMISSIONS"))

    def _parse_action(self, submission_id: int, client_id: uuid.UUID, client_seq: int,
                      action: Mapping[str, object]) -> None:
        """
        Parse and apply an action received from a GradeBook client.

        :param submission_id: The ID of the submission that this action applies to.
        :param client_id: The ID of the GradeBook client that submitted this action event.
        :param client_seq: The sequence number from the GradeBook client that submitted this event.
        :param action: The action, directly from the GradeBook client that submitted it.
        """
        try:
            submission = self.submission_manager.get_submission(submission_id)
        except IndexError:
            raise exceptions.GradeBookPublicError("Invalid submission ID: {}".format(submission_id))
        old_score_tuple = submission.get_grade().get_score()
        self._apply_action_to_grade(submission.get_grade(), action)
        new_score_tuple = submission.get_grade().get_score()

        # Recalculate the score, etc., and tell clients
        self.send_submission_updated(submission_id, client_id, client_seq)

        # If the overall scores changed, update the submission list (so clients get the new overall
        # scores to show in the submission list).
        # NOTE: If a hint was changed, that could affect other submissions' scores, even if it
        # didn't affect us.
        # TODO: Clean this up
        if old_score_tuple != new_score_tuple or action.get("type") == "EDIT_HINT":
            self.send_submission_list()

    @staticmethod
    def _apply_action_to_grade(grade: grades.SubmissionGrade, action: Mapping[str, object]) -> None:
        action_type = action.get("type")

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
            raise exceptions.GradeBookPublicError("Action missing a path", action=action)
        try:
            path = [int(p) for p in cast(List[int], action["path"])]
        except (TypeError, ValueError) as ex:
            raise exceptions.BadPathError("Error parsing path {}".format(action["path"]),
                                          exception=ex)

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
                    raise exceptions.BadPathError("Invalid hint index \"{}\" at path {}"
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
            raise exceptions.GradeBookPublicError("Action missing a value", action=action)
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
                raise exceptions.BadPathError("Invalid hint index \"{}\" at path {}"
                                              .format(action["index"], path), exception=ex)

        # If we're still here, something went wrong...
        raise exceptions.GradeBookPublicError("Action does not have a valid type", action=action)
