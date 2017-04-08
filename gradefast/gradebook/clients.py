"""
Classes for interacting between the GradeBook server and GradeBook clients.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

from typing import Any

from gradefast.gradebook import grades, utils


class ClientUpdate:
    """
    Represents an event that the GradeBook server is sending to GradeBook clients.
    """

    _last_id = 0

    def __init__(self, event: str, data: Any = None, requires_authentication: bool = True):
        """
        Create a new ClientUpdate to send to GradeBook clients.

        :param event: The name of the update
        :param data: The data associated with this update (will be json-encoded if it's not a
            string)
        :param requires_authentication: Whether this update should only be sent to authenticated
            clients
        """
        self._event = event
        self._data = data if isinstance(data, str) else utils.to_json(data)
        self._requires_authentication = requires_authentication

        ClientUpdate._last_id += 1
        self._id = ClientUpdate._last_id

    @staticmethod
    def create_update_event(update_type: str, update_data: dict = None) -> "ClientUpdate":
        """
        Create a new ClientUpdate containing an "update" event to send to GradeBook clients.

        :param update_type: The type of "update" event (see connection.js).
        :param update_data: Data corresponding with this type.
        :return: An instance of ClientUpdate
        """
        return ClientUpdate("update", {
            "update_type": update_type,
            "update_data": update_data or {}
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


class ClientAction:
    """
    Represents an action from a GradeBook client that can be applied to a GradeItem.
    """

    class BadSubmissionError(utils.GradeBookPublicError):
        """
        Error resulting from a bad submission ID being passed into this action.
        """
        pass

    class BadActionError(utils.GradeBookPublicError):
        """
        Error resulting from a bad action being passed into this action.
        """
        pass

    def __init__(self, submission_id: int, client_id: int, client_seq: int, action: dict):
        """
        :param submission_id: The ID of the submission that this action applies to.
        :param client_id: The ID of the GradeBook client that submitted this action event.
        :param client_seq: The sequence number from the GradeBook client that submitted this event.
        :param action: The action, directly from the GradeBook client that submitted it.
        """
        self.submission_id = submission_id
        self.client_id = client_id
        self.client_seq = client_seq
        self.action = action

    def apply_to_gradebook(self, gradebook_instance: "GradeBook"):
        grade = gradebook_instance.get_grade(self.submission_id)
        if grade is None:
            raise ClientAction.BadSubmissionError("Invalid submission_id: " +
                                                  str(self.submission_id))

        # Apply this event on the grade
        more_data = self._apply_to_grade(grade)

        # Recalculate the score, etc.
        data = grade.to_plain_data()
        data.update({
            "submission_id": self.submission_id
        })
        if more_data:
            data.update(more_data)

        # Update any GradeBook clients of the changes
        return data

    def _apply_to_grade(self, grade: grades.SubmissionGrade) -> dict:
        action = self.action
        action_type = action["type"] if "type" in action else None

        # We return this if we've finished successfully
        # At the end of the method, if we still haven't returned, we raise an error.
        done = {
            "originating_client_id": self.client_id,
            "originating_client_seq": self.client_seq
        }

        # It's possible we have no actual action to take, and that's okay
        if not action_type:
            return done

        if action_type == "SET_LATE":
            # Set whether the submission is marked as late
            if "is_late" in action:
                grade.set_late(bool(action["is_late"]))
                return done

        if action_type == "SET_OVERALL_COMMENTS":
            # Set the overall comments of the submission
            if "overall_comments" in action:
                grade.set_overall_comments(action["overall_comments"])
                return done

        # All of the other action types have a path
        if "path" not in action:
            raise ClientAction.BadActionError("Action missing a path", action=action)
        path = action["path"]

        if action_type == "ADD_HINT":
            # Add a hint by changing the grade structure (MUA HA HA HA)
            if "content" in action and \
                    "name" in action["content"] and "value" in action["content"]:
                grade.add_hint_to_all_grades(path,
                                             action["content"]["name"],
                                             action["content"]["value"])
                return done

        if action_type == "EDIT_HINT":
            # Edit a hint by changing the grade structure (MUA HA HA HA)
            if "index" in action and "content" in action and \
                    "name" in action["content"] and "value" in action["content"]:
                grade.replace_hint_for_all_grades(path,
                                                  action["index"],
                                                  action["content"]["name"],
                                                  action["content"]["value"])
                return done

        # All of the rest of the action types operate directly on a grade item
        grade_item = grade.get_by_path(path)

        # They also all have a value
        if "value" not in action:
            raise ClientAction.BadActionError("Action missing a value", action=action)
        value = action["value"]

        if action_type == "SET_ENABLED":
            grade_item.set_enabled(bool(value))
            return done

        if action_type == "SET_SCORE":
            if isinstance(grade_item, grades.GradeScore):
                grade_item.set_effective_score(value)
                return done

        if action_type == "SET_COMMENTS":
            if isinstance(grade_item, grades.GradeScore):
                grade_item.set_comments(value)
                return done

        if action_type == "SET_HINT" and "index" in action:
            grade_item.set_hint(action["index"], bool(value))
            return done

        # If we're still here, something went wrong...
        raise ClientAction.BadActionError("Action does not have a valid type", action=action)
