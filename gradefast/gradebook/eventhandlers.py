"""
This module contains event handlers for events that the GradeBook can handle.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

from .. import events

# All concrete event handlers should be listed here. This is used by the
# GradeBook to register all event handlers (see its "__init__" method).
__all__ = [
    "NewSubmissionListHandler",
    "SubmissionStartedHandler",
    "SubmissionFinishedHandler",
    "EndOfSubmissionsHandler",
    "AuthGrantedEventHandler"
]


class GradeBookEventHandler(events.EventHandler):
    """
    An abstract subclass of EventHandler for GradeBook event handlers.
    """

    _accepted_event_name = None

    def __init__(self, gradebook_instance):
        from .gradebook import GradeBook
        self.gradebook_instance: GradeBook = gradebook_instance

    def __init_subclass__(cls, **kwargs):
        cls._accepted_event_name = kwargs["event"]

    def accept(self, event: events.Event):
        return event.get_name() == self.__class__._accepted_event_name

    def handle(self, event: events.Event):
        raise NotImplementedError()


class NewSubmissionListHandler(GradeBookEventHandler, event="NewSubmissionListEvent"):
    def handle(self, event: events.NewSubmissionListEvent):
        self.gradebook_instance.set_submission_list(event.submissions)


class SubmissionStartedHandler(GradeBookEventHandler, event="SubmissionStartedEvent"):
    def handle(self, event: events.SubmissionStartedEvent):
        self.gradebook_instance.set_current_submission(event.submission_id)


class SubmissionFinishedHandler(GradeBookEventHandler, event="SubmissionFinishedEvent"):
    def handle(self, event: events.SubmissionFinishedEvent):
        self.gradebook_instance.log_submission(event.submission_id, event.log_html)


class EndOfSubmissionsHandler(GradeBookEventHandler, event="EndOfSubmissionsEvent"):
    def handle(self, event: events.EndOfSubmissionsEvent):
        self.gradebook_instance.set_done(True)


class AuthGrantedEventHandler(GradeBookEventHandler, event="AuthGrantedEvent"):
    def handle(self, event: events.AuthGrantedEvent):
        self.gradebook_instance.auth_granted(event.auth_event_id)
