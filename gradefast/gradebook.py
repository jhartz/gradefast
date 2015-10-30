#!/usr/bin/env python3
"""
The Gradebook HTTP server.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jhartz@mail.rit.edu>
"""
import sys
import json
import queue
import logging
import csv
import io
from collections import OrderedDict
import traceback

try:
    import mistune
except ImportError:
    mistune = None

try:
    from flask import Flask, request, Response, render_template, abort,\
        redirect, url_for
except ImportError:
    print("")
    print("*** Couldn't find Flask package!")
    print("    Please install 'flask' and try again.")
    print("")
    sys.exit(1)


FEEDBACK_HTML_TEMPLATES = {
    # (content)
    "base": """<div style="font-family: Helvetica, Arial, sans-serif; """
            """font-size: 10pt; line-height: 1.3;">%s"""
            """<p style="font-size: 11pt;">%s</p></div>""",

    # (points added/deducted, reason); used by "item" and "section"
    "credit": """<div style="text-indent: -20px; margin-left: 20px;">"""
              """<b>%s:</b> <i>%s</i></div>""",

    # (title, points earned, total points)
    "section_header_top": "<p><b><u>%s</u></b><br>Section Score: %s / %s</p>",
    "section_header": "<p><u>%s</u><br>Section Score: %s / %s</p>",
    # (points deducted, percentage deducted)
    "section_deduction": """<p><b>-%s</b> (%s%%)<b>:</b> """
                         """<i>Turned in late</i></p>""",
    # (content)
    "section_body": """<div style="margin-left: 15px;">%s</div>""",

    # (title, points earned, total points)
    "item_header_top": """<p><b><u>%s</u></b><br>Score: %s / %s</p>""",
    "item_header": """<p><u>%s</u><br>Score: %s / %s</p>""",
    # (content)
    "item_body": """<p>%s</p>"""
}


