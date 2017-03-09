"""
Classes and methods for handling grades and feedback for submissions.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

from typing import Any, Callable, Iterable, List, Optional, Tuple, Union

from . import utils

Path = Union[int, str]
Score = Union[int, float]
# Will usually be passed to "make_number" to convert to a Score
WeakScore = Union[Score, str]
# "Plain Old Data"
POD = Union[list, dict]

FEEDBACK_HTML_TEMPLATES = {
    # (content)
    "base": """<div style="font-family: Helvetica, Arial, sans-serif; """
            """font-size: 10pt; line-height: 1.3;">%s"""
            """<p style="font-size: 11pt;">%s</p></div>""",

    # (points added/deducted, reason); used by "item" and "section" for hints
    "credit": """<div style="text-indent: -20px; margin-left: 20px;">"""
              """<b>%+d:</b> <i>%s</i></div>""",

    # (title, points earned, total points)
    "section_header_top": "<p><b><u>%s</u></b><br>Section Score: %s / %s</p>",
    "section_header": "<p><u>%s</u><br>Section Score: %s / %s</p>",
    # (points deducted, percentage deducted)
    "section_deduction": """<p><b>-%s</b> (%s%%)<b>:</b> """
                         """<i>Turned in late</i></p>""",
    # (content)
    "section_body": """<div style="margin-left: 15px;">%s</div>""",

    # (title, score)
    "item_header_top": """<p><b><u>%s</u></b><br>%s</p>""",
    "item_header": """<p><u>%s</u><br>%s</p>""",
    # (points earned, total points)
    "item_score": """Score: %s / %s""",
    # (points)
    "item_score_bonus": """%+d Points""",
    # (content)
    "item_body": """<p>%s</p>"""
}


def make_number(val: WeakScore) -> Score:
    """
    Convert a string or something else to either a float or a int.

    :param val: The value to convert
    :return: The numeric form of val
    """
    try:
        num_val = float(val)
    except:
        raise BadValueException()

    # Make it an int if we can
    if int(num_val) == num_val:
        num_val = int(num_val)
    return num_val


def _get_late_deduction(score: Score, percent_to_deduct: float, precision: int = 0) -> Score:
    """
    Get the amount of points to lop off of a section if the submission is late.

    :param score: The raw score
    :param percent_to_deduct: The percentage to lop off (0-100)
    :param precision: The amount of decimal places
    """
    d = round(score * (percent_to_deduct / 100.0), precision)
    if precision == 0:
        d = int(d)
    return max(0, d)


class BadPathException(Exception):
    """
    Exception resulting from a bad path
    """
    pass


class BadValueException(Exception):
    """
    Exception resulting from a bad number or value
    """
    pass


def check_grade_structure(st: list, _path: List[int] = None) -> bool:
    """
    Check a grade structure and print any errors.

    :param st: The grade structure to check.
    :param _path: The path to the current point in the structure (only used in recursive calls).
    :return: True if the grade structure is valid, False otherwise.
    """
    found_error = False
    if _path is None:
        _path = []

    def warn(*args):
        utils.print_error("STRUCTURE WARNING:", *args, start="", end="")

    def error(*args):
        nonlocal found_error
        utils.print_error("STRUCTURE ERROR:", *args, start="", end="")
        found_error = True

    if not isinstance(st, list):
        error("Grade structure is not a list")
        return False

    for index, grade in enumerate(st, start=1):
        path = _path.copy()
        path.append(index)

        # Check "name"
        if "name" not in grade or not isinstance(grade["name"], str) or not grade["name"]:
            error("Grade item", path, "missing a name")

        # Make sure the name is trimmed of trailing whitespace
        grade["name"] = grade["name"].strip()

        title = "#" + ".".join(str(p) for p in path) + " (\"" + grade["name"] + "\")"

        # Check stuff specific to grade sections
        if "grades" in grade:
            # Check "deduct percent if late" (used to be "deductPercentIfLate")
            if "deductPercentIfLate" in grade and "deduct percent if late" not in grade:
                grade["deduct percent if late"] = grade["deductPercentIfLate"]
            if "deduct percent if late" in grade:
                if grade["deduct percent if late"] < 0 or grade["deduct percent if late"] > 100:
                    error("Grade section", title, "has an invalid \"deduct percent if late\"")

            found_error = check_grade_structure(grade["grades"], path) or found_error

        # Check stuff specific to grade scores
        elif "points" in grade:
            # Check "points"
            if grade["points"] < 0:
                error("Points in grade score", title, "must be at least zero")

            # Check "default points"
            if "default points" in grade:
                if grade["default points"] < 0:
                    error("Default points in grade score", title, "must be at least zero")
                if grade["default points"] > grade["points"]:
                    error("Default points in grade score", title, "must be less than total points")
        else:
            error("Grade item", title, "needs one of either \"points\" or \"grades\"")

        # Check for old, deprecated versions of "hints"
        bad_hints = []
        for old in ["section deductions", "deductions", "point hints"]:
            if old in grade:
                warn("Found deprecated \"%s\"" % old, "in grade item", title,
                     "(converted to hints)")
                bad_hints += grade[old]
        if len(bad_hints):
            if "hints" not in grade:
                grade["hints"] = []
            for bad_hint in bad_hints:
                grade["hints"].append({
                    "name": bad_hint.get("name", "HINT"),
                    "value": bad_hint.get("value", 0) or (-1 * bad_hint.get("minus", 0))
                })

        # Check "hints"
        if "hints" in grade:
            for hint in grade["hints"]:
                if "name" not in hint:
                    error("Hint in", title, "missing name")
                if "value" not in hint:
                    error("Hint \"%s\"" % hint["name"].trim(), "in grade item", title,
                          "is missing a \"value\"")

    return not found_error


