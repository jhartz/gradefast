"""
Events that can be passed to an instance of the GradeBook class.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jhartz@mail.rit.edu>
"""


class GradeBookEvent:
    """
    Base class for an event sent to an instance of the GradeBook web server.
    """
    def handle(self, gradebook):
        """
        Method that executes actions on a GradeBook corresponding to this
        event. This must be overridden in subclasses.

        :param gradebook: The GradeBook instance to perform the action on.
        """
        raise NotImplementedError("This must be implemented in a subclass of "
                                  "GradeBookEvent")


class SubmissionStart(GradeBookEvent):
    """
    An event representing the start of a new submission.
    """
    def __init__(self, index, name):
        """
        :param index: The index of the submission
        :param name: The name of the owner of the new submission
        """
        self.index = index
        self.name = name

    def handle(self, gradebook):
        gradebook.start_submission(self.index, self.name)


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
        gradebook.end_of_submissions()


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
