"""
GradeFast Submission Manager - Glorified list containing all the submissions.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import statistics
import time
from collections import OrderedDict
from typing import Callable, Dict, Iterable, List, NewType, Optional, Tuple

from iochannels import Channel, MemoryLog
from pyprovide import inject

from gradefast import events
from gradefast.grades import SubmissionGrade
from gradefast.hosts import Host
from gradefast.loggingwrapper import get_logger
from gradefast.models import EMPTY_STATS, Path, Settings, Stats
from gradefast.persister import Persister

_logger = get_logger("submissions")
TimerContext = NewType("TimerContext", int)


def _calculate_stats(values_with_ids: List[Tuple[float, int]]) -> Stats:
    if len(values_with_ids) == 0:
        return EMPTY_STATS

    values_with_ids.sort()
    values = [t for t, _ in values_with_ids]

    n = len(values_with_ids)
    i = n // 2
    if n % 2 == 0:
        median_values = [values_with_ids[i - 1][0], values_with_ids[i][0]]
        median = sum(median_values) / 2.0
    else:
        median_values = [values_with_ids[i][0]]
        median = values_with_ids[i][0]

    return Stats(
        min=(values[0],  [id for value, id in values_with_ids if value == values[0]]),
        max=(values[-1], [id for value, id in values_with_ids if value == values[-1]]),
        median=(median,  [id for value, id in values_with_ids if value in median_values]),
        mean=statistics.mean(values),
        std_dev=statistics.pstdev(values),
        modes=_calculate_modes(values))


def _calculate_modes(sorted_values: List[float]) -> List[float]:
    modes = []
    max_mode_count = 0
    current_value = None
    current_count = 0

    def new_value():
        nonlocal modes, max_mode_count
        if current_value is not None:
            if current_count == max_mode_count:
                modes.append(current_value)
            elif current_count > max_mode_count:
                modes = [current_value]
                max_mode_count = current_count

    for value in sorted_values:
        if value == current_value:
            current_count += 1
        else:
            new_value()
            current_value = value
            current_count = 1
    new_value()

    return modes


class Submission:
    """
    A submission by a particular student.
    """

    def __init__(self, submission_id: int, name: str, full_name: str, path: Path,
                 submission_grade: SubmissionGrade) -> None:
        """
        Initialize a new Submission.

        :param submission_id: The unique ID of the submission.
        :param name: The name associated with the submission (i.e. the student's name).
        :param full_name: The full name of the submission (i.e. the full filename of the folder
            containing the submission).
        :param path: The path of the root of the submission.
        :param submission_grade: A SubmissionGrade instance to store the submission's scores and
            feedback.
        """
        self._change_handler = None

        self._submission_id = submission_id
        self._name = name
        self._full_name = full_name
        self._path = path
        self._submission_grade = submission_grade

        self._html_logs = []  # type: List[MemoryLog]
        self._text_logs = []  # type: List[MemoryLog]
        self._start_and_end_times = []  # type: List[Tuple[float, Optional[float]]]

    def get_state(self) -> dict:
        """
        Return state that should be persisted to the GradeFast save file (serialized via pickle).
        See Persister in persister.py for details.

        This doesn't include this submission's SubmissionGrade; that is persisted separately.
        """
        return {
            "id": self._submission_id,
            "name": self._name,
            "full_name": self._full_name,
            "path": self._path,

            "html_logs": self._html_logs,
            "text_logs": self._text_logs,
            "start_and_end_times": self._start_and_end_times
        }

    @staticmethod
    def from_state(state: dict, submission_grade: SubmissionGrade) -> "Submission":
        """
        Create a new Submission based on state persisted from the get_state() method and a
        SubmissionGrade object for the submission.
        """
        submission = Submission(state["id"], state["name"], state["full_name"], state["path"],
                                submission_grade)
        submission._html_logs = state["html_logs"]
        submission._text_logs = state["text_logs"]
        submission._start_and_end_times = state["start_and_end_times"]
        return submission

    def set_change_handler(self, change_handler: Callable[[], None]) -> None:
        self._change_handler = change_handler
        self._submission_grade.set_change_handler(change_handler)

    def changed(self) -> None:
        if self._change_handler:
            self._change_handler()

    def get_id(self) -> int:
        return self._submission_id

    def get_name(self) -> str:
        return self._name

    def get_full_name(self) -> str:
        return self._full_name

    def get_path(self) -> Path:
        return self._path

    def get_grade(self) -> SubmissionGrade:
        return self._submission_grade

    def get_times(self) -> List[Tuple[float, float]]:
        return [(start, end)
                for start, end in self._start_and_end_times
                if end is not None and end - start > 0]

    def add_logs(self, html_log: MemoryLog, text_log: MemoryLog) -> None:
        self._html_logs.append(html_log)
        self._text_logs.append(text_log)
        self.changed()

    def get_html_logs(self) -> List[MemoryLog]:
        return self._html_logs

    def get_text_logs(self) -> List[MemoryLog]:
        return self._text_logs

    def start_timer(self) -> TimerContext:
        context = len(self._start_and_end_times)
        self._start_and_end_times.append((time.time(), None))
        self.changed()
        return context

    def stop_timer(self, context: TimerContext) -> None:
        times = self._start_and_end_times[context]
        assert times[1] is None
        self._start_and_end_times[context] = (times[0], time.time())
        self.changed()

    def __str__(self) -> str:
        if self._name != self._full_name:
            return "{} ({})".format(self._name, self._full_name)
        return self._name

    def to_json(self) -> dict:
        points_earned, points_possible = self._submission_grade.get_score()
        return {
            "id": self._submission_id,
            "name": self._name,
            "full_name": self._full_name,
            "path": str(self._path),
            "has_logs": len(self._html_logs) > 0,
            "times": self.get_times(),
            "is_late": self._submission_grade.is_late(),
            "points_earned": points_earned,
            "points_possible": points_possible
        }


class SubmissionManager:
    """
    Manages the GradeFast list of submissions, related stats.
    """

    @staticmethod
    def _get_submission_key(submission_id: int) -> str:
        return "submission-" + str(submission_id)

    @staticmethod
    def _get_submission_grade_key(submission_id: int) -> str:
        return "submission_grade-" + str(submission_id)

    @inject()
    def __init__(self, channel: Channel, host: Host, persister: Persister,
                 event_manager: events.EventManager, settings: Settings) -> None:
        self.channel = channel
        self.host = host
        self.persister = persister
        self.event_manager = event_manager

        # This could be set to something else when restoring from the save file
        self._grade_structure = settings.grade_structure

        self._submissions_by_id = OrderedDict()  # type: Dict[int, Submission]
        self._last_id = 0

        # Only restore the grades for persisted submissions if we're keeping the same grade
        # structure
        restore_grades = False

        # The save file contains 2 copies of the grade structure:
        #   - "persisted_original_grade_structure" (exactly what was in the YAML file when
        #     GradeFast ran); and
        #   - "persisted_grade_structure" (the original one, plus any modifications like added or
        #     edited hints). This is what we restore from if we decide to use the grade structure
        #     stored in the save file instead of the one in the YAML file.

        # These are NOT necessarily the same. We store both to use when checking if the grade
        # structure in the YAML file has actually changed, so we don't bother the user if they
        # changed the grade structure in GradeFast (e.g. added or edited a hint) but didn't
        # actually change the YAML file.

        # If the save file has a persisted grade structure ("persisted_grade_structure"), to check
        # if we should use it without prompting the user, we check that EITHER:
        #   - settings.grade_structure == persisted_original_grade_structure, indicating that the
        #     structure in the YAML file hasn't changed since the last time we ran GradeFast; OR
        #   - settings.grade_structure == persisted_grade_structure (i.e. the actual grade
        #     structure from the YAML file matches the one stored in the save file, possibly after
        #     modifications like adding or editing hints). If this is true but the above statement
        #     isn't, then this could mean that the user added or edited hints in GradeFast, but
        #     also updated the YAML file to match.

        # This will be written to the save file as the "original_grade_structure" property.
        # If we decide to use the grade structure in the save file, we'll update both
        # self._grade_structure and this guy.
        original_grade_structure = self._grade_structure

        persisted_grade_structure = self.persister.get("submissions", "grade_structure")
        persisted_original_grade_structure = self.persister.get("submissions",
                                                                "original_grade_structure")
        if persisted_grade_structure:
            self.channel.print("Reading data from save file")

            if self._grade_structure == persisted_original_grade_structure or \
                    self._grade_structure == persisted_grade_structure:
                restore_grades = True
            else:
                while True:
                    self.channel.error("The grade structure in the save file is different from "
                                       "the one in the YAML file.")
                    choice = self.channel.prompt(
                        "Do you want to restore the one from the save file?", ["Y", "n"], "y")
                    if choice == "y":
                        restore_grades = True
                        break

                    # Double-confirm (switching the semantics of "y" and "n" to be extra confusing)
                    choice = self.channel.prompt(
                        "This will discard all grade data (scores, comments, etc.) that was stored "
                        "in the save file! Are you sure you want to do this?", ["Y", "n"], "y")
                    if choice == "y":
                        # I guess they're sure; we'll leave restore_grades as False
                        break

            if restore_grades:
                # We're using the persisted grade structure from the save file
                self._grade_structure = persisted_grade_structure
                original_grade_structure = persisted_original_grade_structure

        # Read any persisted submissions from the save file
        persisted_submissions_ids = self.persister.get("submissions", "ids")
        if persisted_submissions_ids:
            for submission_id in persisted_submissions_ids:
                if submission_id in self._submissions_by_id:
                    _logger.warning("Duplicate submission ID {} found in saved data", submission_id)
                else:
                    self._restore_persisted_submission(submission_id, restore_grades=restore_grades)

        # Re-persist everything we got. This will also persist the list of submissions and the
        # grade structure.
        self._persist_all_submissions()
        # Persist the original grade structure (see the wall of comment text above). We only want
        # to do this once, so that if the user makes changes to the grade structure (adding or
        # editing hints), we'll still have the original grade structure stored. If we're using a
        # grade structure that we got out of the save file, then this statement will just set
        # "original_grade_structure" back to what it was before.
        self.persister.set("submissions", "original_grade_structure", original_grade_structure)

        # Phew, all done; tell the world
        self.event_manager.dispatch_event(events.NewSubmissionsEvent())

    def _get_change_handler(self, submission_id: int) -> Callable[[], None]:
        return lambda: self._persist_submission(submission_id)

    def has_submissions(self) -> bool:
        return len(self._submissions_by_id) > 0

    def add_submission(self, name: str, full_name: str, path: Path,
                       send_event: bool = True) -> Submission:
        self._last_id += 1
        new_submission_id = self._last_id
        assert new_submission_id not in self._submissions_by_id

        new_submission_grade = SubmissionGrade(self._grade_structure)
        self._submissions_by_id[new_submission_id] = Submission(
            new_submission_id, name, full_name, path, new_submission_grade)
        self._submissions_by_id[new_submission_id].set_change_handler(
            self._get_change_handler(new_submission_id))

        self._persist_submission(new_submission_id)
        if send_event:
            self.event_manager.dispatch_event(events.NewSubmissionsEvent())

        return self._submissions_by_id[new_submission_id]

    def get_submission(self, submission_id: int) -> Submission:
        return self._submissions_by_id[submission_id]

    def drop_submission(self, submission_id: int) -> None:
        assert submission_id in self._submissions_by_id
        del self._submissions_by_id[submission_id]
        self._clear_persisted_submission(submission_id)
        self.event_manager.dispatch_event(events.NewSubmissionsEvent())

    def _restore_persisted_submission(self, submission_id: int, restore_grades: bool) -> None:
        assert submission_id not in self._submissions_by_id
        try:
            submission_state = self.persister.get(
                "submissions", self._get_submission_key(submission_id))
            if not submission_state:
                _logger.warning("Couldn't find saved submission (ID {})", submission_id)
                return

            submission_grade = SubmissionGrade(self._grade_structure)
            submission_grade_state = self.persister.get(
                "submissions", self._get_submission_grade_key(submission_id))
            submission_grade.set_state(submission_grade_state, restore_grades=restore_grades)

            submission = Submission.from_state(submission_state, submission_grade)
        except:
            _logger.exception("Error restoring saved submission (ID {})", submission_id)
            return

        if not self.host.folder_exists(submission.get_path()):
            _logger.warning("Previously saved submission {} (ID {}) no longer exists at {}",
                            submission, submission_id, submission.get_path())
            return

        submission.set_change_handler(self._get_change_handler(submission_id))
        self._last_id = max(self._last_id, submission_id)
        self._submissions_by_id[submission.get_id()] = submission

    def _clear_persisted_submission(self, submission_id: int) -> None:
        self._persist_metadata()

        self.persister.clear("submissions", self._get_submission_key(submission_id))
        self.persister.clear("submissions", self._get_submission_grade_key(submission_id))

    def _persist_submission(self, submission_id: int) -> None:
        assert submission_id in self._submissions_by_id
        self._persist_metadata()

        self.persister.set("submissions", self._get_submission_key(submission_id),
                           self._submissions_by_id[submission_id].get_state())
        self.persister.set("submissions", self._get_submission_grade_key(submission_id),
                           self._submissions_by_id[submission_id].get_grade().get_state())

    def _persist_all_submissions(self) -> None:
        self.persister.clear_all("submissions")
        self._persist_metadata()

        for submission_id, submission in self._submissions_by_id.items():
            self.persister.set("submissions", self._get_submission_key(submission_id),
                               submission.get_state())
            self.persister.set("submissions", self._get_submission_grade_key(submission_id),
                               submission.get_grade().get_state())

    def _persist_metadata(self) -> None:
        self.persister.set("submissions", "ids", list(self._submissions_by_id.keys()))
        self.persister.set("submissions", "grade_structure", self._grade_structure)

    def get_first_submission_id(self) -> Optional[int]:
        for submission_id in self._submissions_by_id.keys():
            return submission_id
        return None

    def get_last_submission_id(self) -> Optional[int]:
        if self._last_id > 0:
            return self._last_id
        return None

    def get_next_submission_id(self, submission_id: int) -> Optional[int]:
        submission_id += 1
        while True:
            if submission_id > self.get_last_submission_id():
                return None
            if submission_id in self._submissions_by_id:
                return submission_id
            submission_id += 1

    def get_previous_submission_id(self, submission_id: int) -> Optional[int]:
        submission_id -= 1
        while True:
            if submission_id < self.get_first_submission_id():
                return None
            if submission_id in self._submissions_by_id:
                return submission_id
            submission_id -= 1

    def get_all_submission_ids(self) -> Iterable[int]:
        return self._submissions_by_id.keys()

    def get_all_submissions(self) -> Iterable[Submission]:
        return self._submissions_by_id.values()

    def get_grading_stats(self) -> Stats:
        grades_with_id = []  # type: List[Tuple[float, int]]
        for submission_id, submission in self._submissions_by_id.items():
            points_earned, points_possible = submission.get_grade().get_score()
            percentage = 100 * points_earned / points_possible
            grades_with_id.append((percentage, submission_id))

        return _calculate_stats(grades_with_id)

    def get_timing_stats(self) -> Stats:
        times_with_id = []  # type: List[Tuple[float, int]]
        for submission_id, submission in self._submissions_by_id.items():
            total_time = round(sum((end - start)
                                   for start, end in submission._start_and_end_times
                                   if end is not None))
            if total_time > 0:
                times_with_id.append((total_time, submission_id))

        return _calculate_stats(times_with_id)
