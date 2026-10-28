"""Timetable conflict validation service for detecting room, faculty, and section overlapping schedules."""

from datetime import datetime, time
from app.models.timetable import TimetableEntry, TimetableVersion
from app.models.academic import Section, FacultyProfile
from app.models.classroom import Classroom


class TimetableConflictValidator:
    """Validates timetable entries against database constraints and overlapping schedules."""

    @staticmethod
    def parse_time(time_val):
        """Converts string 'HH:MM' or datetime.time object to datetime.time."""
        if isinstance(time_val, time):
            return time_val
        if isinstance(time_val, str):
            parts = time_val.strip().split(":")
            return time(int(parts[0]), int(parts[1]))
        return None

    @classmethod
    def times_overlap(cls, start1, end1, start2, end2):
        """Checks if two time intervals overlap (start1 < end2 and start2 < end1)."""
        s1 = cls.parse_time(start1)
        e1 = cls.parse_time(end1)
        s2 = cls.parse_time(start2)
        e2 = cls.parse_time(end2)
        if not (s1 and e1 and s2 and e2):
            return False
        return s1 < e2 and s2 < e1

    @classmethod
    def validate_single_entry(cls, entry_data, exclude_entry_id=None, version_id=None):
        """
        Validates an individual timetable entry against existing published timetables.
        entry_data dict keys:
          - day_of_week
          - specific_date (optional)
          - start_time
          - end_time
          - classroom_id
          - faculty_id
          - section_id (or inferred from version)
        Returns: list of conflict message strings.
        """
        conflicts = []
        day = entry_data.get("day_of_week") or entry_data.get("day")
        start_t = cls.parse_time(entry_data.get("start_time"))
        end_t = cls.parse_time(entry_data.get("end_time"))
        room_id = entry_data.get("classroom_id")
        faculty_id = entry_data.get("faculty_id")
        section_id = entry_data.get("section_id")

        if not start_t or not end_t:
            conflicts.append("Start time and end time are required.")
            return conflicts

        if start_t >= end_t:
            conflicts.append(f"Invalid class timing: Start time ({start_t}) must be earlier than end time ({end_t}).")

        # Query existing published entries for the same day
        query = (
            TimetableEntry.query.join(TimetableVersion)
            .filter(
                TimetableVersion.status == "published",
                TimetableEntry.day_of_week == day,
                TimetableEntry.status != "Cancelled",
            )
        )

        if exclude_entry_id:
            query = query.filter(TimetableEntry.id != exclude_entry_id)

        published_entries = query.all()

        for ex in published_entries:
            # Check time overlap
            if not cls.times_overlap(start_t, end_t, ex.start_time, ex.end_time):
                continue

            # 1. Classroom conflict
            if room_id and ex.classroom_id == room_id:
                room_no = ex.classroom.room_number if ex.classroom else f"ID {room_id}"
                sec_name = ex.version.section.display_name if ex.version and ex.version.section else "Another section"
                conflicts.append(
                    f"Classroom Conflict: Room {room_no} is already booked on {day} ({ex.start_time.strftime('%I:%M %p')}-{ex.end_time.strftime('%I:%M %p')}) by {sec_name}."
                )

            # 2. Faculty conflict
            if faculty_id and ex.faculty_id == faculty_id:
                fac_name = ex.faculty.full_name if ex.faculty else f"Faculty ID {faculty_id}"
                sec_name = ex.version.section.display_name if ex.version and ex.version.section else "Another section"
                conflicts.append(
                    f"Faculty Conflict: {fac_name} is already assigned on {day} ({ex.start_time.strftime('%I:%M %p')}-{ex.end_time.strftime('%I:%M %p')}) to {sec_name}."
                )

            # 3. Section conflict (if section is same)
            if section_id and ex.version and ex.version.section_id == section_id:
                conflicts.append(
                    f"Section Conflict: Section already has another class scheduled on {day} ({ex.start_time.strftime('%I:%M %p')}-{ex.end_time.strftime('%I:%M %p')})."
                )

        return conflicts

    @classmethod
    def validate_timetable_grid(cls, entries_list, section_id=None, exclude_version_id=None):
        """
        Validates an entire batch of timetable entries (e.g., during OCR review or publication).
        Checks:
        1. Internal conflicts within the batch (e.g. 2 classes scheduled at same time in same room)
        2. External conflicts against other published timetables
        Returns: (is_valid, list_of_conflicts)
        """
        all_conflicts = []

        # 1. Internal conflict check between entries in this batch
        for i in range(len(entries_list)):
            e1 = entries_list[i]
            day1 = e1.get("day_of_week") or e1.get("day")
            s1 = cls.parse_time(e1.get("start_time"))
            e_t1 = cls.parse_time(e1.get("end_time"))
            room1 = e1.get("classroom_id")
            fac1 = e1.get("faculty_id")

            if s1 and e_t1 and s1 >= e_t1:
                all_conflicts.append(f"Entry {i+1} on {day1}: Start time ({s1}) must be earlier than end time ({e_t1}).")

            for j in range(i + 1, len(entries_list)):
                e2 = entries_list[j]
                day2 = e2.get("day_of_week") or e2.get("day")
                if day1 != day2:
                    continue

                s2 = cls.parse_time(e2.get("start_time"))
                e_t2 = cls.parse_time(e2.get("end_time"))

                if cls.times_overlap(s1, e_t1, s2, e_t2):
                    # Check section overlap
                    all_conflicts.append(
                        f"Internal Section Overlap on {day1}: Multiple classes scheduled at {s1.strftime('%H:%M')}-{e_t1.strftime('%H:%M')} and {s2.strftime('%H:%M')}-{e_t2.strftime('%H:%M')}."
                    )
                    # Check room overlap
                    if room1 and room1 == e2.get("classroom_id"):
                        all_conflicts.append(
                            f"Internal Room Conflict on {day1}: Multiple classes assigned to same classroom at overlapping times."
                        )
                    # Check faculty overlap
                    if fac1 and fac1 == e2.get("faculty_id"):
                        all_conflicts.append(
                            f"Internal Faculty Conflict on {day1}: Faculty assigned to multiple simultaneous classes."
                        )

        # 2. External conflict check against published timetables
        for idx, entry in enumerate(entries_list):
            entry_copy = dict(entry)
            if section_id:
                entry_copy["section_id"] = section_id
            ext_conflicts = cls.validate_single_entry(entry_copy)
            for c in ext_conflicts:
                all_conflicts.append(f"Row {idx+1} ({entry_copy.get('day')} P{entry_copy.get('period', '')}): {c}")

        is_valid = len(all_conflicts) == 0
        return is_valid, all_conflicts
