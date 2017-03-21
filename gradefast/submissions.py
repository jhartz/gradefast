"""
Contains classes related to submissions. These are shared between the grader and the gradebook.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""


class Submission:
    """
    A submission by a certain student.
    """

    def __init__(self, id: int, name: str, full_name: str, path: str):
        """
        Initialize a new Submission.

        :param id: The unique ID of the submission.
        :param name: The name associated with the submission (i.e. the student)
        :param full_name: The full name of the submission (i.e. the full filename of the folder
            containing the submission)
        :param path: The path of the root of the submission
        """
        self.id = id
        self.name = name
        self.full_name = full_name
        self.path = path

    def __str__(self):
        if self.name != self.full_name:
            return "%s (%s)" % (self.name, self.full_name)
        return self.name

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "full_name": self.full_name,
            "path": self.path
        }
