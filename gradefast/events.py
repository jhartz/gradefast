"""
Base classes for the events system that enables communication between the GradeBook and the Grader.

This is different from the GradeBook's "client updates" system that it uses to communicate with
GradeBook clients.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import itertools
import logging
import queue
import threading
from typing import List

from pyprovide import Injector, inject

from gradefast.models import Submission

_logger = logging.getLogger("events")


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
        Take some action in response to an event. This method will almost always be called in a
        fresh thread (different from the one that called "accept").
        """
        raise NotImplementedError()


class EventNameHandler(EventHandler):
    """
    An abstract subclass of EventHandler for handling events with a specific name. This simplifies
    event handler implementations that only handle a single event.
    """

    _accepted_event_name = None

    def __init_subclass__(cls, event: str):
        cls._accepted_event_name = event

    def accept(self, event: Event) -> bool:
        return event.get_name() == self._accepted_event_name

    def handle(self, event: Event):
        raise NotImplementedError()


class EventManager:
    """
    Keeps a registry of event handlers and handles dispatching events to event handlers. This
    facilitates communication between the Grader and the GradeBook.

    When an event is dispatched, it is put into a queue and is handled later by a different thread.
    Additionally, multiple event handlers may be running in different threads at the same time.
    """

    @inject(injector=Injector.CURRENT_INJECTOR)
    def __init__(self, injector: Injector):
        self.injector = injector
        self._handlers: List[EventHandler] = []
        self._event_queue = queue.Queue()
        threading.Thread(
            name="EventManTh",
            target=self._event_thread_target,
            daemon=True
        ).start()

    def _event_thread_target(self):
        count = itertools.count()
        while True:
            event = self._event_queue.get()
            for handler in self._handlers:
                if handler.accept(event):
                    threading.Thread(
                        name="EventTh-%02d" % next(count),
                        target=handler.handle,
                        args=(event,),
                        daemon=True
                    ).start()

    def register_event_handlers(self, *event_handlers: EventHandler):
        """
        Register one or more new event handler instances that will be called for any future event
        dispatches.
        """
        _logger.info("Registering event handlers %s", event_handlers)
        self._handlers += event_handlers

    def register_event_handler_classes(self, *event_handler_classes):
        """
        Register one or more new event handler classes that will be called for any future event
        dispatches.

        Instances of these classes are created using the same injector that was used when creating
        the EventManager (so the classes' constructors should be decorated with "@inject()").
        """
        _logger.info("Registering event handler classes %s", event_handler_classes)
        self._handlers += [self.injector.get_instance(cls) for cls in event_handler_classes]

    def register_all_event_handlers(self, module):
        """
        Register all the event handler classes exposed in a module.

        This method relies on "register_event_handler_classes" to actually create the class
        instances, so see that method's documentation for further details.
        """
        self.register_event_handler_classes(*list(self._get_classes_in_module(module)))

    def register_all_event_handlers_with_args(self, module, *args, **kwargs):
        """
        Register all the event handler classes exposed in a module, using the provided args and
        kwargs as arguments to the event handler classes' constructors.
        """
        self.register_event_handlers(*list(cls(*args, **kwargs)
                                           for cls in self._get_classes_in_module(module)))

    @staticmethod
    def _get_classes_in_module(module):
        """
        Get all the event handler classes in a module.
        """
        assert hasattr(module, "__all__")
        for name in module.__all__:
            cls = getattr(module, name)
            try:
                if issubclass(cls, EventHandler):
                    yield cls
            except TypeError:
                pass

    def dispatch_event(self, event: Event):
        """
        Dispatch an event to all event handlers that accept it. This method only enqueues the
        event; the event handling occurs in a different thread, and this method will likely return
        before the event is handled.
        """
        assert isinstance(event, Event)
        self._event_queue.put(event)


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
