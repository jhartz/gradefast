"""
Event handlers for events that the Grader can handle.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import logging

from iochannels import Channel, Msg, DEFAULT_BAD_CHOICE_MSG
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

        _logger.debug("Handling AuthRequestedEvent: Did user allow? %s", choice)
        if choice == "y":
            self.event_manager.dispatch_event(events.AuthGrantedEvent(event.event_id))
