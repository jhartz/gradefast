#!/usr/bin/env python3
"""
The Gradebook HTTP server.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jhartz@mail.rit.edu>
"""
import json, queue, logging, copy, csv, io

from flask import Flask, request, Response, render_template


class ServerSentEvent:
    """
    Represents an event that the server is sending to a client event stream.
    """

    last_id = 0

    def __init__(self, event, data):
        self.event = event
        self.data = data
        ServerSentEvent.last_id += 1
        self._id = ServerSentEvent.last_id

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


class BadStructureException(Exception):
    """Exception resulting from a bad grade structure passed into Grader"""
    pass


class BadPathException(Exception):
    """
    Exception resulting from a bad path provided to one of the
    SubmissionGrade.set_... methods
    """
    pass


class BadValueException(Exception):
    """
    Exception resulting from a bad value provided to one of the
    SubmissionGrade.set_... methods
    """
    pass


class SubmissionGrade:
    """Represents a submission's grade"""
    def __init__(self, name, grade_structure):
        """
        :param name: The name of the owner of the submission being graded
        :param grade_structure: A list of grading items (see GradeBook)
        """
        self.name = name
        self._grade_structure = copy.deepcopy(grade_structure)
        self._is_late = False

    def _get_location(self, path):
        """
        Find a path in the grade structure.
        """
        location = self._grade_structure
        try:
            path_indexes = [int(index) for index in path]
            # Find this point in the grade structure
            for index in path_indexes[:-1]:
                location = location[index]["grades"]
            location = location[path_indexes[-1]]
        except:
            raise BadPathException()
        return location

    def set_late(self, is_late):
        """
        Set whether this submission is late.
        """
        self._is_late = is_late

    def set_points(self, path, points):
        """
        Set the points for a section of this submission's grade.
        """
        path = path.split(".")
        if len(path) < 2 or path[0] != "points":
            raise BadPathException()
        location = self._get_location(path[1:])

        # Store the earned points
        try:
            earned_points = float(points)
        except:
            raise BadValueException()
        location["_earned_points"] = earned_points

    def set_comments(self, path, comments):
        """
        Set the comments for a section of this submission's grade.
        """
        path = path.split(".")
        if len(path) < 2 or path[0] != "comments":
            raise BadPathException()
        location = self._get_location(path[1:])

        # Store the comments
        location["_comments"] = str(comments.replace("\r\n", "\n"))

    def set_deduction(self, path, is_set):
        """
        Enable or disable a deduction for a section of this submission's grade.
        """
        path = path.split(".")
        if len(path) < 3 or path[0] != "deduction":
            raise BadPathException()
        location = self._get_location(path[1:-1])
        try:
            location = location["deductions"][int(path[-1])]
        except:
            raise BadPathException()

        # Store the deduction
        location["_set"] = is_set

    @staticmethod
    def _get_late_deduction(score, percent_to_deduct, precision=0):
        """
        Get the amount of points to lop off of a section if the submission is
        late.
        
        :param score: The raw score
        :param percent_to_deduct: The percentage to lop off
        :param precision: The amount of decimal places
        """
        return max(0, round(score * (percent_to_deduct / 100.0), precision))

    def _get_grades_score(self, grades):
        """
        Get the points for a subset of a grade structure.
        
        :param grades: The subset of self._grade_structure (a list of dict)
        :return: The total points for this subset
        """
        total = 0
        for grade in grades:
            if "grades" in grade:
                # We have sub-grades
                score = self._get_grades_score(grade["grades"])
                if "deductPercentIfLate" in grade and self._is_late:
                    # It's late! Deduct
                    score -= self._get_late_deduction(
                        score,
                        grade["deductPercentIfLate"])
                # Add to the total
                total += score
            else:
                # Just a normal grade item
                if "_earned_points" in grade:
                    total += grade["_earned_points"]
                else:
                    # Default amount of points
                    total += grade["points"]
        return total

    def get_total_score(self):
        """
        Calculate the total score (all points added up) for this submission.
        """
        return self._get_grades_score([{
            "grades": self._grade_structure
        }])

    def _get_grades_comments(self, grades):
        """
        Get the comments for a subset of a grade structure.
        
        :param grades: The subset of self._grade_structure (a list of dict)
        :return: The comments for this subset
        """
        comments = ""
        for grade in grades:
            if "grades" in grade:
                # Add the name of this grading section
                comments += "<p><b><u>%s</u></b></p>" % grade["name"]

                # We have sub-grades
                if "deductPercentIfLate" in grade and self._is_late:
                    # Add the "late" message
                    comments += "<p><b>-%s:</b> <i>Turned in late</i></p>" % \
                        self._get_late_deduction(
                            self._get_grades_score(grade["grades"]),
                            grade["deductPercentIfLate"])
                # Add the comments for all the sub-grades
                comments += "<blockquote>"
                comments += self._get_grades_comments(grade["grades"])
                comments += "</blockquote>"
            else:
                # Add the name of this grading section
                comments += "<p><u>%s</u>" % grade["name"]
                # NOTE: We're missing a </p> on purpose

                # Just a normal grade item
                earned_points = grade["points"]
                if "_earned_points" in grade:
                    earned_points = grade["_earned_points"]
                comments += "<br>Score: %s / %s" % \
                    (earned_points, grade["points"])
                # Add deductions, if applicable
                if "deductions" in grade:
                    for deduction in grade["deductions"]:
                        if "_set" in deduction and deduction["_set"]:
                            comments += "<br><b>-%s:</b> <i>%s</i>" % \
                                (deduction["minus"], deduction["name"])

                # Finally, close that paragraph
                comments += "</p>"

                # Now, add any comments
                if "_comments" in grade and grade["_comments"]:
                    comments += "<blockquote>%s</blockquote>" % \
                        "<br>".join(grade["_comments"].split("\n"))
        return comments

    def get_comments(self):
        """
        Patch together all the grade comments for this submission.
        """
        return """<div style="font-family: Helvetica, Arial, sans-serif; line-height: 1.3;">%s</div>""" % \
            self._get_grades_comments([{
                "name": "Grading Breakdown",
                "grades": self._grade_structure
            }])


