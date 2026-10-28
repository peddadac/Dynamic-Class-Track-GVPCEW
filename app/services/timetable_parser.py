"""Timetable parsing service: converts OCR text into structured draft timetable entries."""

import re
import logging
from datetime import time

logger = logging.getLogger(__name__)

# Standard college period slots
DEFAULT_PERIOD_SLOTS = [
    {"period": 1, "start": "09:00", "end": "09:50"},
    {"period": 2, "start": "09:50", "end": "10:40"},
    {"period": 3, "start": "10:50", "end": "11:40"},
    {"period": 4, "start": "11:40", "end": "12:30"},
    {"period": 5, "start": "13:20", "end": "14:10"},
    {"period": 6, "start": "14:10", "end": "15:00"},
    {"period": 7, "start": "15:00", "end": "15:50"},
]

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


class TimetableParser:
    """Parses timetable text representations into structured, reviewable timetable entries."""

    def __init__(self, known_subjects=None, known_faculty=None, known_classrooms=None):
        """
        known_subjects: list of Subject model instances
        known_faculty: list of FacultyProfile model instances
        known_classrooms: list of Classroom model instances
        """
        self.subjects = known_subjects or []
        self.faculty = known_faculty or []
        self.classrooms = known_classrooms or []

    def parse_raw_text(self, raw_text):
        """
        Parses multi-line timetable text.
        Supports pipe-delimited, tab-delimited, or multi-space line tables.
        Returns a list of structured entry dictionaries.
        """
        if not raw_text:
            return self._generate_default_grid()

        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        entries = []
        found_days = set()

        for line in lines:
            # Check if this line starts with a day name
            matched_day = None
            for d in DAYS_OF_WEEK:
                if re.match(rf"^{d}\b", line, re.IGNORECASE):
                    matched_day = d
                    break

            if not matched_day:
                continue

            found_days.add(matched_day)

            # Split cells by pipe '|' or multiple spaces/tabs
            if "|" in line:
                cells = [c.strip() for c in line.split("|")][1:]  # skip the day column
            else:
                cells = [c.strip() for c in re.split(r"\s{3,}|\t+", line)][1:]

            for idx, slot in enumerate(DEFAULT_PERIOD_SLOTS):
                cell_text = cells[idx] if idx < len(cells) else ""
                entry = self._parse_single_cell(matched_day, slot, cell_text)
                entries.append(entry)

        # If no recognized days were found, generate a baseline draft grid with uncertainty flags
        if not entries:
            logger.info("Could not identify standard day rows in OCR text. Falling back to draft grid.")
            entries = self._generate_default_grid(uncertain=True)

        return entries

    def _parse_single_cell(self, day, slot, cell_text):
        """
        Parses text inside an individual cell.
        Example cell text formats:
        - 'CS501 / FAC01 / C-204'
        - 'Data Structures (Dr. Rao) [C-204]'
        - 'CS502 - C-204'
        - 'Free' or 'Library' or 'Sports'
        """
        cell_text = cell_text.strip()
        is_uncertain = False
        confidence = 1.0

        if not cell_text or cell_text.lower() in ["nil", "free", "-", "--", "na"]:
            return {
                "day": day,
                "period": slot["period"],
                "start_time": slot["start"],
                "end_time": slot["end"],
                "subject_id": None,
                "subject_code": "",
                "subject_name": "Free / Self Study",
                "faculty_id": None,
                "faculty_name": "Unassigned",
                "classroom_id": None,
                "room_number": "TBA",
                "status": "Upcoming",
                "is_uncertain": False,
                "confidence": 1.0,
                "raw_cell": cell_text or "Free",
            }

        # Tokenize cell by separators: '/', '-', ',', '(', ')', '[', ']'
        tokens = [t.strip() for t in re.split(r"[/,()\[\]\-]", cell_text) if t.strip()]

        matched_subject = None
        matched_faculty = None
        matched_room = None

        # 1. Match Subject
        for token in tokens:
            t_upper = token.upper()
            for s in self.subjects:
                if s.code.upper() in t_upper or t_upper in s.code.upper() or s.name.lower() in token.lower():
                    matched_subject = s
                    break
            if matched_subject:
                break

        # 2. Match Faculty
        for token in tokens:
            t_upper = token.upper()
            for f in self.faculty:
                if f.faculty_id.upper() in t_upper or (f.user and f.user.full_name.lower() in token.lower()):
                    matched_faculty = f
                    break
            if matched_faculty:
                break

        # 3. Match Classroom
        for token in tokens:
            t_upper = token.upper()
            for r in self.classrooms:
                if r.room_number.upper() == t_upper or r.room_number.upper().replace("-", "") == t_upper.replace("-", ""):
                    matched_room = r
                    break
            if matched_room:
                break

        # Fallback assignment from known lists if not exact
        if not matched_subject and self.subjects:
            # Check partial match on raw cell
            for s in self.subjects:
                if s.code.lower() in cell_text.lower():
                    matched_subject = s
                    break

        if not matched_faculty and self.faculty:
            for f in self.faculty:
                if f.faculty_id.lower() in cell_text.lower():
                    matched_faculty = f
                    break

        if not matched_room and self.classrooms:
            for r in self.classrooms:
                if r.room_number.lower() in cell_text.lower():
                    matched_room = r
                    break

        if not matched_subject or not matched_faculty or not matched_room:
            is_uncertain = True
            confidence = 0.6

        return {
            "day": day,
            "period": slot["period"],
            "start_time": slot["start"],
            "end_time": slot["end"],
            "subject_id": matched_subject.id if matched_subject else None,
            "subject_code": matched_subject.code if matched_subject else "",
            "subject_name": matched_subject.name if matched_subject else (tokens[0] if tokens else "Uncertain"),
            "faculty_id": matched_faculty.id if matched_faculty else None,
            "faculty_name": matched_faculty.full_name if matched_faculty else "Unassigned",
            "classroom_id": matched_room.id if matched_room else None,
            "room_number": matched_room.room_number if matched_room else "TBA",
            "status": "Upcoming",
            "is_uncertain": is_uncertain,
            "confidence": confidence,
            "raw_cell": cell_text,
        }

    def _generate_default_grid(self, uncertain=False):
        """Generates a regular weekly grid of period slots for all days."""
        grid = []
        for day in DAYS_OF_WEEK:
            for slot in DEFAULT_PERIOD_SLOTS:
                grid.append({
                    "day": day,
                    "period": slot["period"],
                    "start_time": slot["start"],
                    "end_time": slot["end"],
                    "subject_id": self.subjects[0].id if self.subjects else None,
                    "subject_code": self.subjects[0].code if self.subjects else "",
                    "subject_name": self.subjects[0].name if self.subjects else "Select Subject",
                    "faculty_id": self.faculty[0].id if self.faculty else None,
                    "faculty_name": self.faculty[0].full_name if self.faculty else "Select Faculty",
                    "classroom_id": self.classrooms[0].id if self.classrooms else None,
                    "room_number": self.classrooms[0].room_number if self.classrooms else "Select Room",
                    "status": "Upcoming",
                    "is_uncertain": uncertain,
                    "confidence": 0.5 if uncertain else 1.0,
                    "raw_cell": "",
                })
        return grid
