"""
Centralized logging configuration for GradeFast.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import logging
import sys
from typing import List


class LogStyleAdapter(logging.LoggerAdapter):
    _LOG_KWARGS = ["exc_info", "extra", "stack_info"]

    class BraceMessage:
        def __init__(self, fmt, args, kwargs):
            self.fmt = fmt
            self.args = args
            self.kwargs = kwargs

        def __str__(self):
            return str(self.fmt).format(*self.args, **self.kwargs)

    def __init__(self, logger):
        super().__init__(logger, {})
        self.logger = logger

    def log(self, level, msg, *args, **kwargs):
        if self.isEnabledFor(level):
            msg, log_kwargs = self.process(msg, kwargs)
            self.logger._log(level, self.BraceMessage(msg, args, kwargs), (), **log_kwargs)

    def process(self, msg, kwargs):
        return msg, {key: kwargs[key] for key in self._LOG_KWARGS if key in kwargs}


def get_logger(name: str) -> LogStyleAdapter:
    """
    Wrapper around logging.getLogger that enables the use of str.format-style parameters.

    At the program's entry point, be sure to call "init_logging" before doing any logging!
    (And call "shutdown_logging" before exiting.)
    """
    return LogStyleAdapter(logging.getLogger(name))


def init_logging(log_file: str = None) -> None:
    handlers = []  # type: List[logging.Handler]

    # Set up a handler to log everything to a file
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(
            "{asctime}  {threadName:11} {levelname:5} [{name}]  {message}",
            style="{"))
        handlers.append(file_handler)

    # Set up a handler to log WARNING/ERROR/CRITICAL to stderr
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.WARNING)
    stream_handler.setFormatter(logging.Formatter(
        "\n==> {levelname} ({name}): {message}",
        style="{"))
    handlers.append(stream_handler)

    logging.basicConfig(level=logging.DEBUG, handlers=handlers)
    logging.info("STARTING GRADEFAST")
    logging.info("Python version:\n" + sys.version)

    # Set the werkzeug log level to WARNING (since it logs all HTTP requests at INFO, which gets
    # old really fast)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)


def shutdown_logging() -> None:
    logging.info("SHUTTING DOWN GRADEFAST\n")
    logging.shutdown()