class GradeItem:
    """
    Superclass for GradeScore, GradeSection, and GradeRoot
    """
    def __init__(self, structure: Optional[dict], markdown: Callable[[str], str]):
        """
        Initialize the basic components of a GradeItem

        :param structure: The grade structure dictionary for this grade item
        :param markdown: A configured instance of mistune.Markdown, or a compatible function
        """
        self._md = markdown
        self.name = None
        self.enabled = None
        self.hints = []
        self.hints_set = {}
        self.note = None

        if structure:
            self.name = structure["name"]
            self.enabled = "disabled" not in structure or not structure["disabled"]

            try:
                self.note = structure["note"]
            except KeyError:
                try:
                    self.note = structure["notes"]
                except KeyError:
                    pass

            if "hints" not in structure:
                structure["hints"] = []
            self.hints = structure["hints"]

    def enumerate_all(self, include_disabled: bool = False) -> Iterable["GradeItem"]:
        """
        Enumerate recursively over all grade items (sections, scores, etc.), including ourself and
        any children, yielding all enabled grade items (and disabled ones if include_disabled is
        True) and traversing recursively into child grade items.
        """
        raise NotImplementedError("enumerate_all must be implemented by subclass")

    def get_point_titles(self, include_disabled: bool = False) -> List[Tuple[str, int]]:
        """
        Get a list of the titles for individual point items (i.e. GradeScores). This only includes
        titles for leaf nodes, not sections.

        :param include_disabled: Whether to include titles for disabled items.
        :return: A list of item titles represented by a tuple: (name, points)
        """
        raise NotImplementedError("get_point_titles must be implemented by subclass")

    def get_score(self, is_late: bool) -> Tuple[Score, Score, List[Tuple[str, Score]]]:
        """
        Get the total score for this grade item.

        :param is_late: Whether the parent submission is marked as late
        :return: A tuple with the points earned for this item/section (int or float), the total
            points possible for this item/section (int or float), and the individual point scores
            for this item/section (list of (str, int or float) tuples).
        """
        raise NotImplementedError("get_score must be implemented by subclass")

    def get_feedback(self, is_late: bool, depth: int = 0) -> str:
        """
        Get the feedback for this grade item.

        :param is_late: Whether the parent submission is marked as late
        :param depth: How deep we are in the grade structure (used to vary style)
        :return: The feedback, including score and comments, for this item and any children
        """
        raise NotImplementedError("get_feedback must be implemented by subclass")

    def to_plain_data(self) -> POD:
        """
        Get a representation of this grade item as plain data (just lists, dicts, etc.)

        :return: A dictionary or list representing this grade item.
        """
        raise NotImplementedError("to_plain_data must be implemented by subclass")

    def enumerate_enabled_children(self) -> Iterable["GradeItem"]:
        """
        Enumerate over all enabled children (sections and scores) of this grade section.
        """
        if not hasattr(self, "children"):
            raise NotImplementedError("This subclass does not have children")
        for item in self.children:
            if item.enabled:
                yield item

    def set_enabled(self, is_enabled: bool):
        """
        Set whether this grade item is enabled.
        """
        self.enabled = is_enabled

    def set_hint(self, index: int, is_enabled: bool):
        """
        Set whether a specific hint is enabled for this grade item.

        :param index: The index of the hint
        :param is_enabled: Whether the hint should be set to enabled
        """
        self.hints_set[index] = is_enabled


