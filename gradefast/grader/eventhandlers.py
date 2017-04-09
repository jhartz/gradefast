"""
Event handlers for events that the Grader can handle.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import logging

from iochannels import Channel, Msg
from pyprovide import inject

from gradefast import events

# All concrete event handlers should be listed here.
# This is used by the register_all_event_handlers method of EventManager.
__all__ = [
    "AuthRequestedEventHandler"
]

_logger = logging.getLogger("grader.eventhandlers")


class AuthRequestedEventHandler(events.EventNameHandler, event="AuthRequestedEvent"):
    @inject()
    def __init__(self, channel: Channel, event_manager: events.EventManager):
        self.channel: Channel = channel
        self.event_manager = event_manager

    def handle(self, event: events.AuthRequestedEvent):
        _logger.info("Handling AuthRequestedEvent (event %s)", event.event_id)
        choice = self.channel.output_then_prompt(
            Msg(sep="").print("\n")
                       .print("==> ").status("A GradeBook client is trying to connect!").print("\n")
                       .print("==> {}", event.request_details),
            "==> Allow?", ["Y", "n"], "y")
        _logger.debug("Handling AuthRequestedEvent: Did user allow? %s", choice)
        if choice == "y":
            self.event_manager.dispatch_event(events.AuthGrantedEvent(event.event_id))
        self.channel.print()
