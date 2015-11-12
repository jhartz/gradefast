"""
Events that can be passed to an instance of the Gradebook class.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jhartz@mail.rit.edu>
"""


class GradebookEvent:
    def handle(self, gradebook):
        raise NotImplementedError("This must be implemented in a subclass of "
                                  "GradebookEvent")


class SubmissionStart(GradebookEvent):
    def __init__(self, name):
        self.name = name

    def handle(self, gradebook):
        gradebook.start_submission(self.name)


class SubmissionEnd(GradebookEvent):
    def __init__(self, log):
        self.log = log

    def handle(self, gradebook):
        gradebook.log_submission(self.log)


class EndOfSubmissions(GradebookEvent):
    def __init__(self):
        pass

    def handle(self, gradebook):
        gradebook.end_of_submissions()


class SetGradeItem(GradebookEvent):
    def __init__(self, name, points):
        self.name = name
        self.points = points
