"""
Event handlers for events that the GradeBook can handle.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

from gradefast import events
from gradefast.log import get_logger

# All concrete event handlers should be listed here.
# This is used by the register_all_event_handlers method of EventManager.
__all__ = [
    "NewSubmissionListHandler",
    "SubmissionStartedHandler",
    "EndOfSubmissionsHandler",
    "AuthGrantedEventHandler"
]

_logger = get_logger("gradebook.eventhandlers")


class GradeBookEventHandler(events.EventNameHandler):
    """
    An abstract subclass of EventNameHandler for GradeBook event handlers.

    When an event is dispatched by the event manager, the event handler is run in a different
    thread, so all the "handle" implementations have to make sure they are thread-safe. To make
    sure that that is the case here, we use the GradeBook's "event_lock".
    """

    def __init__(self, gradebook_instance) -> None:
        self.gradebook_instance = gradebook_instance

    def handle(self, event: events.Event) -> None:
        _logger.debug("{} got event {}", self.__class__.__name__, event)
        with self.gradebook_instance.event_lock:
            _logger.info("{} handling event {}", self.__class__.__name__, event)
            self._handle_sync(event)

    def _handle_sync(self, event: events.Event) -> None:
        raise NotImplementedError()


class NewSubmissionListHandler(GradeBookEventHandler):
    handled_event_name = "NewSubmissionListEvent"

    def _handle_sync(self, event: events.NewSubmissionListEvent) -> None:
        self.gradebook_instance.set_submission_list(event.submissions)


class SubmissionStartedHandler(GradeBookEventHandler):
    handled_event_name = "SubmissionStartedEvent"

    def _handle_sync(self, event: events.SubmissionStartedEvent) -> None:
        self.gradebook_instance.set_current_submission(
            event.submission_id, event.html_log, event.text_log)


class EndOfSubmissionsHandler(GradeBookEventHandler):
    handled_event_name = "EndOfSubmissionsEvent"

    def _handle_sync(self, event: events.EndOfSubmissionsEvent) -> None:
        self.gradebook_instance.set_done(True)


class AuthGrantedEventHandler(GradeBookEventHandler):
    handled_event_name = "AuthGrantedEvent"

    def _handle_sync(self, event: events.AuthGrantedEvent) -> None:
        self.gradebook_instance.auth_granted(event.auth_event_id)
