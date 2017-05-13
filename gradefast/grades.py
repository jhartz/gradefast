"""
Classes for handling the calculation of grades and rendering of feedback for submissions.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

from typing import Dict, Iterable, List, Optional, Tuple

from gradefast import required_package_warning
from gradefast.gradebook import utils
from gradefast.models import GradeItem, GradeScore, GradeSection, Hint, ScoreNumber, WeakScoreNumber
from gradefast.parsers import make_score_number

try:
    import mistune
    _markdown = mistune.Markdown(renderer=mistune.Renderer(hard_wrap=True))
    has_markdown = True
except ImportError:
    required_package_warning("mistune", "Comments and hints will not be Markdown-parsed.")
    mistune = None
    has_markdown = False


class FeedbackHTMLTemplates:
    base = """\
<div style="font-family: Helvetica, Arial, sans-serif; font-size: 10pt; line-height: 1.3;">
{content}

<div style="font-size: 10.5pt;">
{overall_comments}
</div>
</div>"""

    hint = """
<div style="text-indent: -20px; margin-left: 20px;">
<b>{points:+}:</b> {reason}
</div>"""

    hint_no_points = """
<div style="text-indent: -20px; margin-left: 20px;">
{reason}
</div>"""

    section_header = """
<p>
<u>{title}</u><br>
Section Score: {points_earned} / {points_possible}
</p>"""

    section_late = """
<p><b>{points:+}</b> ({percentage}%)<b>:</b> <i>Turned in late</i></p>"""

    section_body = """
<div style="margin-left: 15px;">
{content}
</div>"""

    item_header = """
<p>
<u>{title}</u><br>
{content}
</p>"""

    item_score = "Score: {points_earned} / {points_possible}"
    item_score_bonus = "{points:+} Points"

    item_comments = """
