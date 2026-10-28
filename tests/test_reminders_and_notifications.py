"""Tests for Upcoming Class Reminders, Duplicate Prevention, Notification State, and Timezones."""

from datetime import datetime, date, time, timedelta
from app.extensions import db
from app.models.user import User
from app.models.academic import Branch, Section, Subject, FacultyProfile, StudentProfile
from app.models.classroom import Classroom
from app.models.timetable import TimetableVersion, TimetableEntry
from app.models.notification import Notification
from app.services.reminder_service import _run_reminder_scan


def test_17_and_18_upcoming_class_reminders_and_duplicate_prevention(app):
    """Req 17 & 18: Reminders generated for classes within 15 min, duplicate reminders prevented."""
    with app.app_context():
        b_cse = Branch.query.filter_by(code="CSE").first()
        sec_a = Section.query.filter_by(name="A", branch_id=b_cse.id).first()
        sub = Subject.query.filter_by(code="CS501").first()
        fac = FacultyProfile.query.filter_by(faculty_id="GVP-FAC-01").first()
        room = Classroom.query.filter_by(room_number="C-204").first()

        now = datetime.now()
        today_name = now.strftime("%A")
        # Class starting 10 minutes from now
        start_t = (now + timedelta(minutes=10)).time()
        end_t = (now + timedelta(minutes=60)).time()

        v = TimetableVersion(branch_id=b_cse.id, academic_year_id=sec_a.academic_year_id, semester_id=sec_a.semester_id, section_id=sec_a.id, status="published")
        db.session.add(v)
        db.session.flush()

        entry = TimetableEntry(timetable_version_id=v.id, day_of_week=today_name, period_number=1, start_time=start_t, end_time=end_t, subject_id=sub.id, faculty_id=fac.id, classroom_id=room.id)
        db.session.add(entry)
        db.session.commit()

        # First reminder run
        sent_first = _run_reminder_scan(app)
        assert sent_first > 0

        # Check reminder created for faculty and student
        fac_rem = Notification.query.filter_by(user_id=fac.user_id, notification_type="class_reminder").first()
        assert fac_rem is not None
        assert "Upcoming Class Reminder" in fac_rem.title

        # Req 18: Second reminder run must NOT send duplicate alerts
        sent_second = _run_reminder_scan(app)
        assert sent_second == 0


def test_19_notification_read_unread_state(client):
    """Req 19: Notification read/unread state changes properly."""
    st_user = User.query.filter_by(username="student_sneha").first()

    notif = Notification(
        user_id=st_user.id,
        title="Test Notification",
        message="Checking read state",
        notification_type="general",
        is_read=False,
    )
    db.session.add(notif)
    db.session.commit()

    assert notif.is_read is False

    # Log in as student
    client.post("/login", data={"username_or_email": "student_sneha", "password": "Student@123", "role": "student"})

    # Mark as read
    res = client.post(f"/student/notifications/mark-read/{notif.id}", follow_redirects=True)
    assert res.status_code == 200

    db.session.refresh(notif)
    assert notif.is_read is True
    assert notif.read_at is not None


def test_23_timezone_handling(app):
    """Req 23: Timetable uses college's configured timezone (Asia/Kolkata)."""
    assert app.config.get("TIMEZONE") == "Asia/Kolkata"
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("Asia/Kolkata")
        kolkata_now = datetime.now(tz)
        assert kolkata_now.tzinfo is not None
    except ImportError:
        pass
