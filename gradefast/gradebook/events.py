"""
Events that can be passed to an instance of the GradeBook class.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jhartz@mail.rit.edu>
"""

import json


class ServerSentEvent:
    """
    Represents an event that the server is sending to a web client event stream.
    """

    last_id = 0

    def __init__(self, event, data=None, is_done=False):
        """
        Create a new ServerSentEvent to send to a web client event source.

        :param event: The name of the event (str)
        :param data: The data associated with the event (json-encoded if it's
            not a string)
        :param is_done: Whether this event indicates the end
        """
        self.event = event
        self.data = data if isinstance(data, str) else json.dumps(data)
        ServerSentEvent.last_id += 1
        self._id = ServerSentEvent.last_id
        self.is_done = is_done

    def encode(self):
        """
        Return the event in the HTML5 Server-Sent Events format.
        """
        if not self.data:
            return ""

        result = ""
        result += "id: " + str(self._id) + "\n"
        if self.event:
            result += "event: " + str(self.event) + "\n"
        result += "data: " + "\ndata:".join(str(self.data).split("\n"))
        result += "\n\n"
        return result


class GradeBookEvent:
    """
    Base class for an event sent to an instance of the GradeBook web server.
    """
    def handle(self, gradebook):
        """
        Method that executes actions on a GradeBook corresponding to this
        event. This must be overridden in subclasses.

        :param gradebook: The GradeBook instance to perform the action on.
        :return: A populated ServerSentEvent, if there is an event that needs
            to be passed to the GradeBook web client (otherwise None).
        """
        raise NotImplementedError("This must be implemented in a subclass of "
                                  "GradeBookEvent")


class SubmissionStart(GradeBookEvent):
    """
    An event representing the start of a new submission.
    """
    def __init__(self, submission_id, name):
        """
        :param submission_id: The ID of the submission
        :param name: The name of the owner of the new submission
        """
        self.submission_id = submission_id
        self.name = name

    def handle(self, gradebook):
        gradebook.start_submission(self.submission_id, self.name)
        return ServerSentEvent("update", {
            "submission_index": self.submission_id
        })


class SubmissionEnd(GradeBookEvent):
    """
    An event representing the end of a submission.
    """
    def __init__(self, log):
        """
        :param log: The log for the submission that just ended.
        """
        self.log = log

    def handle(self, gradebook):
        gradebook.log_submission(self.log)


class EndOfSubmissions(GradeBookEvent):
    """
    An event representing the end of all of the submissions.
    """
    def __init__(self):
        pass

    def handle(self, gradebook):
        gradebook.is_done = True
        return ServerSentEvent("done")


class SetGradeItem(GradeBookEvent):
    """
    An event representing that a certain grade item should be set to a certain
    value for the submission currently being graded.
    """
    def __init__(self, name, points):
        """
        :param name: The name of the grading item to set.
        :param points: The point value to set this grading item to.
        """
        self.name = name
        self.points = points

    def handle(self, gradebook):
        raise NotImplementedError()