<div>
{content}
</div>"""


def _markdown_to_html(text: str, inline_only: bool = False) -> str:
    text = text.rstrip()
    if not has_markdown:
        html = text.replace("&", "&amp;")   \
                   .replace("\"", "&quot;") \
                   .replace("<", "&lt;")    \
                   .replace(">", "&gt;")    \
                   .replace("\n", "<br>")
    else:
        html = _markdown(text)
        if inline_only:
            html = html.replace('<p>', '').replace('</p>', '<br>')
        else:
            html = html.replace('<p>', '<p style="margin: 3px 0">')

        # WARNING: MyCourses (Desire2Learn platform) will cut out any colors provided in "rgba"
        # format for any CSS properties in the "style" attribute
        CODE_STYLE = "background-color: #f5f5f5; padding: 1px 3px; border: 1px solid #cccccc; " \
                     "border-radius: 4px;"
        # Make <code> tags prettier
        html = html.replace(
            '<code>',
            '<code style="' + CODE_STYLE + '">')
        # Except where we have a case of <pre><code>, then apply it to the <pre> instead
        html = html.replace(
            '<pre><code style="' + CODE_STYLE + '">',
            '<pre style="' + CODE_STYLE + '"><code>')

    html = html.rstrip()
    if html.endswith('<br>'):
        html = html[:-4].rstrip()

    return html


def _markdown_to_html_inline(text: str) -> str:
    return _markdown_to_html(text, True)


def _get_late_deduction(score: ScoreNumber, percent_to_deduct: ScoreNumber,
                        precision: int = 0) -> ScoreNumber:
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


class SubmissionGradeItem:
    """
    Superclass for SubmissionGradeScore and SubmissionGradeSection.
    """
    def __init__(self, grade_item: Optional[GradeItem]) -> None:
        """
        Initialize the basic components of a SubmissionGradeItem from a base GradeItem.
        """
        self._name = None       # type: str
        self._name_html = None  # type: str
        self._enabled = True
        self._hints = []        # type: List[Hint]
        self._hints_name_html = []  # type: List[str]
        self._hints_set = {}    # type: Dict[int, bool]
        self._note = None       # type: str
        self._note_html = None  # type: str
        self._children = None   # type: List["SubmissionGradeItem"]

        if grade_item:
            self._name = grade_item.name
            self._name_html = _markdown_to_html_inline(self._name)
            self.set_enabled(grade_item.default_enabled)
            self._note = grade_item.note
            if self._note is not None:
                self._note_html = _markdown_to_html(self._note)
            # NOTE: This needs to stay the same reference to the original grade structure's hints
            # list so that add_hint and replace_hint work!
            self._hints = grade_item.hints
            self._hints_name_html = [_markdown_to_html_inline(hint.name) for hint in self._hints]

    def enumerate_all(self, include_disabled: bool = False) -> Iterable["SubmissionGradeItem"]:
        """
        Enumerate recursively over all grade items (sections, scores, etc.), including ourself and
        any children, yielding all enabled grade items (and disabled ones if include_disabled is
        True) and traversing recursively into child grade items.
        """
        raise NotImplementedError("enumerate_all must be implemented by subclass")

    def get_score(self, is_late: bool) -> Tuple[ScoreNumber, ScoreNumber,
                                                List[Tuple[str, ScoreNumber]]]:
        """
        Get the current point values for this grade item. The third item in each returned tuple
        matches the format used by the get_point_titles function.

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

    def is_name_like(self, other_name: str) -> bool:
        """
        Determine whether the name of this grade item is like the provided name, ignoring case.

        :param other_name: The name to compare against.
        :return: Whether they are pretty much the same.
        """
        return self._name is not None and self._name.lower() == other_name.lower()

    def to_plain_data(self) -> Dict[str, object]:
        """
        Get a representation of this grade item as plain data (just lists, dicts, etc.)
        This should be overridden in subclasses to extend the dict returned here, or replace it
        with a more appropriate representation.
        """
        return {
            "name": self._name,
            "name_html": self._name_html,
            "enabled": self._enabled,
            "hints": [
                {
                    "name": hint.name,
                    "name_html": self._hints_name_html[index],
                    "value": hint.value,
                    "enabled": self.is_hint_enabled(index)
                }
                for index, hint in enumerate(self._hints)
            ],
            "note": self._note,
            "note_html": self._note_html
        }

    def set_enabled(self, is_enabled: bool) -> None:
        """
        Set whether this grade item is enabled.
        """
        self._enabled = is_enabled

    def is_hint_enabled(self, index: int) -> bool:
        """
        Determine whether a particular hint is enabled, given its index in self._hints.
        """
        return self._hints_set.get(index, self._hints[index].default_enabled)

    def set_hint_enabled(self, index: int, is_enabled: bool) -> None:
        """
        Set whether a specific hint is enabled for this grade item.

        :param index: The index of the hint
        :param is_enabled: Whether the hint should be set to enabled
        """
        self._hints_set[index] = is_enabled

    def add_hint(self, name: str, value: WeakScoreNumber) -> None:
        """
        Add a new possible hint to this grade item (and all other instances in other submissions)
        by modifying a list still tied to the original grade structure.

        :param name: The name of the hint to add
        :param value: The point value of the hint to add
        """
        self._hints.append(Hint(name=name, value=make_score_number(value), default_enabled=False))
        self._hints_name_html.append(_markdown_to_html_inline(name))

    def replace_hint(self, index: int, name: str, value: WeakScoreNumber) -> None:
        """
        Replace an existing hint for this grade item (and all other instances in other submissions)
        by modifying a list still tied to the original grade structure.

        This may raise a ValueError or an IndexError if "index" is not valid.

        :param index: The index of the hint to replace in the list of hints
        :param name: The new name of the hint
        :param value: The new point value of the hint
        """
        index = int(index)
        old_hint = self._hints[index]
        self._hints[index] = Hint(name=name, value=make_score_number(value),
                                  default_enabled=old_hint.default_enabled)
        self._hints_name_html[index] = _markdown_to_html_inline(name)


