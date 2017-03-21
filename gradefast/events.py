"""
This module contains the base classes for the events system that enables communication between the
GradeBook and the Grader.

This is different from the GradeBook's "client updates" system that it uses to communicate with
GradeBook clients.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import contextlib
import threading

from typing import List

from .submissions import Submission


class Event:
    """
    Base class for all events. Subclasses should expose sufficient data about an event so that
    event handlers will be able to take the appropriate actions.

    Subclasses should have a name ending in "Event".
    """

    _last_event_id = 0
    _event_id_lock = threading.Lock()

    def __init__(self):
        with Event._event_id_lock:
            Event._last_event_id += 1
            self.event_id = Event._last_event_id

    def get_name(self) -> str:
        return self.__class__.__name__


class EventHandler:
    """
    Base class for all event handlers. An event handler can "accept" one or more types of events,
    and then take action based on those events.

    Subclasses should have names ending in "Handler".
    """

    def accept(self, event: Event) -> bool:
        """
        Determine whether this event handler can handle a certain event.

        :param event: An instance of a subclass of Event.
        :return: True if we should accept the event (which will result in it being passed to the
            "handle" method), or False if we should ignore it.
        """
        raise NotImplementedError()

    def handle(self, event: Event):
        """
        Take some action in response to an event.
        """
        raise NotImplementedError()


class EventManager:
    """
    Keeps a registry of event handlers and handles dispatching events to event handlers.
    """

    class BadEventError(Exception):
        pass

    def __init__(self):
        self._handlers: List[EventHandler] = []
        self._lock = threading.Lock()

    def register_event_handler(self, event_handler: EventHandler):
        """
        Register a new event handler that will be called for any future event dispatches.
        """
        with self._lock:
            self._handlers.append(event_handler)

    def dispatch_event(self, event: Event):
        """
        Dispatch an event to all event handlers that accept it.
        """
        assert isinstance(event, Event)
        # Make sure that only one event is being applied at once
        with self._lock:
            for handler in self._handlers:
                if handler.accept(event):
                    handler.handle(event)

    @contextlib.contextmanager
    def block_event_dispatching(self):
        """
        Returns a context manager that can be used to block event dispatching.
        """
        with self._lock:
            yield


#############################################################################
# Below are some common events used in Grader <--> GradeBook communication. #
#############################################################################


class NewSubmissionListEvent(Event):
    """
    An event with a new list of submissions.

    It is assumed that no submission IDs will be repeated, i.e. if this new list contains
    submissions that were not present before, they have new submission IDs.
    """
    def __init__(self, submissions: List[Submission]):
        super().__init__()
        self.submissions = submissions


class SubmissionStartedEvent(Event):
    """
    An event representing that a new submission is being graded.
    """
    def __init__(self, submission_id: int):
        super().__init__()
        self.submission_id = submission_id


class SubmissionFinishedEvent(Event):
    """
    An event representing that a submission is done being graded.
    """
    def __init__(self, submission_id: int, log_html: str):
        super().__init__()
        self.submission_id = submission_id
        self.log_html = log_html


class EndOfSubmissionsEvent(Event):
    """
    An event representing that all the submissions are done being graded.
    """
    def __init__(self):
        super().__init__()


class AuthRequestedEvent(Event):
    """
    An event representing that someone is requesting authentication.

    This is usually dispatched by the GradeBook, asking for authentication for a new GradeBook
    client that is trying to connect, and it is usually handled by the Grader, who will prompt the
    user.
    """

    def __init__(self, request_details: str):
        super().__init__()
        self.request_details = request_details


class AuthGrantedEvent(Event):
    """
    An event representing that authentication is granted, in response to a previous
    AuthRequestedEvent.

    This is usually dispatched by the Grader to send the successfulness back to the GradeBook.
    """
    def __init__(self, auth_event_id: int):
        super().__init__()
        self.auth_event_id = auth_event_id
