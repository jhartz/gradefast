"""
GradeFast Submission Manager - Glorified list containing all the submissions.

Licensed under the MIT License. For more, see the LICENSE file.

Author: Jake Hartz <jake@hartz.io>
"""

import statistics
import time
from collections import OrderedDict
from typing import Dict, Iterable, List, NewType, Optional, Tuple

from iochannels import MemoryLog
from pyprovide import inject

from gradefast import events
from gradefast.grades import SubmissionGrade
from gradefast.loggingwrapper import get_logger
from gradefast.models import EMPTY_STATS, Path, Settings, Stats

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
        """
        self._submission_id = submission_id
        self._name = name
        self._full_name = full_name
        self._path = path
        self._submission_grade = submission_grade

        self._html_logs = []  # type: List[MemoryLog]
        self._text_logs = []  # type: List[MemoryLog]
        self._start_and_end_times = []  # type: List[Tuple[float, Optional[float]]]

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

    def get_html_logs(self) -> List[MemoryLog]:
        return self._html_logs

    def get_text_logs(self) -> List[MemoryLog]:
        return self._text_logs

    def start_timer(self) -> TimerContext:
        context = len(self._start_and_end_times)
        self._start_and_end_times.append((time.time(), None))
        return context

    def stop_timer(self, context: TimerContext) -> None:
        times = self._start_and_end_times[context]
        assert times[1] is None
        self._start_and_end_times[context] = (times[0], time.time())

    def __str__(self) -> str:
        if self._name != self._full_name:
            return "{} ({})".format(self._name, self._full_name)
        return self._name

    def to_json(self) -> dict:
        points_earned, points_possible, _ = self._submission_grade.get_score()
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

    @inject()
    def __init__(self, event_manager: events.EventManager, settings: Settings) -> None:
        self.event_manager = event_manager
        self.settings = settings

        self._submissions_by_id = OrderedDict()  # type: Dict[int, Submission]
        self._last_id = 0

    def has_submissions(self) -> bool:
        return len(self._submissions_by_id) > 0

    def add_submission(self, name: str, full_name: str, path: Path,
                       send_event: bool = True) -> Submission:
        self._last_id += 1
        new_submission_id = self._last_id
        new_submission_grade = SubmissionGrade(self.settings.grade_structure)

        self._submissions_by_id[new_submission_id] = Submission(
            new_submission_id, name, full_name, path, new_submission_grade)

        if send_event:
            self.event_manager.dispatch_event(events.NewSubmissionsEvent())
        return self._submissions_by_id[new_submission_id]

    def get_submission(self, submission_id: int) -> Submission:
        return self._submissions_by_id[submission_id]

    def drop_submission(self, submission_id: int, send_event: bool = True) -> None:
        del self._submissions_by_id[submission_id]
        if send_event:
            self.event_manager.dispatch_event(events.NewSubmissionsEvent())

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
            points_earned, points_possible, _ = submission.get_grade().get_score()
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