class SubmissionGradeScore(SubmissionGradeItem):
    """
    Represents an individual grade item with a point value and score.
    This is a leaf node in the grade structure tree.
    """
    def __init__(self, grade_score: GradeScore) -> None:
        super().__init__(grade_score)

        self._points = make_score_number(grade_score.points)
        self._base_score = None     # type: ScoreNumber
        self._comments = None       # type: str
        self._comments_html = None  # type: str

        self._default_score = grade_score.default_score
        self._default_comments = grade_score.default_comments

        self.set_base_score(grade_score.default_score)
        self.set_comments(grade_score.default_comments)

    def enumerate_all(self, include_disabled: bool = False) -> Iterable[SubmissionGradeItem]:
        if self._enabled or include_disabled:
            yield self

    def get_score(self, is_late: bool) -> Tuple[ScoreNumber, ScoreNumber,
                                                List[Tuple[str, ScoreNumber]]]:
        points_earned = self._base_score
        for index, hint in enumerate(self._hints):
            if self.is_hint_enabled(index):
                points_earned += hint.value
        return points_earned, self._points, [(self._name, points_earned)]

    def get_feedback(self, is_late: bool, depth: int = 0) -> str:
        # Start off with the score (although we skip the score if it's 0 out of 0)
        points_earned, points_possible, _ = self.get_score(is_late)
        score_feedback = ""
        if points_earned and not points_possible:
            # No total points, but still points earned
            score_feedback = FeedbackHTMLTemplates.item_score_bonus.format(points=points_earned)
        elif points_possible:
            # We have total points, and possibly points earned
            score_feedback = FeedbackHTMLTemplates.item_score.format(
                points_earned=points_earned, points_possible=points_possible)

        # Generate dat feedback
        item_title = self._name_html
        if depth < 2:
            item_title = "<b>" + item_title + "</b>"
        feedback = FeedbackHTMLTemplates.item_header.format(title=item_title,
                                                            content=score_feedback)

        # Add hints, if applicable
        for index, hint in enumerate(self._hints):
            if self.is_hint_enabled(index):
                if hint.value == 0:
                    feedback += FeedbackHTMLTemplates.hint_no_points.format(
                        reason=self._hints_name_html[index])
                else:
                    feedback += FeedbackHTMLTemplates.hint.format(
                        points=hint.value, reason=self._hints_name_html[index])

        # Now, add any comments
        if self._comments:
            feedback += FeedbackHTMLTemplates.item_comments.format(content=self._comments_html)

        return feedback

    def is_touched(self) -> bool:
        """
        Determine whether this grade score has been modified from its defaults, and is affecting
        the overall score or feedback.
        """
        return self._enabled and (
            self._base_score != self._default_score or
            self._comments != self._default_comments or
            any(self.is_hint_enabled(index) != hint.default_enabled
                for index, hint in enumerate(self._hints))
        )

    def to_plain_data(self) -> Dict[str, object]:
        data = super().to_plain_data()
        points_earned, points_possible, _ = self.get_score(False)
        data.update({
            "score": points_earned,
            "points": points_possible,
            "comments": self._comments,
            "comments_html": self._comments_html,
            "touched": self.is_touched()
        })
        return data

    def set_base_score(self, score: WeakScoreNumber) -> None:
        """
        Set the score for this grade item, excluding the effects of enabled hints.
        """
        self._base_score = make_score_number(score)

    def set_effective_score(self, score: WeakScoreNumber) -> None:
        """
        Set the score for this grade item, including any hints that are applied.
        """
        score = make_score_number(score)
        # To get the base score, we need to "undo" the effects of hints
        for index, hint in enumerate(self._hints):
            if self.is_hint_enabled(index):
                score -= hint.value
        self._base_score = score

    def set_comments(self, comments: str) -> None:
        """
        Set the comments for this grade item.
        """
        self._comments = comments
        self._comments_html = _markdown_to_html(comments)


