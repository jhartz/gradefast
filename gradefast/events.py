"""
Base classes for the events system that enables communication between the GradeBook and the Grader.

This is different from the GradeBook's "client updates" system that it uses to communicate with
GradeBook clients.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import itertools
import queue
import threading
from typing import Any, Callable, Iterable, List, Type, TypeVar

from pyprovide import Injector, inject

from gradefast.loggingwrapper import get_logger

_logger = get_logger("events")
T = TypeVar("T")


class Event:
    """
    Base class for all events. Subclasses should expose sufficient data about an event so that
    event handlers will be able to take the appropriate actions.

    Subclasses should have a name ending in "Event".
    """

    _last_event_id = 0
    _event_id_lock = threading.Lock()

    def __init__(self) -> None:
        with Event._event_id_lock:
            Event._last_event_id += 1
            self.event_id = Event._last_event_id

    def __str__(self) -> str:
        return self.__class__.__name__


class EventHandler:
    """
    Base class for all event handlers. Each event handler handles a specific type of event,
    represented by the event's class (or a common superclass of a set of events).

    All EventHandler subclasses should specify a class-level or instance-level property named
    "handled_event_class" that is set to the Event subclass that they handle. (Alternatively, an
    event handler can override the "accept" method for more control.)

    Subclasses should have names ending in "Handler".
    """

    handled_event_class = None

    def accept(self, event: Event) -> bool:
        """
        Determine whether this event handler can handle a certain event. The default implementation
        checks if the event is an instance of the "handled_event_class" property.

        :param event: An instance of a subclass of Event.
        :return: True if we should accept the event (which will result in it being passed to the
            "handle" method), or False if we should ignore it.
        """
        return isinstance(event, self.handled_event_class)

    def handle(self, event: Event) -> None:
        """
        Take some action in response to an event. This method may be called in a fresh thread
        (different from the one that called "accept").
        """
        raise NotImplementedError()

    def __str__(self) -> str:
        return self.__class__.__name__


class EventManager:
    """
    Keeps a registry of event handlers and handles dispatching events to event handlers. This
    facilitates communication between the Grader and the GradeBook.

    When an event is dispatched, it is put into a queue and is handled later by a different thread.
    Additionally, multiple event handlers may be running in different threads at the same time.
    """

    @inject(injector=Injector.CURRENT_INJECTOR)
    def __init__(self, injector: Injector) -> None:
        self.injector = injector
        self._handlers = []  # type: List[EventHandler]
        self._event_queue = queue.Queue()  # type: queue.Queue
        threading.Thread(
            name="EventManTh",
            target=self._event_thread_target,
            daemon=True
        ).start()

    def _event_thread_target(self) -> None:
        count = itertools.count()
        while True:
            event = self._event_queue.get()
            for handler in self._handlers:
                try:
                    accepted = handler.accept(event)
                except:
                    _logger.exception("Exception when calling {}.accept with event {}",
                                      handler, event)
                else:
                    if accepted:
                        threading.Thread(
                            name="EventTh-{:02}".format(next(count)),
                            target=self._event_handle_target,
                            args=(handler, event),
                            daemon=True
                        ).start()

    @staticmethod
    def _event_handle_target(handler: EventHandler, event: Event) -> None:
        try:
            handler.handle(event)
        except:
            _logger.exception("Exception when calling {}.handle with event {}", handler, event)

    def register_event_handler(self, event_class: Type[T], handler: Callable[[T], None]) -> None:
        """
        Register a new event handler function (i.e. an implementation of the "handle" method of the
        EventHandler class) for events with a specific name. This is a shortcut for simple
        EventHandler classes.
        """
        _logger.info("Registering event handler for {}: {}", event_class, handler)

        class FunctionalEventHandler(EventHandler):
            handled_event_class = event_class

            def handle(self, event: Event) -> None:
                handler(event)

        self._handlers.append(FunctionalEventHandler())

    def register_event_handlers(self, *event_handlers: EventHandler) -> None:
        """
        Register one or more new event handler instances that will be called for any future event
        dispatches.
        """
        _logger.info("Registering event handlers: {}",
                     ", ".join(str(h) for h in event_handlers))
        self._handlers += event_handlers

    def register_event_handler_classes(self, *event_handler_classes: Type[EventHandler]) -> None:
        """
        Register one or more new event handler classes that will be called for any future event
        dispatches.

        Instances of these classes are created using the same injector that was used when creating
        the EventManager (so the classes' constructors should be decorated with "@inject()").
        """
        _logger.info("Registering event handler classes: {}",
                     ", ".join(str(c) for c in event_handler_classes))
        self._handlers += [self.injector.get_instance(cls) for cls in event_handler_classes]

    def register_all_event_handlers(self, mod: Any) -> None:
        """
        Register all the event handler classes exposed in a module.

        This method relies on "register_event_handler_classes" to actually create the class
        instances, so see that method's documentation for further details.
        """
        self.register_event_handler_classes(*list(self._get_classes_in_module(mod)))

    @staticmethod
    def _get_classes_in_module(mod: Any) -> Iterable[Type[EventHandler]]:
        """
        Get all the event handler classes in a module.
        """
        assert hasattr(mod, "__all__")
        for name in mod.__all__:
            cls = getattr(mod, name)
            try:
                if issubclass(cls, EventHandler):
                    yield cls
            except TypeError:
                pass

    def dispatch_event(self, event: Event) -> None:
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


class NewSubmissionsEvent(Event):
    """
    An event representing that a new list of submissions is available from the SubmissionManager.
    """


class SubmissionStartedEvent(Event):
    """
    An event representing that a new submission is being graded.
    """
    def __init__(self, submission_id: int) -> None:
        super().__init__()
        self.submission_id = submission_id

    def __str__(self) -> str:
        return "{} (submission ID {})".format(super().__str__(), self.submission_id)


class SubmissionFinishedEvent(Event):
    """
    An event representing that a submission is done being graded.
    """
    def __init__(self, submission_id: int) -> None:
        super().__init__()
        self.submission_id = submission_id

    def __str__(self) -> str:
        return "{} (submission ID {})".format(super().__str__(), self.submission_id)


class EndOfSubmissionsEvent(Event):
    """
    An event representing that all the submissions are done being graded.
    """


class SubmissionGradeExternallyUpdatedEvent(Event):
    """
    An event representing that a component of a submission's grade (score, comments, etc.) has been
    updated. (NOTE: This is NOT triggered when the update occurred from a gradebook client.)
    """
    def __init__(self, submission_id: int) -> None:
        super().__init__()
        self.submission_id = submission_id

    def __str__(self) -> str:
        return "{} (submission ID {})".format(super().__str__(), self.submission_id)


class AuthRequestedEvent(Event):
    """
    An event representing that someone is requesting authentication.

    This is usually dispatched by the GradeBook, asking for authentication for a new GradeBook
    client that is trying to connect, and it is usually handled by the Grader, who will prompt the
    user.
    """

    def __init__(self, request_details: str) -> None:
        super().__init__()
        self.request_details = request_details


class AuthGrantedEvent(Event):
    """
    An event representing that authentication is granted, in response to a previous
    AuthRequestedEvent.

    This is usually dispatched by the Grader to send the successfulness back to the GradeBook.
    """
    def __init__(self, auth_event_id: int) -> None:
        super().__init__()
        self.auth_event_id = auth_event_id

    def __str__(self) -> str:
        return "{} (auth event ID was {})".format(super().__str__(), self.auth_event_id)
