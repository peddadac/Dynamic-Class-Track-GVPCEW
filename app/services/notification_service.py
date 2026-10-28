"""Notification service: handles in-app database alerts, Socket.IO broadcast, and WebPush dispatch."""

import json
import logging
from datetime import datetime, date
from flask import current_app
from app.extensions import db, socketio
from app.models.notification import Notification, PushSubscription
from app.models.user import User
from app.models.academic import StudentProfile, FacultyProfile
from app.models.timetable import TimetableEntry

logger = logging.getLogger(__name__)


class NotificationService:
    """Manages creation, delivery, and real-time dispatch of notifications."""

    @classmethod
    def create_notification(cls, user_id, title, message, notification_type="general", related_entry_id=None):
        """
        Creates a database notification record, emits real-time Socket.IO event,
        and triggers Web Push if subscribed.
        """
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            related_entry_id=related_entry_id,
            delivery_status="delivered",
            created_at=datetime.utcnow(),
        )
        db.session.add(notif)
        db.session.commit()

        # Emit Socket.IO message to user-specific room
        try:
            payload = notif.to_dict()
            socketio.emit(
                "new_notification",
                payload,
                room=f"user_{user_id}",
            )
            # Also emit to global role channel for live dashboard updates
            user = User.query.get(user_id)
            if user:
                socketio.emit(f"{user.role}_update", payload, room=f"role_{user.role}")
        except Exception as e:
            logger.debug(f"SocketIO emission skipped/failed: {e}")

        # Send WebPush if configured and subscribed
        cls._send_web_push(user_id, title, message)
        return notif

    @classmethod
    def notify_room_change(cls, entry, old_room_name, new_room_name, reason=None):
        """
        Targeted notification for a classroom change.
        Only notifies the assigned faculty member and students in this specific section.
        """
        section = entry.version.section if entry.version else None
        branch_code = entry.version.branch.code if (entry.version and entry.version.branch) else ""
        sec_name = section.name if section else ""
        subj_name = entry.subject.name if entry.subject else "Class"
        time_str = entry.time_range_display

        title = f"Classroom Change: {subj_name} ({branch_code}-{sec_name})"
        message = (
            f"Classroom Change: {subj_name}, {branch_code}-{sec_name}, "
            f"Period {entry.period_number}, {time_str}. "
            f"Previous room: {old_room_name}. New room: {new_room_name}."
        )
        if reason:
            message += f" (Reason: {reason})"

        notified_user_ids = set()

        # 1. Notify the assigned faculty member
        if entry.faculty and entry.faculty.user_id:
            notified_user_ids.add(entry.faculty.user_id)
            cls.create_notification(
                user_id=entry.faculty.user_id,
                title=title,
                message=message,
                notification_type="room_change",
                related_entry_id=entry.id,
            )

        # 2. Notify all students belonging strictly to this section
        if section:
            students = (
                StudentProfile.query.filter_by(
                    section_id=section.id,
                    branch_id=entry.version.branch_id,
                    semester_id=entry.version.semester_id,
                    is_active=True,
                ).all()
            )
            for st in students:
                if st.user_id and st.user_id not in notified_user_ids:
                    notified_user_ids.add(st.user_id)
                    cls.create_notification(
                        user_id=st.user_id,
                        title=title,
                        message=message,
                        notification_type="room_change",
                        related_entry_id=entry.id,
                    )

        logger.info(f"Room change notification sent to {len(notified_user_ids)} users for Entry {entry.id}")
        return len(notified_user_ids)

    @classmethod
    def notify_timetable_published(cls, timetable_version):
        """Notifies faculty and students when a new timetable version is published."""
        sec = timetable_version.section
        branch = timetable_version.branch
        title = f"New Timetable Published: {branch.code} Sec {sec.name}"
        message = (
            f"The timetable for {branch.code} Semester {timetable_version.semester.number} "
            f"Section {sec.name} (v{timetable_version.version_number}) has been approved and published."
        )

        user_ids = set()

        # All students in section
        students = StudentProfile.query.filter_by(section_id=sec.id, is_active=True).all()
        for s in students:
            if s.user_id:
                user_ids.add(s.user_id)

        # All faculty teaching any entry in this timetable version
        for entry in timetable_version.entries:
            if entry.faculty and entry.faculty.user_id:
                user_ids.add(entry.faculty.user_id)

        for uid in user_ids:
            cls.create_notification(
                user_id=uid,
                title=title,
                message=message,
                notification_type="timetable_update",
            )
        return len(user_ids)

    @classmethod
    def _send_web_push(cls, user_id, title, message):
        """Delivers WebPush payload using pywebpush if subscriptions and VAPID keys exist."""
        try:
            from pywebpush import webpush, WebPushException
        except ImportError:
            return

        vapid_private = current_app.config.get("VAPID_PRIVATE_KEY")
        vapid_email = current_app.config.get("VAPID_CLAIM_EMAIL")
        if not (vapid_private and vapid_email):
            return

        subs = PushSubscription.query.filter_by(user_id=user_id).all()
        for sub in subs:
            subscription_info = {
                "endpoint": sub.endpoint,
                "keys": {"p256dh": sub.p256dh_key, "auth": sub.auth_key},
            }
            try:
                webpush(
                    subscription_info=subscription_info,
                    data=json.dumps({"title": title, "body": message, "icon": "/static/images/logo.png"}),
                    vapid_private_key=vapid_private,
                    vapid_claims={"sub": f"mailto:{vapid_email}"},
                )
            except Exception as e:
                logger.warning(f"Failed to deliver WebPush to subscription {sub.id}: {e}")