class SubmissionGradeSection(SubmissionGradeItem):
    """
    Represents a section of grade items with SubmissionGradeItem children.
    This is an internal node in the grade structure tree.
    """
    def __init__(self, grade_section: GradeSection) -> None:
        super().__init__(grade_section)

        self._late_deduction = grade_section.deduct_percent_if_late
        self._children = _create_tree_from_structure(grade_section.grades)

    def enumerate_all(self, include_disabled: bool = False) -> Iterable[SubmissionGradeItem]:
        if self._enabled or include_disabled:
            yield self
            for item in self._children:
                yield from item.enumerate_all(include_disabled)

    def enumerate_enabled_children(self) -> Iterable["SubmissionGradeItem"]:
        """
        Enumerate over all enabled children (sections and scores) of this grade section.
        """
        for item in self._children:
            if item._enabled:
                yield item

    def get_score(self, is_late: bool) -> Tuple[ScoreNumber, ScoreNumber,
                                                List[Tuple[str, ScoreNumber]]]:
        points_earned = 0.0
        points_possible = 0.0
        individual_points = []  # type: List[Tuple[str, ScoreNumber]]

        for item in self.enumerate_enabled_children():
            item_earned, item_possible, item_points = item.get_score(is_late)
            # Add to the total
            points_earned += item_earned
            points_possible += item_possible
            individual_points += [(self._name + ": " + name, score) for name, score in item_points]

        # Account for any hints
        for index, hint in enumerate(self._hints):
            if self.is_hint_enabled(index):
                points_earned += hint.value

        # Check if it's late
        if is_late and self._late_deduction:
            # It's late! Deduct
            points_earned -= _get_late_deduction(points_earned, self._late_deduction)

        return points_earned, points_possible, individual_points

    def get_feedback(self, is_late: bool, depth: int = 0) -> str:
        points_earned, points_possible, _ = self.get_score(is_late)

        # Add the title and overall points earned / points possible
        section_title = self._name_html
        if depth < 2:
            section_title = "<b>" + section_title + "</b>"
        feedback = FeedbackHTMLTemplates.section_header.format(title=section_title,
                                                               points_earned=points_earned,
                                                               points_possible=points_possible)

        # Add hint feedback
        for index, hint in enumerate(self._hints):
            if self.is_hint_enabled(index):
                if hint.value == 0:
                    feedback += FeedbackHTMLTemplates.hint_no_points.format(
                        reason=self._hints_name_html[index])
                else:
                    feedback += FeedbackHTMLTemplates.hint.format(
                        points=hint.value, reason=self._hints_name_html[index])

        # Add lateness feedback if necessary
        if is_late and self._late_deduction:
            feedback += FeedbackHTMLTemplates.section_late.format(
                points=-_get_late_deduction(points_earned, self._late_deduction),
                percentage=self._late_deduction)

        # Add the feedback for any children
        feedback += FeedbackHTMLTemplates.section_body.format(
            content="\n".join(item.get_feedback(is_late, depth + 1)
                              for item in self.enumerate_enabled_children()))

        return feedback

    def to_plain_data(self) -> Dict[str, object]:
        data = super().to_plain_data()
        data.update({
            "children": [child.to_plain_data() for child in self._children]
        })
        return data


def _create_tree_from_structure(structure: List[GradeItem]) -> List[SubmissionGradeItem]:
    """
    Create a list of SubmissionGradeItem subclass instances from a list of GradeItems.
    """
    items = []  # type: List[SubmissionGradeItem]
    for item in structure:
        if isinstance(item, GradeScore):
            items.append(SubmissionGradeScore(item))
        elif isinstance(item, GradeSection):
            items.append(SubmissionGradeSection(item))
        else:
            raise ValueError("Invalid structure item: {}".format(item))
    return items


def get_point_titles(structure: List[GradeItem]) -> List[Tuple[str, ScoreNumber]]:
    """
    Get the point titles for all the grade items within the provided grade structure. This matches
    the format used by a SubmissionGradeItem's get_score method.

    :param structure: A list of GradeItems
    :return: A list of item titles represented by tuples: (name, points)
    """
    items = []  # type: List[Tuple[str, ScoreNumber]]
    for item in structure:
        if isinstance(item, GradeScore):
            items.append((item.name, item.points))
        elif isinstance(item, GradeSection):
            items += [(item.name + ": " + name, points)
                      for name, points in get_point_titles(item.grades)]
    return items