def make_number(str_val):
    """
    Convert a string to either a float or a int.
    :param str_val: The string to convert.
    :return: The numeric form of str_val.
    """
    try:
        num_val = float(str_val)
    except:
        raise BadValueException()

    # Make it an int if we can
    if int(num_val) == num_val:
        num_val = int(num_val)
    return num_val


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
    def __init__(self, name, grade_structure, markdown):
        """
        :param name: The name of the owner of the submission being graded
        :param grade_structure: A list of grading items (see GradeBook)
        :param markdown: A configured instance of mistune.Markdown
        """
        self.name = name
        self._grade_structure = grade_structure
        self._grade_data = {}
        self._md = markdown
        self.log = ""

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
        Enumerate over both grade_structure and grade_data at once, yielding
        only enabled grade sections.
        Yields tuples in the form (index, structure, data)

        :param grade_structure: A subset of self._grade_structure
        :param grade_data: A subset of self._grade_data
        """
        for index, structure in enumerate(grade_structure):
            if index not in grade_data:
                grade_data[index] = {
                    "grades": {}
                }
            data = grade_data[index]

            if "_enabled" in data:
                if not data["_enabled"]:
                    # It's been disabled
                    continue
            elif "disabled" in structure:
                # It's disabled by default
                continue

            yield index, structure, grade_data[index]

    @staticmethod
    def enumerate_boolean_list(name, grade_structure, grade_data):
        """
        Enumerate over a list of possible boolean values in both grade_structure
        and grade_data at once.
        Yields tuples in the form (index, item, is_set)

        :param name: The name of the list
        :param grade_structure: A subset of self._grade_structure
        :param grade_data: A subset of self._grade_data
        """
        if name in grade_structure:
            if name not in grade_data:
                grade_data[name] = {}
            for index, item in enumerate(grade_structure[name]):
                is_set = index in grade_data[name] and \
                         "_set" in grade_data[name][index] and \
                         grade_data[name][index]["_set"]
                yield index, item, is_set

    @staticmethod
    def _get_late_deduction(score, percent_to_deduct, precision=0):
        """
        Get the amount of points to lop off of a section if the submission is
        late.

        :param score: The raw score
        :param percent_to_deduct: The percentage to lop off (0-100)
        :param precision: The amount of decimal places
        """
        d = round(score * (percent_to_deduct / 100.0), precision)
        if precision == 0:
            d = int(d)
        return max(0, d)

    @staticmethod
    def get_point_titles(grade_structure):
        """
        Get a list of the titles for individual point items which corresponds
        to the lists that are the third part of the tuples of the return value
        of _get_grades_score.

        :param grade_structure: The grade structure to get item titles from
        :return: A list of item titles represented by a tuple: (name, points)
        """
        items = []
        for grade in grade_structure:
            if "grades" in grade:
                # We have sub-grades
                items += [(grade["name"] + ": " + name, pts) for name, pts in
                          SubmissionGrade.get_point_titles(grade["grades"])]
            else:
                items.append((grade["name"], grade["points"]))
        return items

    @staticmethod
    def get_points_earned(grade_structure, grade_data):
        """
        Get the points earned for a specific grade item.
        Precondition: The grade item has a "points" property (i.e. it is not a
        list of other grade items).

        :param grade_structure: A subset of self._grade_structure
        :param grade_data: A subset of self._grade_data
        """
        if "_points_earned" in grade_data:
            return grade_data["_points_earned"]
        if "default points" in grade_structure:
            return grade_structure["default points"]
        return grade_structure["points"]

    @staticmethod
    def get_comments(grade_structure, grade_data):
        """
        Get the Markdown-parsed comments for a specific grade item.
        Precondition: The grade item is capable of having comments (i.e. it is
        not a list of other grade items).

        :param grade_structure: A subset of self._grade_structure
        :param grade_data: A subset of self._grade_data
        """
        if "_comments" in grade_data:
            return grade_data["_comments"]
        if "default comments" in grade_structure:
            return grade_structure["default comments"]
        return ""

    def set_enabled(self, path, enabled):
        """
        Set whether a grading section is enabled.
        """
        path = path.split(".")
        if len(path) < 2 or path[0] != "enabled":
            raise BadPathException()
        structure, data = self._get_location(path[1:])

        # Store the enabled status
        data["_enabled"] = enabled

    def set_points(self, path, points):
        """
        Set the points for a section of this submission's grade.
        """
        path = path.split(".")
        if len(path) < 2 or path[0] != "points":
            raise BadPathException()
        structure, data = self._get_location(path[1:])

        # Store the points earned
        data["_points_earned"] = make_number(points)

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

    def set_point_hint(self, path, is_set):
        """
        Enable or disable a point hint for a section of this submission's grade.
        """
        path = path.split(".")
        if len(path) < 3 or path[0] != "point_hint":
            raise BadPathException()
        structure, data = self._get_location(path[1:-1])
        try:
            # Find the location to store our point hint data in
            index = int(path[-1])
            if "point hints" not in data:
                data["point hints"] = {}
            if index not in data["point hints"]:
                data["point hints"][index] = {}
            data = data["point hints"][index]
        except:
            raise BadPathException()

        # Store that the point hint is set
        data["_set"] = is_set

    def set_section_deduction(self, path, is_set):
        """
        Enable or disable a section deduction for a section of this
        submission's grade.
        """
        path = path.split(".")
        if len(path) < 3 or path[0] != "section_deduction":
            raise BadPathException()
        structure, data = self._get_location(path[1:-1])
        try:
            # Find the location to store our section deduction data in
            index = int(path[-1])
            if "section deductions" not in data:
                data["section deductions"] = {}
            if index not in data["section deductions"]:
                data["section deductions"][index] = {}
            data = data["section deductions"][index]
        except:
            raise BadPathException()

        # Store that the section deduction is set
        data["_set"] = is_set

    def add_item_to_all_grades(self, path, name, item):
        """
        Add a new possible section deduction or point hint to ALL grade
        structures (by modifying self._grade_structure, since that's shared
        by all SubmissionGrade objects that use it).
        """
        path = path.split(".")
        if len(path) < 2 or path[0] != "":
            raise BadPathException()
        structure, data = self._get_location(path[1:])
        if name not in structure:
            structure[name] = []

        # Add the new item
        structure[name].append(item)

    def _get_subset_values(self, grade_structure, grade_data, path):
        """
        Get the values for each individual grade parameter (point values,
        section deductions and point hints enabled, and comments for each
        grading item) for a subset of a grade structure.

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

            # Record that this one is enabled
            values["enabled" + sub_path] = True
            if "grades" in structure:
                # We have sub-grades
                values.update(self._get_subset_values(structure["grades"],
                                                      data["grades"],
                                                      sub_path))
                # Also add in the section deduction values
                for i, item, is_set in SubmissionGrade.enumerate_boolean_list(
                        "section deductions", structure, data):
                    values["section_deduction" + sub_path + "." + str(i)] = \
                        is_set
            else:
                # Now, do the hard work
                # Firstly, add the point value
                values["points" + sub_path] = \
                    SubmissionGrade.get_points_earned(structure,
                                                      data)
                # Next, the comments
                values["comments" + sub_path] = SubmissionGrade.get_comments(
                    structure, data)
                # Finally, the point hint values
                for i, item, is_set in SubmissionGrade.enumerate_boolean_list(
                        "point hints", structure, data):
                    values["point_hint" + sub_path + "." + str(i)] = is_set
        return values

    def get_values(self):
        """
        Get the values for each individual grade parameter (point values,
        section deductions enabled, and comments for each grading item).

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
                # Check for any section deductions
                for i, section_deduction, is_set in \
                        SubmissionGrade.enumerate_boolean_list(
                            "section deductions", structure, data):
                    if is_set:
                        section_earned -= section_deduction["minus"]
                # Check if it's late
                if "deduct percent if late" in structure and self.is_late:
                    # It's late! Deduct
                    section_earned -= self._get_late_deduction(
                        section_earned,
                        structure["deduct percent if late"])
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
                points_earned_item = SubmissionGrade.get_points_earned(
                    structure, data)
                points_earned += points_earned_item
                individual_points.append((structure["name"],
                                          points_earned_item))

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

    def _get_subset_feedback(self, grade_structure, grade_data, depth=0):
        """
        Get the feedback for a subset of a grade structure.
        
        :param grade_structure: The subset of self._grade_structure (a list of
            dict)
        :param grade_data: The subset of self._grade_data that corresponds with
            `grade_structure`
        :param depth: How deep we are in the grade structure (used to vary
            style)
        :return: The feedback, including score and comments, for this subset
        """
        feedback = ""
        for index, structure, data in SubmissionGrade.enumerate_grades(
                grade_structure, grade_data):

            if "grades" in structure:
                # We have sub-grades
                points_earned, points_possible, _ = self._get_subset_score(
                    structure["grades"], data["grades"])

                # Check for any section deductions
                deduction_feedback = ""
                for i, section_deduction, is_set in \
                        SubmissionGrade.enumerate_boolean_list(
                            "section deductions", structure, data):
                    if is_set:
                        # Take away from points_earned
                        points_earned -= section_deduction["minus"]
                        # Add some feedback about it
                        deduction_feedback += FEEDBACK_HTML_TEMPLATES[
                            "credit"] % ("-" + str(section_deduction["minus"]),
                                         self._md(section_deduction["name"]))

                # Check if it was late and, if so, add that deduction
                if "deduct percent if late" in structure and self.is_late:
                    late_deduction = self._get_late_deduction(
                        points_earned, structure["deduct percent if late"])
                    # Take away from points_earned
                    points_earned -= late_deduction
                    # Add the "late" message to the deduction feedback
                    deduction_feedback += FEEDBACK_HTML_TEMPLATES[
                        "section_deduction"] % (
                        late_deduction, structure["deduct percent if late"])

                # Add the name of this grading section, the total score, and
                # any deductions (deduction_feedback)
                header_name = "section_header"
                if depth < 2: header_name += "_top"
                feedback += FEEDBACK_HTML_TEMPLATES[header_name] % (
                    self._md(structure["name"]),
                    points_earned,
                    points_possible
                )
                feedback += deduction_feedback

                # Add the feedback for all the sub-grades
                feedback += FEEDBACK_HTML_TEMPLATES["section_body"] % \
                    self._get_subset_feedback(structure["grades"],
                                              data["grades"],
                                              depth + 1)
            else:
                # Just a normal grade item
                points_earned = SubmissionGrade.get_points_earned(structure,
                                                                  data)

                header_name = "item_header"
                if depth < 2: header_name += "_top"
                feedback += FEEDBACK_HTML_TEMPLATES[header_name] % \
                    (self._md(structure["name"]), points_earned,
                     structure["points"])

                # Add point hints, if applicable
                for i, item, is_set in SubmissionGrade.enumerate_boolean_list(
                        "point hints", structure, data):
                    if is_set:
                        feedback += FEEDBACK_HTML_TEMPLATES["credit"] % \
                                    (item["value"], self._md(item["name"]))

                # Now, add any comments
                comments = SubmissionGrade.get_comments(structure, data)
                if comments:
                    feedback += FEEDBACK_HTML_TEMPLATES["item_body"] % \
                        self._md(comments)
                        #"<br>".join(comments.splitlines())
        return feedback

    def get_feedback(self):
        """
        Patch together all the grade comments for this submission.
        """
        return FEEDBACK_HTML_TEMPLATES["base"] % (
            self._get_subset_feedback(self._grade_structure, self._grade_data),
            self._md(self.overall_comments))
            #"<br>".join(self.overall_comments.splitlines()))


class GradeBook:
    """Represents a grade book with submissions and grade structures."""
    def __init__(self, grade_structure, grade_name=None):
        """
        Create a WSGI app representing a grade book.
        
        A grade structure is a list of grade items and/or other grade
        structures. For more, see the GradeFast wiki:
        https://github.com/jhartz/gradefast/wiki/Grade-Structure
        
        :param grade_structure: A list of grade items and/or other grade
            structures
        :param grade_name: A name for whatever we're grading
        """
        self._grade_name = grade_name or "grades"

        # Check validity of _grade_structure
        self._grade_structure = grade_structure
        self._check_grade_structure()

        self._grades = []
        self._subscriptions = []
        self._is_done = False

        # Set up Mistune (Markdown)
        if mistune is None:
            print("")
            print("*** Couldn't find mistune package!")
            print("    Items will not be Markdown-parsed.")
            print("")

            def parse_md(*args, **kwargs):
                return args[0]
        else:
            markdown = mistune.Markdown(
                renderer=mistune.Renderer(hard_wrap=True))

            def parse_md(*args, **kwargs):
                text = markdown(*args, **kwargs).strip()
                # Convert paragraphs to <br> tags
                if text.startswith("<p>") and text.endswith("</p>"):
                    text = text[3:-4].replace("</p>\n<p>", "<br>")
                # Stylize code tags
                text = text.replace(
                    '<code>', '<code style="background-color: rgba(0, 0, 0, '
                              '0.04); padding: 1px 3px; border-radius: 5px;">')
                return text

        self._md = parse_md

        app = Flask(__name__)
        self._app = app

        # Now, initialize the routes for the app

        @app.route("/gradefast/")
        def _gradefast_():
            return redirect(url_for("_gradefast_gradebook_"))

        # Index pages (redirect to current gradebook)
        @app.route("/gradefast/gradebook/")
        def _gradefast_gradebook_():
            current_submission_id = 0
            if len(self._grades) > 0:
                current_submission_id = len(self._grades) - 1
            return redirect(url_for("_gradefast_gradebook__",
                                    grade_id=str(current_submission_id)))

        # Gradebook page
        @app.route("/gradefast/gradebook/<grade_id>")
        def _gradefast_gradebook__(grade_id):
            current_submission_id_json = "null"
            # If nothing has been started, keep the default of null
            if len(self._grades) != 0:
                grade = self._get_grade(grade_id)
                if grade is None:
                    abort(404)
                    return
                current_submission_id_json = json.dumps(grade_id)

            return render_template(
                "gradebook.html",
                gradeStructure=json.dumps(self._grade_structure),
                isDone=json.dumps(self._is_done),
                currentSubmissionID=current_submission_id_json,
                # TODO: implement (from YAML file)
                checkPointHintRange=json.dumps(False))

        # Log page
        @app.route("/gradefast/log/<grade_id>")
        def _gradefast_log__(grade_id):
            grade = self._get_grade(grade_id)
            if grade is None:
                abort(404)
            else:
                return render_template(
                    "log.html",
                    title="Log for %s" % grade.name,
                    content=grade.log
                )

        # AJAX calls regarding grades
        @app.route("/gradefast/_/<command>", methods=["POST"])
        def _gradefast_ajax__(command):
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
                elif command == "enabled":
                    grade.set_enabled(request.form["path"],
                                      request.form["value"] == "true")
                elif command == "points":
                    grade.set_points(request.form["path"],
                                     request.form["value"])
                elif command == "comments":
                    grade.set_comments(request.form["path"],
                                       request.form["value"])
                elif command == "point_hint":
                    grade.set_point_hint(request.form["path"],
                                         request.form["value"] == "true")
                elif command == "section_deduction":
                    grade.set_section_deduction(request.form["path"],
                                                request.form["value"] == "true")
                elif command == "add_point_hint":
                    # Change the grade structure (MUA HA HA HA)
                    grade.add_item_to_all_grades(
                        request.form["path"],
                        "point hints",
                        {
                            "name": request.form["name"],
                            "value": make_number(request.form["value"])
                        })
                elif command == "add_section_deduction":
                    # Change the grade structure (MUA HA HA HA)
                    grade.add_item_to_all_grades(
                        request.form["path"],
                        "section deductions",
                        {
                            "name": request.form["name"],
                            "minus": -1 * make_number(request.form["value"])
                        })

                # Return the current state of this grade
                points_earned, points_total, _ = grade.get_score()
                return json.dumps({
                    "status": "Aight",
                    "name": grade.name,
                    "is_late": grade.is_late,
                    "overallComments": grade.overall_comments,
                    "currentScore": points_earned,
                    "maxScore": points_total,
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
        @app.route("/gradefast/grades.csv")
        def _gradefast_grades_csv():
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
        @app.route("/gradefast/grades.json")
        def _gradefast_grades_json():
            return Response(self._get_json(), mimetype="application/json")

        # Event stream
        @app.route("/gradefast/events.stream")
        def _gradefast_events_stream():
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
            if "name" not in grade or not isinstance(grade["name"], str) or \
                    not grade["name"]:
                raise BadStructureException("Grade item missing a name")
            if "grades" in grade:
                if "section deductions" in grade:
                    for section_deduction in grade["section deductions"]:
                        if "name" not in section_deduction:
                            raise BadStructureException(
                                "Section deduction missing name")
                        if "minus" not in section_deduction:
                            raise BadStructureException(
                                "Section deduction missing points")
                if "deduct percent if late" in grade:
                    if grade["deduct percent if late"] < 0 or \
                       grade["deduct percent if late"] > 100:
                        raise BadStructureException(
                            "Grade item has an invalid \"deduct percent if "
                            "late\"")
                max_score += self._check_grade_structure(grade["grades"])
            elif "points" in grade:
                if grade["points"] < 0:
                    raise BadStructureException("Points must be greater than "
                                                "zero")
                max_score += grade["points"]
                if "default points" in grade:
                    if grade["default points"] < 0:
                        raise BadStructureException("Default points must be "
                                                    "greater than zero")
                    if grade["default points"] > grade["points"]:
                        raise BadStructureException("Default points must be "
                                                    "less than total points")
                if "point hints" in grade:
                    for point_hint in grade["point hints"]:
                        if "name" not in point_hint:
                            raise BadStructureException(
                                "Point hint missing name")
                        if "value" not in point_hint:
                            raise BadStructureException(
                                "Point hint missing value")
            else:
                raise BadStructureException(
                    "Grade item needs one of either points or grades")

        return max_score

    def _get_grade(self, grade_id):
        """
        Test whether an ID is valid and, if so, get the Grade corresponding to
        it.
        
        :param grade_id: The ID to test (can be any type)
        :return: a Grade if valid, or None otherwise
        """
        int_id = None
        try:
            int_id = int(grade_id)
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
        grade = SubmissionGrade(name, self._grade_structure, self._md)
        grade_id = len(self._grades)
        self._grades.append(grade)
        self._send_event("start_submission", {
            "id": grade_id
        })

    def log_submission(self, log):
        """
        Add log info for the last-started submission.

        :param log: The HTML log info
        """
        if len(self._grades):
            grade_id = len(self._grades) - 1
            self._grades[grade_id].log += log

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
            grade_details["possible_score"] = points_possible
            grade_details["percentage"] = 100 * points_earned / points_possible
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
        row_titles = ["Name", "Total Score", "Percentage", "Feedback", ""] + \
                     ["(%s) %s" % (pts, title) for title, pts in point_titles]
        csv_writer.writerow(row_titles)

        # Make the value rows
        for grade in self._get_grades():
            csv_writer.writerow([
                grade["name"],
                grade["score"],
                grade["percentage"],
                grade["feedback"],
                ""
            ] + ["" if title not in grade else grade[title]
                 for title, pts in point_titles])

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

