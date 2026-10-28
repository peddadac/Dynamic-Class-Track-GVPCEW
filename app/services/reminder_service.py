"""Upcoming class reminder service with background scheduler and duplicate prevention."""

import logging
from datetime import datetime, date, timedelta, time
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None
from app.extensions import db
from app.models.timetable import TimetableEntry, TimetableVersion
from app.models.academic import StudentProfile
from app.models.notification import Notification
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


def check_and_send_class_reminders(app=None):
    """
    Scans for classes starting within reminder thresholds (15 min) and dispatches reminders.
    Ensures idempotency so users don't receive duplicate reminders on the same day.
    """
    if app:
        with app.app_context():
            _run_reminder_scan(app)
    else:
        _run_reminder_scan()


def _run_reminder_scan(app=None):
    tz_str = "Asia/Kolkata"
    if app:
        tz_str = app.config.get("TIMEZONE", "Asia/Kolkata")
    
    try:
        if ZoneInfo:
            tz = ZoneInfo(tz_str)
            now_local = datetime.now(tz)
        else:
            now_local = datetime.now()
    except Exception:
        now_local = datetime.now()

    today_day = now_local.strftime("%A")  # Monday, Tuesday, ...
    current_time = now_local.time()
    today_date = now_local.date()

    # Query published entries for today
    entries = (
        TimetableEntry.query.join(TimetableVersion)
        .filter(
            TimetableVersion.status == "published",
            TimetableEntry.day_of_week == today_day,
            TimetableEntry.status != "Cancelled",
        )
        .all()
    )

    reminders_sent = 0

    for entry in entries:
        # Calculate time difference between now and entry start_time
        entry_dt = datetime.combine(today_date, entry.start_time)
        now_dt = datetime.combine(today_date, current_time)
        diff_minutes = (entry_dt - now_dt).total_seconds() / 60.0

        # If class starts between 0 and 15 minutes from now
        if 0 <= diff_minutes <= 15:
            mins_rounded = max(1, int(round(diff_minutes)))
            subj_name = entry.subject.name if entry.subject else "Class"
            room_no = entry.classroom.room_number if entry.classroom else "TBA"
            sec = entry.version.section
            br = entry.version.branch.code if entry.version.branch else ""
            title = f"Upcoming Class Reminder: {subj_name}"
            message = (
                f"Reminder: {subj_name} ({br}-{sec.name}) starts in ~{mins_rounded} minutes "
                f"at {entry.start_time.strftime('%I:%M %p')} in Room {room_no}."
            )

            # Target users: assigned faculty + students in section
            target_user_ids = set()
            if entry.faculty and entry.faculty.user_id:
                target_user_ids.add(entry.faculty.user_id)

            if sec:
                students = StudentProfile.query.filter_by(
                    section_id=sec.id,
                    branch_id=entry.version.branch_id,
                    is_active=True,
                ).all()
                for s in students:
                    if s.user_id:
                        target_user_ids.add(s.user_id)

            for uid in target_user_ids:
                # Idempotency check: did we already send a reminder today for this entry to this user?
                start_of_day = datetime.combine(today_date, time.min)
                existing = (
                    Notification.query.filter(
                        Notification.user_id == uid,
                        Notification.related_entry_id == entry.id,
                        Notification.notification_type == "class_reminder",
                        Notification.created_at >= start_of_day,
                    ).first()
                )
                if not existing:
                    NotificationService.create_notification(
                        user_id=uid,
                        title=title,
                        message=message,
                        notification_type="class_reminder",
                        related_entry_id=entry.id,
                    )
                    reminders_sent += 1

    if reminders_sent > 0:
        logger.info(f"Dispatched {reminders_sent} upcoming class reminders.")
    return reminders_sent


def init_scheduler(app):
    """Initializes APScheduler background job for periodic reminders."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler(daemon=True)
        scheduler.add_job(
            func=check_and_send_class_reminders,
            args=[app],
            trigger="interval",
            minutes=2,
            id="class_reminders_job",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("APScheduler background class reminders job initialized.")
        return scheduler
    except Exception as e:
        logger.warning(f"Could not initialize APScheduler: {e}")
        return None
