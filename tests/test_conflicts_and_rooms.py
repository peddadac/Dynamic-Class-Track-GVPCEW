"""Tests for Conflict Validation, Classroom Changes, Targeted Alerts, and Audit History."""

from datetime import datetime, date, time
from app.extensions import db
from app.models.user import User
from app.models.academic import Branch, Section, Subject, FacultyProfile, StudentProfile
from app.models.classroom import Classroom
from app.models.timetable import TimetableVersion, TimetableEntry, RoomChangeHistory
from app.models.notification import Notification
from app.services.timetable_validation import TimetableConflictValidator


def test_12_and_13_conflict_validation_detects_room_and_faculty_clashes():
    """Req 12 & 13: Conflict validator detects room double-booking and simultaneous faculty assignments."""
    b_cse = Branch.query.filter_by(code="CSE").first()
    sec_a = Section.query.filter_by(name="A", branch_id=b_cse.id).first()
    sec_b = Section.query.filter_by(name="B", branch_id=b_cse.id).first()
    sub = Subject.query.filter_by(code="CS501").first()
    fac = FacultyProfile.query.filter_by(faculty_id="GVP-FAC-01").first()
    room = Classroom.query.filter_by(room_number="C-204").first()

    # Create published entry: Monday 09:00 - 09:50 in C-204 taught by fac
    v1 = TimetableVersion(branch_id=b_cse.id, academic_year_id=sec_a.academic_year_id, semester_id=sec_a.semester_id, section_id=sec_a.id, status="published")
    db.session.add(v1)
    db.session.flush()

    e1 = TimetableEntry(timetable_version_id=v1.id, day_of_week="Monday", period_number=1, start_time=time(9, 0), end_time=time(9, 50), subject_id=sub.id, faculty_id=fac.id, classroom_id=room.id)
    db.session.add(e1)
    db.session.commit()

    # 1. Test room clash: another section trying to book C-204 at overlapping time (09:20 - 10:10)
    clash_entry_room = {
        "day": "Monday",
        "start_time": "09:20",
        "end_time": "10:10",
        "classroom_id": room.id,
        "faculty_id": None,
        "section_id": sec_b.id,
    }
    conflicts_room = TimetableConflictValidator.validate_single_entry(clash_entry_room)
    assert any("Classroom Conflict" in c for c in conflicts_room)

    # 2. Test faculty clash: another section booking same faculty at overlapping time
    clash_entry_fac = {
        "day": "Monday",
        "start_time": "09:00",
        "end_time": "09:50",
        "classroom_id": None,
        "faculty_id": fac.id,
        "section_id": sec_b.id,
    }
    conflicts_fac = TimetableConflictValidator.validate_single_entry(clash_entry_fac)
    assert any("Faculty Conflict" in c for c in conflicts_fac)


def test_14_15_16_20_room_change_targeted_notifications_and_history(client):
    """
    Req 14: Room changes update correct entry.
    Req 15: Room changes generate alerts for affected faculty & students.
    Req 16: Unrelated users (e.g. students in Section B) DO NOT receive alerts.
    Req 20: Historical room changes remain stored in database.
    """
    client.post("/login", data={"username_or_email": "admin_test", "password": "Admin@123", "role": "admin"})

    b_cse = Branch.query.filter_by(code="CSE").first()
    sec_a = Section.query.filter_by(name="A", branch_id=b_cse.id).first()
    sub_ds = Subject.query.filter_by(code="CS501").first()
    fac = FacultyProfile.query.filter_by(faculty_id="GVP-FAC-01").first()
    r204 = Classroom.query.filter_by(room_number="C-204").first()
    r305 = Classroom.query.filter_by(room_number="C-305").first()

    # Published timetable for Section A
    v_a = TimetableVersion(branch_id=b_cse.id, academic_year_id=sec_a.academic_year_id, semester_id=sec_a.semester_id, section_id=sec_a.id, status="published")
    db.session.add(v_a)
    db.session.flush()

    entry = TimetableEntry(timetable_version_id=v_a.id, day_of_week="Monday", period_number=2, start_time=time(9, 50), end_time=time(10, 40), subject_id=sub_ds.id, faculty_id=fac.id, classroom_id=r204.id)
    db.session.add(entry)
    db.session.commit()

    # Admin changes classroom from C-204 to C-305
    res = client.post(
        "/admin/room-changes",
        data={
            "entry_id": entry.id,
            "new_classroom_id": r305.id,
            "reason": "Projector repair in progress",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200

    # Req 14: Check timetable entry updated
    updated_entry = TimetableEntry.query.get(entry.id)
    assert updated_entry.classroom_id == r305.id

    # Req 20: History record exists
    hist = RoomChangeHistory.query.filter_by(timetable_entry_id=entry.id).first()
    assert hist is not None
    assert hist.old_classroom_id == r204.id
    assert hist.new_classroom_id == r305.id
    assert "Projector repair" in hist.reason

    # Req 15: Affected faculty received notification
    notif_fac = Notification.query.filter_by(user_id=fac.user_id, related_entry_id=entry.id).first()
    assert notif_fac is not None
    assert "Classroom Change" in notif_fac.title
    assert "C-204" in notif_fac.message
    assert "C-305" in notif_fac.message

    # Req 15: Student in Section A (student_sneha) received notification
    st_sneha = User.query.filter_by(username="student_sneha").first()
    notif_st = Notification.query.filter_by(user_id=st_sneha.id, related_entry_id=entry.id).first()
    assert notif_st is not None
    assert "C-305" in notif_st.message

    # Req 16: Unrelated student in Section B (student_b) MUST NOT receive room change alert
    st_b = User.query.filter_by(username="student_b").first()
    notif_unrelated = Notification.query.filter_by(user_id=st_b.id, related_entry_id=entry.id).first()
    assert notif_unrelated is None