class GradeScore(GradeItem):
    """
    Represents an individual grade item with a point value and score.
    This is a leaf node in the grade structure tree.
    """
    def __init__(self, structure: dict, **kwargs):
        super().__init__(structure, **kwargs)

        self.points = make_number(structure["points"])
        self.score = make_number(structure["default points"] if "default points" in structure
                                 else structure["points"])

        self.comments = structure["default comments"] if "default comments" in structure else ""

    def enumerate_all(self, include_disabled: bool = False) -> Iterable[GradeItem]:
        if self.enabled or include_disabled:
            yield self

    def get_point_titles(self, include_disabled: bool = False) -> List[Tuple[str, Score]]:
        if self.enabled or include_disabled:
            return [(self.name, self.points)]
        else:
            return []

    def get_score(self, is_late: bool) -> Tuple[Score, Score, List[Tuple[str, Score]]]:
        return self.score, self.points, [(self.name, self.score)]

    def get_feedback(self, is_late: bool, depth: int = 0) -> str:
        # Bolded header only if depth 2 or less
        header_name = "item_header"
        if depth < 2:
            header_name += "_top"

        # Start off with the score
        # (although we skip the score if it's 0 out of 0)
        score = ""
        if self.score and not self.points:
            # No total points, but still points earned
            score = FEEDBACK_HTML_TEMPLATES["item_score_bonus"] % \
                self.score
        elif self.points:
            # We have total points, and possibly points earned
            score = FEEDBACK_HTML_TEMPLATES["item_score"] % \
                    (self.score, self.points)

        # Generate dat feedback
        feedback = FEEDBACK_HTML_TEMPLATES[header_name] % \
            (self._md(self.name), score)

        # Add hints, if applicable
        for index, hint in enumerate(self.hints):
            if self.hints_set.get(index):
                feedback += FEEDBACK_HTML_TEMPLATES["credit"] % \
                            (hint["value"], self._md(hint["name"]))

        # Now, add any comments
        if self.comments:
            feedback += FEEDBACK_HTML_TEMPLATES["item_body"] % \
                self._md(self.comments)

        return feedback

    def to_plain_data(self) -> dict:
        return {
            "name": self.name,
            "enabled": self.enabled,
            "hints": self.hints,
            "hints_set": self.hints_set,
            "note": self.note,
            # TODO: Update the JS side of things to make the proper "points" vs. "score" distinction
            "points": self.points,
            "score": self.score,
            "comments": self.comments
        }

    def set_score(self, score: WeakScore):
        """
        Set the points (score) for this grade item.

        :param score: The earned score
        """
        self.score = make_number(score)

    def set_comments(self, comments: str):
        """
        Set the comments for this grade item.

        :param comments: The new comment
        """
        self.comments = comments


