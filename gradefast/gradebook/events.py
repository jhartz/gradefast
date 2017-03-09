"""
This module contains 2 types of events:
    GradeBookEvent (events that are applied to a GradeBook instance), and
    ClientUpdate (events that are sent to GradeBook JavaScript clients).

GradeBookEvent instances can return an instance of a ClientUpdate when they are applied to a
GradeBook. This allows actions taken on GradeBooks to send updates to GradeBook JavaScript clients
after updating the GradeBook.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

from typing import Any, Optional

from . import grades, utils


class ClientUpdate:
    """
    Represents an event that the server is sending to GradeBook JavaScript clients.
    """

    last_id = 0

    def __init__(self, event: str, data: Any = None, requires_authentication: bool = True):
        """
        Create a new ClientUpdate to send to GradeBook JavaScript clients.

        :param event: The name of the update
        :param data: The data associated with this update (will be json-encoded if it's not a
            string)
        :param requires_authentication: Whether this update should only be sent to authenticated
            clients
        """
        self._event = event
        self._data = data if isinstance(data, str) else utils.to_json(data)
        self._requires_authentication = requires_authentication

        ClientUpdate.last_id += 1
        self._id = ClientUpdate.last_id

    @staticmethod
    def create_update_event(type: str, data: dict = None) -> "ClientUpdate":
        """
        Create a new ClientUpdate containing an "update" event to send to GradeBook JavaScript
        clients.

        :param type: The type of "update" event (see connection.js).
        :param data: Data corresponding with this type.
        :return: An instance of ClientUpdate
        """
        return ClientUpdate("update", {
            "update_type": type,
            "update_data": data or {}
        })

    def requires_authentication(self):
        return self._requires_authentication

    def encode(self) -> str:
        """
        Return the event in the HTML5 Server-Sent Events format.

        https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events
        """
        if not self._data:
            return ""

        result = ""
        result += "id: " + str(self._id) + "\n"
        if self._event:
            result += "event: " + str(self._event) + "\n"
        result += "data: " + "\ndata:".join(str(self._data).split("\n"))
        result += "\n\n"
        return result


class GradeBookEvent:
    """
    Base class for an event sent to an instance of the GradeBook web server from any source.
    """
    def apply(self, gradebook_instance: "GradeBook") -> Optional[ClientUpdate]:
        """
        Execute this event's actions on a GradeBook. This must be overridden in subclasses.

        This method should never be called directly; instead, an instance of a subclass of
        GradeBookEvent should be passed to GradeBook's apply_event method.

        :param gradebook_instance: The GradeBook instance to perform the action on.
        :return: A populated ClientUpdate, if there is an event that needs to be passed to the
            GradeBook web client (otherwise None).
        """
        raise NotImplementedError("This must be implemented in a subclass of GradeBookEvent")


class SubmissionStart(GradeBookEvent):
    """
    A GradeBook event representing the start of a new submission.
    """
    def __init__(self, submission_id: int, name: str):
        """
        :param submission_id: The ID of the submission
        :param name: The name of the owner of the new submission
        """
        self.submission_id = submission_id
        self.name = name

    def apply(self, gradebook_instance: "GradeBook") -> ClientUpdate:
        gradebook_instance.start_submission(self.submission_id, self.name)
        return ClientUpdate.create_update_event("SUBMISSION_START", {
            "submission_id": self.submission_id
        })


class SubmissionEnd(GradeBookEvent):
    """
    A GradeBook event representing the end of a submission.
    """
    def __init__(self, log: str):
        """
        :param log: The log for the submission that just ended.
        """
        self.log = log

    def apply(self, gradebook_instance: "GradeBook") -> None:
        gradebook_instance.log_submission(self.log)


class EndOfSubmissions(GradeBookEvent):
    """
    A GradeBook event representing the end of all of the submissions.
    """
    def __init__(self):
        pass

    def apply(self, gradebook_instance: "GradeBook") -> ClientUpdate:
        gradebook_instance.is_done = True
        return ClientUpdate.create_update_event("END_OF_SUBMISSIONS")


class ActionEvent(GradeBookEvent):
    """
    Base class for GradeBook events that correspond to actions that affects a specific submission
    in the GradeBook.
    """

    class BadSubmissionException(Exception):
        """
        Exception resulting from a bad submission ID in an ActionEvent.
        """
        pass

    def __init__(self, submission_id: Optional[int] = None):
        """
        :param submission_id: The ID of the submission that this action applies to. If not
            provided, then the current submission is used.
        """
        self.submission_id = submission_id

    def apply(self, gradebook_instance: "GradeBook") -> ClientUpdate:
        submission_id = self.submission_id
        if submission_id is None:
            submission_id = gradebook_instance.get_current_submission_id()

        grade = gradebook_instance.get_grade(submission_id)
        if grade is None:
            raise ActionEvent.BadSubmissionException()

        # Apply this event on the grade
        more_data = self.apply_to_grade(grade)

        # Recalculate the score, etc.
        points_earned, points_total, _ = grade.get_score()
        data = {
            "submission_id": submission_id,
            "name": grade.name,
            "is_late": grade.is_late,
            "overall_comments": grade.overall_comments,
            "current_score": points_earned,
            "max_score": points_total,
            "grades": grade.get_plain_grades()
        }
        if more_data:
            data.update(more_data)

        # Update any GradeBook JavaScript clients of the changes
        return ClientUpdate.create_update_event("SUBMISSION_UPDATE", data)

    def apply_to_grade(self, grade: grades.SubmissionGrade) -> Optional[dict]:
        """
        Execute this event's actions on a SubmissionGrade. This must be overridden in subclasses.

        :param grade: The SubmissionGrade instance to perform the action on.
        :return: A dictionary of extra items to send back to GradeBook JavaScript clients with the
            update event (if applicable).
        """
        raise NotImplementedError("This must be implemented in a subclass of ActionEvent")


class ClientActionEvent(ActionEvent):
    """
    An ActionEvent representing an action from a GradeBook client.
    """

    class BadActionException(Exception):
        """
        Exception resulting from a bad action type passed to a ClientActionEvent.
        """
        pass

    def __init__(self, submission_id: int, client_id: int, client_seq: int, action: dict):
        """
        :param submission_id: The ID of the submission that this action applies to.
        :param client_id: The ID of the JavaScript GradeBook client that submitted this action
            event.
        :param client_seq: The sequence number from the JavaScript GradeBook client that submitted
            this action event.
        :param action: The action, directly from the GradeBook client that submitted it.
        """
        super().__init__(submission_id)
        self.client_id = client_id
        self.client_seq = client_seq
        self.action = action

    def apply_to_grade(self, grade: grades.SubmissionGrade) -> dict:
        action = self.action
        type = action["type"] if "type" in action else None

        # We return this if we've finished successfully
        # At the end of the method, if we still haven't returned, we raise an exception.
        done = {
            "originating_client_id": self.client_id,
            "originating_client_seq": self.client_seq
        }

        # It's possible we have no actual action to take, and that's okay
        if not type:
            return done

        if type == "SET_LATE":
            # Set whether the submission is marked as late
            if "is_late" in action:
                grade.is_late = bool(action["is_late"])
                return done

        if type == "SET_OVERALL_COMMENTS":
            # Set the overall comments of the submission
            if "overall_comments" in action:
                grade.overall_comments = action["overall_comments"]
                return done

        # All of the other action types have a path
        if "path" not in action:
            raise ClientActionEvent.BadActionException()
        path = action["path"]

        if type == "ADD_HINT":
            # Add a hint by changing the grade structure (MUA HA HA HA)
            if "content" in action and \
                    "name" in action["content"] and "value" in action["content"]:
                grade.add_content_to_all_grades(
                    path,
                    "hints",
                    {
                        "name": action["content"]["name"],
                        "value": grades.make_number(action["content"]["value"])
                    })
                return done

        if type == "EDIT_HINT":
            # Edit a hint by changing the grade structure (MUA HA HA HA)
            if "index" in action and "content" in action and \
                    "name" in action["content"] and "value" in action["content"]:
                grade.replace_content_for_all_grades(
                    path,
                    "hints",
                    action["index"],
                    {
                        "name": action["content"]["name"],
                        "value": grades.make_number(action["content"]["value"])
                    })
                return done

        # All of the rest of the action types operate directly on a grade item
        grade_item = grade.get_by_path(path)

        # They also all have a value
        if "value" not in action:
            raise ClientActionEvent.BadActionException()
        value = action["value"]

        if type == "SET_ENABLED":
            grade_item.set_enabled(bool(value))
            return done

        if type == "SET_SCORE":
            if isinstance(grade_item, grades.GradeScore):
                grade_item.set_score(value)
                return done

        if type == "SET_COMMENTS":
            if isinstance(grade_item, grades.GradeScore):
                grade_item.set_comments(value)
                return done

        if type == "SET_HINT" and "index" in action:
            grade_item.set_hint(action["index"], bool(value))
            return done

        # If we're still here, something went wrong...
        raise ClientActionEvent.BadActionException()


class SetGradeItemScore(ActionEvent):
    """
    An ActionEvent representing that a grade item (identified by name) should be set to a certain
    score for the current submission.
    """

    def __init__(self, name: str, score: int):
        """
        :param name: The name of the grade item to set.
        :param score: The score to set this grade item to.
        """
        super().__init__()
        self.name = name
        self.score = score

    def apply_to_grade(self, grade: grades.SubmissionGrade) -> None:
        for grade_item in grade.get_by_name(self.name):
            if isinstance(grade_item, grades.GradeScore):
                grade_item.set_score(self.score)
