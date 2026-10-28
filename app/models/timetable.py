"""Timetable models: TimetableVersion, TimetableEntry, UploadedTimetableImage, and RoomChangeHistory."""

from datetime import datetime, date, time
from app.extensions import db


class TimetableVersion(db.Model):
    __tablename__ = "timetable_versions"

    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False)
    academic_year_id = db.Column(db.Integer, db.ForeignKey("academic_years.id"), nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey("semesters.id"), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey("sections.id"), nullable=False)
    version_number = db.Column(db.Integer, default=1, nullable=False)
    status = db.Column(db.String(20), default="draft", nullable=False, index=True)  # draft, published, archived
    timetable_type = db.Column(db.String(20), default="regular", nullable=False)     # regular, override
    effective_date = db.Column(db.Date, default=date.today, nullable=False)
    expiry_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.String(255), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    approved_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    branch = db.relationship("Branch", back_populates="timetable_versions")
    academic_year = db.relationship("AcademicYear", back_populates="timetable_versions")
    semester = db.relationship("Semester", back_populates="timetable_versions")
    section = db.relationship("Section", back_populates="timetable_versions")
    created_by = db.relationship("User", foreign_keys=[created_by_id])
    entries = db.relationship("TimetableEntry", back_populates="version", cascade="all, delete-orphan", order_by="TimetableEntry.period_number")
    uploaded_image = db.relationship("UploadedTimetableImage", back_populates="timetable_version", uselist=False)

    @property
    def is_published(self):
        return self.status == "published"

    @property
    def title(self):
        sec = self.section.name if self.section else ""
        br = self.branch.code if self.branch else ""
        sem = self.semester.number if self.semester else ""
        return f"{br} Sem {sem} - Sec {sec} (v{self.version_number})"

    def __repr__(self):
        return f"<TimetableVersion {self.id}: {self.title} [{self.status}]>"


class TimetableEntry(db.Model):
    __tablename__ = "timetable_entries"

    id = db.Column(db.Integer, primary_key=True)
    timetable_version_id = db.Column(db.Integer, db.ForeignKey("timetable_versions.id"), nullable=False, index=True)
    day_of_week = db.Column(db.String(15), nullable=False, index=True)  # Monday, Tuesday, ...
    specific_date = db.Column(db.Date, nullable=True, index=True)       # For date-specific overrides
    period_number = db.Column(db.Integer, nullable=False)               # 1, 2, 3...
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculty_profiles.id"), nullable=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey("classrooms.id"), nullable=True)
    status = db.Column(db.String(20), default="Upcoming", nullable=False)  # Upcoming, Ongoing, Completed, Cancelled
    notes = db.Column(db.String(255), nullable=True)
    is_uncertain = db.Column(db.Boolean, default=False, nullable=False)    # Flagged by OCR for review
    confidence_score = db.Column(db.Float, default=1.0, nullable=False)

    # Relationships
    version = db.relationship("TimetableVersion", back_populates="entries")
    subject = db.relationship("Subject", back_populates="timetable_entries")
    faculty = db.relationship("FacultyProfile", back_populates="timetable_entries")
    classroom = db.relationship("Classroom", back_populates="timetable_entries")
    room_changes = db.relationship("RoomChangeHistory", back_populates="timetable_entry", cascade="all, delete-orphan", order_by="desc(RoomChangeHistory.change_timestamp)")

    @property
    def time_range_display(self):
        s = self.start_time.strftime("%I:%M %p") if self.start_time else ""
        e = self.end_time.strftime("%I:%M %p") if self.end_time else ""
        return f"{s} - {e}"

    @property
    def current_status(self):
        """Dynamic status based on today's time if class is today."""
        return self.status

    def to_dict(self):
        return {
            "id": self.id,
            "version_id": self.timetable_version_id,
            "day": self.day_of_week,
            "specific_date": self.specific_date.isoformat() if self.specific_date else None,
            "period": self.period_number,
            "start_time": self.start_time.strftime("%H:%M") if self.start_time else "",
            "end_time": self.end_time.strftime("%H:%M") if self.end_time else "",
            "time_range": self.time_range_display,
            "subject_id": self.subject_id,
            "subject_name": self.subject.name if self.subject else "Unassigned",
            "subject_code": self.subject.code if self.subject else "",
            "faculty_id": self.faculty_id,
            "faculty_name": self.faculty.full_name if self.faculty else "Unassigned",
            "classroom_id": self.classroom_id,
            "room_number": self.classroom.room_number if self.classroom else "TBA",
            "status": self.status,
            "is_uncertain": self.is_uncertain,
            "notes": self.notes or "",
        }

    def __repr__(self):
        return f"<TimetableEntry {self.day_of_week} P{self.period_number} Subj={self.subject_id}>"


class UploadedTimetableImage(db.Model):
    __tablename__ = "uploaded_timetable_images"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, default=0, nullable=False)
    mime_type = db.Column(db.String(100), default="image/png", nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False)
    academic_year_id = db.Column(db.Integer, db.ForeignKey("academic_years.id"), nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey("semesters.id"), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey("sections.id"), nullable=False)
    timetable_version_id = db.Column(db.Integer, db.ForeignKey("timetable_versions.id"), nullable=True)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status = db.Column(db.String(30), default="uploaded", nullable=False)  # uploaded, processing, parsed, reviewed, failed
    extracted_raw_text = db.Column(db.Text, nullable=True)
    extracted_json = db.Column(db.Text, nullable=True)
    error_message = db.Column(db.Text, nullable=True)

    # Relationships
    branch = db.relationship("Branch")
    academic_year = db.relationship("AcademicYear")
    semester = db.relationship("Semester")
    section = db.relationship("Section")
    uploaded_by = db.relationship("User", foreign_keys=[uploaded_by_id])
    timetable_version = db.relationship("TimetableVersion", back_populates="uploaded_image")

    def __repr__(self):
        return f"<UploadedTimetableImage {self.id}: {self.filename} [{self.status}]>"


class RoomChangeHistory(db.Model):
    __tablename__ = "room_change_histories"

    id = db.Column(db.Integer, primary_key=True)
    timetable_entry_id = db.Column(db.Integer, db.ForeignKey("timetable_entries.id"), nullable=False, index=True)
    old_classroom_id = db.Column(db.Integer, db.ForeignKey("classrooms.id"), nullable=False)
    new_classroom_id = db.Column(db.Integer, db.ForeignKey("classrooms.id"), nullable=False)
    changed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    change_timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    reason = db.Column(db.String(255), nullable=True)
    effective_date = db.Column(db.Date, default=date.today, nullable=False)

    # Relationships
    timetable_entry = db.relationship("TimetableEntry", back_populates="room_changes")
    old_classroom = db.relationship("Classroom", foreign_keys=[old_classroom_id])
    new_classroom = db.relationship("Classroom", foreign_keys=[new_classroom_id])
    changed_by = db.relationship("User", foreign_keys=[changed_by_id])

    def __repr__(self):
        return f"<RoomChangeHistory Entry={self.timetable_entry_id} {self.old_classroom_id}->{self.new_classroom_id}>"
