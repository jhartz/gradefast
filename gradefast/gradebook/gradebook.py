"""
The GradeBook HTTP server.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jhartz@mail.rit.edu>
"""
import os
import sys
import json
import queue
import logging
import csv
import io
import subprocess
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

from . import events, grades


GRADEBOOK_DIR = os.path.dirname(os.path.abspath(__file__))
JSX_DIR = os.path.join(GRADEBOOK_DIR, "static", "jsx")
JSX_COMPILED = os.path.join(GRADEBOOK_DIR, "static", "bin", "jsx-compiled.js")


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

        self._grades = {}
        self._current_submission_index = None
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

        # Compile JSX, if necessary
        GradeBook.check_compiled_jsx()

        app = Flask(__name__)
        self._app = app

        # Now, initialize the routes for the app

        @app.route("/gradefast/")
        def _gradefast_():
            return redirect(url_for("_gradefast_gradebook_"))

        # Index pages (redirect to current gradebook)
        @app.route("/gradefast/gradebook/")
        def _gradefast_gradebook_():
            return redirect(url_for(
                    "_gradefast_gradebook__",
                    grade_id=str(self._current_submission_index or 0)))

        # GradeBook page
        @app.route("/gradefast/gradebook/<grade_id>")
        def _gradefast_gradebook__(grade_id):
            current_submission_id_json = "null"
            # If nothing has been started, keep the default of null
            if len(self._grades) > 0:
                grade = self._get_grade(grade_id)
                if grade is None:
                    abort(404)
                    return
                current_submission_id_json = json.dumps(grade_id)

            return render_template(
                "gradebook.html",
                gradeStructure=json.dumps(self._grade_structure),
                #isDone=json.dumps(self._is_done),
                #currentSubmissionID=current_submission_id_json,
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

        @app.route("/gradefast/_ng", methods=["POST"])
        def _gradefast_ng__():
            retval = {
                "submission": {
                    "name": "Test Bob"
                }
            }
            return Response(json.dumps(retval), mimetype="application/json")

        # AJAX calls regarding grades
        @app.route("/gradefast/_/<command>", methods=["POST"])
        def _gradefast_ajax__(command):
            try:
                grade = self._get_grade(request.form["id"])
                if grade is None:
                    return json.dumps({
                        "status": "Invalid grade ID"
                    })

                # Commands make it change something before getting the info,
                # but providing a valid command in the URL is not required
                self._parse_command(command, grade)

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
            except grades.BadPathException:
                return json.dumps({
                    "status": "Invalid path"
                })
            except grades.BadValueException:
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
        if int_id not in self._grades:
            return None
        return self._grades[int_id]

    def _parse_command(self, command, grade):
        """
        Parse and execute an AJAX command.
        :param command: The command to run (does not need to be valid)
        :param grade: The GradeStructure instance to execute the command on
        """
        if command == "late":
            # Set whether the submission is marked as late
            grade.is_late = request.form["is_late"] == "true"
        elif command == "overall_comments":
            # Set the overall comments of the submission
            grade.overall_comments = request.form["value"]
        elif command == "add_point_hint":
            # Change the grade structure (MUA HA HA HA)
            grade.add_value_to_all_grades(
                request.form["path"],
                "point hints",
                {
                    "name": request.form["name"],
                    "value": grades.make_number(request.form["value"])
                })
        elif command == "add_section_deduction":
            # Change the grade structure (MUA HA HA HA)
            grade.add_value_to_all_grades(
                request.form["path"],
                "section deductions",
                {
                    "name": request.form["name"],
                    "minus": -1 * grades.make_number(request.form["value"])
                })
        else:
            # We have a command with a path
            path = request.form["path"].split(".")
            if len(path) <= 1:
                raise grades.BadPathException()

            path = path[1:]
            index = None
            if command == "point_hint" or command == "section_deduction":
                index = path[-1]
                path = path[:-1]

            grade_item = grade.get_by_path(path[1:])

            if command == "enabled":
                grade_item.set_enabled(request.form["value"] == "true")
            elif command == "points":
                grade_item.set_points(request.form["value"])
            elif command == "comments":
                grade_item.set_comments(request.form["value"])
            elif command == "point_hint":
                grade_item.set_point_hint(
                    index,
                    request.form["value"] == "true")
            elif command == "section_deduction":
                grade_item.set_section_deduction(
                    index,
                    request.form["value"] == "true")

    # def set_grade_property_by_name(self, name, prop):
    #     """
    #     Set a property for a specific grade item for the current submission.
    #
    #     :param name: The name of the grade item to set
    #     :param prop: The details about the property to set (as an instance
    #         of a subclass of grades.Property)
    #     """
    #     assert isinstance(prop, grades.Property)
    #     grade = self._grades[self._current_submission_index]
    #     grade.set_property_by_name(name, prop)

    def _get_grades(self):
        """
        Return a list of ordered dicts representing the scores and feedback for
        each submission.
        """
        grade_list = []
        for grade in self._grades.values():
            points_earned, points_possible, individual_points = \
                grade.get_score()
            grade_details = OrderedDict()
            grade_details["name"] = grade.name
            grade_details["score"] = points_earned
            grade_details["possible_score"] = points_possible
            grade_details["percentage"] = 0 if points_possible == 0 else \
                100 * points_earned / points_possible
            grade_details["feedback"] = grade.get_feedback()
            for item_name, item_points in individual_points:
                grade_details[item_name] = item_points
            grade_list.append(grade_details)
        return grade_list

    def _get_csv(self):
        """
        Return a stream representing the grades as a CSV file.
        """
        csv_stream = io.StringIO()
        csv_writer = csv.writer(csv_stream)

        # Make the header row
        point_titles = grades.get_point_titles(self._grade_structure)
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

    def _send_client_event(self, event, data):
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

    def start_submission(self, index, name):
        """
        Initialize a new submission and tell any open gradebook clients about
        it.

        :param index: The index of the submission.
        :param name: The name of the owner of the submission.
        """
        # Make a new Grade object for this submission
        if index not in self._grades:
            self._grades[index] = grades.SubmissionGrade(
                name, self._grade_structure, self._md)
        self._current_submission_index = index
        self._send_client_event("start_submission", {
            "id": index
        })

    def log_submission(self, log):
        """
        Add log info for the last-started submission.

        :param log: The HTML log info
        """
        if len(self._grades):
            self._grades[self._current_submission_index].log += log

    def end_of_submissions(self):
        """
        Tell any open gradebook clients that there are no more submissions and
        total up all the grades.
        """
        self._is_done = True
        self._send_client_event("done", {
            "grades": self._get_grades()
        })

    def event(self, event):
        """
        Handle a GradeBook Event with this gradebook.

        :param event: An instance of a subclass of events.GradeBookEvent
        """
        if not isinstance(event, events.GradeBookEvent):
            raise TypeError("Event must be a subclass of GradeBookEvent")

        # Run the event on this GradeBook
        event.handle(self)

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
            "threaded": True,
            "use_reloader": False
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

    @staticmethod
    def check_compiled_jsx():
        """
        Check JSX_DIR and JSX_COMPILED and compile jsx files if necessary.

        Requirements:
        - Node
        - NPM packages: babel-cli, babel-preset-react, babel-preset-es2015
        """
        subprocess.check_call(["babel", "--presets", "react,es2015",
                               JSX_DIR,
                               "--out-file", JSX_COMPILED,
                               "--source-maps", "--minified"])
