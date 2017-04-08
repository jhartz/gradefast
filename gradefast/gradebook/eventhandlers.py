"""
Event handlers for events that the GradeBook can handle.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

from pyprovide import Injector, inject

from gradefast import events

# All concrete event handlers should be listed here.
# This is used by the register_all_event_handlers method of EventManager.
__all__ = [
    "NewSubmissionListHandler",
    "SubmissionStartedHandler",
    "SubmissionFinishedHandler",
    "EndOfSubmissionsHandler",
    "AuthGrantedEventHandler"
]


class GradeBookEventHandler(events.EventNameHandler, event=None):
    """
    An abstract subclass of EventNameHandler for GradeBook event handlers.

    When an event is dispatched by the event manager, the event handler is run in a different
    thread, so all the "handle" implementations have to make sure they are thread-safe. To make
    sure that that is the case here, we use the GradeBook's "event_lock".
    """

    def __init_subclass__(cls, event: str):
        super().__init_subclass__(event)

    def __init__(self, gradebook_instance):
        self.gradebook_instance = gradebook_instance

    def handle(self, event: events.Event):
        with self.gradebook_instance.event_lock:
            self._handle_sync(event)

    def _handle_sync(self, event: events.Event):
        raise NotImplementedError()


class NewSubmissionListHandler(GradeBookEventHandler, event="NewSubmissionListEvent"):
    def _handle_sync(self, event: events.NewSubmissionListEvent):
        self.gradebook_instance.set_submission_list(event.submissions)


class SubmissionStartedHandler(GradeBookEventHandler, event="SubmissionStartedEvent"):
    def _handle_sync(self, event: events.SubmissionStartedEvent):
        self.gradebook_instance.set_current_submission(event.submission_id)


class SubmissionFinishedHandler(GradeBookEventHandler, event="SubmissionFinishedEvent"):
    def _handle_sync(self, event: events.SubmissionFinishedEvent):
        self.gradebook_instance.log_submission(event.submission_id, event.log_html)


class EndOfSubmissionsHandler(GradeBookEventHandler, event="EndOfSubmissionsEvent"):
    def _handle_sync(self, event: events.EndOfSubmissionsEvent):
        self.gradebook_instance.set_done(True)


class AuthGrantedEventHandler(GradeBookEventHandler, event="AuthGrantedEvent"):
    def _handle_sync(self, event: events.AuthGrantedEvent):
        self.gradebook_instance.auth_granted(event.auth_event_id)
