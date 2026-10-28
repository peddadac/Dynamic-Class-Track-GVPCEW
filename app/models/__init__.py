"""Models package initialization exporting all domain models."""

from app.models.user import User
from app.models.academic import (
    Branch,
    AcademicYear,
    Semester,
    Section,
    Subject,
    FacultyProfile,
    StudentProfile,
)
from app.models.classroom import Classroom
from app.models.timetable import (
    TimetableVersion,
    TimetableEntry,
    UploadedTimetableImage,
    RoomChangeHistory,
)
from app.models.notification import Notification, PushSubscription
from app.models.audit import AuditLog

__all__ = [
    "User",
    "Branch",
    "AcademicYear",
    "Semester",
    "Section",
    "Subject",
    "FacultyProfile",
    "StudentProfile",
    "Classroom",
    "TimetableVersion",
    "TimetableEntry",
    "UploadedTimetableImage",
    "RoomChangeHistory",
    "Notification",
    "PushSubscription",
    "AuditLog",
]