class SubmissionGrade:
    """
    Represents a submission's grade.
    """

    def __init__(self, grade_structure: List[GradeItem]) -> None:
        self._grades = _create_tree_from_structure(grade_structure)

        self._is_late = False
        self._overall_comments = ""
        self._overall_comments_html = ""

    def enumerate_all(self, include_disabled: bool = False) -> Iterable[SubmissionGradeItem]:
        for item in self._grades:
            yield from item.enumerate_all(include_disabled)

    def get_by_path(self, path: List[int]) -> SubmissionGradeItem:
        """
        Find a path in the grade structure.

        :param path: A list of ints that acts as a path of indices representing a location within
            the grade item tree
        :return: A SubmissionGradeItem subclass instance
        """
        try:
            item = self._grades[path[0]]
            for index in path[1:]:
                item = item._children[index]
        except (ValueError, IndexError) as ex:
            raise utils.BadPathError("Error parsing path {}".format(path), exception=ex)
        return item

    def get_by_name(self, name: str, include_disabled: bool = False) \
            -> Iterable[SubmissionGradeItem]:
        """
        Find all the grade items in the grade structure that have this name.

        :param name: The name to look for
        :param include_disabled: Whether to include disabled grade items
        :return: A generator that yields SubmissionGradeItem subclass instances
        """
        for item in self.enumerate_all(include_disabled):
            if item.is_name_like(name):
                yield item

    def add_hint_to_all_grades(self, path: List[int], name: str, value: ScoreNumber) -> None:
        """
        Add a new possible hint to ALL grade structures (by modifying a list still tied into the
        original grade_structure).

        :param path: A list of ints that acts as a path of indices representing a location within
            the grade item tree
        :param name: The name of the hint to add
        :param value: The point value of the hint to add
        """
        if len(path) == 0:
            raise utils.BadPathError("Path is empty")

        self.get_by_path(path).add_hint(name, value)

    def replace_hint_for_all_grades(self, path: List[int], index: int, name: str,
                                    value: ScoreNumber) -> None:
        """
        Replace an existing hint for ALL grade structures (by modifying a list still tied into the
        original grade_structure).

        :param path: A list of ints that acts as a path of indices representing a location within
            the grade item tree
        :param index: The index of the hint to replace in the list of hints
        :param name: The new name of the hint
        :param value: The new point value of the hint
        """
        if len(path) == 0:
            raise utils.BadPathError("Path is empty")

        try:
            self.get_by_path(path).replace_hint(index, name, value)
        except (ValueError, IndexError) as ex:
            raise utils.BadPathError("Invalid hint index {} at path {}".format(index, path),
                                     exception=ex)

    def is_late(self) -> bool:
        return self._is_late

    def get_score(self) -> Tuple[ScoreNumber, ScoreNumber, List[Tuple[str, ScoreNumber]]]:
        """
        Calculate the total score (all points added up) for this submission.

        :return: A tuple with the points earned for this submission, the total points possible for
            this submission, and the individual point scores for this submission
        """
        points_earned = 0.0
        points_possible = 0.0
        individual_points = []  # type: List[Tuple[str, ScoreNumber]]

        for item in self._grades:
            if item._enabled:
                item_earned, item_possible, item_points = item.get_score(self._is_late)
                # Add to the total
                points_earned += item_earned
                points_possible += item_possible
                individual_points += item_points

        # Make everything an int if we can
        points_earned = make_score_number(points_earned)
        points_possible = make_score_number(points_possible)

        return points_earned, points_possible, individual_points

    def get_feedback(self) -> str:
        """
        Patch together all the grade comments for this submission.
        """
        content = "\n".join(item.get_feedback(self._is_late, 1) for item in self._grades)
        return FeedbackHTMLTemplates.base.format(content=content,
                                                 overall_comments=self._overall_comments_html)

    def to_plain_data(self) -> Dict[str, object]:
        """
        Get the grade values as plain old data.
        """
        points_earned, points_possible, _ = self.get_score()
        return {
            "is_late": self._is_late,
            "overall_comments": self._overall_comments,
            "overall_comments_html": self._overall_comments_html,
            "points_earned": points_earned,
            "points_possible": points_possible,
            "grades": [item.to_plain_data() for item in self._grades]
        }

    def set_late(self, is_late: bool) -> None:
        self._is_late = is_late

    def set_overall_comments(self, overall_comments: str) -> None:
        self._overall_comments = overall_comments
        self._overall_comments_html = _markdown_to_html(overall_comments)
