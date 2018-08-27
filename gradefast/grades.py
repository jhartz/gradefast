"""
Classes for handling the calculation of grades and rendering of feedback for submissions.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from gradefast import exceptions, utils
from gradefast.models import GradeItem, GradeScore, GradeSection, Hint, ScoreNumber, WeakScoreNumber
from gradefast.parsers import make_score_number


class FeedbackHTMLTemplates:
    base = """\
<div style="font-family: Helvetica, Arial, sans-serif; font-size: 10pt; line-height: 1.3;">
{content}

<div style="font-size: 10.5pt;">
{overall_comments}
</div>
</div>"""

    # For the last lab before Christmas:
#     base = """\
# <table cellspacing="0" cellpadding="0" border="0">
# <tbody>
# <tr>
# <td colspan="3"><img src="https://www.cs.rit.edu/~jxh6994/lights.gif" /><img src="https://www.cs.rit.edu/~jxh6994/lights.gif" /><img src="https://www.cs.rit.edu/~jxh6994/lights.gif" /></td>
# </tr>
# <tr>
# <td width="1"><img src="https://www.cs.rit.edu/~jxh6994/lights270.gif" /><br /><img src="https://www.cs.rit.edu/~jxh6994/lights270.gif" /><br /><img src="https://www.cs.rit.edu/~jxh6994/lights270.gif" /><br /><img src="https://www.cs.rit.edu/~jxh6994/lights270.gif" /></td>
# <td>
#
# <div style="font-family: Helvetica, Arial, sans-serif; font-size: 10pt; line-height: 1.3;">
# {content}
#
# <div style="font-size: 10.5pt;">
# {overall_comments}
# </div>
# </div>
#
# </td>
# <td width="1"><img src="https://www.cs.rit.edu/~jxh6994/lights90.gif" /><br /><img src="https://www.cs.rit.edu/~jxh6994/lights90.gif" /><br /><img src="https://www.cs.rit.edu/~jxh6994/lights90.gif" /><br /><img src="https://www.cs.rit.edu/~jxh6994/lights90.gif" /></td>
# </tr>
# <tr>
# <td colspan="3"><img src="https://www.cs.rit.edu/~jxh6994/lights180.gif" /><img src="https://www.cs.rit.edu/~jxh6994/lights180.gif" /><img src="https://www.cs.rit.edu/~jxh6994/lights180.gif" /></td>
# </tr>
# </tbody>
# </table>"""

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


def _get_deducted_points(score: ScoreNumber, late_deduction_percent: ScoreNumber,
                         precision: int = 0) -> ScoreNumber:
    """
    Get the amount of points to lop off of a section if the submission is late.

    :param score: The raw score
    :param late_deduction_percent: The percentage to lop off (0-100)
    :param precision: The amount of decimal places
    """
    d = round(score * (late_deduction_percent / 100.0), precision)
    if precision == 0:
        d = int(d)
    return max(0, d)


