"""
Events that can be passed to an instance of the GradeBook class.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import json
from typing import Any, Optional


class ClientUpdate:
    """
    Represents an event that the server is sending to a web client event stream.
    """

    last_id = 0

    def __init__(self, event: str, data: Any = None, is_done: bool = False):
        """
        Create a new ClientUpdate to send to a web client event source.

        :param event: The name of the event
        :param data: The data associated with the event (will be json-encoded if it's not a string)
        :param is_done: Whether this event indicates the end
        """
        self.event = event
        self.data = data if isinstance(data, str) else json.dumps(data)
        ClientUpdate.last_id += 1
        self._id = ClientUpdate.last_id
        self.is_done = is_done

    def encode(self) -> str:
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
    def handle(self, gradebook_instance: "GradeBook") -> Optional[ClientUpdate]:
        """
        Method that executes actions on a GradeBook corresponding to this event. This must be
        overridden in subclasses.

        :param gradebook_instance: The GradeBook instance to perform the action on.
        :return: A populated ClientUpdate, if there is an event that needs to be passed to the
            GradeBook web client (otherwise None).
        """
        raise NotImplementedError("This must be implemented in a subclass of GradeBookEvent")


class SubmissionStart(GradeBookEvent):
    """
    An event representing the start of a new submission.
    """
    def __init__(self, submission_id: int, name: str):
        """
        :param submission_id: The ID of the submission
        :param name: The name of the owner of the new submission
        """
        self.submission_id = submission_id
        self.name = name

    def handle(self, gradebook_instance: "GradeBook") -> ClientUpdate:
        gradebook_instance.start_submission(self.submission_id, self.name)
        return ClientUpdate("update", {
            "update_type": "SubmissionStart",
            "submission_index": self.submission_id
        })


class SubmissionEnd(GradeBookEvent):
    """
    An event representing the end of a submission.
    """
    def __init__(self, log: str):
        """
        :param log: The log for the submission that just ended.
        """
        self.log = log

    def handle(self, gradebook_instance: "GradeBook"):
        gradebook_instance.log_submission(self.log)


class EndOfSubmissions(GradeBookEvent):
    """
    An event representing the end of all of the submissions.
    """
    def __init__(self):
        pass

    def handle(self, gradebook_instance: "GradeBook") -> ClientUpdate:
        gradebook_instance.is_done = True
        return ClientUpdate("done")


class ClientAction(GradeBookEvent):
    """
    Base class for an event that corresponds to an action of a particular GradeBook client.
    """

    class BadSubmissionException(Exception):
        """
        Exception resulting from a bad submission ID in a ClientEvent.
        """
        pass

    def __init__(self, submission_id: int, client_id: int, action: dict):
        """
        :param submission_id: The ID of the submission that this action applies to.
        :param client_id: The ID of the GradeBook client that submitted this action.
        :param action: The action, directly from the GradeBook client that submitted it.
        """
        self.submission_id = submission_id
        self.client_id = client_id
        self.action = action

    def handle(self, gradebook_instance: "GradeBook") -> ClientUpdate:
        grade = gradebook_instance.get_grade(self.submission_id)
        if grade is None:
            raise ClientAction.BadSubmissionException()

        # etc.


class SetGradeItemPoints(GradeBookEvent):
    """
    An event representing that a property of a certain grade item should be set
    to a certain value for the submission currently being graded.
    """
    def __init__(self, name: str, points: int):
        """
        :param name: The name of the grade item to set.
        :param points: The point value to set this grading item to.
        """
        self.name = name
        self.points = points

    def handle(self, gradebook_instance: "GradeBook"):
        raise NotImplementedError()