class GradeBook:
    """Represents a grade book with submissions and grade structures."""
    def __init__(self, grade_structure):
        """
        Create a WSGI app representing a grade book.
        
        A grading structure is composed of a list of grading items. This is
        detailed in the documentation for the YAML format.
        
        :param grade_structure: A list of grading items
        """
        # Check validity of _grade_structure
        self._grade_structure = grade_structure
        self._max_score = self._check_grade_structure()

        self._grades = []
        self._subscriptions = []
        self._is_done = False

        app = Flask(__name__)
        self._app = app

        # Now, initialize the routes for the app

        # Index page
        @app.route("/gradefast/gradebook/")
        def index():
            return render_template(
                "gradebook.html",
                gradeStructure=json.dumps(self._grade_structure),
                maxScore=self._max_score,
                isDone=json.dumps(self._is_done))

        # AJAX calls regarding grades
        @app.route("/gradefast/gradebook/_/<command>", methods=["POST"])
        def gradebook_ajax(command):
            grade = self._get_grade(request.form["id"])
            if grade is None:
                return "Invalid grade ID"
            try:
                if command == "late":
                    grade.set_late(request.form["is_late"] == "true")
                elif command == "points":
                    grade.set_points(request.form["path"],
                                     request.form["value"])
                elif command == "comments":
                    grade.set_comments(request.form["path"],
                                       request.form["value"])
                elif command == "deduction":
                    grade.set_deduction(request.form["path"],
                                        request.form["value"])
            except BadPathException:
                return "Bad path"
            except BadValueException:
                return "Bad value"
            except Exception as ex:
                print("GRADEBOOK AJAX HANDLER EXCEPTION:", ex)
                return "Look what you did..."
            # All good
            return json.dumps({
                "status": "Aight",
                "currentScore": grade.get_total_score()
            })

        # Grades CSV file
        @app.route("/gradefast/gradebook/grades.csv")
        def gradebook_csv():
            csv_stream = self._get_csv()

            def gen():
                try:
                    while True:
                        line = csv_stream.readline()
                        if line == "":
                            break
                        yield line
                except GeneratorExit:
                    pass
            return Response(gen(), mimetype="text/csv")

        # Grades JSON file
        @app.route("/gradefast/gradebook/grades.json")
        def gradebook_json():
            return Response(self._get_json(), mimetype="application/json")

        # Event stream
        @app.route("/gradefast/gradebook/events")
        def gradebook_events():
            def gen():
                q = queue.Queue()
                self._subscriptions.append(q)
                try:
                    while True:
                        result = q.get()
                        ev = ServerSentEvent(result["event"], result["data"])
                        yield ev.encode()
                        if ev.event == "done":
                            break
                except GeneratorExit:
                    pass
                finally:
                    self._subscriptions.remove(q)
            return Response(gen(), mimetype="text/event-stream")

    def _check_grade_structure(self, st=None):
        """
        Check a grade structure and raise a BadStructureException if the
        structure is invalid. If not, return the maximum score.
        
        :param st: The structure to check. If not provided, defaults to
                   self._grade_structure
        :return: The maximum score for this grade structure.
        """
        if st is None:
            st = self._grade_structure
        if not isinstance(st, list):
            raise BadStructureException("Grade structure is not a list")

        max_score = 0

        for grade in st:
            if not isinstance(grade["name"], str) or not grade["name"]:
                raise BadStructureException("Grade item missing a name")
            if "grades" in grade:
                if "deductPercentIfLate" in grade:
                    if grade["deductPercentIfLate"] < 0 or \
                       grade["deductPercentIfLate"] > 100:
                        raise BadStructureException(
                            "Grade item has an invalid deductPercentIfLate")
                max_score += self._check_grade_structure(grade["grades"])
            elif "points" in grade:
                max_score += grade["points"]
                if "deductions" in grade:
                    for deduction in grade["deductions"]:
                        if not "name" in deduction:
                            raise BadStructureException(
                                "Deduction missing name")
                        if not "minus" in deduction:
                            raise BadStructureException(
                                "Deduction missing points")
            else:
                raise BadStructureException(
                    "Grade item needs one of points or grades")

        return max_score

    def _get_grade(self, id_):
        """
        Test whether an ID is valid and, if so, get the Grade corresponding to
        it.
        
        :param id_: The ID to test (can be any type)
        :return: a Grade if valid, or None otherwise
        """
        int_id = None
        try:
            int_id = int(id_)
        except ValueError:
            pass
        if int_id is None:
            return None
        if int_id < 0 or int_id >= len(self._grades):
            return None
        return self._grades[int_id]

    def _send_event(self, event, data):
        """
        Send an event to any open gradebook clients.
        
        The following are valid events:
          * "start_submission": A new submission has just started. The data
            has 2 properties: "name" (the name of the owner of the submission),
            and "id" (the ID of the submission in this gradebook).
          * "done": There are no more submissions. The data has no properties.
        
        :param event: The name of the event (a string)
        :param data: The data associated with the event (a dict)
        """
        # Send this event to any open gradebook clients
        for q in self._subscriptions:
            q.put({
                "event": event,
                "data": json.dumps(data)
            })

    def start_submission(self, name):
        """
        Initialize a new submission and tell any open gradebook clients about
        it.
        
        :param name: The name of the owner of the submission.
        """
        # Make a new Grade object for this submission
        grade = SubmissionGrade(name, self._grade_structure)
        id_ = len(self._grades)
        self._grades.append(grade)
        self._send_event("start_submission", {
            "name": name,
            "id": id_
        })

    def end_of_submissions(self):
        """
        Tell any open gradebook clients that there are no more submissions and
        total up all the grades.
        """
        self._is_done = True
        self._send_event("done", {
            "grades": self._get_grades()
        })

    def _get_grades(self):
        """
        Return a list of dicts representing the scores and comments for each
        submission.
        """
        return [{
            "name": grade.name,
            "score": grade.get_total_score(),
            "comments": grade.get_comments()
        } for grade in self._grades]

    def _get_csv(self):
        """
        Return a stream representing the grades as a CSV file.
        """
        csv_stream = io.StringIO()
        csv_writer = csv.writer(csv_stream)
        csv_writer.writerow(["Name", "Score", "Comments"])
        for grade in self._get_grades():
            csv_writer.writerow([
                grade["name"],
                grade["score"],
                grade["comments"]
            ])
        csv_stream.seek(0)
        return csv_stream

    def _get_json(self):
        """
        Return a string representing the grades as JSON.
        """
        return json.dumps(self._get_grades())

    def run(self, hostname, port, log_level=logging.ERROR):
        """
        Start the Flask server (using Werkzeug internally).
        
        :param hostname: The hostname to run on
        :param port: The port to run on
        :param log_level: The level to set the Werkzeug logger at
        """
        # Set logging level
        server_log = logging.getLogger("werkzeug")
        server_log.setLevel(log_level)
        # Start the server
        self._app.run(hostname, port, threaded=True)

    def get_wsgi_app(self):
        """
        Get a function representing the server as a WSGI app.
        """
        return self._app.wsgi_app

