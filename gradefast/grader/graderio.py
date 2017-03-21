"""
Handles input and output between the grader and the user.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

from enum import Enum
from typing import Callable, List, Optional, Tuple

try:
    import readline
except ImportError:
    readline = None

try:
    import colorama
except ImportError:
    colorama = None


class Msg:
    """
    A message that can be printed using an instance of an implementation of GraderIO.
    """

    class PartType(Enum):
        PROMPT_QUESTION = -1
        PROMPT_ANSWER = -2

        PRINT = 1
        STATUS = 2
        ERROR = 3
        BRIGHT = 4
        BG_HAPPY = 5
        BG_SAD = 6
        BG_MEH = 7

    def __init__(self, sep: str = " ", end: str = "\n"):
        """
        Initialize a new message.

        :param sep: The separator between parts of the message.
        :param end: A string to use to terminate the message.
        """
        self._parts: List[Tuple[Msg.PartType, str]] = []
        self._sep = sep
        self._end = end

    def add(self, part_type: "Msg.PartType", base: str, *args, **kwargs) -> "Msg":
        base = base or ""
        self._parts.append((part_type, str(base).format(args)))
        return self

    def print(self, *args, **kwargs) -> "Msg":
        return self.add(Msg.PartType.PRINT, *args, **kwargs)

    def status(self, *args, **kwargs) -> "Msg":
        return self.add(Msg.PartType.STATUS, *args, **kwargs)

    def error(self, *args, **kwargs) -> "Msg":
        return self.add(Msg.PartType.ERROR, *args, **kwargs)

    def bright(self, *args, **kwargs) -> "Msg":
        return self.add(Msg.PartType.BRIGHT, *args, **kwargs)

    def bg_happy(self, *args, **kwargs) -> "Msg":
        return self.add(Msg.PartType.BG_HAPPY, *args, **kwargs)

    def bg_sad(self, *args, **kwargs) -> "Msg":
        return self.add(Msg.PartType.BG_SAD, *args, **kwargs)

    def bg_meh(self, *args, **kwargs) -> "Msg":
        return self.add(Msg.PartType.BG_MEH, *args, **kwargs)

    def get_string(self, part_processor: Callable[["Msg.PartType", str], str]) -> str:
        """
        Transform this message into a string representation.

        :param part_processor: A function that takes in 2 arguments (part type, part string) and
            transforms it into a string representing the part.
        :return: The result of processing all the parts with the part_processor.
        """
        return self._sep.join(part_processor(*part) for part in self._parts) + self._end

    def for_each_part(self, part_handler: Callable[[Optional["Msg.PartType"], str], None]):
        """
        Perform an action for each part in the message.

        :param part_handler: A function that takes in 2 arguments (part type, part string). Unlike
            get_string, the part type may be None, indicating no formatting.
        """
        for index, part in enumerate(self._parts):
            if index > 0:
                part_handler(None, self._sep)
            part_handler(*part)
        part_handler(None, self._end)


class GraderIO:
    """
    Provide methods for the grader to get input from the user and give output back to the user,
    following a command-line-like setting. The actual input and output operations are implemented
    in subclasses. A subclass can also be read-only, meaning that it supports writing output but
    not reading input. By convention, read-only subclasses end in "GraderIOLog", while others just
    end in "GraderIO".

    In the Grader, one instance of one subclass of this class is used as the "primary" IO
    implementation. The primary IO implementation CANNOT be read-only.

    An instance of GraderIO can have "delegates", which are other GraderIO instances that are
    written to whenever the original instance outputs something (or to echo back user input).
    Because delegates can be read-only, they are useful for logging.
    """

    _inited_subclasses = set()

    def __init__(self, *delegates: List["GraderIO"]):
        self._delegates: List[GraderIO] = delegates

        if self.__class__ not in GraderIO._inited_subclasses:
            self._class_init()
            GraderIO._inited_subclasses.add(self.__class__)

    def _class_init(self):
        """
        Any initialization that needs to be done once per class (not per each instance).
        This method should be overridden in subclasses, if necessary.
        """
        pass

    def _in(self, autocomplete_choices: List[str] = None) -> str:
        """
        See GraderIO::input. This method should be overridden in subclasses to do the actual input
        operation.

        If a subclass is read-only (i.e. it cannot prompt the user for input, usually used for
        GraderIO subclasses that just log the output), just leave this method non-overridden.
        This will ensure that that subclass can only be used as an IO delegate, not as the primary
        IO implementation.
        """
        raise NotImplementedError()

    def _out(self, message: Msg):
        """
        See GraderIO::out. This method should be overridden in subclasses to do the actual output
        operation.
        """
        raise NotImplementedError()

    def _message_delegates(self, message: Msg):
        """
        Output a message to all delegates.
        """
        for delegate in self._delegates:
            delegate.output(message)

    def input(self, prompt: Optional[str] = None, autocomplete_choices: List[str] = None) -> str:
        """
        Ask the user for a line of input.

        :param prompt: The message to prompt the user with.
        :param autocomplete_choices: A list of choices to use for autocompletion (if implemented).
        :return: The text entered by the user.
        """
        if prompt:
            self.output(Msg(end=" ").add(Msg.PartType.PROMPT_QUESTION, prompt))
        line = self._in(autocomplete_choices).rstrip()
        self._message_delegates(Msg().add(Msg.PartType.PROMPT_ANSWER, line))
        return line

    def output(self, message: Msg):
        """
        Print a message to the user.
        """
        self._out(message)
        self._message_delegates(message)

    def print(self, *args, **kwargs):
        """Shortcut for out(Msg().print(...))"""
        self.output(Msg(**kwargs).print(*args))

    def status(self, *args, **kwargs):
        """Shortcut for out(Msg().status(...))"""
        self.output(Msg(**kwargs).status(*args))

    def error(self, *args, **kwargs):
        """Shortcut for out(Msg().error(...))"""
        self.output(Msg(**kwargs).error(*args))

    def bright(self, *args, **kwargs):
        """Shortcut for out(Msg().bright(...))"""
        self.output(Msg(**kwargs).bright(*args))

    def bg_happy(self, *args, **kwargs):
        """Shortcut for out(Msg().bg_happy(...))"""
        self.output(Msg(**kwargs).bg_happy(*args))

    def bg_sad(self, *args, **kwargs):
        """Shortcut for out(Msg().bg_sad(...))"""
        self.output(Msg(**kwargs).bg_sad(*args))

    def bg_meh(self, *args, **kwargs):
        """Shortcut for out(Msg().bg_meh(...))"""
        self.output(Msg(**kwargs).bg_meh(*args))

    def prompt(self, prompt: str, choices: List[str], default_choice: Optional[str] = None,
               show_choices: bool = True, hidden_choices: bool = None) -> str:
        """
        Ask the user a question, returning their choice.

        :param prompt: The message to prompt the user with.
        :param choices: The list of valid choices (possibly including "").
        :param default_choice: The default choice from choices (only used if "" is not in choices).
        :param show_choices: Whether to show the user the list of choices.
        :param hidden_choices: If show_choices is True, this can be a list of choices to hide from
            the user at the prompt.
        :return: An element of choices chosen by the user (lowercased).
        """
        our_choices = []
        user_choices = ""
        has_empty_choice = False

        for choice in choices:
            if choice == "":
                has_empty_choice = True
            else:
                our_choices.append(choice.lower())
                if hidden_choices is None or choice not in hidden_choices:
                    user_choices += choice + "/"

        if has_empty_choice:
            # We add in this choice last
            user_choices += "Enter"
        else:
            # Strip trailing slash
            user_choices = user_choices[:-1]

        msg = prompt
        if show_choices:
            msg += " (%s)" % user_choices
        msg += ": "

        while True:
            choice = self.input(msg).strip().lower()
            if choice == "" and has_empty_choice:
                return ""
            elif choice == "" and not has_empty_choice and default_choice is not None:
                return default_choice.lower()
            elif choice in our_choices:
                return choice
            else:
                self.error("Learn how to read, dumbass. `{}' ain't a choice!", choice)


class TextGraderIOLog(GraderIO):
    """
    A read-only GraderIO implementation that generates a plain text log.
    """

    def __init__(self, writer: Callable[[str], None], *delegates: List[GraderIO]):
        """
        :param writer: A function to call whenever we have output to log.
        """
        super().__init__(*delegates)
        self._writer = writer

    def _out(self, message: Msg):
        message.for_each_part(lambda _, part: self._writer(part))


class HTMLGraderIOLog(GraderIO):
    """
    A read-only GraderIO implementation that generates an HTML log.
    """

    @staticmethod
    def _wrap_fg_color(color, s):
        return '<span style="color: %s">%s</span>' % (color, s)

    @staticmethod
    def _wrap_bg_color(color, s):
        return '<span style="background-color: %s">%s</span>' % (color, s)

    _transforms_by_part_type = {
        Msg.PartType.PROMPT_QUESTION: lambda s: HTMLGraderIOLog._wrap_fg_color("cyan", s),
        Msg.PartType.PROMPT_ANSWER:   lambda s: s,

        Msg.PartType.PRINT:    lambda s: s,
        Msg.PartType.STATUS:   lambda s: HTMLGraderIOLog._wrap_fg_color("green", s),
        Msg.PartType.ERROR:    lambda s: HTMLGraderIOLog._wrap_fg_color("red", s),
        Msg.PartType.BRIGHT:   lambda s: s,
        Msg.PartType.BG_HAPPY: lambda s: HTMLGraderIOLog._wrap_bg_color("green", s),
        Msg.PartType.BG_SAD:   lambda s: HTMLGraderIOLog._wrap_bg_color("red", s),
        Msg.PartType.BG_MEH:   lambda s: HTMLGraderIOLog._wrap_bg_color("blue", s)
    }

    @staticmethod
    def _escape_html(text: str):
        return text.replace("&", "&amp;").replace("\"", "&quot;").replace("'", "&apos;") \
                   .replace("<", "&lt;").replace(">", "&gt;")

    def __init__(self, writer: Callable[[str], None], *delegates: List[GraderIO]):
        """
        :param writer: A function to call whenever we have output to log.
        """
        super().__init__(*delegates)
        self._writer = writer

    def _out(self, message: Msg):
        message.for_each_part(self._handle_message_part)

    def _handle_message_part(self, part_type: Optional[Msg.PartType], part_str: str):
        part_str = HTMLGraderIOLog._escape_html(part_str)
        if part_type is not None:
            part_str = HTMLGraderIOLog._transforms_by_part_type[part_type](part_str)
        self._writer(part_str.replace("\n", "<br>\n"))


class CLIGraderIO(GraderIO):
    """
    A GraderIO implementation that reads from stdin and writes to stdout.
    """

    class InputCompleter:
        """Class used to handle autocomplete on an input via the readline module."""

        def __init__(self, options):
            self.options = options
            self.matches = None

        def complete(self, text, state):
            """
            Handle autocompletion.

            :param text: The text that the user has entered so far
            :param state: The index of the item in the results list
            :return: The item matched by text and state, or None
            """
            if state == 0:
                # First trigger; build possible matches
                if text:
                    # Cache matches (entries that start with entered text)
                    self.matches = [s for s in self.options
                                    if s and s.startswith(text)]
                else:
                    # No text entered, all matched possible
                    self.matches = self.options[:]
            # Return match indexed by state
            try:
                return self.matches[state]
            except IndexError:
                return None

    def _class_init(self):
        if readline is not None:
            readline.parse_and_bind("tab: complete")

    def _in(self, autocomplete_choices: List[str] = None) -> str:
        if readline is not None:
            readline.set_completer(CLIGraderIO.InputCompleter(autocomplete_choices))

        try:
            line = input()
        except EOFError:
            line = ""

        if readline is not None:
            readline.set_completer(None)
        return line

    def _out(self, message: Msg):
        print(message.get_string(lambda _, part: part), end="")


class ColorCLIGraderIO(CLIGraderIO):
    """
    A GraderIO implementation that reads from stdin and writes to stdout.
    """

    @staticmethod
    def _wrap_bright(s):
        return "%s%s%s" % (colorama.Style.BRIGHT, s, colorama.Style.NORMAL)

    @staticmethod
    def _wrap_fg_color(color, s):
        return "%s%s%s" % (getattr(colorama.Fore, color),
                           ColorCLIGraderIO._wrap_bright(s),
                           colorama.Fore.RESET)

    @staticmethod
    def _wrap_bg_color(color, s):
        return "%s%s%s" % (getattr(colorama.Back, color),
                           ColorCLIGraderIO._wrap_fg_color("WHITE", s),
                           colorama.Back.RESET)

    _transforms_by_part_type = {
        Msg.PartType.PROMPT_QUESTION: lambda s: ColorCLIGraderIO._wrap_fg_color("CYAN", s),
        Msg.PartType.PROMPT_ANSWER:   lambda s: s,

        Msg.PartType.PRINT:    lambda s: s,
        Msg.PartType.STATUS:   lambda s: ColorCLIGraderIO._wrap_fg_color("GREEN", s),
        Msg.PartType.ERROR:    lambda s: ColorCLIGraderIO._wrap_fg_color("RED", s),
        Msg.PartType.BRIGHT:   lambda s: ColorCLIGraderIO._wrap_bright(s),
        Msg.PartType.BG_HAPPY: lambda s: ColorCLIGraderIO._wrap_bg_color("GREEN", s),
        Msg.PartType.BG_SAD:   lambda s: ColorCLIGraderIO._wrap_bg_color("RED", s),
        Msg.PartType.BG_MEH:   lambda s: ColorCLIGraderIO._wrap_bg_color("BLUE", s)
    }

    def _class_init(self):
        if colorama is None:
            print("")
            print("*** Couldn't find Colorama package!")
            print("    CLI will fall back to a boring version without color.")
            print("    Please install 'colorama' to get pretty colors.")
            print("")
        else:
            colorama.init()

    def _out(self, message: Msg):
        if colorama is None:
            return super()._out(message)

        print(message.get_string(lambda part_type, part_str:
                                 ColorCLIGraderIO._transforms_by_part_type[part_type](part_str)
                                 ), end="")