class GradeSection(GradeItem):
    """
    Represents a section of grade items with GradeItem children.
    This is an internal node in the grade structure tree.
    """
    def __init__(self, structure: dict, **kwargs):
        super().__init__(structure, **kwargs)

        self.late_deduction = make_number(structure["deduct percent if late"]) \
            if "deduct percent if late" in structure else 0

        self.children = _create_tree_from_structure(structure["grades"], **kwargs)

    def enumerate_all(self, include_disabled: bool = False) -> Iterable[GradeItem]:
        # If we're not enabled, stop
        if self.enabled or include_disabled:
            # First, yield ourself
            yield self

            # Next, yield our children
            for item in self.children:
                yield from item.enumerate_all(include_disabled)

    def get_point_titles(self, include_disabled: bool = False) -> List[Tuple[str, Score]]:
        items = []
        if self.enabled or include_disabled:
            for item in self.children:
                items += [(self.name + ": " + name, points) for name, points in
                          item.get_point_titles(include_disabled)]
        return items

    def get_score(self, is_late: bool) -> Tuple[Score, Score, List[Tuple[str, Score]]]:
        points_earned = 0.0
        points_possible = 0.0
        individual_points = []

        for item in self.enumerate_enabled_children():
            item_earned, item_possible, item_points = item.get_score(is_late)
            # Add to the total
            points_earned += item_earned
            points_possible += item_possible
            individual_points += [(self.name + ": " + name, score) for name, score in item_points]

        # Account for any hints
        for index, hint in enumerate(self.hints):
            if self.hints_set.get(index):
                points_earned += hint["value"]

        # Check if it's late
        if is_late and self.late_deduction:
            # It's late! Deduct
            points_earned -= _get_late_deduction(points_earned, self.late_deduction)

        return points_earned, points_possible, individual_points

    def get_feedback(self, is_late: bool, depth: int = 0) -> str:
        # Get the score for this section
        points_earned, points_possible, _ = self.get_score(is_late)

        # Add the name of this grading section, the total score, and any
        # deduction feedback
        header_name = "section_header"
        if depth < 2:
            header_name += "_top"
        feedback = FEEDBACK_HTML_TEMPLATES[header_name] % (
            self._md(self.name),
            points_earned,
            points_possible
        )

        # Add hint feedback
        for index, hint in enumerate(self.hints):
            if self.hints_set.get(index):
                feedback += FEEDBACK_HTML_TEMPLATES["credit"] % (
                    hint["value"],
                    self._md(hint["name"])
                )

        # Add lateness feedback if necessary
        if is_late and self.late_deduction:
            feedback += FEEDBACK_HTML_TEMPLATES["section_deduction"] % (
                _get_late_deduction(points_earned, self.late_deduction),
                self.late_deduction
            )

        # Add the feedback for any children
        feedback += FEEDBACK_HTML_TEMPLATES["section_body"] % \
            "\n".join(item.get_feedback(is_late, depth + 1)
                      for item in self.enumerate_enabled_children())

        return feedback

    def to_plain_data(self) -> dict:
        return {
            "name": self.name,
            "enabled": self.enabled,
            "hints": self.hints,
            "hints_set": self.hints_set,
            "note": self.note,
            "children": [child.to_plain_data() for child in self.children]
        }


class GradeRoot(GradeItem):
    """
    Represents the root of the grade item tree.
    """

    def __init__(self, structure: List[dict], **kwargs):
        super().__init__(None, **kwargs)

        self.children = _create_tree_from_structure(structure, **kwargs)

    def enumerate_all(self, include_disabled: bool = False) -> Iterable[GradeItem]:
        for item in self.children:
            yield from item.enumerate_all()

    def get_point_titles(self, include_disabled: bool = False) -> List[Tuple[str, Score]]:
        items = []
        for item in self.children:
            items += item.get_point_titles(include_disabled)
        return items

    def get_score(self, is_late: bool) -> Tuple[Score, Score, List[Tuple[str, Score]]]:
        points_earned = 0.0
        points_possible = 0.0
        individual_points = []

        for item in self.enumerate_enabled_children():
            item_earned, item_possible, item_points = item.get_score(is_late)
            # Add to the total
            points_earned += item_earned
            points_possible += item_possible
            individual_points += item_points

        # Make everything an int if we can
        if int(points_earned) == points_earned:
            points_earned = int(points_earned)
        if int(points_possible) == points_possible:
            points_possible = int(points_possible)

        return points_earned, points_possible, individual_points

    def get_feedback(self, is_late: bool, depth: int = 0) -> str:
        return "\n".join(item.get_feedback(is_late, depth + 1) for item in self.children)

    def to_plain_data(self) -> List[POD]:
        return [child.to_plain_data() for child in self.children]


def _create_tree_from_structure(structure: List[dict], **kwargs) -> List[GradeItem]:
    """
    Create a list of GradeItem subclass instances from a list of grade structure dictionaries.

    Any additional keyword arguments are passed on to the Grade___ constructors. This is called by
    any Grade___ constructors that have children.

    :param structure: A list of grade structure items
    :return: A list of instances of subclasses of GradeItem
    """
    return [
        GradeSection(item, **kwargs) if "grades" in item else GradeScore(item, **kwargs)
        for item in structure
    ]


