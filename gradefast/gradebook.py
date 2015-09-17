#!/usr/bin/env python3
"""
The Gradebook HTTP server.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jhartz@mail.rit.edu>
"""
import json
import queue
import logging
import csv
import io
from collections import OrderedDict
import traceback

from flask import Flask, request, Response, render_template


FEEDBACK_HTML_TEMPLATES = {
    # (content)
    "base": """<div style="font-family: Helvetica, Arial, sans-serif; """
            """font-size: 10pt; line-height: 1.3;">%s"""
            """<p style="font-size: 11pt;">%s</p></div>""",

    # (title, earned points, total points)
    "section_header": "<p><b><u>%s</u></b><br>Section Score: %s / %s</p>",
    # (points deducted, percentage deducted)
    "section_deduction": "<p><b>-%s</b> (%s%%)<b>:</b> "
                         "<i>Turned in late</i></p>",
    # (content)
    "section_body": """<div style="margin-left: 15px;">%s</div>""",

    # (title, earned points, total points)
    "item_header": "<p><u>%s</u><br>Score: %s / %s</p>",
    # (points deducted, reason)
    "item_deduction": """<div style="text-indent: -20px; margin-left: 20px;">"""
                      "<b>-%s:</b> <i>%s</i></div>",
    # (content)
    "item_body": "<p>%s</p>"
}


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
        self._grade_structure = grade_structure
        self._grade_data = {}

        self.is_late = False
        self.overall_comments = ""

    def _get_location(self, path):
        """
        Find a path in the grade structure.

        :param path: A string with a dot-separated path of indices representing
            a location in self._grade_structure
        :return: A tuple with (structure, data) where "structure" is from
            self._grade_structure and "data" is from self._grade_data
        """
        structure = self._grade_structure
        data = self._grade_data
        try:
            path_indexes = [int(index) for index in path]

            # Find this point in the grade structure
            for index in path_indexes[:-1]:
                structure = structure[index]["grades"]
                # For the _grade_data section, we might have to make some
                # shit if it hasn't been initialized yet
                if index not in data:
                    data[index] = {
                        "grades": {}
                    }
                data = data[index]["grades"]

            # Last location:
            index = path_indexes[-1]
            # Move to the last location in structure
            structure = structure[index]
            # Move to the last location in data
            if index not in data:
                data[index] = {}
            data = data[index]
        except:
            raise BadPathException()
        return structure, data

    @staticmethod
    def enumerate_grades(grade_structure, grade_data):
        """
        Enumerate over both grade_structure and grade_data at once.

        :param grade_structure: A subset of self._grade_structure
        :param grade_data: A subset of self._grade_data
        """
        for index, structure in enumerate(grade_structure):
            if index not in grade_data:
                grade_data[index] = {
                    "grades": {}
                }
            yield index, structure, grade_data[index]

    def set_points(self, path, points):
        """
        Set the points for a section of this submission's grade.
        """
        path = path.split(".")
        if len(path) < 2 or path[0] != "points":
            raise BadPathException()
        structure, data = self._get_location(path[1:])

        # Store the earned points
        try:
            earned_points = float(points)
        except:
            raise BadValueException()
        # Make it an int if we can
        if int(earned_points) == earned_points:
            earned_points = int(earned_points)
        data["_earned_points"] = earned_points

    def set_comments(self, path, comments):
        """
        Set the comments for a section of this submission's grade.
        """
        path = path.split(".")
        if len(path) < 2 or path[0] != "comments":
            raise BadPathException()
        structure, data = self._get_location(path[1:])

        # Store the comments
        data["_comments"] = str(comments)

    def set_deduction(self, path, is_set):
        """
        Enable or disable a deduction for a section of this submission's grade.
        """
        path = path.split(".")
        if len(path) < 3 or path[0] != "deduction":
            raise BadPathException()
        structure, data = self._get_location(path[1:-1])
        try:
            # Find the location to store our deduction data in
            index = int(path[-1])
            if "deductions" not in data:
                data["deductions"] = {}
            if index not in data["deductions"]:
                data["deductions"][index] = {}
            data = data["deductions"][index]
        except:
            raise BadPathException()

        # Store the deduction
        data["_set"] = is_set

    def add_deduction_to_all_grades(self, path, name, minus):
        """
        Add a new possible deduction to ALL grade structures (by modifying
        self._grade_structure, since that's shared by all SubmissionGrade
        objects that use it).
        """
        path = path.split(".")
        if len(path) < 2 or path[0] != "":
            raise BadPathException()
        structure, data = self._get_location(path[1:])
        if "deductions" not in structure:
            structure["deductions"] = []

        # Convert the minus (string) to a float
        try:
            minus = float(minus)
        except ValueError:
            raise BadValueException()

        # Make it an int if we can
        if int(minus) == minus:
            minus = int(minus)

        # Add the new deduction
        structure["deductions"].append({
            "name": name,
            "minus": minus
        })

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

    @staticmethod
    def get_point_titles(grade_structure):
        """
        Get a list of the titles for individual point items which corresponds
        to the lists that are the third part of the tuples of the return value
        of _get_grades_score.

        :param grade_structure: The grade structure to get item titles from
        :return: A list of item titles
        """
        items = []
        for grade in grade_structure:
            if "grades" in grade:
                # We have sub-grades
                items += [grade["name"] + ": " + name for name in
                          SubmissionGrade.get_point_titles(grade["grades"])]
            else:
                items.append(grade["name"])
        return items

    def _get_subset_values(self, grade_structure, grade_data, path):
        """
        Get the values for each individual grade parameter (point values,
        deductions enabled, and comments for each grading item) for a subset of
        a grade structure.

        :param grade_structure: The subset of self._grade_structure (a list of
            dict)
        :param grade_data: The subset of self._grade_data that corresponds with
            `grade_structure`
        :param path: The path to this subset
        :return: A dict representing the ID of the grading item (in the HTML
            page) and its value.
        """
        values = {}
        for index, structure, data in SubmissionGrade.enumerate_grades(
                grade_structure, grade_data):

            sub_path = path + "." + str(index)
            if "grades" in structure:
                # We have sub-grades
                values.update(self._get_subset_values(structure["grades"],
                                                      data["grades"],
                                                      sub_path))
            else:
                # Now, do the hard work
                # Firstly, add the point value
                values["points" + sub_path] = structure["points"] \
                    if "_earned_points" not in data else data["_earned_points"]
                # Next, the comments
                values["comments" + sub_path] = "" if "_comments" not in data \
                    else data["_comments"]
                # Finally, the deduction values
                if "deductions" in structure:
                    if "deductions" not in data:
                        data["deductions"] = {}
                    for dindex, deduction in enumerate(structure["deductions"]):
                        is_set = dindex in data["deductions"] and \
                                 "_set" in data["deductions"][dindex] and \
                                 data["deductions"][dindex]["_set"]
                        values["deduction" + sub_path + "." + str(dindex)] = \
                            is_set
        return values

    def get_values(self):
        """
        Get the values for each individual grade parameter (point values,
        deductions enabled, and comments for each grading item).

        :return: A dict representing the ID of the grading item (in the HTML
            page) and its value.
        """
        return self._get_subset_values(self._grade_structure,
                                       self._grade_data, "")

    def _get_subset_score(self, grade_structure, grade_data):
        """
        Get the points for a subset of a grade structure.
        
        :param grade_structure: The subset of self._grade_structure (a list of
            dict)
        :param grade_data: The subset of self._grade_data that corresponds with
            `grade_structure`
        :return: A tuple with the points earned for this subset (int), the
            total points possible for this subset (int), and the individual
            point scores for this subset (list of (str, int) tuples).
        """
        points_earned = 0.0
        points_possible = 0.0
        individual_points = []

        for index, structure, data in SubmissionGrade.enumerate_grades(
                grade_structure, grade_data):

            if "grades" in structure:
                # We have sub-grades
                section_earned, section_possible, section_points = \
                    self._get_subset_score(structure["grades"],
                                           data["grades"])
                if "deductPercentIfLate" in structure and self.is_late:
                    # It's late! Deduct
                    section_earned -= self._get_late_deduction(
                        section_earned,
                        structure["deductPercentIfLate"])
                # Add to the total
                points_earned += section_earned
                points_possible += section_possible
                if "name" in structure:
                    individual_points += [(structure["name"] + ": " + name,
                                           score)
                                          for name, score in section_points]
                else:
                    individual_points += section_points
            else:
                # Just a normal grade item
                points_possible += structure["points"]
                if "_earned_points" in data:
                    points_earned += data["_earned_points"]
                    individual_points.append((structure["name"],
                                              data["_earned_points"]))
                else:
                    # Default amount of points
                    points_earned += structure["points"]
                    individual_points.append((structure["name"],
                                              structure["points"]))

        # Make everything an int if we can
        if int(points_earned) == points_earned:
            points_earned = int(points_earned)
        if int(points_possible) == points_possible:
            points_possible = int(points_possible)

        return points_earned, points_possible, individual_points

    def get_score(self):
        """
        Calculate the total score (all points added up) for this submission.

        :return: A tuple with the points earned for this submission (int), the
            total points possible for this submission (int), and the individual
            point scores for this submission (list of (str, int) tuples).
        """
        return self._get_subset_score(self._grade_structure, self._grade_data)

    def _get_subset_feedback(self, grade_structure, grade_data):
        """
        Get the feedback for a subset of a grade structure.
        
        :param grade_structure: The subset of self._grade_structure (a list of
            dict)
        :param grade_data: The subset of self._grade_data that corresponds with
            `grade_structure`
        :return: The feedback, including score and comments, for this subset
        """
        feedback = ""
        for index, structure, data in SubmissionGrade.enumerate_grades(
                grade_structure, grade_data):

            if "grades" in structure:
                # We have sub-grades
                points_earned, points_possible, _ = self._get_subset_score(
                    structure["grades"], data["grades"])
                # Add the name of this grading section and the total score
                feedback += FEEDBACK_HTML_TEMPLATES["section_header"] % (
                    structure["name"],
                    points_earned,
                    points_possible
                )

                # Check if it was late and, if so, add that deduction
                if "deductPercentIfLate" in structure and self.is_late:
                    # Add the "late" message
                    feedback += FEEDBACK_HTML_TEMPLATES["section_deduction"] % \
                        (
                            self._get_late_deduction(
                                points_earned,
                                structure["deductPercentIfLate"]),
                            structure["deductPercentIfLate"])

                # Add the feedback for all the sub-grades
                feedback += FEEDBACK_HTML_TEMPLATES["section_body"] % \
                    self._get_subset_feedback(structure["grades"],
                                              data["grades"])
            else:
                # Just a normal grade item
                earned_points = structure["points"]
                if "_earned_points" in data:
                    earned_points = data["_earned_points"]

                feedback += FEEDBACK_HTML_TEMPLATES["item_header"] % \
                    (structure["name"], earned_points, structure["points"])

                # Add deductions, if applicable
                if "deductions" in structure:
                    # Make sure we have data["deductions"]
                    if "deductions" not in data:
                        data["deductions"] = {}
                    for dindex, deduction in enumerate(structure["deductions"]):
                        if dindex in data["deductions"] and \
                                "_set" in data["deductions"][dindex] and \
                                data["deductions"][dindex]["_set"]:
                            feedback += FEEDBACK_HTML_TEMPLATES[
                                            "item_deduction"] % \
                                (deduction["minus"], deduction["name"])

                # Now, add any comments
                if "_comments" in data and data["_comments"]:
                    feedback += FEEDBACK_HTML_TEMPLATES["item_body"] % \
                        "<br>".join(data["_comments"].splitlines())
        return feedback

    def get_feedback(self):
        """
        Patch together all the grade comments for this submission.
        """
        return FEEDBACK_HTML_TEMPLATES["base"] % (
            self._get_subset_feedback(self._grade_structure, self._grade_data),
            "<br>".join(self.overall_comments.splitlines()))


