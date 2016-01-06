"""
Classes and methods for handling grades and feedback for submissions.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jhartz@mail.rit.edu>
"""

FEEDBACK_HTML_TEMPLATES = {
    # (content)
    "base": """<div style="font-family: Helvetica, Arial, sans-serif; """
            """font-size: 10pt; line-height: 1.3;">%s"""
            """<p style="font-size: 11pt;">%s</p></div>""",

    # (points added/deducted, reason); used by "item" and "section"
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


def make_number(val):
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


def _get_late_deduction(score, percent_to_deduct, precision=0):
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


class GradeItem:
    """
    Superclass for GradeScore, GradeSection, and GradeRoot
    """
    def __init__(self, structure, markdown):
        """
        Initialize the basic components of a GradeItem

        :param structure: The grade structure dictionary for this grade item
            (may be None)
        :param markdown: A configured instance of mistune.Markdown
        """
        self._md = markdown
        self.name = None
        self.enabled = None

        if structure:
            self.name = structure["name"]
            self.enabled = "disabled" not in structure or \
                           not structure["disabled"]

            try:
                self.note = structure["note"]
            except ValueError:
                try:
                    self.note = structure["notes"]
                except ValueError:
                    pass

    def enumerate_all(self, include_disabled=False):
        """
        Enumerate recursively over all grade items (sections, scores, etc.),
        including ourself and any children, yielding all enabled grade items
        (and disabled ones if include_disabled is True) and traversing
        recursively into child grade items.
        """
        raise NotImplementedError("enumerate_all must be implemented by "
                                  "subclass")

    def get_point_titles(self, include_disabled=False):
        """
        Get a list of the titles for individual point items (i.e. GradeScores).
        This only includes titles for leaf nodes, not sections.

        :param include_disabled: Whether to include titles for disabled items.
        :return: A list of item titles represented by a tuple: (name, points)
        """
        raise NotImplementedError("get_point_titles must be implemented by "
                                  "subclass")

    def get_score(self, is_late):
        """
        Get the total score for this grade item.

        :param is_late: Whether the parent submission is marked as late
        :return: A tuple with the points earned for this item/section (int),
            the total points possible for this item/section (int), and
            the individual point scores for this item/section (list of (str,
            int) tuples).
        """
        raise NotImplementedError("get_score must be implemented by subclass")

    def get_feedback(self, is_late, depth=0):
        """
        Get the feedback for this grade item.

        :param is_late: Whether the parent submission is marked as late
        :param depth: How deep we are in the grade structure (used to vary
            style)
        :return: The feedback, including score and comments, for this item and
            any children
        """
        raise NotImplementedError("get_feedback must be implemented by "
                                  "subclass")

    def enumerate_enabled_children(self):
        """
        Enumerate over all enabled children (sections and scores) of this grade
        section.
        """
        if not hasattr(self, "children"):
            raise NotImplementedError("This subclass does not have children")
        for item in self.children:
            if item.enabled:
                yield item

    def set_enabled(self, is_enabled):
        """
        Set whether this grade item is enabled.
        """
        self.enabled = is_enabled


class GradeScore(GradeItem):
    """
    Represents an individual grade item with a point value and score.
    This is a leaf node in the grade structure tree.
    """
    def __init__(self, structure, **kwargs):
        super().__init__(structure, **kwargs)

        self.points = make_number(structure["points"])
        self.score = make_number(
            structure["default points"] if "default points" in structure
            else structure["points"])

        self.comments = structure["default comments"] \
            if "default comments" in structure else ""

        if "point hints" not in structure:
            structure["point hints"] = []
        self.point_hint_values = structure["point hints"]
        self.point_hint_set = {}

    def enumerate_all(self, include_disabled=False):
        if self.enabled or include_disabled:
            yield self

    def get_point_titles(self, include_disabled=False):
        if self.enabled or include_disabled:
            return [(self.name, self.points)]
        else:
            return []

    def get_score(self, is_late):
        return self.score, self.points, [(self.name, self.score)]

    def get_feedback(self, is_late, depth=0):
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

        # Add point hints, if applicable
        for index, hint in enumerate(self.point_hint_values):
            if self.point_hint_set.get(index):
                feedback += FEEDBACK_HTML_TEMPLATES["credit"] % \
                            (hint["value"], self._md(hint["name"]))

        # Now, add any comments
        if self.comments:
            feedback += FEEDBACK_HTML_TEMPLATES["item_body"] % \
                self._md(self.comments)

        return feedback

    def set_score(self, score):
        """
        Set the points (score) for this grade item.

        :param score: The earned score (anything castable to float)
        """
        self.score = make_number(score)

    def set_point_hint(self, index, is_enabled):
        """
        Set whether a specific point hint is enabled for this grade item.

        :param index: The index of the point hint
        :param is_enabled: Whether the point hint should be set to enabled
        """
        self.point_hint_set[index] = is_enabled


class GradeSection(GradeItem):
    """
    Represents a section of grade items with GradeItem children.
    This is an internal node in the grade structure tree.
    """
    def __init__(self, structure, **kwargs):
        super().__init__(structure, **kwargs)

        self.late_deduction = make_number(structure["deduct percent if late"]) \
            if "deduct percent if late" in structure else 0

        if "section deductions" not in structure:
            structure["section deductions"] = []
        self.section_deduction_values = structure["section deductions"]
        self.section_deduction_set = {}

        self.children = _create_tree_from_structure(structure, **kwargs)

    def enumerate_all(self, include_disabled=False):
        # If we're not enabled, stop
        if self.enabled or include_disabled:
            # First, yield ourself
            yield self

            # Next, yield our children
            for item in self.children:
                yield from item.enumerate_all(include_disabled)

    def get_point_titles(self, include_disabled=False):
        items = []
        if self.enabled or include_disabled:
            for item in self.children:
                items += [(self.name + ": " + name, pts) for name, pts in
                          item.get_point_titles(include_disabled)]
        return items

    def get_score(self, is_late):
        points_earned = 0.0
        points_possible = 0.0
        individual_points = []

        for item in self.enumerate_enabled_children():
            item_earned, item_possible, item_points = item.get_score(is_late)
            # Add to the total
            points_earned += item_earned
            points_possible += item_possible
            individual_points += [(self.name + ": " + name, score)
                                  for name, score in item_points]

        # Account for any section deductions
        for index, deduction in enumerate(self.section_deduction_values):
            if self.section_deduction_set.get(index):
                points_earned -= deduction["minus"]

        # Check if it's late
        if is_late and self.late_deduction:
            # It's late! Deduct
            points_earned -= _get_late_deduction(points_earned,
                                                 self.late_deduction)

        return points_earned, points_possible, individual_points

    def get_feedback(self, is_late, depth=0):
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

        # Add section deduction feedback
        for index, deduction in enumerate(self.section_deduction_values):
            if self.section_deduction_set.get(index):
                feedback += FEEDBACK_HTML_TEMPLATES["credit"] % (
                    -1 * deduction["minus"],
                    self._md(deduction["name"])
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


class GradeRoot(GradeItem):
    """
    Represents the root of the grade item tree.
    """

    def __init__(self, structure, **kwargs):
        super().__init__(None, **kwargs)

        self.children = _create_tree_from_structure(structure, **kwargs)

    def get_point_titles(self, include_disabled=False):
        items = []
        for item in self.children:
            items += item.get_point_titles(include_disabled)
        return items

    def get_score(self, is_late):
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

    def enumerate_all(self, include_disabled=False):
        for item in self.children:
            yield from item.enumerate_all()

    def get_feedback(self, is_late, depth=0):
        return "\n".join(item.get_feedback(is_late, depth + 1)
                         for item in self.children)


def _create_tree_from_structure(structure, **kwargs):
    """
    Create a list of GradeItem subclass instances from a list of grade
    structure dictionaries.
    Any additional keyword arguments are passed on to the Grade___ constructors.
    This is called by any Grade___ constructors that have children.

    :param structure: A grade structure dictionary with a "grades" property
        that contains children.
    :return: A list of instances of subclasses of GradeItem
    """
    assert("grades" in structure)
    return [
        GradeSection(item, **kwargs) if "grades" in item else
        GradeScore(item, **kwargs)
        for item in structure["grades"]
    ]


def get_point_titles(structure, include_disabled=False):
    """
    Get the point titles for all the grade items within the provided grade
    structure.

    NOTE: Each SubmissionGrade also has a get_point_titles that works just like
    this one, except it respects whether items are disabled.

    :param structure: A list of grading items
    :param include_disabled: Whether to include items that are disabled by
        default
    :return: A list of item titles represented by tuples: (name, points)
    """
    # Create a temporary GradeItem tree based on this structure
    grades = GradeRoot(structure, markdown=None)
    return grades.get_point_titles(include_disabled)


class SubmissionGrade:
    """Represents a submission's grade"""

    def __init__(self, name, grade_structure, markdown):
        """
        :param name: The name of the owner of the submission being graded
        :param grade_structure: A list of grading items (see GradeBook)
        :param markdown: A configured instance of mistune.Markdown,
            or a compatible polyfill function
        """
        self.name = name
        self._grades = GradeRoot(grade_structure, markdown=markdown)
        self._md = markdown
        self.log = ""

        self.is_late = False
        self.overall_comments = ""

    def get_by_path(self, path):
        """
        Find a path in the grade structure.

        :param path: A list of ints (or ints as strings) that acts as a path of
            indices representing a location within the grade item tree
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

    def get_by_name(self, name, include_disabled=False):
        """
        Find all the grade items in the grade structure that have this name.

        :param name: The name to look for
        :return: A generator that yields GradeItem subclass instances
        """
        for item in self._grades.enumerate_all(include_disabled):
            if item.name == name:
                yield item

    def add_value_to_all_grades(self, path, name, value):
        """
        Add a new possible section deduction or point hint to ALL grade
        structures (by modifying an array still tied into the original
        grade_structure).

        :param path: A list of ints that acts as a path of indices representing
            a location within the grade item tree
        :param name: The name of the list to add to (for example, "point hints"
            or "section deductions")
        :param value: The value to add
        """
        if len(path) == 0:
            raise BadPathException()
        item = self.get_by_path(path)

        # Add the new item
        if hasattr(item, name):
            getattr(item, name).append(value)
        else:
            raise BadPathException("%s not found at path %s" % (name, path))

    def get_score(self):
        """
        Calculate the total score (all points added up) for this submission.

        :return: A tuple with the points earned for this submission (int), the
            total points possible for this submission (int), and the individual
            point scores for this submission (list of (str, int) tuples).
        """
        return self._grades.get_score(self.is_late)

    def get_feedback(self):
        """
        Patch together all the grade comments for this submission.
        """
        return FEEDBACK_HTML_TEMPLATES["base"] % (
                self._grades.get_feedback(self.is_late),
                self._md(self.overall_comments))

    ###########################################################################

    # def _get_subset_values(self, grade_structure, grade_data, path):
    #     """
    #     Get the values for each individual grade parameter (point values,
    #     section deductions and point hints enabled, and comments for each
    #     grading item) for a subset of a grade structure.
    #
    #     :param grade_structure: The subset of self._grade_structure (a list of
    #         dict)
    #     :param grade_data: The subset of self._grade_data that corresponds with
    #         `grade_structure`
    #     :param path: The path to this subset
    #     :return: A dict representing the ID of the grading item (in the HTML
    #         page) and its value.
    #     """
    #     values = {}
    #     for index, structure, data in enumerate_grades(grade_structure,
    #                                                    grade_data):
    #         sub_path = path + "." + str(index)
    #
    #         # Record that this one is enabled
    #         values["enabled" + sub_path] = True
    #         if "grades" in structure:
    #             # We have sub-grades
    #             values.update(self._get_subset_values(structure["grades"],
    #                                                   data["grades"],
    #                                                   sub_path))
    #             # Also add in the section deduction values
    #             for i, item, is_set in enumerate_boolean_list(
    #                     "section deductions", structure, data):
    #                 values["section_deduction" + sub_path + "." + str(i)] = \
    #                     is_set
    #         else:
    #             # Now, do the hard work
    #             # Firstly, add the point value
    #             values["points" + sub_path] = \
    #                 PointsProperty.get_value(structure, data)
    #             # Next, the comments
    #             values["comments" + sub_path] = \
    #                 CommentsProperty.get_value(structure, data)
    #             # Finally, the point hint values
    #             for i, item, is_set in enumerate_boolean_list(
    #                     "point hints", structure, data):
    #                 values["point_hint" + sub_path + "." + str(i)] = is_set
    #     return values
    #
    # def get_values(self):
    #     """
    #     Get the values for each individual grade parameter (point values,
    #     section deductions enabled, and comments for each grading item).
    #
    #     :return: A dict representing the ID of the grading item (in the HTML
    #         page) and its value.
    #     """
    #     return self._get_subset_values(self._grade_structure,
    #                                    self._grade_data, "")
