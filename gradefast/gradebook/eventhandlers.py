"""
Event handlers for events that the GradeBook can handle.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

from iochannels import Channel, Msg, DEFAULT_BAD_CHOICE_MSG
from pyprovide import Injector, inject

from gradefast import events
from gradefast.loggingwrapper import get_logger

# All concrete event handlers should be listed here.
# This is used by the register_all_event_handlers method of EventManager.
__all__ = [
    "NewSubmissionsHandler",
    "SubmissionStartedHandler",
    "SubmissionFinishedHandler",
    "EndOfSubmissionsHandler",
    "SubmissionGradeExternallyUpdatedHandler",
    "AuthGrantedEventHandler",

    "AuthRequestedEventHandler"
]

_logger = get_logger("gradebook.eventhandlers")


class GradeBookEventHandler(events.EventHandler):
    """
    An abstract subclass of EventHandler for GradeBook event handlers.

    When an event is dispatched by the event manager, the event handler is run in a different
    thread, so all the "handle" implementations have to make sure they are thread-safe. To make
    sure that that is the case here, we use the GradeBook's "event_lock".
    """

    @inject(injector=Injector.CURRENT_INJECTOR)
    def __init__(self, injector: Injector) -> None:
        # We can't actually get a GradeBook instance from the injector yet because that would cause
        # a circular dependency (since the event handlers are created in GradeBook's constructor).
        # TODO: This is pretty hacky
        self.injector = injector

    def handle(self, event: events.Event) -> None:
        from gradefast.gradebook.gradebook import GradeBook
        gradebook_instance = self.injector.get_instance(GradeBook)

        _logger.debug("{} got event {}", self.__class__.__name__, event)
        with gradebook_instance.event_lock:
            _logger.info("{} handling event {}", self.__class__.__name__, event)
            self._handle_sync(event, gradebook_instance)

    def _handle_sync(self, event: events.Event, gradebook_instance) -> None:
        raise NotImplementedError()


class NewSubmissionsHandler(GradeBookEventHandler):
    handled_event_class = events.NewSubmissionsEvent

    def _handle_sync(self, event: events.NewSubmissionsEvent, gradebook_instance) -> None:
        gradebook_instance.send_submission_list()


class SubmissionStartedHandler(GradeBookEventHandler):
    handled_event_class = events.SubmissionStartedEvent

    def _handle_sync(self, event: events.SubmissionStartedEvent, gradebook_instance) -> None:
        # Switch to this submission for all gradebook clients
        gradebook_instance.set_current_submission(event.submission_id)
        # Send the submission list too, now that we probably have logs for this guy
        gradebook_instance.send_submission_list()


class SubmissionFinishedHandler(GradeBookEventHandler):
    handled_event_class = events.SubmissionFinishedEvent

    def _handle_sync(self, event: events.SubmissionFinishedEvent, gradebook_instance) -> None:
        # Send the submission list so gradebook clients have updated timing info
        gradebook_instance.send_submission_list()


class EndOfSubmissionsHandler(GradeBookEventHandler):
    handled_event_class = events.EndOfSubmissionsEvent

    def _handle_sync(self, event: events.EndOfSubmissionsEvent, gradebook_instance) -> None:
        gradebook_instance.set_done()


class SubmissionGradeExternallyUpdatedHandler(GradeBookEventHandler):
    handled_event_class = events.SubmissionGradeExternallyUpdatedEvent

    # NOTE: This is NOT called when the change came from the gradebook itself!
    def _handle_sync(self, event: events.SubmissionGradeExternallyUpdatedEvent,
                     gradebook_instance) -> None:
        # Send the submission's latest details to any interested gradebook clients
        gradebook_instance.send_submission_updated(event.submission_id)
        # Send the latest submission list, in case total scores were updated
        gradebook_instance.send_submission_list()


class AuthGrantedEventHandler(GradeBookEventHandler):
    handled_event_class = events.AuthGrantedEvent

    def _handle_sync(self, event: events.AuthGrantedEvent, gradebook_instance) -> None:
        gradebook_instance.auth_granted(event.auth_event_id)


# This is the only one that doesn't inherit GradeBookEventHandler, since it doesn't actually touch
# the gradebook at all (that's done in its sister event handler, AuthGrantedEventHandler)
class AuthRequestedEventHandler(events.EventHandler):
    handled_event_class = events.AuthRequestedEvent

    @inject()
    def __init__(self, channel: Channel, event_manager: events.EventManager) -> None:
        self.channel = channel
        self.event_manager = event_manager

    def handle(self, event: events.AuthRequestedEvent) -> None:
        _logger.info("Handling AuthRequestedEvent (event {})", event.event_id)

        with self.channel.blocking_io() as (output_func, input_func, prompt_func):
            lines = [
                "A GradeBook client is trying to connect!",
                event.request_details
            ]
            max_line_len = max(len(l) for l in lines)
            separator = Msg().add(Msg.PartType.PROMPT_QUESTION, "   " + "-" * (max_line_len + 2))
            prefix = "   | "

            output_func(Msg().print())
            output_func(separator)
            for l in lines:
                if len(l) < max_line_len:
                    l += " " * (max_line_len - len(l))
                output_func(Msg(sep="").add(Msg.PartType.PROMPT_QUESTION, prefix).print("{}", l))

            choice = prompt_func(prefix + "Allow?", ["Y", "n"], "y",
                                 bad_choice_msg=prefix + DEFAULT_BAD_CHOICE_MSG)
            output_func(separator)
            output_func(Msg().print())

        _logger.debug("Handling AuthRequestedEvent: Did user allow? {}", choice)
        if choice == "y":
            self.event_manager.dispatch_event(events.AuthGrantedEvent(event.event_id))