class SubmissionGradeItem:
    """
    Superclass for SubmissionGradeScore and SubmissionGradeSection.
    """

    __slots__ = ("_change_handler", "_grade_item", "_name", "_name_html", "_notes", "_notes_html",
                 "_enabled", "_hints_set")

    def __init__(self, grade_item: GradeItem) -> None:
        """
        Initialize the state of a SubmissionGradeItem from a base GradeItem.
        """
        self._change_handler = None
        self._grade_item = grade_item

        # "None" indicates that we should use the default from grade_item. (We'll set these
        # properties if they're changed for this specific submission.) This technique is also used
        # for mutable but expensive properties in subclasses (i.e. anything that's not numeric).
        self._name = None        # type: Optional[str]
        self._name_html = None   # type: Optional[str]
        self._notes = None       # type: Optional[str]
        self._notes_html = None  # type: Optional[str]

        self._enabled = grade_item.default_enabled
        self._hints_set = {}  # type: Dict[int, bool]

    def get_state(self) -> dict:
        """
        Return state that should be persisted to the GradeFast save file (serialized via pickle).
        This should include state specific to the submission, but not anything that's part of the
        grade structure itself (unless it is something that can be modified on a per-submission
        basis).

        This method should be extended in subclasses.
        """
        return {
            "name": self._name,
            "notes": self._notes,
            "enabled": self._enabled,
            "hints_set": self._hints_set
        }

    def set_state(self, state: dict) -> None:
        """
        Set state that was previously persisted with get_state().

        This method should be extended in subclasses.
        """
        self.set_name(state["name"])
        self.set_notes(state["notes"])
        self.set_enabled(state["enabled"])
        self._hints_set = state["hints_set"]

    def set_change_handler(self, change_handler: Callable[[], None]) -> None:
        """
        Set a handler that should be called whenever this grade item's state has changed. This will
        overwrite a previously set handler.

        This method is usually called as a result of the SubmissionManager calling
        set_change_handler() on a SubmissionGrade instance.
        """
        self._change_handler = change_handler

    def changed(self) -> None:
        """
        Tell the world (or at least someone who cares to listen) that our state has changed.
        """
        if self._change_handler:
            self._change_handler()

    def enumerate_all(self, include_disabled: bool = False) -> Iterable["SubmissionGradeItem"]:
        """
        Enumerate recursively over all grade items (sections, scores, etc.), including ourself and
        any children, yielding all enabled grade items (and disabled ones if include_disabled is
        True) and traversing recursively into child grade items.
        """
        raise NotImplementedError("enumerate_all must be implemented by subclass")

    def is_name_like(self, other_name: str) -> bool:
        """
        Determine whether the name of this grade item is like the provided name, ignoring case.

        :param other_name: The name to compare against.
        :return: Whether they are pretty much the same.
        """
        name = self.get_name()
        return name.lower() == other_name.lower()

    def get_name(self) -> str:
        return self._name if self._name is not None else self._grade_item.default_name

    def get_name_html(self) -> str:
        return self._name_html if self._name_html is not None else \
               self._grade_item.get_default_name_html()

    def set_name(self, name: Optional[str]) -> None:
        """
        Set the name of this grade item. This changes the name only for this submission; other
        submissions will still have the original name.
        """
        if name is None or name == self._grade_item.default_name:
            self._name = None
            self._name_html = None
        else:
            self._name = name
            self._name_html = utils.markdown_to_html_inline(name)
        self.changed()

    def get_notes(self) -> str:
        return self._notes if self._notes is not None else self._grade_item.default_notes

    def get_notes_html(self) -> str:
        return self._notes_html if self._notes_html is not None else \
               self._grade_item.get_default_notes_html()

    def set_notes(self, notes: Optional[str]) -> None:
        """
        Set this grade item's notes. This changes the notes only for this submission; other
        submissions will still have the original notes.
        """
        if notes is None or notes == self._grade_item.default_notes:
            self._notes = None
            self._notes_html = None
        else:
            self._notes = notes
            self._notes_html = utils.markdown_to_html(notes)
        self.changed()

    def is_enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, is_enabled: Optional[bool]) -> None:
        """
        Set whether this grade item is enabled. This changes the enabled status only for this
        submission; it won't change whether this grade item is enabled for other submissions.
        """
        self._enabled = is_enabled
        self.changed()

    def is_hint_enabled(self, index: int) -> bool:
        """
        Determine whether a particular hint is enabled, given its index in self._hints.
        """
        return self._hints_set.get(index, self._grade_item.hints[index].default_enabled)

    def set_hint_enabled(self, index: int, is_enabled: bool) -> None:
        """
        Set whether a specific hint is enabled for this grade item.

        :param index: The index of the hint
        :param is_enabled: Whether the hint should be set to enabled
        """
        self._hints_set[index] = is_enabled
        self.changed()

    def add_hint(self, name: str, value: WeakScoreNumber) -> None:
        """
        Add a new possible hint to this grade item (and all other instances in other submissions)
        by modifying a list in the original grade structure.

        :param name: The name of the hint to add
        :param value: The point value of the hint to add
        """
        self._grade_item.add_hint(Hint(name=name, value=make_score_number(value),
                                       default_enabled=False))
        self.changed()

    def replace_hint(self, index: int, name: str, value: WeakScoreNumber) -> None:
        """
        Replace an existing hint for this grade item (and all other instances in other submissions)
        by modifying a list in the original grade structure.

        This may raise a ValueError or an IndexError if "index" is not valid.

        :param index: The index of the hint to replace in the list of hints
        :param name: The new name of the hint
        :param value: The new point value of the hint
        """
        index = int(index)
        old_hint = self._grade_item.hints[index]
        self._grade_item.replace_hint(index, Hint(name=name, value=make_score_number(value),
                                                  default_enabled=old_hint.default_enabled))
        self.changed()

    def get_score(self, is_late: bool) -> Tuple[ScoreNumber, ScoreNumber]:
        """
        Get the current point values and total possible points for this grade item.

        :param is_late: Whether the parent submission is marked as late
        :return: A tuple with the points earned for this item/section (int or float) and the total
            points possible for this item/section (int or float).
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

    def get_data(self) -> Dict[str, object]:
        """
        Get a representation of this grade item as plain data (just lists, dicts, etc.), mostly
        for use by the gradebook.
        This should be overridden in subclasses to extend the dict returned here, or replace it
        with a more appropriate representation.
        """
        return {
            "name": self.get_name(),
            "name_html": self.get_name_html(),
            "notes": self.get_notes(),
            "notes_html": self.get_notes_html(),
            "enabled": self._enabled,
            "hints": [
                {
                    "name": hint.name,
                    "name_html": hint.get_name_html(),
                    "value": hint.value,
                    "enabled": self.is_hint_enabled(index)
                }
                for index, hint in enumerate(self._grade_item.hints)
            ]
        }

    def get_export_data(self, is_late: bool) -> Dict[str, object]:
        """
        Get export data for this grade item. This is similar to "get_data()", but includes
        data that is more useful for other applications rather than the gradebook.
        This should be overridden in subclasses to extend the dict returned here, or replace it
        with a more appropriate representation.

        :param is_late: Whether the parent submission is marked as late
        """
        if self.is_enabled():
            points_earned, points_possible = self.get_score(is_late)
            return {
                "name": self.get_name(),
                "enabled": True,
                "points_earned": points_earned,
                "points_possible": points_possible,
                "enabled_hints": [
                    {
                        "name": hint.name,
                        "value": hint.value
                    }
                    for index, hint in enumerate(self._grade_item.hints) if self.is_hint_enabled(index)
                ]
            }
        else:
            return {
                "name": self.get_name(),
                "enabled": False
            }


class SubmissionGradeScore(SubmissionGradeItem):
    """
    Represents an individual grade item with a point value and score. This is a leaf node in the
    grade structure tree; it's the equivalent to a GradeScore, but with state for a particular
    submission.
    """

    __slots__ = ("_points", "_base_score", "_comments", "_comments_html")

    def __init__(self, grade_score: GradeScore) -> None:
        super().__init__(grade_score)

        self._points = grade_score.points
        self._base_score = grade_score.default_score

        # Like in the parent class, we'll use the defaults for these (from the GradeScore) until
        # they're actually modified.
        self._comments = None       # type: str
        self._comments_html = None  # type: str

    def get_state(self) -> dict:
        state = super().get_state()
        state.update({
            "base_score": self._base_score,
            "comments": self._comments
        })
        return state

    def set_state(self, state: dict) -> None:
        super().set_state(state)
        self._base_score = state["base_score"]
        self.set_comments(state["comments"])

    def enumerate_all(self, include_disabled: bool = False) -> Iterable[SubmissionGradeItem]:
        if self._enabled or include_disabled:
            yield self

    def is_touched(self) -> bool:
        """
        Determine whether this grade score has been modified from its defaults, and is affecting
        the overall score or feedback.
        """
        return self._enabled and (
            self._base_score != self._grade_item.default_score or
            self._comments is not None or
            any(self.is_hint_enabled(index) != hint.default_enabled
                for index, hint in enumerate(self._grade_item.hints))
        )

    def set_base_score(self, score: WeakScoreNumber) -> None:
        """
        Set the score for this grade item, excluding the effects of enabled hints.
        """
        self._base_score = make_score_number(score)
        self.changed()

    def set_effective_score(self, score: WeakScoreNumber) -> None:
        """
        Set the score for this grade item, including any hints that are applied.
        """
        score = make_score_number(score)
        # To get the base score, we need to "undo" the effects of hints
        for index, hint in enumerate(self._grade_item.hints):
            if self.is_hint_enabled(index):
                score -= hint.value
        self._base_score = score
        self.changed()

    def get_comments(self) -> str:
        return self._comments if self._comments is not None else \
               self._grade_item.default_comments

    def get_comments_html(self) -> str:
        return self._comments_html if self._comments_html is not None else \
               self._grade_item.get_default_comments_html()

    def set_comments(self, comments: Optional[str]) -> None:
        if comments is None or comments == self._grade_item.default_comments:
            self._comments = None
            self._comments_html = None
        else:
            self._comments = comments
            self._comments_html = utils.markdown_to_html(comments)
        self.changed()

    def get_score(self, is_late: bool) -> Tuple[ScoreNumber, ScoreNumber]:
        points_earned = self._base_score
        for index, hint in enumerate(self._grade_item.hints):
            if self.is_hint_enabled(index):
                points_earned += hint.value
        return points_earned, self._points

    def get_feedback(self, is_late: bool, depth: int = 0) -> str:
        # Start off with the score (although we skip the score if it's 0 out of 0)
        points_earned, points_possible = self.get_score(is_late)
        score_feedback = ""
        if points_earned and not points_possible:
            # No total points, but still points earned
            score_feedback = FeedbackHTMLTemplates.item_score_bonus.format(points=points_earned)
        elif points_possible:
            # We have total points, and possibly points earned
            score_feedback = FeedbackHTMLTemplates.item_score.format(
                points_earned=points_earned, points_possible=points_possible)

        # Generate dat feedback
        name_html = self.get_name_html()
        if depth < 2:
            name_html = "<b>" + name_html + "</b>"
        feedback = FeedbackHTMLTemplates.item_header.format(title=name_html,
                                                            content=score_feedback)

        # Add hints, if applicable
        for index, hint in enumerate(self._grade_item.hints):
            if self.is_hint_enabled(index):
                if hint.value == 0:
                    feedback += FeedbackHTMLTemplates.hint_no_points.format(
                        reason=hint.get_name_html())
                else:
                    feedback += FeedbackHTMLTemplates.hint.format(
                        points=hint.value, reason=hint.get_name_html())

        # Now, add any comments
        comments_html = self.get_comments_html()
        if comments_html:
            feedback += FeedbackHTMLTemplates.item_comments.format(content=comments_html)

        return feedback

    def get_data(self) -> Dict[str, object]:
        data = super().get_data()
        points_earned, points_possible = self.get_score(False)
        data.update({
            "score": points_earned,
            "points": points_possible,
            "comments": self.get_comments(),
            "comments_html": self.get_comments_html(),
            "touched": self.is_touched()
        })
        return data

    def get_export_data(self, is_late: bool) -> Dict[str, object]:
        return super().get_export_data(is_late)


class SubmissionGradeSection(SubmissionGradeItem):
    """
    Represents a section of grade items with SubmissionGradeItem children.
    This is an internal node in the grade structure tree.
    """

    __slots__ = ("_late_deduction", "_children")

    def __init__(self, grade_section: GradeSection) -> None:
        super().__init__(grade_section)

        self._late_deduction = grade_section.default_late_deduction
        self._children = _create_tree_from_structure(grade_section.grades)

    def get_state(self) -> dict:
        state = super().get_state()
        state.update({
            "late_deduction": self._late_deduction,
            "children": [child.get_state() for child in self._children]
        })
        return state

    def set_state(self, state: dict) -> None:
        super().set_state(state)
        self.set_late_deduction(state["late_deduction"])
        for index, child_state in enumerate(state["children"]):
            self._children[index].set_state(child_state)

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

    def set_late_deduction(self, late_deduction: ScoreNumber) -> None:
        """
        Set the late deduction for this submission. This changes the late deduction only for this
        submission; other submissions will still have the original late deduction.
        """
        self._late_deduction = late_deduction
        self.changed()

    def get_score(self, is_late: bool) -> Tuple[ScoreNumber, ScoreNumber]:
        points_earned = 0.0
        points_possible = 0.0

        for item in self.enumerate_enabled_children():
            item_earned, item_possible = item.get_score(is_late)
            # Add to the total
            points_earned += item_earned
            points_possible += item_possible

        # Account for any hints
        for index, hint in enumerate(self._grade_item.hints):
            if self.is_hint_enabled(index):
                points_earned += hint.value

        # Check if it's late
        if is_late and self._late_deduction:
            # It's late! Deduct
            points_earned -= _get_deducted_points(points_earned, self._late_deduction)

        # Make everything an int if we can
        points_earned = make_score_number(points_earned)
        points_possible = make_score_number(points_possible)

        return points_earned, points_possible

    def get_feedback(self, is_late: bool, depth: int = 0) -> str:
        points_earned, points_possible = self.get_score(is_late)

        # Add the title and overall points earned / points possible
        name_html = self.get_name_html()
        if depth < 2:
            name_html = "<b>" + name_html + "</b>"
        feedback = FeedbackHTMLTemplates.section_header.format(title=name_html,
                                                               points_earned=points_earned,
                                                               points_possible=points_possible)

        # Add hint feedback
        for index, hint in enumerate(self._grade_item.hints):
            if self.is_hint_enabled(index):
                if hint.value == 0:
                    feedback += FeedbackHTMLTemplates.hint_no_points.format(
                        reason=hint.get_name_html())
                else:
                    feedback += FeedbackHTMLTemplates.hint.format(
                        points=hint.value, reason=hint.get_name_html())

        # Add lateness feedback if necessary
        if is_late and self._late_deduction:
            feedback += FeedbackHTMLTemplates.section_late.format(
                points=-_get_deducted_points(points_earned, self._late_deduction),
                percentage=self._late_deduction)

        # Add the feedback for any children
        feedback += FeedbackHTMLTemplates.section_body.format(
            content="\n".join(item.get_feedback(is_late, depth + 1)
                              for item in self.enumerate_enabled_children()))

        return feedback

    def get_data(self) -> Dict[str, object]:
        data = super().get_data()
        data.update({
            "children": [child.get_data() for child in self._children]
        })
        return data

    def get_export_data(self, is_late: bool) -> Dict[str, object]:
        data = super().get_export_data(is_late)
        if self.is_enabled():
            data.update({
                "children": [child.get_export_data(is_late) for child in self._children]
            })
        return data


def _create_tree_from_structure(structure: Sequence[GradeItem]) -> List[SubmissionGradeItem]:
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


class SubmissionGrade:
    """
    Represents a submission's grade, including the grade structure tree with state (scores,
    comments, hints enabled, etc.) for a particular submission.

    Many of the undocumented methods are equivalents to a similar method in the SubmissionGradeItem
    class.
    """

    __slots__ = ("_change_handler", "_grades", "_is_late", "_overall_comments",
                 "_overall_comments_html")

    def __init__(self, grade_structure: Sequence[GradeItem]) -> None:
        self._change_handler = None

        self._grades = _create_tree_from_structure(grade_structure)

        self._is_late = False
        self._overall_comments = ""
        self._overall_comments_html = ""

    def get_state(self) -> dict:
        return {
            "grades": [grade_item.get_state() for grade_item in self._grades],

            "is_late": self._is_late,
            "overall_comments": self._overall_comments
        }

    def set_state(self, state: dict, restore_grades: bool) -> None:
        if restore_grades:
            for index, grade_item_state in enumerate(state["grades"]):
                self._grades[index].set_state(grade_item_state)

        self.set_late(state["is_late"])
        self.set_overall_comments(state["overall_comments"])

    def set_change_handler(self, change_handler: Callable[[], None]) -> None:
        self._change_handler = change_handler
        for item in self.enumerate_all(include_disabled=True):
            item.set_change_handler(change_handler)

    def changed(self) -> None:
        if self._change_handler:
            self._change_handler()

    def enumerate_all(self, include_disabled: bool = False) -> Iterable[SubmissionGradeItem]:
        for item in self._grades:
            yield from item.enumerate_all(include_disabled)

    def get_by_path(self, path: Sequence[int]) -> SubmissionGradeItem:
        """
        Find a SubmissionGradeItem in this submission's grade structure by its path.

        :param path: A list of ints that acts as a path of indices representing a location within
            the grade item tree
        """
        try:
            item = self._grades[path[0]]
            for index in path[1:]:
                item = item._children[index]
        except (ValueError, IndexError) as ex:
            raise exceptions.BadPathError("Error parsing path {}".format(path), exception=ex)
        return item

    def get_by_name(self, name: str, include_disabled: bool = False) \
            -> Iterable[SubmissionGradeItem]:
        """
        Find all the SubmissionGradeItems in this submission's grade structure that have a certain
        name.

        :param name: The name to look for
        :param include_disabled: Whether to include disabled grade items
        :return: A generator that yields SubmissionGradeItem subclass instances
        """
        for item in self.enumerate_all(include_disabled):
            if item.is_name_like(name):
                yield item

    def add_hint_to_all_grades(self, path: Sequence[int], name: str, value: ScoreNumber) -> None:
        """
        Add a new possible hint to the grade structures FOR ALL SUBMISSIONS (by modifying a list
        still tied into the original grade_structure).

        :param path: A list of ints that acts as a path of indices representing a location within
            the grade item tree
        :param name: The name of the hint to add
        :param value: The point value of the hint to add
        """
        if len(path) == 0:
            raise exceptions.BadPathError("Path is empty")

        self.get_by_path(path).add_hint(name, value)

    def replace_hint_for_all_grades(self, path: Sequence[int], index: int, name: str,
                                    value: ScoreNumber) -> None:
        """
        Replace an existing hint in the grade structures FOR ALL SUBMISSIONS (by modifying a list
        still tied into the original grade_structure).

        :param path: A list of ints that acts as a path of indices representing a location within
            the grade item tree
        :param index: The index of the hint to replace in the list of hints
        :param name: The new name of the hint
        :param value: The new point value of the hint
        """
        if len(path) == 0:
            raise exceptions.BadPathError("Path is empty")

        try:
            self.get_by_path(path).replace_hint(index, name, value)
        except (ValueError, IndexError) as ex:
            raise exceptions.BadPathError("Invalid hint index {} at path {}".format(index, path),
                                          exception=ex)

    def is_late(self) -> bool:
        return self._is_late

    def set_late(self, is_late: bool) -> None:
        self._is_late = is_late
        self.changed()

    def set_overall_comments(self, overall_comments: str) -> None:
        self._overall_comments = overall_comments
        self._overall_comments_html = utils.markdown_to_html(overall_comments)
        self.changed()

    def get_score(self) -> Tuple[ScoreNumber, ScoreNumber]:
        """
        Calculate the total score (all points added up) for this submission.

        :return: A tuple with the points earned for this submission and the total points possible
            for this submission.
        """
        points_earned = 0.0
        points_possible = 0.0

        for item in self._grades:
            if item._enabled:
                item_earned, item_possible = item.get_score(self._is_late)
                # Add to the total
                points_earned += item_earned
                points_possible += item_possible

        # Make everything an int if we can
        points_earned = make_score_number(points_earned)
        points_possible = make_score_number(points_possible)

        return points_earned, points_possible

    def get_feedback(self) -> str:
        """
        Patch together all the grade comments for this submission.
        """
        content = "\n".join(item.get_feedback(self._is_late, 1)
                            for item in self._grades
                            if item._enabled)
        return FeedbackHTMLTemplates.base.format(content=content,
                                                 overall_comments=self._overall_comments_html)

    def get_data(self) -> Dict[str, object]:
        """
        Get a representation of this submission's grade items as plain data (lists, dicts, etc.).
        """
        points_earned, points_possible = self.get_score()
        return {
            "is_late": self.is_late(),
            "overall_comments": self._overall_comments,
            "overall_comments_html": self._overall_comments_html,
            "points_earned": points_earned,
            "points_possible": points_possible,
            "grades": [item.get_data() for item in self._grades]
        }

    def get_export_data(self) -> Dict[str, object]:
        """
        Get export data for this submission's grade items. This is similar to "get_data()",
        but includes data that is more useful for other applications rather than the gradebook.
        This does not include data such as the overall score and feedback.
        """
        return {
            "is_late": self.is_late(),
            "grades": [item.get_export_data(self.is_late()) for item in self._grades]
        }