class GradeBook:
    """Represents a grade book with submissions and grade structures."""
    def __init__(self, grade_structure, grade_name=None):
        """
        Create a WSGI app representing a grade book.
        
        A grading structure is composed of a list of grading items. This is
        detailed in the documentation for the YAML format.
        
        :param grade_structure: A list of grading items
        :param grade_name: A name for whatever we're grading
        """
        self._grade_name = grade_name or "grades"

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
            # The "current submission" is the most recent grade
            current_submission_id_json = "null"
            if len(self._grades) > 0:
                current_submission_id_json = json.dumps(len(self._grades) - 1)

            return render_template(
                "gradebook.html",
                gradeStructure=json.dumps(self._grade_structure),
                maxScore=json.dumps(self._max_score),
                isDone=json.dumps(self._is_done),
                currentSubmissionID=current_submission_id_json)

        # AJAX calls regarding grades
        @app.route("/gradefast/gradebook/_/<command>", methods=["POST"])
        def gradebook_ajax(command):
            try:
                grade = self._get_grade(request.form["id"])
                if grade is None:
                    return json.dumps({
                        "status": "Invalid grade ID"
                    })

                # Commands make it change something before getting the info
                if command == "late":
                    grade.is_late = request.form["is_late"] == "true"
                elif command == "overall_comments":
                    grade.overall_comments = request.form["value"]
                elif command == "points":
                    grade.set_points(request.form["path"],
                                     request.form["value"])
                elif command == "comments":
                    grade.set_comments(request.form["path"],
                                       request.form["value"])
                elif command == "deduction":
                    grade.set_deduction(request.form["path"],
                                        request.form["value"] == "true")
                elif command == "add_deduction":
                    # Change the grade structure (MUA HA HA HA)
                    grade.add_deduction_to_all_grades(request.form["path"],
                                                      request.form["name"],
                                                      request.form["minus"])

                # Return the current state of this grade
                return json.dumps({
                    "status": "Aight",
                    "name": grade.name,
                    "is_late": grade.is_late,
                    "overallComments": grade.overall_comments,
                    "currentScore": grade.get_score()[0],
                    "values": grade.get_values()
                })
            except BadPathException:
                return json.dumps({
                    "status": "Invalid path"
                })
            except BadValueException:
                return json.dumps({
                    "status": "Invalid value"
                })
            except Exception as ex:
                print("\n\nGRADEBOOK AJAX HANDLER EXCEPTION:", ex)
                print(traceback.format_exc())
                print("")
                return json.dumps({
                    "status": "Look what you did... (seriously, look in the "
                              "server error log)"
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
            resp = Response(gen(), mimetype="text/csv")
            filename_param = 'filename="%s.csv"' % self._grade_name\
                .replace("\\", "").replace('"', '\\"')
            resp.headers["Content-disposition"] = "attachment; " + \
                                                  filename_param
            return resp

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
                        if "name" not in deduction:
                            raise BadStructureException(
                                "Deduction missing name")
                        if "minus" not in deduction:
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
        Return a list of ordered dicts representing the scores and feedback for
        each submission.
        """
        grades = []
        for grade in self._grades:
            points_earned, points_possible, individual_points = \
                grade.get_score()
            grade_details = OrderedDict()
            grade_details["name"] = grade.name
            grade_details["score"] = points_earned
            grade_details["feedback"] = grade.get_feedback()
            for item_name, item_points in individual_points:
                grade_details[item_name] = item_points
            grades.append(grade_details)
        return grades

    def _get_csv(self):
        """
        Return a stream representing the grades as a CSV file.
        """
        csv_stream = io.StringIO()
        csv_writer = csv.writer(csv_stream)

        # Make the header row
        point_titles = SubmissionGrade.get_point_titles(self._grade_structure)
        row_titles = ["Name", "Total Score", "Feedback", ""] + point_titles
        csv_writer.writerow(row_titles)

        # Make the value rows
        for grade in self._get_grades():
            csv_writer.writerow([
                grade["name"],
                grade["score"],
                grade["feedback"],
                ""
            ] + [grade[title] for title in point_titles])

        # Return the resulting stream
        csv_stream.seek(0)
        return csv_stream

    def _get_json(self):
        """
        Return a string representing the grades as JSON.
        """
        return json.dumps(self._get_grades())

    def run(self, hostname, port, log_level=logging.WARNING, debug=False):
        """
        Start the Flask server (using Werkzeug internally).
        
        :param hostname: The hostname to run on
        :param port: The port to run on
        :param log_level: The level to set the Werkzeug logger at
        :param debug: Whether to start the server in debug mode (prints
            tracebacks with 500 errors)
        """
        # Set logging level
        server_log = logging.getLogger("werkzeug")
        server_log.setLevel(log_level)
        # Start the server
        kwargs = {
            "threaded": True
        }
        if debug:
            kwargs["debug"] = True
            kwargs["use_reloader"] = False
        self._app.run(hostname, port, **kwargs)

    def get_wsgi_app(self):
        """
        Get a function representing the server as a WSGI app.
        """
        return self._app.wsgi_app

