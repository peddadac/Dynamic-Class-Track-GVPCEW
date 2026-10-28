"""Faculty Portal routes for personal schedule, cross-branch teaching, and class updates."""

from datetime import datetime, date, time
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.auth.decorators import faculty_required
from app.models.timetable import TimetableEntry, TimetableVersion
from app.models.academic import FacultyProfile
from app.models.notification import Notification
from app.services.timetable_parser import DAYS_OF_WEEK, DEFAULT_PERIOD_SLOTS

faculty_bp = Blueprint("faculty", __name__, url_prefix="/faculty")


@faculty_bp.before_request
@login_required
@faculty_required
def require_faculty():
    """Ensure all faculty routes require authenticated faculty account."""
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
    """
    Computes class status dynamically based on day and current time:
    - Cancelled: if marked Cancelled in db
    - Ongoing: if today is entry.day_of_week and start_time <= now_time <= end_time
    - Completed: if today is entry.day_of_week and now_time > end_time
    - Upcoming: if today is entry.day_of_week and now_time < start_time
    """
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


@faculty_bp.route("/dashboard")
def dashboard():
    faculty_profile = current_user.faculty_profile
    if not faculty_profile:
        flash("Faculty profile not associated with this account.", "danger")
        return redirect(url_for("main.index"))

    now_local = get_current_local_time()
    today_day = now_local.strftime("%A")
    now_time = now_local.time()
    today_display = now_local.strftime("%A, %B %d, %Y")

    # Fetch ALL published entries assigned to this faculty across ALL branches & sections
    all_assigned_query = (
        TimetableEntry.query.join(TimetableVersion)
        .filter(
            TimetableVersion.status == "published",
            TimetableEntry.faculty_id == faculty_profile.id,
        )
    )

    # Today's classes sorted by period / start_time
    today_classes = (
        all_assigned_query.filter(TimetableEntry.day_of_week == today_day)
        .order_by(TimetableEntry.start_time)
        .all()
    )

    current_class = None
    next_class = None
    remaining_count = 0

    classes_with_status = []
    for c in today_classes:
        status = compute_class_status(c, today_day, now_time)
        classes_with_status.append({"entry": c, "dynamic_status": status})

        if status == "Ongoing":
            current_class = c
        elif status == "Upcoming":
            remaining_count += 1
            if not next_class:
                next_class = c

    # Notifications
    unread_notifications = (
        Notification.query.filter_by(user_id=current_user.id, is_read=False)
        .order_by(Notification.created_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "faculty/dashboard.html",
        faculty=faculty_profile,
        today_date=today_display,
        today_classes=classes_with_status,
        current_class=current_class,
        next_class=next_class,
        remaining_count=remaining_count,
        notifications=unread_notifications,
    )


@faculty_bp.route("/schedule")
def schedule():
    """Full weekly schedule across all branches and sections with optional day filter."""
    faculty_profile = current_user.faculty_profile
    day_filter = request.args.get("day")

    query = (
        TimetableEntry.query.join(TimetableVersion)
        .filter(
            TimetableVersion.status == "published",
            TimetableEntry.faculty_id == faculty_profile.id,
        )
    )

    if day_filter and day_filter in DAYS_OF_WEEK:
        query = query.filter(TimetableEntry.day_of_week == day_filter)

    entries = query.order_by(TimetableEntry.day_of_week, TimetableEntry.start_time).all()

    # Organize entries into weekly grid by day & period
    weekly_grid = {day: [] for day in DAYS_OF_WEEK}
    for e in entries:
        weekly_grid.setdefault(e.day_of_week, []).append(e)

    now_local = get_current_local_time()
    today_day = now_local.strftime("%A")

    return render_template(
        "faculty/schedule.html",
        faculty=faculty_profile,
        weekly_grid=weekly_grid,
        days=DAYS_OF_WEEK,
        active_day=day_filter or "all",
        today_day=today_day,
        periods=DEFAULT_PERIOD_SLOTS,
    )


@faculty_bp.route("/notifications")
def notifications():
    all_notifs = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    return render_template("faculty/notifications.html", notifications=all_notifs)


@faculty_bp.route("/notifications/mark-read/<int:notif_id>", methods=["POST"])
def mark_notification_read(notif_id):
    notif = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first_or_404()
    notif.is_read = True
    notif.read_at = datetime.utcnow()
    db.session.commit()
    flash("Notification marked as read.", "success")
    return redirect(url_for("faculty.notifications"))


@faculty_bp.route("/notifications/mark-all-read", methods=["POST"])
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update(
        {Notification.is_read: True, Notification.read_at: datetime.utcnow()}
    )
    db.session.commit()
    flash("All notifications marked as read.", "info")
    return redirect(url_for("faculty.notifications"))
