"""Student Portal routes strictly restricted to the authenticated student's assigned section."""

from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.auth.decorators import student_required
from app.models.timetable import TimetableEntry, TimetableVersion
from app.models.notification import Notification
from app.services.timetable_parser import DAYS_OF_WEEK, DEFAULT_PERIOD_SLOTS

student_bp = Blueprint("student", __name__, url_prefix="/student")


@student_bp.before_request
@login_required
@student_required
def require_student():
    """Ensure all student routes strictly require authenticated student role."""
    pass


def get_current_local_time():
    tz_str = current_app.config.get("TIMEZONE", "Asia/Kolkata")
    try:
        if ZoneInfo:
            return datetime.now(ZoneInfo(tz_str))
        return datetime.now()
    except Exception:
        return datetime.now()


def compute_class_status(entry, current_day, now_time):
    if entry.status == "Cancelled":
        return "Cancelled"
    if entry.day_of_week == current_day:
        if entry.start_time <= now_time <= entry.end_time:
            return "Ongoing"
        elif now_time > entry.end_time:
            return "Completed"
        else:
            return "Upcoming"
    return "Upcoming"


@student_bp.route("/dashboard")
def dashboard():
    student_profile = current_user.student_profile
    if not student_profile:
        flash("Student profile not found for this account.", "danger")
        return redirect(url_for("main.index"))

    # Active published timetable strictly for this student's section
    active_version = (
        TimetableVersion.query.filter_by(
            section_id=student_profile.section_id,
            status="published",
        )
        .order_by(TimetableVersion.version_number.desc())
        .first()
    )

    now_local = get_current_local_time()
    today_day = now_local.strftime("%A")
    now_time = now_local.time()
    today_display = now_local.strftime("%A, %B %d, %Y")

    today_classes_with_status = []
    current_class = None
    next_class = None
    remaining_count = 0

    if active_version:
        today_entries = (
            TimetableEntry.query.filter_by(
                timetable_version_id=active_version.id,
                day_of_week=today_day,
            )
            .order_by(TimetableEntry.start_time)
            .all()
        )

        for e in today_entries:
            st = compute_class_status(e, today_day, now_time)
            today_classes_with_status.append({"entry": e, "dynamic_status": st})

            if st == "Ongoing":
                current_class = e
            elif st == "Upcoming":
                remaining_count += 1
                if not next_class:
                    next_class = e

    unread_notifications = (
        Notification.query.filter_by(user_id=current_user.id, is_read=False)
        .order_by(Notification.created_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "student/dashboard.html",
        student=student_profile,
        version=active_version,
        today_date=today_display,
        today_classes=today_classes_with_status,
        current_class=current_class,
        next_class=next_class,
        remaining_count=remaining_count,
        notifications=unread_notifications,
    )


@student_bp.route("/schedule")
def schedule():
    """Full weekly timetable for this student's assigned section."""
    student_profile = current_user.student_profile
    active_version = (
        TimetableVersion.query.filter_by(
            section_id=student_profile.section_id,
            status="published",
        )
        .order_by(TimetableVersion.version_number.desc())
        .first()
    )

    weekly_grid = {day: {} for day in DAYS_OF_WEEK}
    if active_version:
        for entry in active_version.entries:
            weekly_grid.setdefault(entry.day_of_week, {})[entry.period_number] = entry

    now_local = get_current_local_time()
    today_day = now_local.strftime("%A")

    return render_template(
        "student/schedule.html",
        student=student_profile,
        version=active_version,
        weekly_grid=weekly_grid,
        days=DAYS_OF_WEEK,
        periods=DEFAULT_PERIOD_SLOTS,
        today_day=today_day,
    )


@student_bp.route("/notifications")
def notifications():
    all_notifs = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    return render_template("student/notifications.html", notifications=all_notifs)


@student_bp.route("/notifications/mark-read/<int:notif_id>", methods=["POST"])
def mark_notification_read(notif_id):
    notif = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first_or_404()
    notif.is_read = True
    notif.read_at = datetime.utcnow()
    db.session.commit()
    flash("Notification marked as read.", "success")
    return redirect(url_for("student.notifications"))


@student_bp.route("/notifications/mark-all-read", methods=["POST"])
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update(
        {Notification.is_read: True, Notification.read_at: datetime.utcnow()}
    )
    db.session.commit()
    flash("All notifications marked as read.", "info")
    return redirect(url_for("student.notifications"))