def get_point_titles(structure: List[dict], include_disabled: bool = False) \
        -> List[Tuple[str, Score]]:
    """
    Get the point titles for all the grade items within the provided grade structure.

    NOTE: Each SubmissionGrade also has a get_point_titles that works just like this one, except it
    respects whether items are disabled.

    :param structure: A list of grading items
    :param include_disabled: Whether to include items that are disabled by default
    :return: A list of item titles represented by tuples: (name, points)
    """
    # Create a temporary GradeItem tree based on this structure
    grades = GradeRoot(structure, markdown=lambda s: s)
    return grades.get_point_titles(include_disabled)


class SubmissionGrade:
    """
    Represents a submission's grade.
    """

    def __init__(self, name: str, grade_structure: List[dict], markdown: Callable[[str], str]):
        """
        :param name: The name of the owner of the submission being graded
        :param grade_structure: A list of grade items (see GradeBook class)
        :param markdown: A configured instance of mistune.Markdown, or a compatible function
        """
        self.name = name
        self._grades = GradeRoot(grade_structure, markdown=markdown)
        self._md = markdown
        self.log = ""

        self.is_late = False
        self.overall_comments = ""

    def get_by_path(self, path: Path) -> GradeItem:
        """
        Find a path in the grade structure.

        :param path: A list of ints (or ints as strings) that acts as a path of indices
            representing a location within the grade item tree
        :return: A GradeItem subclass instance
        """
        item = self._grades
        try:
            path_indexes = [int(index) for index in path]

            # Traverse all the GradeSections until we get to where we want
            for index in path_indexes:
                item = item.children[index]
        except (ValueError, IndexError, AttributeError):
            raise BadPathException()

        return item

    def get_by_name(self, name: str, include_disabled: bool = False) -> Iterable[GradeItem]:
        """
        Find all the grade items in the grade structure that have this name.

        :param name: The name to look for
        :param include_disabled: Whether to include disabled grade items
        :return: A generator that yields GradeItem subclass instances
        """
        for item in self._grades.enumerate_all(include_disabled):
            if item.name == name:
                yield item

    def add_content_to_all_grades(self, path: Path, name: str, content: Any):
        """
        Add a new list item (e.g. a new possible hint) to ALL grade structures (by modifying a list
        still tied into the original grade_structure).

        :param path: A list of ints that acts as a path of indices representing a location within
            the grade item tree
        :param name: The name of the list to add to (for example, "hints")
        :param content: The content of the list item to add
        """
        if len(path) == 0:
            raise BadPathException()
        item = self.get_by_path(path)

        # Add the new item
        if hasattr(item, name):
            getattr(item, name).append(content)
        else:
            raise BadPathException("%s not found at path %s" % (name, path))

    def replace_content_for_all_grades(self, path: Path, name: str, index: int, content: Any):
        """
        Replace an existing list item (e.g. for modifying a hint) for ALL grade structures (by
        modifying a list still tied into the original grade_structure).

        :param path: A list of ints that acts as a path of indices representing a location within
            the grade item tree
        :param name: The name of the list to modify (for example, "hints")
        :param index: The index of the list item to replace
        :param content: The new content of the list item
        """
        if len(path) == 0:
            raise BadPathException()
        item = self.get_by_path(path)

        # Replace the item
        if hasattr(item, name):
            lst = getattr(item, name)
            if index < 0 or len(lst) >= index:
                raise BadPathException("Invalid index %s in %s at path %s" % (index, name, path))
            lst[index] = content
        else:
            raise BadPathException("%s not found at path %s" % (name, path))

    def get_score(self) -> Tuple[Score, Score, List[Tuple[str, Score]]]:
        """
        Calculate the total score (all points added up) for this submission.

        :return: A tuple with the points earned for this submission, the total points possible for
            this submission, and the individual point scores for this submission
        """
        return self._grades.get_score(self.is_late)

    def get_feedback(self) -> str:
        """
        Patch together all the grade comments for this submission.
        """
        return FEEDBACK_HTML_TEMPLATES["base"] % (self._grades.get_feedback(self.is_late),
                                                  self._md(self.overall_comments))

    def get_plain_grades(self) -> List[dict]:
        """
        Get the grade values as a plain old list of dicts.
        """
        return self._grades.to_plain_data()
